import sys
import os
import yaml
import logging
import time

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

def test_initialization():
    print("\n--- Testing Initialization ---")
    try:
        from os_detector import detect_and_save_os
        detect_and_save_os("config.yaml")
        print("✓ OS Detection passed")
        
        with open("config.yaml", 'r') as f:
            config = yaml.safe_load(f)
        print("✓ Config loading passed")
        
        from core.loop import CognitiveLoop
        loop = CognitiveLoop(config)
        print("✓ CognitiveLoop initialization passed")
        
        return loop
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_conversation(loop):
    print("\n--- Testing Conversation ---")
    try:
        # We'll use a mock or a very simple call to avoid long waits if LLM is slow
        print("Sending 'Hello' to LUNA...")
        result = loop.run("Hello")
        print(f"✓ Conversation result: {result.content}")
        return True
    except Exception as e:
        print(f"✗ Conversation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    loop = test_initialization()
    if loop:
        # Set a timeout for the conversation test
        import threading
        
        def run_test():
            test_conversation(loop)
            
        thread = threading.Thread(target=run_test)
        thread.start()
        thread.join(timeout=30)
        
        if thread.is_alive():
            print("\n✗ TEST TIMEOUT: The loop.run() call is hanging!")
            # Try to see where it's hanging by looking at the stack
            import faulthandler
            faulthandler.dump_traceback()
            sys.exit(1)
        else:
            print("\nAll diagnostic tests completed.")
    else:
        sys.exit(1)
