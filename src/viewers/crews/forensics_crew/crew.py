from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# --- Import Forensics Tools ---
from ..tools.forensics import (
    AutopsyTool,
    ExifToolWrapper,
    ForemostTool,
    FtkImagerTool,
    SteghideTool,
    VolatilityTool
)
# --- Import relevant tools from other categories ---
from ..tools.binary_exploit import FileTool, StringsTool, BinwalkTool
from ..tools.traffic_analysis.tshark_tool import TsharkTool # For PCAP analysis
from ..tools.general.terminal_tool import InteractiveTerminalTool

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
            # --- Assign Tools ---
            tools=[
                FileTool(), # Essential for identifying type
                InteractiveTerminalTool() # For basic checks if needed
            ],
            verbose=True,
            allow_delegation=False
        )

    @agent
    def forensics_planner(self) -> Agent:
        """Agent that creates the analysis plan using appropriate tools."""
        return Agent(
            config=self.agents_config['forensics_planner'],
             # --- Assign Tools ---
            tools=[
                # File Analysis Tools
                ExifToolWrapper(),
                StringsTool(),
                BinwalkTool(),
                # Steganography
                SteghideTool(),
                # File Carving
                ForemostTool(),
                # Memory Analysis
                VolatilityTool(),
                # Network Analysis (if PCAP)
                TsharkTool(),
                # Instructional Tools (GUI)
                AutopsyTool(),
                FtkImagerTool(),
                # General Execution
                InteractiveTerminalTool(),
            ],
            verbose=True,
            allow_delegation=False # Planner should formulate the steps
        )

    @agent
    def evidence_validator(self) -> Agent:
        """Agent that validates the analysis plan."""
        return Agent(
            config=self.agents_config['evidence_validator'],
            tools=[], # Validator reviews the plan text
            verbose=True,
            allow_delegation=False
        )

    # --- Task Definitions ---
    @task
    def analyze_evidence_type_task(self) -> Task:
        """Task to identify evidence type and technique using FileTool."""
        return Task(
            config=self.tasks_config['analyze_evidence_type_task'],
            agent=self.file_analyst(),
            context=[self.validate_forensics_plan_task()] # Feedback context
        )

    @task
    def develop_forensics_plan_task(self) -> Task:
        """Task to create the forensics analysis plan using available tools."""
        return Task(
            config=self.tasks_config['develop_forensics_plan_task'],
            agent=self.forensics_planner(),
            # Needs context from analyst (type) and validator (feedback)
            context=[self.analyze_evidence_type_task(), self.validate_forensics_plan_task()]
        )

    @task
    def validate_forensics_plan_task(self) -> Task:
        """Task to validate the entire plan (type, technique, tools, steps)."""
        # Output Pydantic model is handled by the flow
        return Task(
            config=self.tasks_config['validate_forensics_plan_task'],
            agent=self.evidence_validator(),
            # Needs the plan developed by the planner
            context=[self.develop_forensics_plan_task()]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the ForensicsCrew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential, # analyze type -> develop plan -> validate plan
            memory=True, # Enable memory
            verbose=True,
        )
