import logging
from typing import List, Optional
import os

from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, router, start

from src.common.openrouter_api import OpenRouterAPI
from src.viewers.navigator import Navigator

# --- Crew Imports ---
# The "Generator" Crew
from src.viewers.crews.research_crew import ResearchCrew
# The "Evaluator" Crew and its output Pydantic model
# (We assume this new crew will be created, following the example's pattern)
from src.viewers.crews.analysis_review_crew import AnalysisReviewCrew, AnalysisVerification

logger = logging.getLogger(__name__)


# --- State Model for the Flow ---
class ModuleAnalysisState(BaseModel):
    """
    Pydantic state model to hold data for the module analysis flow.
    This is passed between all steps of the self-evaluation loop.
    """
    # Input data from the crawler
    crawl_data: dict = {}

    # Intermediate data
    analysis: str = ""
    feedback: Optional[str] = None
    valid: bool = False
    retry_count: int = 0


# --- Self-Evaluation Flow Class ---
class ModuleAnalysisFlow(Flow[ModuleAnalysisState]):
    """
    This Flow implements the self-evaluation loop for a single module.
    It uses one crew to generate analysis and another to review it,
    looping with feedback until the analysis is valid.
    """

    @start("retry")
    def generate_analysis(self):
        """
        [Generator Step]
        Kicks off the ResearchCrew to generate the initial analysis
        for the module's crawl_data.
        """
        logger.info(f"Flow: Generating analysis (Attempt {self.state.retry_count + 1})...")

        # Get inputs from the flow's current state
        module_name = self.state.crawl_data.get("module_name", "Unknown Module")
        crawl_data = self.state.crawl_data.get("crawl_data", {})

        # Instantiate the generator crew
        research_crew = ResearchCrew()

        # Run the crew, passing in the crawl data and any feedback from a previous loop
        result = (
            research_crew.crew()
            .kickoff(inputs={
                "module_name": module_name,
                "crawl_data": crawl_data,
                "feedback": self.state.feedback
            })
        )

        # Save the crew's output back to the flow's state
        self.state.analysis = result.raw
        logger.info(f"Flow: Analysis generated for {module_name}.")

    @router(generate_analysis)
    def evaluate_analysis(self):
        """
        [Evaluator Step]
        Kicks off the AnalysisReviewCrew to validate the generated analysis.
        This step routes the flow to "complete" or back to "retry".
        """
        # Check for max retries first
        if self.state.retry_count > 3:
            logger.warning("Flow: Max retry count exceeded.")
            return "max_retry_exceeded"

        logger.info("Flow: Evaluating analysis...")

        # Instantiate the evaluator crew
        review_crew = AnalysisReviewCrew()

        # Run the evaluator crew, passing in the analysis for review
        # We expect it to return a pydantic object `AnalysisVerification`
        result: AnalysisVerification = (
            review_crew.crew()
            .kickoff(inputs={"analysis_text": self.state.analysis})
        )

        # Update the state with the review results
        self.state.valid = result.valid
        self.state.feedback = result.feedback
        self.state.retry_count += 1

        if self.state.valid:
            logger.info("Flow: Analysis is VALID. Completing.")
            return "complete"
        else:
            logger.warning(f"Flow: Analysis is INVALID. Retrying. Feedback: {self.state.feedback}")
            return "retry"

    @listen("complete")
    def save_final_analysis(self):
        """
        [Success Exit]
        Saves the validated analysis as a markdown "ticket" file.
        """
        logger.info("Flow: Analysis complete and validated. Saving ticket.")

        # Sanitize module name for filename
        module_name = self.state.crawl_data.get(
            "module_name", "unknown_module"
        ).replace(" ", "_").lower()

        filename = f"data/ticket_{module_name}.md"
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.state.analysis)

        logger.info(f"Flow: Successfully saved ticket to {filename}")

    @listen("max_retry_exceeded")
    def log_failure(self):
        """
        [Failure Exit]
        Logs the failure if the loop exits without a valid analysis.
        """
        logger.error(f"Flow: Max retries exceeded for module. Analysis could not be validated.")
        logger.error(f"Flow: Final invalid analysis: {self.state.analysis}")
        logger.error(f"Flow: Final feedback: {self.state.feedback}")


# --- Main Controller Class ---
class CrewController:
    def __init__(self):
        """
        Initializes the controller for managing agentic crews.
        """
        self.openrouter_api = OpenRouterAPI()
        # self.llm = self.openrouter_api.get_llm() # Ready for when crews need LLM
        logger.info("CrewController initialized.")

    async def organize_teams(self, navigator: Navigator, crawl_results: List[tuple]):
        """
        Asynchronously organize teams to process the pre-collected crawl_results.
        This function performs all data analysis and ticket generation.
        """
        logger.info("Starting team organization (data analysis)")
        if not crawl_results:
            logger.warning("No crawl results to organize. Stopping.")
            return

        try:
            # Loop through the results gathered by clone_site
            for module_name, results in crawl_results:
                if "error" in results:
                    logger.error(f"Skipping team for {module_name} due to crawl error: {results['error']}")
                    continue

                logger.info(f"--- Kicking off analysis flow for: {module_name} ---")

                # 1. Instantiate the self-evaluation flow for this module
                analysis_flow = ModuleAnalysisFlow()

                # 2. Set the initial state with the crawler's data
                initial_state = {
                    "crawl_data": {
                        "module_name": module_name,
                        "crawl_data": results
                    }
                }

                # 3. Kick off the entire flow. This will block until the
                #    flow either completes or fails, handling its own retries.
                final_state = analysis_flow.kickoff(initial_state)

                logger.info(f"--- Analysis flow for {module_name} complete. Valid: {final_state.valid} ---")

            logging.info(f"All {len(crawl_results)} modules have been processed by teams!")

        except Exception as e:
            logger.error(f"Team organization failed: {str(e)}", exc_info=True)
            raise