"""
LUNA AI Agent - GUI Launcher
Author: IRFAN

Launch LUNA cognitive monitor interface.
"""

import sys
import os
import yaml
from PyQt6.QtWidgets import QApplication
from gui.monitor import MonitorWindow


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def main():
    """Launch GUI."""
    app = QApplication(sys.argv)
    app.setApplicationName("LUNA COGNITIVE MONITOR")
    
    try:
        config = load_config("config.yaml")
        window = MonitorWindow(config)
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Failed to launch GUI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
