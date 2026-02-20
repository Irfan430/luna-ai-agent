# LUNA AI Agent - v4.0

**LUNA (Latent Understanding & Neural Architecture)** is a sophisticated, autonomous AI agent designed for complex task execution, self-healing, and deep reasoning. This repository contains the complete source code for LUNA v4.0, which includes significant stabilization, architectural repairs, and professionalization across its entire stack.

![LUNA Architecture](architecture.png)

This major update (from v2.0 to v4.0) focused on hardening the agent's core systems, professionalizing the user interface, and implementing robust error handling and verification mechanisms. The agent is now significantly more reliable, predictable, and capable.

---

## Key Features

| Feature                  | Description                                                                                                                              |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Cognitive Loop**       | An advanced iterative loop for planning, execution, and reflection, enabling multi-step reasoning and dynamic plan revision.               |
| **LLM Routing Layer**    | Intelligently classifies user input to decide between direct conversation, planning, or action, improving efficiency and responsiveness.      |
| **Hardened Execution**   | A secure execution kernel with OS control, injection detection, and post-execution verification for reliable task completion.              |
| **Advanced Memory**      | A multi-layered memory system with short-term context, long-term episodic history, and auto-compression to manage token pressure.        |
| **Voice Mode**           | Includes passive wake-word listening ("LUNA"), asynchronous operation, and configurable acknowledgments without blocking the main loop. |
| **Professional GUI**     | A comprehensive monitoring interface with a chat panel, execution timeline, process monitor, config editor, and live system stats.         |

---

## Architecture Overview

The LUNA architecture is designed for modularity and robustness. The core components are:

1.  **LLM Router (`llm/router.py`)**: The entry point for all user input. It uses an LLM to classify the user's intent and routes it to the appropriate handler—either a direct conversational response or the main Cognitive Loop for task execution.

2.  **Cognitive Loop (`core/loop.py`)**: The agent's brain. It orchestrates the entire task-completion process through a three-step cycle:
    *   **Analyze & Plan**: Generates a step-by-step plan to achieve the user's goal based on the current state and memory.
    *   **Execute Action**: Sends the next action to the Execution Kernel and awaits the result.
    *   **Reflect & Update**: Analyzes the outcome of the action, updates its internal state, and revises the plan if necessary.

3.  **Execution Kernel (`execution/kernel.py`)**: The hands of the agent. It provides a hardened layer for interacting with the operating system, including file operations, shell commands, process management, and GUI automation. Every action includes verification to ensure it was completed successfully.

4.  **Memory System (`memory/system.py`)**: The agent's memory. It maintains three levels of memory:
    *   **Short-Term**: The active context of the current task.
    *   **Episodic**: A long-term history of completed tasks.
    *   **Compressed Long-Term**: An LLM-generated summary of episodic memory to provide historical context without excessive token usage.

5.  **Voice Engine (`voice/engine.py`)**: Provides a full voice interface, including passive wake-word detection that runs in a separate thread, ensuring the agent is always ready for voice commands without impacting performance.

6.  **GUI (`gui/monitor.py`)**: A professional PyQt6-based interface for monitoring and interacting with the agent. It provides a complete view of the agent's cognitive state, memory, and the system's resources.

---

## Getting Started

### Prerequisites

- Python 3.8+
- `pip` for package installation
- For Voice Mode on Linux: `sudo apt-get install portaudio19-dev python3-pyaudio`
- For Voice Mode on macOS: `brew install portaudio`

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Irfan430/luna-ai-agent.git
    cd luna-ai-agent
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure the agent:**
    - Rename `config.yaml.example` to `config.yaml`.
    - Edit `config.yaml` to add your LLM API keys.
    - For offline wake-word detection, download a [Vosk model](https://alphacephei.com/vosk/models) and update the `vosk_model_path` in `config.yaml`.

### Running LUNA

To run the agent with the GUI, use the `gui_launcher.py` script:

```bash
python gui_launcher.py
```

---

## Summary of v4.0 Stabilization Fixes

This release addresses critical stability and architectural issues present in earlier versions.

| Phase | Module(s) Affected | Key Fixes Implemented |
| :--- | :--- | :--- |
| **1. Critical Stabilization** | `core/loop.py`, `llm/router.py` | - Fixed `KeyError` from unsafe `.format()` in prompts.<br>- Corrected schema validation for conversational mode.<br>- Implemented a unified LLM routing layer.<br>- Added a JSON repair fallback mechanism. |
| **2. Voice Mode Repair** | `voice/engine.py`, `config.yaml` | - Implemented asynchronous wake-word detection.<br>- Added configurable acknowledgments and silence timeout.<br>- Ensured voice engine runs in a non-blocking thread. |
| **3. GUI Professionalization** | `gui/monitor.py` | - Redesigned all GUI panels for a professional look.<br>- Added a process monitor, config editor, and execution timeline.<br>- Fixed `AttributeError` related to the memory system. |
| **4. Execution Verification** | `execution/kernel.py` | - Enhanced `_launch_app` to verify process startup with retries.<br>- Improved `_run_command` to report exact exit codes in errors.<br>- Added post-execution verification for all critical OS operations. |
| **5. Memory Stabilization** | `memory/system.py` | - Implemented accurate token counting with `tiktoken`.<br>- Added validation for memory compression thresholds.<br>- Fixed state-bleeding issues by resetting `execution_state`.<br>- Prevented duplicate consecutive messages. |
| **6. README** | `README.md` | - This document. |

