"""
LUNA AI Agent - OS Agent Entry Point v11.0
Author: IRFAN

Structural Stabilization Refactor:
  - Initialize Task Orchestrator and Persistent Browser.
  - Launch non-blocking GUI monitor.
  - Handle graceful shutdown.
"""

import os
import yaml
import logging
import threading
import sys
from core.loop import CognitiveLoop
from gui.monitor import start_gui

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("luna.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("luna.main")

def load_config():
    """Load system configuration from config.yaml."""
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    logger.info("--- LUNA OS AGENT STARTING ---")
    
    # 1. Load Config
    config = load_config()
    
    # 2. Initialize Cognitive Loop (Brain + Orchestrator)
    try:
        loop = CognitiveLoop(config)
        logger.info("Cognitive Loop initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Cognitive Loop: {e}")
        sys.exit(1)

    # 3. Start Voice Passive Listening (if enabled)
    if loop.voice.enabled:
        loop.start_voice_mode()
        logger.info("Voice passive listening started.")

    # 4. Launch GUI (Main Thread)
    try:
        logger.info("Launching GUI...")
        start_gui(loop)
    except Exception as e:
        logger.error(f"GUI Error: {e}")
    finally:
        # Graceful Shutdown
        logger.info("Shutting down LUNA...")
        loop.stop()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    main()
