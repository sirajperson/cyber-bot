# Cyber Bot 🤖

A web crawler and AI agent system designed to navigate the CyberSkyline Gymnasium platform, extract challenge data using Vision-Language Models (VLM), analyze challenges with specialized AI crews, and generate solution plans within a containerized Kali Linux environment.

## Overview

Cyber Bot logs into CyberSkyline, navigates to the Gymnasium, and crawls modules. It captures page content (HTML) and visual layout (screenshots) for each challenge. This data is then processed by specialized AI agent crews, leveraging OpenRouter's VLM for initial markdown conversion and CrewAI for analysis. Each crew uses a self-evaluation loop (Generator + Evaluator agents) to refine its analysis before producing a final solution plan ("ticket") saved as markdown. The project also generates a Mermaid.js mind map of the site structure. The entire process runs within a Docker container based on Kali Linux, providing access to necessary security tools.

## Features

* **Authentication & Navigation**: Securely logs in and navigates the CyberSkyline Gymnasium using Selenium.
* **VLM-Powered Data Extraction**: Uses screenshots and HTML with a VLM (Qwen via OpenRouter) to generate rich markdown representations of challenges.
* **Specialized AI Crews**: Employs dedicated crews for each challenge category (OSINT, Crypto, Forensics, etc.) using CrewAI.
* **Self-Evaluation Loop**: Each crew uses a Generator-Evaluator pattern within a `Flow` to ensure high-quality analysis and feedback-driven refinement.
* **Modular Architecture (MVC)**: Organized using Model-View-Controller for clarity and maintainability.
* **Organized Tooling**: Tools used by crews are structured by category.
* **Containerized Environment**: Runs in a Docker container with a Kali Linux base, providing pre-installed security tools and GPU support via NVIDIA Container Toolkit.
* **Mind Mapping**: Generates a Mermaid.js mind map of the crawled site structure.
* **Multi-Threaded Crawling**: Efficiently gathers data using concurrent workers.

## Architecture (MVC Pattern)

Cyber Bot uses a Model-View-Controller approach:

* **Models (`src/models/`)**: Defines **interfaces** (abstract base classes) for core components.
* **Views (`src/viewers/`)**: Handles **interaction with external systems** (website, AI APIs) and data gathering. Includes `navigator.py` (Selenium), `crawler.py` (VLM integration).
* **Controllers (`src/controllers/`)**: **Orchestrate the workflow**. `graph_controller.py` handles crawling; `crew_controller.py` handles crew analysis via self-evaluation flows.
* **Common Utilities (`src/common/`)**: Shared resources (Config, API clients, File IO, utils).
* **Crews (`src/viewers/crews/`)**: The **AI agents** for analysis, structured by category (e.g., `crypto_crew`), each with Generator/Evaluator agents defined in YAML.
* **Tools (`src/viewers/crews/tools/`)**: **Specialized functions** callable by agents, organized by category (e.g., `recon/nmap_tool.py`).

### Workflow Summary

1.  User runs `./run_docker.sh`.
2.  Docker container starts, executing `src/main.py`.
3.  `main.py` starts, authenticates using `Navigator`.
4.  `main.py` calls `GraphController.clone_site()`.
5.  `GraphController` uses `ModuleCrawler` (uses `Navigator` + `OpenRouterAPI`) to crawl, screenshot, get VLM markdown.
6.  `main.py` passes `crawl_results` to `CrewController.organize_teams()`.
7.  `CrewController` loops through results:
    * Selects specialized **Generator Crew** (e.g., `CryptoCrew`).
    * Selects generic **Evaluator Crew** (`AnalysisReviewCrew`).
    * Runs `ModuleAnalysisFlow` (Generator -> Evaluator -> Loop).
    * `Flow` saves valid analysis ticket using `FileHandler`.
8.  `main.py` finishes. Output (tickets, logs, screenshots) is persisted via mounted volumes.

## Prerequisites

* **Host System**: Linux (Debian/Ubuntu, Fedora/RPM-based, or Arch recommended).
* **NVIDIA GPU & Drivers**: Required for GPU acceleration within the container. Install drivers *before* running setup scripts. 
* **Docker Engine**: Containerization platform.
* **NVIDIA Container Toolkit**: Enables Docker containers to access NVIDIA GPUs.
* **Internet Connection**: For building the Docker image and API calls.
* **OpenRouter.ai Account & API Key**: For VLM processing.
* **CyberSkyline Account**: Username & Password.

## Installation & Setup

1.  **Clone Repository**:
    ```bash
    git clone [https://github.com/sirajperson/cyber-bot.git](https://github.com/sirajperson/cyber-bot.git)
    cd cyber-bot
    ```

2.  **Configure Environment Variables**:
    ```bash
    cp env.example .env
    ```
    Edit the `.env` file and add your `USERNAME`, `PASSWORD` (for CyberSkyline), and `OPENROUTER_API_KEY`.

3.  **Setup Host Docker Environment**:
    * **Install NVIDIA Drivers**: Ensure your host system has the correct NVIDIA drivers installed and working. Refer to NVIDIA's documentation.
    * **Run System Config Script**: Execute the setup script with `sudo` for your distribution to install Docker and the NVIDIA Container Toolkit. **Make sure `system-config.sh` is executable (`chmod +x system-config.sh`)**.
        ```bash
        # For Debian/Ubuntu:
        sudo ./system-config.sh debian

        # For Fedora/RHEL/CentOS:
        sudo ./system-config.sh fedora

        # For Arch Linux:
        sudo ./system-config.sh arch
        ```
        Follow any on-screen prompts. This script might take some time. Verify Docker is running (`sudo systemctl status docker`) and the NVIDIA toolkit is configured (e.g., test with `sudo docker run --rm --gpus all nvidia/cuda:12.6.0-base-debian12 nvidia-smi`).

## Usage

Run the Cyber Bot within the pre-configured Docker container using the provided script. **Make sure `run_docker.sh` is executable (`chmod +x run_docker.sh`)**.

```bash
./run_docker.sh
````

This script will:

1.  Build the `cyber-bot-kali:latest` Docker image if it doesn't exist (using the `Dockerfile`).
2.  Run the container, mounting the `.env` file, `data` directory, and `logs` directory.
3.  Enable GPU access within the container.
4.  Execute the main bot script (`src/main.py`).

Outputs will be saved to your local `./data` and `./logs` directories.

## Project Structure

```
.
├── Dockerfile            # Defines the Kali+CUDA+Python+Tools container environment
├── data/                 # Output directory (mounted into container)
├── env.example           # Environment variable template
├── logs/                 # Log files (mounted into container)
├── pyproject.toml        # Project metadata and Python dependencies (for UV)
├── README.md             # This file
├── run_docker.sh         # Script to build (if needed) and run the Docker container
├── src/                  # Source code root
│   ├── common/           # Shared utilities
│   ├── controllers/      # MVC Controllers (GraphController, CrewController)
│   ├── __init__.py
│   ├── integrations/       # External examples (ignore)
│   ├── main.py             # Main entry point
│   ├── models/             # MVC Model Interfaces
│   └── viewers/            # MVC Views (Navigator, Crawler, Crews, Tools)
│       ├── crawler.py
│       ├── crews/
│       │   ├── binary_exploit_crew/ # <<< Crew Structure
│       │   ├── ... (other crews)
│       │   ├── tools/
│       │   │   ├── binary_exploit/   # <<< Tool Structure
│       │   │   ├── ... (other tool categories)
│       │   │   └── general/
│       │   └── ...
│       └── navigator.py
├── system-config.sh      # Script to set up Docker + NVIDIA Toolkit on HOST
├── tests/                # Unit/Integration tests
└── uv.lock               # Lock file for Python dependencies
```

## Contributing

Pull requests welcome. Please open an issue first for major changes.

## License

[MIT](https://www.google.com/search?q=LICENSE)

## Development Notes

  * **Last Updated**: Saturday, October 25, 2025, 7:24 PM EDT
  * **Status**: Docker environment defined (`Dockerfile`, `run_docker.sh`, `system-config.sh`). Project structure includes specialized crews and tools placeholders. Self-evaluation flow implemented in `CrewController`.
  * **Next Steps**:
    1.  **Define Tool Interfaces (Implement `_run`)**: Implement the core logic (`_run` method) for the placeholder tool wrappers in `src/viewers/crews/tools/`. This involves writing Python code (likely using `subprocess`) to interact with the underlying command-line tools available in the Kali Docker container (e.g., `nmap`, `hashcat`, `tshark`, etc.) based on arguments provided by the agents.
    2.  **Implement `AnalysisReviewCrew`**: Create the generic "Evaluator" crew (`src/viewers/crews/analysis_review_crew/`) responsible for validating the output of the generator crews using the `AnalysisVerification` Pydantic model. Define its agents and tasks in YAML.
    3.  **Refine Container Configuration**: Test the `Dockerfile` build process. Ensure all necessary Kali tools (especially Ghidra, if needed manually) are installed correctly and accessible. Verify Python dependencies install correctly via `uv sync`.
    4.  **Refine Crews**: Fine-tune agent prompts (`agents.yaml`) and task descriptions (`tasks.yaml`) for each specialized crew based on initial testing and how they interact with the implemented tools.
    5.  **Test Pipeline**: Test the full crawl -\> analyze -\> review -\> save workflow end-to-end using `./run_docker.sh` within the built container environment. Debug interactions between crews, tools, and the VLM.

<!-- end list -->
