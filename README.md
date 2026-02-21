# LUNA AI Agent - OS Agent v12.0

LUNA is an advanced AI agent designed to control your OS, browse the web, and perform tasks through a unified interface.

## Features
- **Unified Entry Point:** Run both GUI and CLI from a single file.
- **Persistent Browser:** Uses Playwright for web automation.
- **Memory System:** 5-day rolling history for context-aware interactions.
- **Voice Support:** Integrated TTS and Speech Recognition.
- **System Monitoring:** Real-time CPU and RAM usage display in GUI.

## Installation

### Prerequisites
- Python 3.11+
- `pip` for package installation

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/Irfan430/luna-ai-agent.git
   cd luna-ai-agent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. Configure API Keys:
   Edit `config.yaml` and add your DeepSeek or OpenAI API keys.

## Usage

### GUI Mode (Default)
```bash
python main.py
```

### CLI Mode
```bash
python main.py --cli
```

## Configuration
All settings are managed in `config.yaml`. You can toggle voice, change LLM providers, and adjust browser settings there.

---
**Author:** IRFAN  
**Revision:** Manus AI
