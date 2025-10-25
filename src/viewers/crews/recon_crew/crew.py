from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# Import tools if needed later, e.g., NmapTool

@CrewBase
class ReconCrew:
    """ReconCrew plans and validates network scanning and reconnaissance tasks."""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def recon_planner(self) -> Agent:
        """Agent that creates the reconnaissance plan."""
        return Agent(
            config=self.agents_config['recon_planner'],
            # tools=[], # Add Nmap tool or similar if needed
            verbose=True
        )

    @agent
    def pentest_lead(self) -> Agent:
        """Agent that validates the reconnaissance plan."""
        return Agent(
            config=self.agents_config['pentest_lead'],
            verbose=True
        )

    @task
    def plan_recon_task(self) -> Task:
        """Task for the planner to create the recon steps and commands."""
        # Receives feedback context from the validator
        return Task(
            config=self.tasks_config['plan_recon_task'],
            agent=self.recon_planner(),
            context=[self.validate_recon_plan_task()] # Feedback context
        )

    @task
    def validate_recon_plan_task(self) -> Task:
        """Task for the lead to validate the plan's logic and commands."""
        # Output Pydantic model is handled by the flow
        return Task(
            config=self.tasks_config['validate_recon_plan_task'],
            agent=self.pentest_lead(),
            context=[self.plan_recon_task()] # Needs the plan to validate
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ReconCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential, # plan -> validate
            verbose=True,
        )