# LUNA 2.0: Advanced Cognitive Operating Agent for Device Automation

**Author: IRFAN**

LUNA 2.0 is a significantly upgraded, high-autonomy cognitive operating agent designed as a personal AI operating system core for IRFAN. It moves beyond basic task execution to provide **full OS-level control and device automation capabilities**, implementing a multi-layer cognitive orchestration engine for robust and reliable autonomous operations.

---

## Core Requirements & Advanced Capabilities

LUNA 2.0 is built upon an enhanced foundation of AI principles, integrating several key components for unparalleled autonomy and control:

*   **Iterative Reasoning Loop**: A continuous cycle of analysis, planning, execution, and reflection that drives LUNA's decision-making process, now with increased depth for complex automation tasks.
*   **Planner → Executor → Reflector Cycle**: This core cognitive loop ensures every action is thoughtfully planned, executed deterministically, and critically evaluated, with enhanced self-healing capabilities.
*   **Advanced Execution Kernel (AEK)**: A robust and predictable layer for deep OS-level interactions, including process management, network control, and system information retrieval.
*   **Self-Healing Retry System 2.0**: Enhanced mechanisms to detect execution failures, diagnose issues, generate fix plans, and attempt repairs, significantly improving system resilience.
*   **Token-Limit Continuation Engine**: An intelligent system to manage LLM context windows, ensuring complete responses even when faced with token limitations.
*   **Memory Compression Layer**: A dynamic memory management system that compresses historical data to maintain relevant context without exceeding capacity.
*   **Strict Structured Output Enforcement**: All LLM interactions produce structured JSON outputs, strictly validated before any action is taken.
*   **Config-Driven Single/Multi LLM Abstraction**: Flexible architecture for seamless integration and switching between various Large Language Models, with configurable fallback strategies.
*   **Controlled Autonomy Risk Engine**: A critical safety component that classifies actions by risk level and enforces appropriate confirmation or blocking mechanisms, now with more granular control for OS-level operations.
*   **Dynamic Tool Discovery and Plugin System**: A modular architecture allowing LUNA to discover and integrate new capabilities through plugins, extending its functionality without core code changes.

LUNA 2.0 is a **multi-stage cognitive engine**, designed for complex, multi-step device automation and problem-solving.

## Cognitive Loop Design 2.0

LUNA 2.0 operates on an advanced iterative control loop, now with enhanced multi-step reasoning and self-healing capabilities:

```python
while not goal_completed:
    # 1. Analyze current state: Evaluate environment, memory, and real-time system stats.
    # 2. Generate next structured action (LLM): Propose the next logical step, considering AEK tools.
    # 3. Validate action schema: Ensure the proposed action conforms to predefined structures.
    # 4. Execute deterministically: Carry out the action via the Advanced Execution Kernel.
    # 5. Capture result: Record the outcome, including updated system state.
    # 6. Reflect using LLM: Evaluate the result against the goal and internal state, generating fix plans if needed.
    # 7. Update internal state: Adjust memory and context based on reflection.
    # 8. Detect stagnation: Identify if the agent is stuck or making no progress.
    # 9. Enforce max iteration limit: Prevent infinite loops.
```

The maximum number of reasoning iterations is configurable, with an increased default limit to accommodate more complex tasks.

## Prompt Pack Architecture

LUNA 2.0 continues to use a modular **Prompt Pack Architecture** for dynamic assembly of prompts, ensuring context-specific and highly effective LLM interactions:

*   **`identity.prompt`**: Defines LUNA's core persona, purpose, and operational guidelines.
*   **`planning.prompt`**: Guides the LLM in breaking down complex goals into actionable, structured steps, now considering advanced OS automation.
*   **`execution.prompt`**: Provides the schema and context for generating commands executable by the Advanced Execution Kernel, including new OS control tools.
*   **`verification.prompt`**: Defines criteria for evaluating the success or failure of executed actions, with consideration for system state changes.
*   **`reflection.prompt`**: Facilitates self-assessment and learning from past actions and outcomes, crucial for self-healing.
*   **`continuation.prompt`**: Instructs the LLM on how to resume truncated responses, ensuring completeness.

## LLM Abstraction Layer

LUNA 2.0 features a robust LLM abstraction layer, providing flexibility and resilience. The `config.yaml` file centrally manages all LLM-related settings.

### Configuration (`config.yaml`)

```yaml
llm:
  mode: single | multi             # Operation mode: single provider or multi-provider with fallback
  default_provider: deepseek       # The primary LLM provider to use
  
  providers:
    deepseek:
      api_key: "sk-YOUR_DEEPSEEK_API_KEY" # DeepSeek API key (e.g., from DDOS-XO repo)
      model: "deepseek-chat"
      base_url: "https://api.deepseek.com"
    
    openrouter:
      api_key: "sk-YOUR_OPENROUTER_API_KEY"
      model: "anthropic/claude-3.5-sonnet"
      base_url: "https://openrouter.ai/api/v1"
    
    openai:
      api_key: "sk-YOUR_OPENAI_API_KEY"
      model: "gpt-4"
      base_url: "https://api.openai.com/v1"
    
    local:
      api_key: ""                      # Not always required for local models
      model: "llama3"
      base_url: "http://localhost:11434" # Example for Ollama
```

### Modes of Operation

*   **`single` mode**: LUNA exclusively uses the `default_provider`. If this provider encounters an error, the operation will fail without attempting a fallback.
*   **`multi` mode**: LUNA first attempts to use the `default_provider`. In case of failure, it intelligently falls back to other configured providers in the order they appear in the `providers` list until a successful response is obtained.

## Token Limit Continuation Engine

LUNA 2.0's **Token Limit Continuation Engine** is enhanced to ensure complete and valid outputs from LLMs, especially crucial for complex structured responses in device automation.

*   **Detection**: Automatically identifies incomplete JSON structures or explicit token limit error messages.
*   **Context Preservation**: Extracts the last valid step or partial output.
*   **Memory Compression**: If necessary, the memory system will compress the context to make space for continuation.
*   **Re-prompting**: Rebuilds the prompt with the summarized state and an explicit instruction for the LLM to continue from the last incomplete step.
*   **Retry Mechanism**: Allows for a maximum of 3 continuation retries to ensure a complete response.

## Memory System

LUNA 2.0 employs a sophisticated three-layer memory system to manage context and knowledge efficiently, now more critical for long-running automation tasks:

1.  **Short-term Memory**: Holds the current task context, including recent interactions and intermediate reasoning steps. This memory is volatile and frequently updated.
2.  **Episodic Memory**: Stores summaries of recently completed tasks, providing LUNA with a history of its past achievements and challenges.
3.  **Compressed Long-term Memory**: Contains a highly summarized and persistent representation of the overall project state and accumulated knowledge. This layer is updated less frequently and is designed for long-term retention.

When LUNA detects **token pressure**, it automatically triggers an intelligent memory compression process. This process prioritizes retaining the core goal and critical execution state while discarding irrelevant conversational chatter, ensuring that essential information is always available to the LLM.

## Advanced Execution Kernel (AEK)

The **Advanced Execution Kernel (AEK)** is LUNA 2.0's core operational layer for deep OS control. It is strictly separated from the LLM's cognitive functions. The LLM *never* directly executes raw commands; instead, it generates structured actions that are validated against a schema and then passed to the AEK for execution. This design ensures maximum safety, predictability, and reliability for device automation.

### Capabilities

*   **File Operations**: Create, read, edit, delete, move, and list files and directories.
*   **Git Automation**: Perform standard Git operations such as `init`, `clone`, `add`, `commit`, `push`, `pull`, `branch` management, and `checkout`.
*   **Terminal Execution**: Run arbitrary shell commands using non-blocking subprocesses, with enhanced error handling.
*   **Python Execution**: Execute Python scripts or code snippets within the environment.
*   **OS Application Launching**: Open system applications or files with their default handlers.
*   **Process Management**: List, find, and terminate running system processes by PID or name.
*   **Network Control**: Ping hosts, check open ports, and list network interfaces.
*   **System Information**: Retrieve detailed OS, CPU, memory, and disk usage statistics.

All AEK operations include validation of return codes, and LUNA **never marks success without explicit verification** of the outcome.

## Self-Healing System 2.0

LUNA 2.0's **Self-Healing System** is significantly enhanced to gracefully handle execution failures and minimize manual intervention, crucial for robust device automation:

1.  **Error Capture**: Automatically captures detailed error output from failed executions.
2.  **Structured Failure Report**: Generates a comprehensive failure report and feeds it back to the LLM.
3.  **Intelligent Fix Plan Generation**: The LLM analyzes the failure report and proposes a detailed, multi-step plan to resolve the issue, leveraging AEK capabilities.
4.  **Automated Retry Mechanism**: LUNA attempts to re-execute the task after applying the fix plan.
5.  **Repair Limits**: A maximum of 3 repair attempts are allowed to prevent infinite loops.
6.  **Graceful Abort**: If the task continues to fail after multiple repair attempts, LUNA aborts gracefully, providing a comprehensive failure analysis and suggested manual intervention.

## Risk Engine (Controlled Autonomy Mode C)

LUNA 2.0's **Risk Engine** is central to its controlled autonomy, ensuring that OS-level actions are performed safely and with appropriate oversight. Every proposed action is classified by its potential impact:

*   **Low Risk**: Actions with minimal impact, such as reading files or simple system information queries. These are **auto-executed**.
*   **Medium Risk**: Actions with moderate impact, like creating new files, installing non-critical packages, or listing processes. These may require **optional confirmation**.
*   **High Risk**: Actions with significant potential impact, such as deleting files, pushing to a Git repository, or terminating critical processes. These require **mandatory user confirmation**.
*   **Dangerous Risk**: Actions that could lead to system instability or data loss (e.g., `rm -rf /`, system shutdowns). These actions are **blocked by default**.

The Risk Engine implements sophisticated risk scoring logic to accurately categorize actions and enforce the configured autonomy level, providing a critical safety net for device automation.

## Task Result Contract

To ensure transparency and consistency, every operation within LUNA adheres to a strict **Task Result Contract**. All components, including the GUI and Voice Engine, render information strictly based on this standardized JSON object:

```json
{
  "status": "success | failed | partial",
  "content": "A summary or output of the operation",
  "error": "Error message if status is failed or partial",
  "execution_used": true/false, # Indicates if the execution kernel was invoked
  "confidence": 0.0-1.0,        # Agent's confidence in the result
  "risk_level": "low | medium | high | dangerous",
  "verified": true/false,       # Indicates if the result was independently verified
  "system_state": { ... }       # Real-time system resource usage after execution
}
```

This contract guarantees that users receive clear, verifiable, and consistent feedback on LUNA's operations, preventing any form of "fake success."

## Voice Personality Engine

LUNA 2.0 incorporates an enhanced **Voice Personality Engine** to provide a consistent and professional auditory interaction experience, now with more nuanced responses for device automation scenarios:

*   **Calm**: Maintains a steady and reassuring tone.
*   **Minimal Verbosity**: Communicates concisely and directly, avoiding unnecessary chatter.
*   **No Emotional Fluctuation**: Responses are neutral and objective.
*   **No Fake Success**: Always honest about outcomes; if a task fails, it is clearly stated.
*   **Clear Failure Explanation**: Provides technical reasons if asked "why" an operation failed, including system-level diagnostics.
*   **Step-by-Step Solutions**: Offers actionable, step-by-step guidance if asked "what to do" next after a failure, leveraging self-healing capabilities.

This engine utilizes Text-to-Speech (TTS) for output and Speech-to-Text (STT) for input, enabling hands-free interaction with LUNA.

## GUI Monitoring Interface

LUNA 2.0 features an upgraded **GUI Monitoring Interface** built with PyQt6, providing real-time insights into LUNA's operations and system health:

*   **Real-time System Resource Dashboard**: Live display of CPU, RAM, and Disk usage, updated every 2 seconds.
*   **Execution Timeline**: Visual representation of LUNA's cognitive steps, actions, and results.
*   **Rich Chat Display**: Enhanced formatting for user and agent messages, including status, risk level, and confidence scores.
*   **Cognitive State Panel**: Displays current LLM mode, provider, memory usage, and kernel capabilities.
*   **Interactive Input**: Allows users to provide goals and confirm high-risk actions.

## Project Structure

LUNA 2.0 maintains a clean, modular project structure, now with dedicated directories for plugins and enhanced organization:

```
luna/
├── main.py                 # CLI entry point for the cognitive loop
├── gui_launcher.py         # GUI entry point for the monitoring interface
├── config.yaml             # Central configuration file for all LUNA settings
├── requirements.txt        # Python dependencies for the project
├── Dockerfile              # Docker configuration for containerized deployment
├── README.md               # Comprehensive project documentation
├── .gitignore              # Git ignore rules for version control
├── core/                   # Core cognitive loop and orchestration logic
│   └── loop.py             # Implements the Analyze -> Plan -> Execute -> Reflect cycle
├── llm/                    # LLM abstraction layer and related functionalities
│   ├── provider.py         # Abstract LLM provider interface and manager
│   └── continuation.py     # Token limit continuation engine
├── prompts/                # Modular prompt packs for dynamic LLM interaction
│   ├── identity.prompt     # LUNA's persona and operational guidelines
│   ├── planning.prompt     # Guides LLM in task decomposition
│   ├── execution.prompt    # Schema for kernel-executable actions
│   ├── verification.prompt # Criteria for action success/failure
│   ├── reflection.prompt   # Logic for self-correction and learning
│   └── continuation.prompt # Instructions for resuming truncated responses
├── execution/              # Advanced Execution Kernel for OS interactions
│   ├── kernel.py           # Handles file ops, git, terminal, python, app launch, process, network, system info
│   └── plugins.py          # Dynamic tool discovery and plugin manager
├── memory/                 # Three-layer memory management system
│   └── system.py           # Short-term, episodic, and compressed long-term memory
├── risk/                   # Risk scoring and safety guardrails
│   └── engine.py           # Classifies actions and enforces autonomy levels
├── voice/                  # Personality-driven voice engine
│   └── engine.py           # TTS and STT capabilities with LUNA's persona
├── gui/                    # Professional monitoring interface
│   └── monitor.py          # PyQt6-based GUI for real-time status and activity
└── plugins/                # Directory for dynamically loaded plugins
    └── __init__.py         # Plugin package initializer
```

## Run Modes

LUNA 2.0 supports multiple modes of operation:

1.  **CLI Mode**: For command-line interaction and scripting.

    ```bash
    python main.py
    ```

2.  **GUI Mode**: For a rich, real-time monitoring and interaction experience.

    ```bash
    python gui_launcher.py
    ```

3.  **Docker Container**: For isolated, portable, and consistent deployment.

    ```bash
    # Build the Docker image
    docker build -t luna .

    # Run the container (CLI mode, mounting config.yaml)
    docker run -it --rm -v $(pwd)/config.yaml:/app/config.yaml luna
    ```

## Deliverables

This project delivers a comprehensive and functional LUNA 2.0 Cognitive Operating Agent, including:

1.  **Advanced Architecture Design**: Detailed documentation of LUNA's multi-layer cognitive orchestration engine with device automation.
2.  **Enhanced Module Breakdown**: A clear overview of all upgraded components and their interconnections.
3.  **Advanced Control Loop Implementation**: The iterative reasoning cycle (Analyze → Plan → Execute → Reflect) fully implemented with self-healing.
4.  **Robust LLM Abstraction**: A flexible and powerful LLM provider system with advanced continuation capabilities.
5.  **Advanced Execution Kernel**: A deterministic and safe execution layer for full OS automation.
6.  **Dynamic Tool Discovery**: A plugin system for extensibility.
7.  **Comprehensive Documentation**: This updated `README.md` and `luna_advanced_automation_architecture.md`.

---

**Project Status: ✓ COMPLETE AND VERIFIED**

This project was bootstrapped by Manus AI.
