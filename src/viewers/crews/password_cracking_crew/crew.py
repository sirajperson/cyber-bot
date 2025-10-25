from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# Import tools if needed later, e.g., Hash identifier tool

@CrewBase
class PasswordCrackingCrew:
    """PasswordCrackingCrew identifies hashes and plans cracking strategies."""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def hash_analyst(self) -> Agent:
        """Agent that identifies hash types."""
        return Agent(
            config=self.agents_config['hash_analyst'],
            # tools=[HashIDTool()], # Example Tool
            verbose=True
        )

    @agent
    def cracking_planner(self) -> Agent:
        """Agent that creates the cracking command."""
        return Agent(
            config=self.agents_config['cracking_planner'],
            verbose=True
        )

    @agent
    def cracking_qa(self) -> Agent:
        """Agent that validates the cracking plan."""
        return Agent(
            config=self.agents_config['cracking_qa'],
            verbose=True
        )

    @task
    def identify_hash_task(self) -> Task:
        """Task to identify the hash type and mode."""
        # Receives feedback context from validator
        return Task(
            config=self.tasks_config['identify_hash_task'],
            agent=self.hash_analyst(),
            context=[self.validate_cracking_plan_task()] # Feedback context
        )

    @task
    def develop_cracking_plan_task(self) -> Task:
        """Task to create the cracking command."""
        # Needs hash type context from analyst and feedback from validator
        return Task(
            config=self.tasks_config['develop_cracking_plan_task'],
            agent=self.cracking_planner(),
            context=[self.identify_hash_task(), self.validate_cracking_plan_task()]
        )

    @task
    def validate_cracking_plan_task(self) -> Task:
        """Task to validate the hash ID and command."""
        # Output Pydantic model is handled by the flow
        return Task(
            config=self.tasks_config['validate_cracking_plan_task'],
            agent=self.cracking_qa(),
            context=[self.develop_cracking_plan_task()] # Needs the plan/command to validate
        )

    @crew
    def crew(self) -> Crew:
        """Creates the PasswordCrackingCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential, # identify -> develop -> validate
            verbose=True,
        )