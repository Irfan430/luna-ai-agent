import os
import yaml
import logging
import sys
import time
from core.loop import CognitiveLoop

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("luna.e2e_test")

def load_config():
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    # Use OpenAI for testing in this environment
    config["llm"]["default_provider"] = "openai"
    if config["llm"]["providers"]["openai"]["api_key"].startswith("your-"):
        config["llm"]["providers"]["openai"]["api_key"] = os.getenv("OPENAI_API_KEY")
    return config

def run_task(loop, goal):
    print(f"\n>>> Task: {goal}")
    loop.run(goal)
    # Wait for task to be processed (orchestrator runs in background)
    timeout = 30
    start_time = time.time()
    # Initial wait for queue to be populated if needed
    time.sleep(2)
    while loop.task_queue.qsize() > 0:
        if time.time() - start_time > timeout:
            print("!!! Task timed out")
            break
        time.sleep(1)
    
    time.sleep(2) # Final wait for processing
    if loop.memory.short_term:
        last_msg = loop.memory.short_term[-1]
        print(f"LUNA Response: {last_msg['content']}")
    else:
        print("!!! No response received")

if __name__ == "__main__":
    config = load_config()
    loop = CognitiveLoop(config)
    
    # Task 1: Simple conversation
    run_task(loop, "Hello LUNA, who are you?")
    
    # Task 2: System command
    run_task(loop, "Check the current directory files.")
    
    # Cleanup
    loop.stop()
    print("\nE2E Test Completed.")
