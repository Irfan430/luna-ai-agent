"""
LUNA AI Agent - Verification Script
Author: IRFAN

Verify LUNA 2.0 with real-world device automation tasks using DeepSeek API.
"""

import yaml
import os
from core.loop import CognitiveLoop


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def verify_luna():
    """Run verification tasks for LUNA."""
    print("--- LUNA 2.0 VERIFICATION START ---")
    
    try:
        config = load_config("config.yaml")
        loop = CognitiveLoop(config)
        
        # Task 1: System Information Retrieval
        print("\n[TASK 1] Get detailed system information and save to a file.")
        result1 = loop.run("Get detailed system information (OS, CPU, Memory, Disk) and save it to a file named 'system_report.txt' in the current directory.")
        print(f"Task 1 Status: {result1.status}")
        
        # Task 2: Process Monitoring
        print("\n[TASK 2] Find all Python processes and list them.")
        result2 = loop.run("Find all running Python processes on this system and list their PIDs and names.")
        print(f"Task 2 Status: {result2.status}")
        
        # Task 3: Network Check
        print("\n[TASK 3] Check connectivity to google.com and verify port 443.")
        result3 = loop.run("Check if google.com is reachable via ping and verify if port 443 is open on google.com.")
        print(f"Task 3 Status: {result3.status}")
        
        print("\n--- LUNA 2.0 VERIFICATION COMPLETE ---")
        
    except Exception as e:
        print(f"\nVerification failed with error: {e}")


if __name__ == "__main__":
    verify_luna()
