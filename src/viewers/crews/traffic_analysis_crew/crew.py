from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# Import tools if needed later, e.g., TsharkTool

@CrewBase
class TrafficAnalysisCrew:
    """TrafficAnalysisCrew analyzes network packet captures."""
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def pcap_analyst(self) -> Agent:
        """Agent that plans the pcap analysis."""
        return Agent(
            config=self.agents_config['pcap_analyst'],
            # tools=[], # Add Tshark tool or similar if needed
            verbose=True
        )

    @agent
    def netsec_verifier(self) -> Agent:
        """Agent that validates the analysis plan."""
        return Agent(
            config=self.agents_config['netsec_verifier'],
            verbose=True
        )

    @task
    def analyze_pcap_task(self) -> Task:
        """Task for the analyst to create the traffic analysis plan."""
        # Receives feedback context from the validator
        return Task(
            config=self.tasks_config['analyze_pcap_task'],
            agent=self.pcap_analyst(),
            context=[self.validate_traffic_analysis_task()] # Feedback context
        )

    @task
    def validate_traffic_analysis_task(self) -> Task:
        """Task for the validator to review the plan's filters/commands."""
        # Output Pydantic model is handled by the flow
        return Task(
            config=self.tasks_config['validate_traffic_analysis_task'],
            agent=self.netsec_verifier(),
            context=[self.analyze_pcap_task()] # Needs the plan to validate
        )

    @crew
    def crew(self) -> Crew:
        """Creates the TrafficAnalysisCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential, # plan -> validate
            verbose=True,
        )