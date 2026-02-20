"""
LUNA AI Agent - GUI Launcher
Author: IRFAN

Launch LUNA GUI interface.
"""

import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow


def main():
    """Launch GUI."""
    app = QApplication(sys.argv)
    app.setApplicationName("LUNA AI Agent")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
