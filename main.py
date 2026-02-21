"""
LUNA AI Agent - Unified Entry Point v12.0
Author: IRFAN
Revision: Manus AI

Unified Entry Point:
  - Supports both GUI and CLI modes.
  - Usage: 
      python main.py         (Default: GUI)
      python main.py --cli   (CLI Mode)
"""
import os
import yaml
import logging
import threading
import sys
import argparse
from core.loop import CognitiveLoop

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

def run_cli(loop):
    """Run LUNA in Command Line Interface mode."""
    print("\n" + "="*50)
    print(" LUNA AI Agent - CLI Mode")
    print(" Type 'exit' or 'quit' to stop.")
    print("="*50 + "\n")
    
    while True:
        try:
            user_input = input("User > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                break
            
            print("LUNA is thinking...")
            loop.run(user_input)
            
            # Wait for processing
            import time
            while loop.task_queue.qsize() > 0:
                time.sleep(0.5)
            
            # Small delay for memory update
            time.sleep(1)
            if loop.memory.short_term:
                last_msg = loop.memory.short_term[-1]
                if last_msg['role'] == 'assistant':
                    print(f"LUNA > {last_msg['content']}")
                else:
                    # Check if there's a response in the history
                    found = False
                    for msg in reversed(loop.memory.short_term):
                        if msg['role'] == 'assistant':
                            print(f"LUNA > {msg['content']}")
                            found = True
                            break
                    if not found:
                        print("LUNA > (Action executed successfully)")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"CLI Error: {e}")
            print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="LUNA AI Agent")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode instead of GUI")
    args = parser.parse_args()

    logger.info("--- LUNA OS AGENT STARTING ---")
    
    # 1. Load Config
    config = load_config()
    
    # 2. Initialize Cognitive Loop
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

    # 4. Launch Mode
    if args.cli:
        try:
            run_cli(loop)
        finally:
            logger.info("Shutting down LUNA...")
            loop.stop()
    else:
        try:
            from gui.monitor import start_gui
            logger.info("Launching GUI...")
            start_gui(loop)
        except Exception as e:
            logger.error(f"GUI Error: {e}")
            print(f"GUI failed to start. Try running with --cli. Error: {e}")
        finally:
            logger.info("Shutting down LUNA...")
            loop.stop()

if __name__ == "__main__":
    main()
