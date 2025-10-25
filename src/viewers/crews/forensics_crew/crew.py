from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# Import tools if needed later, e.g.:
# from src.viewers.crews.tools.forensics_tools import ExifToolWrapper

@CrewBase
class ForensicsCrew:
    """ForensicsCrew analyzes digital evidence in forensics challenges."""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def file_analyst(self) -> Agent:
        """Agent that identifies evidence type and technique."""
        return Agent(
            config=self.agents_config['file_analyst'],
            # tools=[ExifToolWrapper()], # Example Tool
            verbose=True
        )

    @agent
    def forensics_planner(self) -> Agent:
        """Agent that creates the analysis plan."""
        return Agent(
            config=self.agents_config['forensics_planner'],
            verbose=True
        )

    @agent
    def evidence_validator(self) -> Agent:
        """Agent that validates the analysis plan."""
        return Agent(
            config=self.agents_config['evidence_validator'],
            verbose=True
        )

    @task
    def analyze_evidence_type_task(self) -> Task:
        """Task to identify evidence type and technique."""
        return Task(
            config=self.tasks_config['analyze_evidence_type_task'],
            agent=self.file_analyst(),
            context=[self.validate_forensics_plan_task()] # Pass feedback context if retrying
        )

    @task
    def develop_forensics_plan_task(self) -> Task:
        """Task to create the forensics analysis plan."""
        return Task(
            config=self.tasks_config['develop_forensics_plan_task'],
            agent=self.forensics_planner(),
            context=[self.analyze_evidence_type_task(), self.validate_forensics_plan_task()] # Needs type and feedback
        )

    @task
    def validate_forensics_plan_task(self) -> Task:
        """Task to validate the entire plan."""
        # Output Pydantic model is handled by the flow
        return Task(
            config=self.tasks_config['validate_forensics_plan_task'],
            agent=self.evidence_validator(),
            context=[self.develop_forensics_plan_task()] # Needs the plan to validate
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ForensicsCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential, # analyze type -> develop plan -> validate plan
            verbose=True,
        )