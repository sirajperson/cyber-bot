# Cyber Bot

A web crawler designed to navigate and map the CyberSkyline Gymnasium platform, extracting module structures, questions, and visual data into markdown format, and generating a Mermaid.js-compatible mind map with VLM (Vision-Language Model) support.

## Overview

Cyber Bot automates authentication into the CyberSkyline platform, navigates to the "Gymnasium" section, and crawls through module groups and challenges. It leverages OpenRouter's AI models for text and image analysis, converting HTML question frames to markdown using screenshots for VLM processing, and creates a hierarchical mind map for visualization.

## Features
- **Authentication**: Securely logs into CyberSkyline with provided credentials.
- **Navigation**: Explores "Gymnasium" dropdowns and module links with screenshot support.
- **Content Extraction**: Converts HTML to markdown, integrating VLM for image-based analysis.
- **Mind Mapping**: Generates a Mermaid.js mind map of topics, modules, and questions.
- **Multi-Threaded Crawling**: Utilizes concurrent workers for efficient site traversal.
- **VLM Integration**: Captures screenshots for each page, enhancing AI-driven content extraction.

## Architecture

The Cyber Bot project is organized using the **Model-View-Controller (MVC)** architectural pattern to ensure modularity and scalability:

- **Models (`src/models/`)**: Define interfaces and data structures for the application's core logic. This includes:
  - `agent_interface.py`: Contracts for agent operations (e.g., processing modules, generating tickets).
  - `crawler_interface.py`: Blueprint for web crawling functionality.
  - `file_interface.py`: Contract for file handling operations.
  These interfaces ensure consistent behavior across implementations.

- **Views (`src/views/`)**: Handle data presentation and interaction with external systems (e.g., CyberSkyline). Key components include:
  - `crawler.py`: Performs multi-threaded crawling, capturing screenshots for VLM analysis.
  - `module_team.py`: Processes module data into structured formats using VLM.
  - `research_crew.py`: Analyzes questions and suggests solutions.
  - `navigator.py`: Drives browser interactions for navigation and authentication.
  Views generate data (e.g., markdown, screenshots) for the controller.

- **Controllers (`src/controllers/`)**: Orchestrate the workflow between models and views. The primary file:
  - `graph_controller.py`: Coordinates crawling, module processing, ticket generation, and mind map creation.
  The controller ensures the bot executes tasks asynchronously, leveraging the view tools.

- **Common Utilities (`src/common/`)**: Shared resources across the project:
  - `config.py`: Manages environment variables (e.g., API keys, credentials).
  - `file_handler.py`: Implements file operations (download, save, etc.).
  - `openrouter_api.py`: Integrates OpenRouter AI for VLM processing.
  - `utils.py`: Provides utility functions (e.g., mind map generation).

The workflow begins with the controller initiating the crawler, which navigates CyberSkyline, takes screenshots, and extracts module data. The module team and research crew process this data asynchronously, generating tickets and leveraging VLM for analysis. Finally, the controller compiles a mind map, saving all outputs to the `data/` directory.

## Prerequisites
- Python 3.12 or higher
- UV package manager
- OpenRouter.ai Account:
  1. Visit [https://openrouter.ai](https://openrouter.ai) and sign up for an account.
  2. Navigate to the API section and generate an API key.
  3. Save the API key securely, as it will be required in the `.env` file during configuration.
- CyberSkyline Account:
  1. Register or log in at [https://cyberskyline.com/competition](https://cyberskyline.com/competition).
  2. Obtain a valid username and password for authentication.

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/sirajperson/cyber-bot.git
   cd cyber-bot
   ```
2. Install UV (if not already installed):
   - For Debian-based systems (e.g., Ubuntu):
     ```bash
     sudo apt update
     sudo apt install uv
     ```
   - For other systems or if `apt` is unavailable, install via pip:
     ```bash
     pip install uv
     ```
3. Sync dependencies:
   ```bash
   uv sync
   ```
4. Copy `env.example` to `.env`:
   ```bash
   cp env.example .env
   ```
5. Configure `.env`:
   - Set `USERNAME` and `PASSWORD` with your CyberSkyline credentials.
   - Set `OPENROUTER_API_KEY` with the API key generated from your OpenRouter account.

## Usage
Run the bot:
```bash
uv run -m src.main
```

Output will be saved to:
- `data/cyberskyline_mindmap.txt` (mind map)
- `data/screenshots/` (page screenshots)
- `data/` (module tickets, e.g., `cryptography-fencing-q1.txt`)

## Project Structure
```
.
├── data
│   ├── cyberskyline_mindmap.txt
│   ├── meeting_notes.txt
│   └── screenshots
│       ├── https:__cyberskyline.com_competition_dashboard_screenshot.png
│       └── https:__cyberskyline.com_world_684c235bdbe1ed8e2a7f7e69_screenshot.png
├── env.example
├── logs
│   └── bot.log
├── pyproject.toml
├── README.md
├── src
│   ├── common
│   │   ├── config.py
│   │   ├── file_handler.py
│   │   ├── __init__.py
│   │   ├── openrouter_api.py
│   │   ├── slack_helper.py
│   │   ├── trello_helper.py
│   │   ├── types.py
│   │   └── utils.py
│   ├── controllers
│   │   ├── crew_controller.py
│   │   ├── graph_controller.py
│   │   ├── __init__.py
│   │   └── main.py
│   ├── data
│   ├── __init__.py
│   ├── integrations
│   │   ├── azure_model
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── poetry.lock
│   │   │   ├── pyproject.toml
│   │   │   ├── README.md
│   │   │   └── uv.lock
│   │   ├── CrewAI-LangGraph
│   │   │   ├── CrewAI-LangGraph.png
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── README.md
│   │   │   ├── requirements.txt
│   │   │   └── src
│   │   │       ├── crew
│   │   │       │   ├── agents.py
│   │   │       │   ├── crew.py
│   │   │       │   ├── __init__.py
│   │   │       │   ├── tasks.py
│   │   │       │   └── tools.py
│   │   │       ├── graph.py
│   │   │       ├── __init__.py
│   │   │       ├── nodes.py
│   │   │       └── state.py
│   │   ├── __init__.py
│   │   ├── nvidia_models
│   │   │   ├── __init__.py
│   │   │   ├── intro
│   │   │   │   ├── __init__.py
│   │   │   │   ├── main.py
│   │   │   │   ├── Makefile
│   │   │   │   ├── pyproject.toml
│   │   │   │   ├── README.md
│   │   │   │   ├── scripts
│   │   │   │   │   ├── check_pydantic.sh
│   │   │   │   │   └── lint_imports.sh
│   │   │   │   └── uv.lock
│   │   │   └── marketing_strategy
│   │   │       ├── __init__.py
│   │   │       ├── Makefile
│   │   │       ├── marketing_posts.ipynb
│   │   │       ├── pyproject.toml
│   │   │       ├── README.md
│   │   │       ├── scripts
│   │   │       │   ├── check_pydantic.sh
│   │   │       │   └── lint_imports.sh
│   │   │       ├── src
│   │   │       │   ├── __init__.py
│   │   │       │   └── marketing_posts
│   │   │       │       ├── config
│   │   │       │       │   ├── agents.yaml
│   │   │       │       │   └── tasks.yaml
│   │   │       │       ├── crew.py
│   │   │       │       ├── __init__.py
│   │   │       │       ├── llm.py
│   │   │       │       └── main.py
│   │   │       └── uv.lock
│   │   └── README.md
│   ├── main.py
│   ├── models
│   │   ├── agent_interface.py
│   │   ├── crawler_interface.py
│   │   ├── file_interface.py
│   │   └── __init__.py
│   └── viewers
│       ├── crawler.py
│       ├── crews
│       │   ├── game_builder_crew
│       │   │   ├── config
│       │   │   │   ├── agents.yaml
│       │   │   │   ├── gamedesign.yaml
│       │   │   │   └── tasks.yaml
│       │   │   ├── crew.py
│       │   │   ├── crew_runner.py
│       │   │   ├── __init__.py
│       │   │   └── README.md
│       │   ├── __init__.py
│       │   ├── markdown_validator_crew
│       │   │   ├── config
│       │   │   │   ├── agents.yaml
│       │   │   │   └── tasks.yaml
│       │   │   ├── crew.py
│       │   │   ├── crew_runner.py
│       │   │   ├── __init__.py
│       │   │   └── README.md
│       │   ├── meeting_assistant_crew
│       │   │   ├── config
│       │   │   │   ├── agents.yaml
│       │   │   │   └── tasks.yaml
│       │   │   ├── __init__.py
│       │   │   ├── meeting_assistant_crew.py
│       │   │   └── README.md
│       │   ├── module_crew.py
│       │   ├── prep-for-a-meeting
│       │   │   ├── agents.py
│       │   │   ├── __init__.py
│       │   │   ├── main.py
│       │   │   └── tasks.py
│       │   ├── research_crew.py
│       │   ├── shakespeare_crew
│       │   │   ├── config
│       │   │   │   ├── agents.yaml
│       │   │   │   └── tasks.yaml
│       │   │   ├── __init__.py
│       │   │   └── shakespeare_crew.py
│       │   ├── tools
│       │   │   ├── browser_tools.py
│       │   │   ├── calculator_tools.py
│       │   │   ├── CharacterCounterTool.py
│       │   │   ├── ExaSearchTool.py
│       │   │   ├── __init__.py
│       │   │   ├── markdownTools.py
│       │   │   └── search_tools.py
│       │   ├── trip_planner
│       │   │   ├── __init__.py
│       │   │   ├── main.py
│       │   │   ├── README.md
│       │   │   ├── trip_agents.py
│       │   │   └── trip_tasks.py
│       │   └── x_post_review_crew
│       │       ├── config
│       │       │   ├── agents.yaml
│       │       │   └── tasks.yaml
│       │       ├── __init__.py
│       │       └── x_post_review_crew.py
│       ├── __init__.py
│       └── navigator.py
├── temp
├── tests
│   ├── __init__.py
│   ├── test_crawler.py
│   ├── test_navigator.py
│   └── test_openrouter_api.py
└── uv.lock

```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss.

## License
[MIT](LICENSE)

## Development Notes
- **Last Updated**: 12:35 AM EDT, Monday, October 20, 2025
- **Status**: Alpha phase, with ongoing testing of VLM integration and async workflows.
- **Next Steps**: Test full pipeline, refine VLM prompts, and document troubleshooting steps.
```

### Instructions for Canvas File Editor
1. **Open Canvas Editor**: Access the canvas panel in your environment and select the option to create or edit a file (e.g., "README.md").
2. **Paste Content**: Copy the entire text block above and paste it into the canvas editor's text area.
3. **Save File**: Use the save functionality of the canvas tool to persist the file as `README.md` in your project directory (e.g., `~/ai/cyber_bot/`).
4. **Verify Rendering**: If the canvas supports Markdown rendering, check that the tree structure under "Project Structure" displays with proper indentation (each level should be indented with 4 spaces) and that the new "Architecture" section is visible and well-formatted.

### Changes Made
- **Added Architecture Section**: Inserted a detailed explanation of the MVC pattern, describing the roles of `models`, `views`, `controllers`, and `common` utilities, and how they interact in the workflow.
- **Updated Timestamp**: Reflected the current time (12:35 AM EDT, Monday, October 20, 2025) in the "Development Notes" section.

### Next Steps
- **Commit Changes**: After pasting and saving, run `git add README.md && git commit -m "Add Architecture section to README"`.
- **Test Rendering**: Verify the "Architecture" section displays correctly in your canvas editor and that the tree structure is intact.
- **Feedback**: Let me know if the formatting needs adjustment or if you want to expand the architecture description further!

