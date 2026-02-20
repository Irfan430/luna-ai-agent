"""
LUNA AI Agent - Main Entry Point
Author: IRFAN

Main entry point for LUNA agent.
"""

import sys
import os
from core.agent import LunaAgent
from core.task_result import TaskResult


def print_banner():
    """Print LUNA banner."""
    banner = """
╔══════════════════════════════════════════╗
║                                          ║
║           LUNA AI AGENT v1.0             ║
║   Personal AI Operating Agent            ║
║   Author: IRFAN                          ║
║                                          ║
╚══════════════════════════════════════════╝
"""
    print(banner)


def print_result(result: TaskResult):
    """Print task result."""
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
    
    # Initialize agent
    try:
        agent = LunaAgent()
        print(f"\n✓ {agent.name} initialized successfully")
        print(f"  LLM Mode: {agent.llm_manager.mode}")
        print(f"  Provider: {agent.llm_manager.get_active_provider_name()}")
    except Exception as e:
        print(f"\n✗ Failed to initialize agent: {e}")
        print("\nPlease check your config.yaml and ensure API keys are set.")
        return
    
    print("\nType 'exit' or 'quit' to exit")
    print("Type 'status' to see agent status")
    print("Type 'reset' to reset conversation history\n")
    
    # Main loop
    while True:
        try:
            user_input = input(f"\n{agent.name}> ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit']:
                print("\nGoodbye!")
                break
            
            if user_input.lower() == 'status':
                status = agent.get_status()
                print("\nAgent Status:")
                for key, value in status.items():
                    print(f"  {key}: {value}")
                continue
            
            if user_input.lower() == 'reset':
                agent.reset()
                print("\n✓ Agent state reset")
                continue
            
            # Process input
            print(f"\nProcessing...")
            result = agent.process_input(user_input)
            print_result(result)
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Type 'exit' to quit.")
        except Exception as e:
            print(f"\n✗ Error: {e}")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Future: handle command line arguments
        print("Command line arguments not yet supported. Running CLI mode.")
    
    run_cli()


if __name__ == "__main__":
    main()
