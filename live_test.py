import os
import yaml
import logging
from core.loop import CognitiveLoop

# Configure logging
logging.basicConfig(level=logging.INFO)

def run_live_test():
    print("\n🚀 STARTING LUNA LIVE TEST...")
    
    # Load config (ensure OPENAI_API_KEY is available)
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment.")
        return

    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    # Initialize Loop
    try:
        loop = CognitiveLoop(config)
        print("✅ LUNA Initialized.")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return

    # Task 1: Simple conversation
    print("\n--- Task 1: Conversation ---")
    res1 = loop.run("Hello LUNA, who are you and what is your current mode?")
    print(f"LUNA: {res1.content}")
    
    # Task 2: System command (Check uptime)
    print("\n--- Task 2: System Command (uptime) ---")
    res2 = loop.run("Check the system uptime using shell command.")
    print(f"LUNA Result: {res2.status}")
    print(f"Content: {res2.content}")

    # Task 3: Browser task (Search for LUNA AI)
    # Note: We'll just check if it routes correctly to browser action
    print("\n--- Task 3: Browser Routing ---")
    res3 = loop.run("Search for 'LUNA AI Agent' on Google using the browser.")
    print(f"LUNA Result: {res3.status}")
    print(f"Content: {res3.content}")

if __name__ == "__main__":
    run_live_test()
