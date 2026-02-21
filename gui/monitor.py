"""
LUNA AI Agent - OS Agent GUI v11.0
Author: IRFAN

Structural Stabilization Refactor:
  - Non-blocking GUI interaction with Task Orchestrator.
  - Mode and Voice toggles.
  - Real-time status and memory display.
"""

import sys
import logging
import psutil
from typing import Dict, Any
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                             QLabel, QComboBox, QCheckBox, QProgressBar)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject

logger = logging.getLogger("luna.gui.monitor")

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QTextEdit {
    background-color: #252526;
    border: 1px solid #3e3e3e;
    border-radius: 4px;
    padding: 8px;
}
QLineEdit {
    background-color: #3c3c3c;
    border: 1px solid #3e3e3e;
    border-radius: 4px;
    padding: 8px;
    color: white;
}
QPushButton {
    background-color: #007acc;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
}
QPushButton:hover {
    background-color: #0062a3;
}
"""

class GUISignals(QObject):
    update_log = pyqtSignal(str)
    update_memory = pyqtSignal(str)

class LUNAMonitor(QMainWindow):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.signals = GUISignals()
        self.setStyleSheet(DARK_STYLE)
        self.init_ui()
        
        # Connect signals
        self.signals.update_log.connect(self.append_log)
        self.signals.update_memory.connect(self.refresh_memory)
        
        # Periodic refresh timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.periodic_update)
        self.timer.start(1000)

    def init_ui(self):
        self.setWindowTitle("LUNA OS Agent - DeepSeek Orchestrator")
        self.setMinimumSize(1000, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        
        # Left Panel: Main Interaction
        left_panel = QVBoxLayout()
        
        # Header
        header = QHBoxLayout()
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("font-weight: bold; color: #007acc;")
        header.addWidget(self.status_label)
        header.addStretch()
        
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["FAST", "AGENT"])
        self.mode_selector.currentTextChanged.connect(self.change_mode)
        header.addWidget(QLabel("Mode:"))
        header.addWidget(self.mode_selector)
        
        self.voice_toggle = QCheckBox("Voice Enabled")
        self.voice_toggle.setChecked(self.loop.voice.enabled)
        self.voice_toggle.stateChanged.connect(self.toggle_voice)
        header.addWidget(self.voice_toggle)
        left_panel.addLayout(header)
        
        # Memory Display
        left_panel.addWidget(QLabel("Conversation History:"))
        self.memory_display = QTextEdit()
        self.memory_display.setReadOnly(True)
        left_panel.addWidget(self.memory_display)
        
        # Input Area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter command for LUNA (e.g., 'open browser and search for news')...")
        self.input_field.returnPressed.connect(self.send_command)
        
        self.send_btn = QPushButton("Execute")
        self.send_btn.clicked.connect(self.send_command)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        left_panel.addLayout(input_layout)
        
        # Right Panel: System Stats & Logs
        right_panel = QVBoxLayout()
        right_panel.setFixedWidth(300)
        
        # Stats
        right_panel.addWidget(QLabel("System Resources:"))
        self.cpu_bar = QProgressBar()
        self.ram_bar = QProgressBar()
        right_panel.addWidget(QLabel("CPU:"))
        right_panel.addWidget(self.cpu_bar)
        right_panel.addWidget(QLabel("RAM:"))
        right_panel.addWidget(self.ram_bar)
        
        right_panel.addSpacing(20)
        
        # Logs
        right_panel.addWidget(QLabel("Real-time Logs:"))
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(Qt.ScrollBarAlwaysOff) # Use small font
        self.log_display.setStyleSheet("font-size: 10px; color: #888;")
        right_panel.addWidget(self.log_display)
        
        layout.addLayout(left_panel, 3)
        layout.addLayout(right_panel, 1)

    def send_command(self):
        text = self.input_field.text().strip()
        if text:
            self.append_log(f"User Input: {text}")
            self.loop.run(text)
            self.input_field.clear()
            self.status_label.setText("Status: Processing...")

    def append_log(self, text):
        self.log_display.append(text)

    def refresh_memory(self, text):
        self.memory_display.setText(text)

    def change_mode(self, mode):
        self.loop.mode = mode
        self.append_log(f"System: Switched to {mode} mode.")

    def toggle_voice(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.loop.voice.enabled = enabled
        self.append_log(f"System: Voice {'enabled' if enabled else 'disabled'}.")
        if enabled:
            self.loop.start_voice_mode()
        else:
            self.loop.voice.stop_passive_listening()

    def periodic_update(self):
        # Update memory display
        history_text = ""
        for entry in self.loop.memory.short_term:
            role = entry['role'].upper()
            content = entry['content']
            history_text += f"<b>{role}:</b> {content}<br><br>"
        self.signals.update_memory.emit(history_text)
        
        # Update status
        qsize = self.loop.task_queue.qsize()
        if qsize == 0:
            self.status_label.setText("Status: Ready")
        else:
            self.status_label.setText(f"Status: Processing ({qsize} tasks in queue)")
            
        # Update bars
        self.cpu_bar.setValue(int(psutil.cpu_percent()))
        self.ram_bar.setValue(int(psutil.virtual_memory().percent))

def start_gui(loop):
    app = QApplication(sys.argv)
    monitor = LUNAMonitor(loop)
    monitor.show()
    sys.exit(app.exec())
