"""
LUNA AI Agent - OS Detector v8.0
Author: IRFAN

Phase 1: Install-Time OS Detection
  - Detect OS ONLY ONCE at first run.
  - Store result in config.yaml.
  - Architecture and username detection.
"""

import platform
import os
import yaml
import logging

logger = logging.getLogger("luna.os_detector")

def detect_and_save_os(config_path: str = "config.yaml"):
    """Detect OS and save to config if not already present."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        
        # Check if system info already exists
        if 'system' in config and config['system'].get('os'):
            logger.info(f"OS already detected: {config['system']['os']}")
            return config['system']

        # Detect system info
        system_info = {
            'os': platform.system(),
            'architecture': platform.machine(),
            'username': os.environ.get('USER', 'unknown'),
            'node': platform.node(),
            'release': platform.release(),
            'version': platform.version()
        }

        # Update config
        config['system'] = system_info
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        logger.info(f"OS detected and saved: {system_info['os']}")
        return system_info

    except Exception as e:
        logger.error(f"Error detecting OS: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    detect_and_save_os()
