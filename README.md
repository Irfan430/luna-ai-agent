# LUNA AI Agent

**Author: IRFAN**

LUNA is a personal, LLM-driven, controlled autonomous AI agent designed for robust OS automation. It is built to be a powerful, stable, and transparent tool for developers and power users.

---

## Core Objective

The primary goal of LUNA is to provide a fully LLM-driven autonomous agent that can:

- Understand natural language commands.
- Plan tasks in a structured manner.
- Execute tasks deterministically and safely.
- Verify the outcome of every action.
- Report results with full transparency.
- **Never produce fake success.**

This project emphasizes stability, modularity, and a professional code structure, optimized for personal use rather than as a public-facing SaaS.

## Features

- **LLM-Powered Intent Parsing**: All user inputs are processed by a Large Language Model to extract structured, actionable intent.
- **Multi-Provider LLM Support**: Seamlessly switch between LLM providers. Supports `single` mode (one provider) and `multi` mode (automatic fallback on failure).
- **Token Limit Auto-Resume**: Automatically detects truncated LLM responses (e.g., due to token limits) and continues the generation to ensure complete results.
- **Deterministic Execution Engine**: A separate, non-LLM layer handles all system operations, including running commands, managing files, and interacting with Git.
- **Controlled Autonomy with Risk Control**: Every action is classified by risk level (`low`, `medium`, `high`, `dangerous`). High-risk operations require user confirmation, and dangerous ones are blocked by default.
- **Standardized Task Result Protocol**: All operations return a consistent JSON object, ensuring that the GUI and other components have a reliable data source for status, content, and errors.
- **Voice Mode**: A human-like but consistent voice personality for hands-free interaction.
- **Docker Support**: Comes with a `Dockerfile` for easy containerization and deployment.

## Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/Irfan430/luna-ai-agent.git
    cd luna-ai-agent
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Copy the example configuration file:**

    ```bash
    cp config.yaml.example config.yaml
    ```

2.  **Edit `config.yaml`:**

    Open `config.yaml` in a text editor and add your API keys for the desired LLM providers (e.g., DeepSeek, OpenRouter, OpenAI).

    ```yaml
    llm:
      mode: single  # single | multi
      default_provider: deepseek
      
      providers:
        deepseek:
          api_key: "your-deepseek-api-key-here"
          model: "deepseek-chat"
        
        openrouter:
          api_key: "your-openrouter-api-key-here"
          model: "anthropic/claude-3.5-sonnet"
    ```

### Single vs. Multi LLM Mode

-   **`single` mode**: LUNA will only use the `default_provider` specified in the configuration. If this provider fails, the operation will fail.
-   **`multi` mode**: LUNA will first attempt to use the `default_provider`. If it fails, it will automatically fall back to other configured providers in the list until one succeeds.

### Token Continuation

If an LLM response is cut off (e.g., because it reached the maximum token limit), LUNA's `ContinuationHandler` will automatically detect the incomplete response. It then sends a new request to the LLM, asking it to continue from where it left off. This process can be retried up to `max_retries` times (default: 3) to ensure a complete JSON or text response is received.

### Risk Control

LUNA's `RiskClassifier` and `Guardrails` work together to ensure safety. Before any command is executed, it is classified into one of four risk levels. The behavior for each level is defined in `config.yaml`:

-   **`low`**: Automatically executed (e.g., `ls`, `echo`).
-   **`medium`**: Can be set to require optional confirmation (e.g., `git commit`, `pip install`).
-   **`high`**: Requires user confirmation (e.g., `git push`, `rm -rf <directory>`).
-   **`dangerous`**: Blocked by default (e.g., `rm -rf /`, `shutdown`).

## How to Run

### CLI Mode

For a command-line interface, run `main.py`:

```bash
python main.py
```

### GUI Mode

For a graphical user interface, run `gui_launcher.py`:

```bash
python gui_launcher.py
```

### Docker Usage

You can build and run LUNA in a Docker container for a clean, isolated environment.

1.  **Build the Docker image:**

    ```bash
    docker build -t luna .
    ```

2.  **Run the container (interactive CLI mode):**

    Make sure your `config.yaml` is in the project directory before running.

    ```bash
    docker run -it --rm -v $(pwd)/config.yaml:/app/config.yaml luna
    ```

---
> This project was bootstrapped by Manus AI.
