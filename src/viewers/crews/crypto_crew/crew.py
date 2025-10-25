from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# Import tools if needed later, e.g.:
# from src.viewers.crews.tools.crypto_tools import FrequencyAnalysisTool

@CrewBase
class CryptoCrew:
    """CryptoCrew specializes in solving cryptographic challenges."""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def cipher_identifier(self) -> Agent:
        """Agent that identifies the cipher used."""
        return Agent(
            config=self.agents_config['cipher_identifier'],
            # tools=[FrequencyAnalysisTool()], # Example Tool
            verbose=True
        )

    @agent
    def crypto_solver(self) -> Agent:
        """Agent that plans the decryption process."""
        return Agent(
            config=self.agents_config['crypto_solver'],
            verbose=True
        )

    @agent
    def crypto_verifier(self) -> Agent:
        """Agent that validates the identification and plan."""
        return Agent(
            config=self.agents_config['crypto_verifier'],
            verbose=True
        )

    @task
    def identify_cipher_task(self) -> Task:
        """Task to identify the cipher."""
        return Task(
            config=self.tasks_config['identify_cipher_task'],
            agent=self.cipher_identifier(),
            context=[self.validate_crypto_plan_task()] # Pass feedback context if retrying
        )

    @task
    def develop_decryption_plan_task(self) -> Task:
        """Task to create the decryption plan."""
        # This task implicitly depends on the output of identify_cipher_task
        # and incorporates feedback via context from validate_crypto_plan_task
        return Task(
            config=self.tasks_config['develop_decryption_plan_task'],
            agent=self.crypto_solver(),
            context=[self.identify_cipher_task(), self.validate_crypto_plan_task()]
        )

    @task
    def validate_crypto_plan_task(self) -> Task:
        """Task to validate the entire plan (id + steps)."""
        # The output Pydantic model (AnalysisVerification) is handled by the flow
        return Task(
            config=self.tasks_config['validate_crypto_plan_task'],
            agent=self.crypto_verifier(),
            context=[self.develop_decryption_plan_task()] # Context includes the plan to validate
        )

    @crew
    def crew(self) -> Crew:
        """Creates the CryptoCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential, # identify -> develop -> validate
            verbose=True,
        )