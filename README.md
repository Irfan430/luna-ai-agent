# LUNA AI Agent - v6.0
Author: IRFAN

**LUNA (Latent Understanding & Neural Architecture)** is a fully autonomous, cross-platform cognitive operating system layer. This repository contains the complete source code for LUNA v6.0, featuring a performance-focused architectural upgrade.

![LUNA Architecture](architecture.png)

---

## Key Features

| Feature                  | Description                                                                                                                              |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Intent Routing**       | Classifies requests into conversation, direct_action, or complex_plan to minimize cognitive overhead.                                     |
| **Direct Action Pipeline**| Single-pass execution for simple tasks, bypassing the iterative loop for maximum speed.                                                  |
| **Live Visibility**      | Real-time file creation visibility in the GUI, showing code blocks, write status, and verification results.                              |
| **Execution Control**    | GUI now features a STOP button to interrupt tasks, with input field locking during execution.                                            |
| **Voice UI Improvements**| Visual feedback for voice activity, system tray support, and continuous background operation.                                            |
| **Speed Optimization**   | Reduced plan regeneration and redundant reflection loops, with strict iteration limits based on task complexity.                         |
| **Failure Clarity**      | Detailed error reporting including exact errors, attempted actions, verification results, and LLM-suggested fixes.                       |

---

## Installation

### Prerequisites
- Python 3.11+
- `pip` for package installation

### Linux
```bash
sudo apt install portaudio19-dev ffmpeg xdotool wmctrl playerctl libasound2-dev
pip install -r requirements.txt
playwright install
```

### Windows
- Install Visual C++ Redistributable
- Install FFmpeg
- `pip install -r requirements.txt`
- `playwright install`

### macOS
```bash
brew install portaudio ffmpeg
pip install -r requirements.txt
playwright install
```

---

## Usage

### Running LUNA
To start the agent with the GUI:
```bash
python main.py
```

### Docker
Build and run the containerized version:
```bash
docker build -t luna-agent .
docker run -it luna-agent
```

---

## Architectural Upgrade Summary (v6.0)

| Phase | Module(s) Affected | Key Upgrades Implemented |
| :--- | :--- | :--- |
| **1. Intent Routing** | `llm/router.py` | - New classification: conversation, direct_action, complex_plan.<br>- Conversation bypasses planning. |
| **2. Direct Action** | `core/loop.py` | - Single-pass execution for direct_action mode.<br>- Verification-first approach. |
| **3. Live Visibility** | `execution/kernel.py` | - Code block display during file creation.<br>- File size and path verification. |
| **4. GUI Control** | `gui/monitor.py` | - STOP button to interrupt execution thread.<br>- Input field locking during tasks. |
| **5. Voice UI** | `gui/monitor.py` | - Visual feedback for voice states.<br>- System tray icon support. |
| **6. Speed** | `core/loop.py` | - Iteration limits (1 for simple, 5 for complex).<br>- Reduced redundant reflection. |
| **7. Failure Clarity** | `core/loop.py` | - Detailed error reporting.<br>- LLM-suggested fixes on failure. |
