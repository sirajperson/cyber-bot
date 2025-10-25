from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# Import tools if needed later, e.g.:
# from src.viewers.crews.tools.log_analysis_tools import RegexTool

@CrewBase
class LogAnalysisCrew:
    """LogAnalysisCrew analyzes log files for security incidents and anomalies."""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def log_parser(self) -> Agent:
        """Agent that plans log parsing."""
        return Agent(
            config=self.agents_config['log_parser'],
            # tools=[RegexTool()], # Example Tool
            verbose=True
        )

    @agent
    def threat_identifier(self) -> Agent:
        """Agent that identifies threats in logs."""
        return Agent(
            config=self.agents_config['threat_identifier'],
            verbose=True
        )

    @agent
    def soc_validator(self) -> Agent:
        """Agent that validates the log analysis findings."""
        return Agent(
            config=self.agents_config['soc_validator'],
            verbose=True
        )

    @task
    def parse_logs_task(self) -> Task:
        """Task to create the log parsing plan."""
        # This task might receive feedback from the validator on subsequent runs
        return Task(
            config=self.tasks_config['parse_logs_task'],
            agent=self.log_parser(),
            context=[self.validate_log_analysis_task()] # Feedback context
        )

    @task
    def identify_threats_task(self) -> Task:
        """Task to identify threats based on parsed logs or context."""
        # Depends on the parsing plan (implicitly via context or shared state)
        # Also receives feedback context
        return Task(
            config=self.tasks_config['identify_threats_task'],
            agent=self.threat_identifier(),
            context=[self.parse_logs_task(), self.validate_log_analysis_task()]
        )

    @task
    def validate_log_analysis_task(self) -> Task:
        """Task to validate the parsing plan and findings."""
        # Output Pydantic model is handled by the flow
        return Task(
            config=self.tasks_config['validate_log_analysis_task'],
            agent=self.soc_validator(),
            # Context needs the combined plan + findings, likely from identify_threats_task
            context=[self.identify_threats_task()]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the LogAnalysisCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential, # parse -> identify -> validate
            verbose=True,
        )