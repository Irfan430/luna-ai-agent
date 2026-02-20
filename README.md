# LUNA AI Agent - v7.0
Author: IRFAN

**LUNA (Latent Understanding & Neural Architecture)** is a fully autonomous, cross-platform cognitive operating system layer. This repository contains the complete source code for LUNA v7.0, featuring a core stabilization and structural consistency upgrade.

![LUNA Architecture](architecture.png)

---

## Key Features

| Feature                  | Description                                                                                                                              |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **Strict Brain Contract**| All LLM outputs are normalized into a strict `BrainOutput` model to prevent routing crashes and handle unexpected inputs.                |
| **Routing Guard**        | Conversational requests bypass the execution layer completely, and numeric inputs are handled safely without entering cognitive loops.    |
| **Execution Transparency**| Real-time file creation visibility with absolute path reporting, file size verification, and detailed error reporting.                   |
| **Logging Fix**          | The execution timeline now logs actual action names, real results, success/failure status, and precise timestamps.                       |
| **Voice UI Integrity**   | Visual indicators for voice states (Active, Passive, Wake Detected) are now linked to the real listener thread state.                    |
| **System Tray Fix**      | Improved tray icon initialization with platform support checks and error-free icon loading.                                              |
| **Error Isolation**      | Cognitive errors are isolated from the UI thread, preventing crashes and returning structured error reports to the chat.                 |

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

## Structural Consistency Upgrade Summary (v7.0)

| Phase | Module(s) Affected | Key Upgrades Implemented |
| :--- | :--- | :--- |
| **1. Brain Contract** | `llm/router.py` | - `BrainOutput` model for normalized responses.<br>- `normalize_brain_output` for crash prevention. |
| **2. Routing Guard** | `core/loop.py` | - Conversation bypasses execution layer.<br>- Numeric input safety guard. |
| **3. Transparency** | `execution/kernel.py` | - Absolute path and file size reporting.<br>- Real error reporting for file operations. |
| **4. Logging Fix** | `gui/monitor.py` | - Detailed timeline logging with timestamps.<br>- No fake success allowed. |
| **5. Voice UI** | `gui/monitor.py` | - Visual state indicators (Green/Gray).<br>- Linked to real listener thread. |
| **6. System Tray** | `gui/monitor.py` | - Platform support checks.<br>- Valid icon loading logic. |
| **7. Error Isolation** | `gui/monitor.py` | - Try/except wrap for cognitive routing.<br>- Structured error reporting to chat. |
