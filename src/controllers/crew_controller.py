import logging
from typing import List, Optional, Type, Dict, Any
import os

from pydantic import BaseModel
from crewai.project import CrewBase
from crewai.flow.flow import Flow, listen, router, start

from src.common.openrouter_api import OpenRouterAPI
from src.viewers.navigator import Navigator

# --- Specialized Crew Imports ---
# Import all 9 specialized generator crews
from src.viewers.crews.osint_crew.crew import OSINTCrew
from src.viewers.crews.crypto_crew.crew import CryptoCrew
from src.viewers.crews.password_cracking_crew.crew import PasswordCrackingCrew
from src.viewers.crews.log_analysis_crew.crew import LogAnalysisCrew
from src.viewers.crews.traffic_analysis_crew.crew import TrafficAnalysisCrew
from src.viewers.crews.forensics_crew.crew import ForensicsCrew
from src.viewers.crews.recon_crew.crew import ReconCrew
from src.viewers.crews.web_exploit_crew.crew import WebExploitCrew
from src.viewers.crews.binary_exploit_crew.crew import BinaryExploitCrew

# The generic "Evaluator" Crew and its output Pydantic model
# (We assume this crew will be created at src/viewers/crews/analysis_review_crew/crew.py)
from src.viewers.crews.analysis_review_crew.crew import AnalysisReviewCrew, AnalysisVerification

logger = logging.getLogger(__name__)


# --- State Model for the Flow ---
class ModuleAnalysisState(BaseModel):
    """
    Pydantic state model to hold data for the module analysis flow.
    """
    # Input data from the crawler
    crawl_data: dict = {}

    # Intermediate data
    analysis: str = ""
    feedback: Optional[str] = None
    valid: bool = False
    retry_count: int = 0


# --- Self-Evaluation Flow Class (Now Generic) ---
class ModuleAnalysisFlow(Flow[ModuleAnalysisState]):
    """
    This Flow implements the self-evaluation loop for a single module.
    It uses the provided generator and evaluator crews, looping with
    feedback until the analysis is valid.
    """

    def __init__(self, generator_crew_class: Type[CrewBase], evaluator_crew_class: Type[CrewBase]):
        """
        Initializes the flow with specific crew classes.
        Args:
            generator_crew_class: The class of the crew to use for generating analysis.
            evaluator_crew_class: The class of the crew to use for evaluating analysis.
        """
        super().__init__()  # Initialize the base Flow class
        self.generator_crew_class = generator_crew_class
        self.evaluator_crew_class = evaluator_crew_class
        logger.info(
            f"ModuleAnalysisFlow initialized with {generator_crew_class.__name__} and {evaluator_crew_class.__name__}")

    @start("retry")
    def generate_analysis(self):
        """
        [Generator Step]
        Kicks off the assigned generator crew.
        """
        logger.info(
            f"Flow: Generating analysis using {self.generator_crew_class.__name__} (Attempt {self.state.retry_count + 1})...")
        module_name = self.state.crawl_data.get("module_name", "Unknown Module")
        crawl_data = self.state.crawl_data.get("crawl_data", {})

        # Instantiate the SPECIFIC generator crew passed during __init__
        generator_crew_instance = self.generator_crew_class()

        result = (
            generator_crew_instance.crew()
            .kickoff(inputs={
                "module_name": module_name,
                "crawl_data": crawl_data,
                "feedback": self.state.feedback
            })
        )
        self.state.analysis = result.raw
        logger.info(f"Flow: Analysis generated for {module_name}.")

    @router(generate_analysis)
    def evaluate_analysis(self):
        """
        [Evaluator Step]
        Kicks off the assigned evaluator crew.
        """
        if self.state.retry_count > 3:
            logger.warning("Flow: Max retry count exceeded.")
            return "max_retry_exceeded"

        logger.info(f"Flow: Evaluating analysis using {self.evaluator_crew_class.__name__}...")

        # Instantiate the SPECIFIC evaluator crew passed during __init__
        evaluator_crew_instance = self.evaluator_crew_class()

        # Assuming the evaluator crew takes 'analysis_text' and returns AnalysisVerification
        result: AnalysisVerification = (
            evaluator_crew_instance.crew()
            .kickoff(inputs={"analysis_text": self.state.analysis})
        )

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
        [Success Exit] Saves the validated analysis ticket.
        """
        logger.info("Flow: Analysis complete and validated. Saving ticket.")
        module_name = self.state.crawl_data.get("module_name", "unknown_module").replace(" ", "_").lower()
        filename = f"data/ticket_{module_name}.md"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.state.analysis)
        logger.info(f"Flow: Successfully saved ticket to {filename}")

    @listen("max_retry_exceeded")
    def log_failure(self):
        """
        [Failure Exit] Logs the failure.
        """
        module_name = self.state.crawl_data.get("module_name", "unknown_module")
        logger.error(f"Flow: Max retries exceeded for module '{module_name}'. Analysis could not be validated.")
        logger.error(f"Flow: Final invalid analysis: {self.state.analysis}")
        logger.error(f"Flow: Final feedback: {self.state.feedback}")


# --- Crew Selection Helper ---
def get_crew_for_module(module_name: str) -> Optional[Type[CrewBase]]:
    """
    Selects the appropriate specialized crew class based on the module name.
    Returns None if no specific crew matches.
    """
    # Normalize module name for matching (lowercase, remove plurals if needed)
    norm_name = module_name.lower().strip()

    # --- Mapping from keywords/names to Crew Classes ---
    # This dictionary acts as our factory selector
    crew_map = {
        "open source intelligence": OSINTCrew,
        "cryptography": CryptoCrew,
        "password cracking": PasswordCrackingCrew,
        "log analysis": LogAnalysisCrew,
        "network traffic analysis": TrafficAnalysisCrew,
        "forensics": ForensicsCrew,
        "scanning & reconnaissance": ReconCrew,
        "web application exploitation": WebExploitCrew,
        "enumeration & exploitation": BinaryExploitCrew,
    }

    # Find the matching crew
    for keyword, crew_class in crew_map.items():
        if keyword in norm_name:
            logger.info(f"Selected crew '{crew_class.__name__}' for module '{module_name}'")
            return crew_class

    logger.warning(f"No specialized crew found for module '{module_name}'. Cannot proceed with analysis.")
    return None


# --- Main Controller Class ---
class CrewController:
    def __init__(self):
        """
        Initializes the controller for managing agentic crews.
        """
        self.openrouter_api = OpenRouterAPI()
        logger.info("CrewController initialized.")

    async def organize_teams(self, navigator: Navigator, crawl_results: List[tuple]):
        """
        Asynchronously organize teams to process the pre-collected crawl_results.
        Selects the correct specialized crew for each module and runs the
        self-evaluation flow.
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

                logger.info(f"--- Processing module: {module_name} ---")

                # 1. Select the appropriate GENERATOR crew for this module
                generator_crew_class = get_crew_for_module(module_name)

                # Use the generic AnalysisReviewCrew as the EVALUATOR
                evaluator_crew_class = AnalysisReviewCrew

                if generator_crew_class is None:
                    # Skip if no specialized crew is found (e.g., for "Survey")
                    continue

                    # 2. Instantiate the self-evaluation flow WITH the selected crews
                analysis_flow = ModuleAnalysisFlow(
                    generator_crew_class=generator_crew_class,
                    evaluator_crew_class=evaluator_crew_class
                )

                # 3. Set the initial state with the crawler's data
                initial_state = ModuleAnalysisState(  # Directly instantiate the Pydantic model
                    crawl_data={
                        "module_name": module_name,
                        "crawl_data": results
                    }
                )

                # 4. Kick off the entire flow for this module
                final_state = analysis_flow.kickoff(state=initial_state)  # Pass state object

                logger.info(
                    f"--- Analysis flow for {module_name} complete. Final Valid Status: {final_state.valid} ---")

            logging.info(f"All processable modules ({len(crawl_results)}) have been analyzed by teams!")

        except Exception as e:
            logger.error(f"Team organization failed: {str(e)}", exc_info=True)
            raise