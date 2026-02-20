"""
LUNA AI Agent - Main Entry Point
Author: IRFAN

Main entry point for LUNA cognitive operating agent.
"""

import sys
import os
import yaml
from core.loop import CognitiveLoop
from execution.kernel import ExecutionResult


def print_banner():
    """Print LUNA banner."""
    banner = """
╔══════════════════════════════════════════╗
║                                          ║
║           LUNA COGNITIVE AGENT           ║
║   High-Autonomy Operating System Core    ║
║   Author: IRFAN                          ║
║                                          ║
╚══════════════════════════════════════════╝
"""
    print(banner)


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def print_result(result: ExecutionResult):
    """Print execution result."""
    status_symbol = {
        "success": "✓",
        "failed": "✗",
        "partial": "⚠"
    }
    
    symbol = status_symbol.get(result.status, "?")
    
    print(f"\n{symbol} Status: {result.status.upper()}")
    
    if result.content:
        print(f"\nContent:\n{result.content}")
    
    if result.error:
        print(f"\nError: {result.error}")
    
    print(f"\nRisk Level: {result.risk_level}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Verified: {result.verified}")
    print(f"Execution Used: {result.execution_used}")


def run_cli():
    """Run CLI interface."""
    print_banner()
    
    # Initialize cognitive loop
    try:
        config = load_config("config.yaml")
        loop = CognitiveLoop(config)
        print(f"\n✓ LUNA initialized successfully")
        print(f"  LLM Mode: {loop.llm_manager.mode}")
        print(f"  Default Provider: {loop.llm_manager.default_provider_name}")
    except Exception as e:
        print(f"\n✗ Failed to initialize LUNA: {e}")
        print("\nPlease check your config.yaml and ensure API keys are set.")
        return
    
    print("\nType 'exit' or 'quit' to exit")
    print("Type 'reset' to reset memory\n")
    
    # Main loop
    while True:
        try:
            user_input = input(f"\nLUNA> ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit']:
                print("\nGoodbye!")
                break
            
            if user_input.lower() == 'reset':
                loop.memory_system.clear_short_term()
                print("\n✓ Memory reset")
                continue
            
            # Process input through cognitive loop
            print(f"\nProcessing goal: {user_input}")
            result = loop.run(user_input)
            print_result(result)
            
        except (KeyboardInterrupt, EOFError):
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n✗ Error: {e}")


def main():
    """Main entry point."""
    run_cli()


if __name__ == "__main__":
    main()
