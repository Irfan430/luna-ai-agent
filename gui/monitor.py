"""
LUNA AI Agent - OS Agent GUI v11.1
Author: IRFAN
Revision: Manus AI

Structural Stabilization Refactor:
  - Non-blocking GUI interaction with Task Orchestrator.
  - Mode and Voice toggles.
  - Real-time status and memory display.
  - Fixed font setting bug.
  - Externalized stylesheet.
"""
import sys
import logging
import psutil
import os
from typing import Dict, Any
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                             QLabel, QComboBox, QCheckBox, QProgressBar)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont

logger = logging.getLogger("luna.gui.monitor")

class LUNASignals(QObject):
    update_log = pyqtSignal(str)
    update_memory = pyqtSignal(str)

class LUNAMonitor(QMainWindow):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.signals = LUNASignals()

        self.init_ui()
        self.load_stylesheet()
        
        self.signals.update_log.connect(self.append_log)
        self.signals.update_memory.connect(self.refresh_memory)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.periodic_update)
        self.timer.start(1000)

    def init_ui(self):
        self.setWindowTitle("LUNA OS Agent - DeepSeek Orchestrator")
        self.setMinimumSize(1000, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        
        left_panel = QVBoxLayout()
        
        header = QHBoxLayout()
        self.status_label = QLabel("Status: Ready")
        self.status_label.setObjectName("statusLabel")
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
        
        left_panel.addWidget(QLabel("Conversation History:"))
        self.memory_display = QTextEdit()
        self.memory_display.setReadOnly(True)
        left_panel.addWidget(self.memory_display)
        
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter command for LUNA...")
        self.input_field.returnPressed.connect(self.send_command)
        
        self.send_btn = QPushButton("Execute")
        self.send_btn.clicked.connect(self.send_command)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        left_panel.addLayout(input_layout)
        
        right_panel_widget = QWidget()
        right_panel_widget.setFixedWidth(300)
        right_panel = QVBoxLayout(right_panel_widget)
        
        right_panel.addWidget(QLabel("System Resources:"))
        self.cpu_bar = QProgressBar()
        self.ram_bar = QProgressBar()
        right_panel.addWidget(QLabel("CPU:"))
        right_panel.addWidget(self.cpu_bar)
        right_panel.addWidget(QLabel("RAM:"))
        right_panel.addWidget(self.ram_bar)
        
        right_panel.addSpacing(20)
        
        right_panel.addWidget(QLabel("Real-time Logs:"))
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        log_font = QFont("Monospace")
        log_font.setPointSize(10)
        self.log_display.setFont(log_font)
        right_panel.addWidget(self.log_display)
        
        layout.addLayout(left_panel, 3)
        layout.addWidget(right_panel_widget, 1)

    def load_stylesheet(self):
        style_path = os.path.join(os.path.dirname(__file__), "style.qss")
        try:
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            logger.warning("Stylesheet (style.qss) not found. Using default style.")

    def send_command(self):
        text = self.input_field.text().strip()
        if text:
            self.signals.update_log.emit(f"User Input: {text}")
            self.loop.run(text)
            self.input_field.clear()
            self.status_label.setText("Status: Processing...")

    def append_log(self, text):
        self.log_display.append(text)

    def refresh_memory(self, text):
        self.memory_display.setHtml(text)

    def change_mode(self, mode):
        self.loop.mode = mode
        self.signals.update_log.emit(f"System: Switched to {mode} mode.")

    def toggle_voice(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.loop.voice.enabled = enabled
        state_str = "enabled" if enabled else "disabled"
        self.signals.update_log.emit(f"System: Voice {state_str}.")
        if enabled:
            self.loop.start_voice_mode()
        else:
            self.loop.voice.stop_passive_listening()

    def periodic_update(self):
        history_text = ""
        for entry in self.loop.memory.short_term:
            role = entry["role"].upper()
            content = entry["content"].replace("\n", "<br>")
            history_text += f"<b>{role}:</b> {content}<br><br>"
        self.signals.update_memory.emit(history_text)
        
        qsize = self.loop.task_queue.qsize()
        if qsize == 0 and "Processing" in self.status_label.text():
             self.status_label.setText("Status: Ready")
        elif qsize > 0:
            self.status_label.setText(f"Status: Processing ({qsize} tasks in queue)")
            
        self.cpu_bar.setValue(int(psutil.cpu_percent()))
        self.ram_bar.setValue(int(psutil.virtual_memory().percent))

def start_gui(loop):
    app = QApplication(sys.argv)
    monitor = LUNAMonitor(loop)
    monitor.show()
    sys.exit(app.exec())
