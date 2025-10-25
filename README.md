# Cyber Bot 🤖

A web crawler and AI agent system designed to navigate the CyberSkyline Gymnasium platform, extract challenge data using Vision-Language Models (VLM), analyze challenges with specialized AI crews, and generate solution plans.

## Overview

Cyber Bot logs into CyberSkyline, navigates to the Gymnasium, and crawls modules. It captures page content (HTML) and visual layout (screenshots) for each challenge. This data is then processed by specialized AI agent crews, leveraging OpenRouter's VLM for initial markdown conversion and CrewAI for analysis. Each crew uses a self-evaluation loop (Generator + Evaluator agents) to refine its analysis before producing a final solution plan ("ticket") saved as markdown. The project also generates a Mermaid.js mind map of the site structure.

## Features

* **Authentication & Navigation**: Securely logs in and navigates the CyberSkyline Gymnasium.
* **VLM-Powered Data Extraction**: Uses screenshots and HTML with a VLM (Qwen via OpenRouter) to generate rich markdown representations of challenges.
* **Specialized AI Crews**: Employs dedicated crews for each challenge category (OSINT, Crypto, Forensics, etc.) using CrewAI.
* **Self-Evaluation Loop**: Each crew uses a Generator-Evaluator pattern within a `Flow` to ensure high-quality analysis and feedback-driven refinement.
* **Modular Architecture (MVC)**: Organized using Model-View-Controller for clarity and maintainability.
* **Organized Tooling**: Tools used by crews are structured by category.
* **Mind Mapping**: Generates a Mermaid.js mind map of the crawled site structure.
* **Multi-Threaded Crawling**: Efficiently gathers data using concurrent workers.

## Architecture (MVC Pattern)

Cyber Bot uses a Model-View-Controller approach:

* **Models (`src/models/`)**: Defines **interfaces** (abstract base classes) for core components, ensuring consistent contracts.
    * `crawler_interface.py`: Blueprint for any web crawler.
    * `agent_interface.py`: Contract for agent operations (implemented implicitly by CrewAI crews).
    * `file_interface.py`: Contract for file handling.

* **Views (`src/viewers/`)**: Handles **interaction with external systems** and data gathering.
    * `navigator.py`: The low-level Selenium browser driver for login and page interaction.
    * `crawler.py` (`ModuleCrawler`): Implements `CrawlerInterface`. Orchestrates the `Navigator` to crawl pages, take screenshots, and trigger VLM markdown conversion via `OpenRouterAPI`. This is the primary data gathering view.

* **Controllers (`src/controllers/`)**: **Orchestrate the workflow** between Models and Views.
    * `graph_controller.py` (`GraphController`): Responsible **only for data collection**. Its `clone_site` method uses the `ModuleCrawler` to crawl the target site and gather HTML, screenshots, and VLM markdown for all modules.
    * `crew_controller.py` (`CrewController`): Responsible **only for data analysis**. Its `organize_teams` method takes the results from `clone_site`, selects the appropriate specialized **Crew** for each module, and runs a **self-evaluation `ModuleAnalysisFlow`** (Generator Crew -> Evaluator Crew -> Loop with feedback) to produce the final analysis ticket.

* **Common Utilities (`src/common/`)**: Shared resources.
    * `config.py`: Loads environment variables (`.env`).
    * `openrouter_api.py`: Client for interacting with OpenRouter VLM (Qwen model).
    * `file_handler.py`: Implements `FileInterface` for saving tickets, screenshots, etc.
    * `utils.py`: Helper functions (e.g., `generate_mermaid_mindmap`).

* **Crews (`src/viewers/crews/`)**: The **AI agents** responsible for analysis, structured by challenge category.
    * Each category (e.g., `crypto_crew`, `osint_crew`) has its own directory containing `crew.py`, `config/agents.yaml`, and `config/tasks.yaml`.
    * Follows the `@CrewBase` pattern for defining agents and tasks.
    * Each specialized crew acts as the **"Generator"** in the self-evaluation flow.
    * A generic `analysis_review_crew` (to be created) acts as the **"Evaluator"**.

* **Tools (`src/viewers/crews/tools/`)**: **Specialized functions** callable by agents, organized by category.
    * `general/`: Contains tools usable by multiple crews (e.g., search, browser).
    * Category-specific directories (e.g., `crypto/`, `recon/`) contain tools relevant to those challenges (e.g., `nmap_tool.py`).

### Workflow Summary

1.  `main.py` starts, authenticates using `Navigator`.
2.  `main.py` calls `GraphController.clone_site()`.
3.  `GraphController` uses `ModuleCrawler` (which uses `Navigator` and `OpenRouterAPI`) to crawl modules, take screenshots, get VLM markdown, and collect results.
4.  `main.py` passes `crawl_results` to `CrewController.organize_teams()`.
5.  `CrewController` iterates through results:
    * Selects the appropriate specialized **Generator Crew** (e.g., `CryptoCrew`).
    * Selects the generic **Evaluator Crew** (`AnalysisReviewCrew`).
    * Instantiates and kicks off `ModuleAnalysisFlow` with these two crews.
    * `ModuleAnalysisFlow` runs the Generator, then the Evaluator, looping with feedback until valid.
    * The `Flow` saves the final valid analysis using `FileHandler`.
6.  `main.py` finishes, potentially generating the mind map via `utils.py`.

## Prerequisites

* Python 3.12+
* UV package manager (`pip install uv` or `sudo apt install uv`)
* OpenRouter.ai Account & API Key (for VLM)
* CyberSkyline Account (Username & Password)

## Installation

1.  Clone: `git clone https://github.com/sirajperson/cyber-bot.git && cd cyber-bot`
2.  Install UV: (See Prerequisites)
3.  Sync Deps: `uv sync`
4.  Configure Env: `cp env.example .env` and edit `.env` with your `USERNAME`, `PASSWORD`, and `OPENROUTER_API_KEY`.

## Usage

Run the main bot workflow:

```bash
uv run -m src.main
````

Outputs:

  * Mind map: `data/cyberskyline_mindmap.txt`
  * Screenshots: `data/screenshots/`
  * Analysis Tickets: `data/ticket_*.md`

## Project Structure

```
.
├── data/                 # Output directory
│   ├── cyberskyline_mindmap.txt
│   ├── ticket_*.md       # Generated analysis tickets
│   └── screenshots/      # Page screenshots for VLM
├── env.example           # Environment variable template
├── logs/                 # Log files
│   └── bot.log
├── pyproject.toml        # Project metadata and dependencies (for UV)
├── README.md             # This file
├── src/                  # Source code root
│   ├── common/           # Shared utilities (Config, API clients, File IO)
│   │   ├── config.py
│   │   ├── file_handler.py
│   │   ├── __init__.py
│   │   ├── openrouter_api.py
│   │   └── utils.py
│   ├── controllers/      # Orchestration layer (MVC Controller)
│   │   ├── crew_controller.py  # Handles agent crews & analysis flow
│   │   ├── graph_controller.py # Handles crawling & data collection
│   │   ├── __init__.py
│   │   └── main.py           # Example secondary workflow (Meeting Bot)
│   ├── __init__.py         # Makes 'src' a package
│   ├── integrations/       # External examples/experiments (ignore for core bot)
│   ├── main.py             # Main entry point for the Cyber Bot
│   ├── models/             # Interfaces/Abstract Base Classes (MVC Model)
│   │   ├── agent_interface.py
│   │   ├── crawler_interface.py
│   │   ├── file_interface.py
│   │   └── __init__.py
│   └── viewers/            # Interaction layer (MVC View)
│       ├── crawler.py      # Implements CrawlerInterface (uses Navigator, OpenRouterAPI)
│       ├── crews/          # AI Agent Crews and Tools
│       │   ├── binary_exploit_crew/ # Example specialized crew dir
│       │   │   ├── config/
│       │   │   │   ├── agents.yaml
│       │   │   │   └── tasks.yaml
│       │   │   ├── crew.py     # Defines the @CrewBase class
│       │   │   ├── __init__.py
│       │   │   └── README.md
│       │   ├── crypto_crew/
│       │   ├── forensics_crew/
│       │   ├── __init__.py     # Crews package init
│       │   ├── log_analysis_crew/
│       │   ├── osint_crew/
│       │   ├── password_cracking_crew/
│       │   ├── recon_crew/
│       │   ├── research_crew.py # (May become generic base or be removed)
│       │   ├── traffic_analysis_crew/
│       │   ├── tools/          # Tools used by agents
│       │   │   ├── binary_exploit/ # Example specialized tool dir
│       │   │   │   ├── __init__.py
│       │   │   │   └── ghidra_tool.py # Placeholder tool
│       │   │   ├── crypto/
│       │   │   ├── forensics/
│       │   │   ├── general/    # Tools usable by multiple crews
│       │   │   │   ├── browser_tools.py
│       │   │   │   ├── __init__.py
│       │   │   │   └── search_tools.py
│       │   │   ├── __init__.py # Tools package init
│       │   │   ├── log_analysis/
│       │   │   ├── osint/
│       │   │   ├── password_cracking/
│       │   │   ├── recon/
│       │   │   ├── traffic_analysis/
│       │   │   └── web_exploit/
│       │   └── web_exploit_crew/
│       ├── __init__.py         # Viewers package init
│       └── navigator.py    # Selenium browser driver wrapper
├── tests/                # Unit/Integration tests
│   ├── __init__.py
│   ├── test_crawler.py
│   └── test_navigator.py
└── uv.lock               # Lock file for dependencies
```

## Contributing

Pull requests welcome. Please open an issue first for major changes.

## License

[MIT](https://www.google.com/search?q=LICENSE)

## Development Notes

  * **Last Updated**: Saturday, October 25, 2025, 5:40 PM EDT
  * **Status**: Refactoring complete. Structure for specialized crews and tools established. Self-evaluation flow implemented in `CrewController`.
  * **Next Steps**:
    1.  Implement the `AnalysisReviewCrew` (the generic Evaluator).
    2.  Implement the core logic (`_run` method) for the placeholder tools in `src/viewers/crews/tools/`.
    3.  Refine agent prompts (`agents.yaml`) and task descriptions (`tasks.yaml`) for each specialized crew.
    4.  Test the full pipeline end-to-end.

<!-- end list -->

