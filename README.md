# Cyber Bot

A web crawler designed to navigate and map the CyberSkyline Gymnasium platform, extracting module structures and questions into a markdown format and generating a visual mind map.

## Overview

Cyber Bot automates the process of authenticating into the CyberSkyline platform, navigating its dashboard, selecting the "Gymnasium" section, and crawling through module groups and challenges. It converts question frames into markdown using OpenRouter's AI models (supporting both text and image analysis) and creates a Mermaid.js-compatible mind map for visualization.

## Features
- **Authentication**: Logs into CyberSkyline with provided credentials.
- **Navigation**: Clicks through "Gymnasium" and explores dropdown menus and module links.
- **Content Extraction**: Converts HTML question frames to markdown, handling text and images.
- **Mind Mapping**: Generates a hierarchical mind map of topics, modules, and questions.
- **Multi-Threaded Crawling**: Uses concurrent workers for efficient site traversal.

## Prerequisites
- Python 3.12 or higher
- UV package manager

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/sirajperson/cyber-bot.git
   cd cyber-bot
