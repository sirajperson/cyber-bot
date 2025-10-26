from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# --- Import Crypto Tools ---
# Import tools from the sibling 'tools' directory structure
from ..tools.crypto import (
    FrequencyAnalysisTool,
    CyberchefTool,
    OnlineSolverTool,
    OpensslTool,
    CryptoLibTool
)
# --- Import General Tools if needed ---
from ..tools.general import InteractiveTerminalTool

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
            # --- Assign Tools ---
            tools=[
                FrequencyAnalysisTool(), # For classical cipher analysis
                CryptoLibTool(), # For checking Base64/Hex encoding
                # InteractiveTerminalTool() # Maybe less useful for identifier? Add if needed.
            ],
            verbose=True,
            allow_delegation=False # Identifier should focus
        )

    @agent
    def crypto_solver(self) -> Agent:
        """Agent that plans and potentially executes decryption steps."""
        return Agent(
            config=self.agents_config['crypto_solver'],
             # --- Assign Tools ---
            tools=[
                CyberchefTool(), # Generate instructions for CyberChef
                OnlineSolverTool(), # Generate instructions for dcode etc.
                OpensslTool(), # Execute openssl commands (e.g., AES decrypt)
                CryptoLibTool(), # Execute Base64/Hex decode/encode
                InteractiveTerminalTool() # For running other simple commands or viewing decrypted files
            ],
            verbose=True,
            allow_delegation=False # Solver should execute plans directly where possible
        )

    @agent
    def crypto_verifier(self) -> Agent:
        """Agent that validates the identification and plan."""
        return Agent(
            config=self.agents_config['crypto_verifier'],
            tools=[], # Validator typically doesn't execute, only reviews text/plan
            verbose=True,
            allow_delegation=False
        )

    # --- Task Definitions ---
    # Note: Task context handling is crucial for the self-evaluation loop

    @task
    def identify_cipher_task(self) -> Task:
        """Task to identify the cipher."""
        return Task(
            config=self.tasks_config['identify_cipher_task'],
            agent=self.cipher_identifier(),
            # This task's output will be used by develop_decryption_plan_task
            # It receives feedback context from the validator on retry loops
            context=[self.validate_crypto_plan_task()]
        )

    @task
    def develop_decryption_plan_task(self) -> Task:
        """Task to create the decryption plan using available tools."""
        return Task(
            config=self.tasks_config['develop_decryption_plan_task'],
            agent=self.crypto_solver(),
            # Needs context from the identifier (cipher type) and validator (feedback)
            context=[self.identify_cipher_task(), self.validate_crypto_plan_task()]
        )

    @task
    def validate_crypto_plan_task(self) -> Task:
        """Task to validate the entire plan (id + steps)."""
        # This task produces the AnalysisVerification output for the flow controller
        return Task(
            config=self.tasks_config['validate_crypto_plan_task'],
            agent=self.crypto_verifier(),
            # Needs the final plan developed by the solver
            context=[self.develop_decryption_plan_task()]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the CryptoCrew with sequential execution and memory."""
        return Crew(
            agents=self.agents, # Populated by @agent decorators
            tasks=self.tasks,   # Populated by @task decorators
            process=Process.sequential, # identify -> develop -> validate
            memory=True, # Enable memory for context between steps/retries
            verbose=True,
        )

