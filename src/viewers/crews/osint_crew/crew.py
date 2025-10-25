from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# Import necessary tools for OSINT, e.g., SerperDevTool or custom web search tools
# from crewai_tools import SerperDevTool
# from src.viewers.crews.tools.web_search_tools import BrowserTool # Example

# Assuming environment variables for tools like SERPER_API_KEY are set

@CrewBase
class OSINTCrew:
    """OSINTCrew gathers and analyzes open-source intelligence."""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def public_data_miner(self) -> Agent:
        """Agent that performs OSINT gathering and synthesis."""
        return Agent(
            config=self.agents_config['public_data_miner'],
            # Example Tools:
            # tools=[SerperDevTool(), BrowserTool()],
            verbose=True,
            allow_delegation=False # Usually OSINT tasks require focused searching
        )

    @agent
    def osint_validator(self) -> Agent:
        """Agent that validates the OSINT findings."""
        return Agent(
            config=self.agents_config['osint_validator'],
            verbose=True
        )

    @task
    def gather_osint_task(self) -> Task:
        """Task for the miner to gather and report OSINT."""
        # This task receives feedback context from the validator
        return Task(
            config=self.tasks_config['gather_osint_task'],
            agent=self.public_data_miner(),
            context=[self.validate_osint_task()] # Feedback context
        )

    @task
    def validate_osint_task(self) -> Task:
        """Task for the validator to review the OSINT report."""
        # Output Pydantic model is handled by the flow
        return Task(
            config=self.tasks_config['validate_osint_task'],
            agent=self.osint_validator(),
            context=[self.gather_osint_task()] # Needs the report to validate
        )

    @crew
    def crew(self) -> Crew:
        """Creates the OSINTCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential, # gather -> validate
            verbose=True,
        )