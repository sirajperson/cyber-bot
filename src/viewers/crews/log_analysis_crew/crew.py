from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# --- Import Log Analysis Tools ---
from ..tools.log_analysis import (
    AwkTool,
    CutTool,
    GrepTool,
    RegexTool,
    SedTool
)
# --- Import General Tools ---
from ..tools.general.terminal_tool import InteractiveTerminalTool

@CrewBase
class LogAnalysisCrew:
    """LogAnalysisCrew analyzes log files for security incidents and anomalies."""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def log_parser(self) -> Agent:
        """Agent that plans and executes log parsing using CLI tools."""
        return Agent(
            config=self.agents_config['log_parser'],
            # --- Assign Tools ---
            tools=[
                GrepTool(), # Filtering lines
                AwkTool(), # Field extraction and complex logic
                CutTool(), # Simpler field/character extraction
                SedTool(), # Stream editing/substitution
                RegexTool(), # Python regex on smaller text blocks
                InteractiveTerminalTool() # For chaining commands or simple checks
            ],
            verbose=True,
            allow_delegation=False # Parser should execute the plan
        )

    @agent
    def threat_identifier(self) -> Agent:
        """Agent that identifies threats in parsed log data."""
        return Agent(
            config=self.agents_config['threat_identifier'],
            # This agent primarily analyzes text output from the parser
            tools=[
                 RegexTool() # May need regex to find patterns in parser output
            ],
            verbose=True,
            allow_delegation=False
        )

    @agent
    def soc_validator(self) -> Agent:
        """Agent that validates the log analysis plan and findings."""
        return Agent(
            config=self.agents_config['soc_validator'],
            tools=[], # Validator reviews text
            verbose=True,
            allow_delegation=False
        )

    # --- Task Definitions ---
    @task
    def parse_logs_task(self) -> Task:
        """Task to create and execute the log parsing plan."""
        return Task(
            config=self.tasks_config['parse_logs_task'],
            agent=self.log_parser(),
            context=[self.validate_log_analysis_task()] # Feedback context
        )

    @task
    def identify_threats_task(self) -> Task:
        """Task to identify threats based on parsed logs or context."""
        return Task(
            config=self.tasks_config['identify_threats_task'],
            agent=self.threat_identifier(),
            # Needs output from parser and feedback from validator
            context=[self.parse_logs_task(), self.validate_log_analysis_task()]
        )

    @task
    def validate_log_analysis_task(self) -> Task:
        """Task to validate the parsing plan and findings."""
        # Output Pydantic model is handled by the flow
        return Task(
            config=self.tasks_config['validate_log_analysis_task'],
            agent=self.soc_validator(),
            # Needs the combined plan/output and findings from identify_threats_task
            context=[self.identify_threats_task()]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the LogAnalysisCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential, # parse -> identify -> validate
            memory=True, # Enable memory
            verbose=True,
        )
