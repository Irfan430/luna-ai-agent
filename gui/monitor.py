"""
LUNA AI Agent - Professional GUI v5.0
Author: IRFAN

Phase 6: Professional GUI
  - Chat panel with proper SEND button.
  - Execution timeline panel.
  - Process monitor.
  - Resource monitor (CPU/RAM).
  - Config editor panel.
  - Active LLM provider display.
  - Risk level indicator.
  - Token usage display.
  - Voice control button.
"""

import sys
import os
import time
import psutil
import yaml
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QProgressBar,
    QTabWidget, QListWidget, QFrame, QSplitter, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QStatusBar,
    QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor, QIcon

from core.loop import CognitiveLoop
from core.task_result import TaskResult

logger = logging.getLogger("luna.gui.monitor")

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
    font-family: Consolas, 'Courier New', monospace;
}
QTabWidget::pane {
    border: 1px solid #3e3e3e;
    background-color: #1e1e1e;
}
QTabBar::tab {
    background: #252526;
    color: #808080;
    padding: 6px 14px;
    border: 1px solid #3e3e3e;
}
QTabBar::tab:selected {
    background: #1e1e1e;
    color: #007acc;
    border-bottom: 2px solid #007acc;
}
"""

class AgentWorker(QThread):
    finished = pyqtSignal(object)
    def __init__(self, loop: CognitiveLoop, goal: str):
        super().__init__()
        self.loop = loop
        self.goal = goal
    def run(self):
        try:
            result = self.loop.run(self.goal)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(TaskResult.failure(str(e)))

class MonitorWindow(QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.loop = CognitiveLoop(config)
        self.setStyleSheet(DARK_STYLE)
        self.init_ui()
        
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(2000)

    def init_ui(self):
        self.setWindowTitle("LUNA 5.0 — COGNITIVE OPERATING SYSTEM")
        self.setMinimumSize(1200, 800)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        
        # Left: Chat & Timeline
        left_panel = QSplitter(Qt.Orientation.Vertical)
        
        # Chat
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        chat_layout.addWidget(QLabel("LUNA CHAT"))
        chat_layout.addWidget(self.chat_display)
        
        # Input
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your goal...")
        self.input_field.returnPressed.connect(self.send_goal)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_goal)
        self.voice_btn = QPushButton("🎤")
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.voice_btn)
        input_layout.addWidget(self.send_btn)
        chat_layout.addLayout(input_layout)
        
        # Timeline
        self.timeline = QTableWidget(0, 3)
        self.timeline.setHorizontalHeaderLabels(["Time", "Action", "Status"])
        self.timeline.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        left_panel.addWidget(chat_widget)
        left_panel.addWidget(self.timeline)
        
        # Right: Monitors
        right_panel = QTabWidget()
        right_panel.setFixedWidth(350)
        
        # Monitor Tab
        mon_tab = QWidget()
        mon_layout = QVBoxLayout(mon_tab)
        self.cpu_bar = QProgressBar()
        self.ram_bar = QProgressBar()
        mon_layout.addWidget(QLabel("CPU USAGE"))
        mon_layout.addWidget(self.cpu_bar)
        mon_layout.addWidget(QLabel("RAM USAGE"))
        mon_layout.addWidget(self.ram_bar)
        
        self.provider_lbl = QLabel(f"Provider: {self.config['llm']['default_provider']}")
        self.risk_lbl = QLabel("Risk: Low")
        self.token_lbl = QLabel("Tokens: 0")
        mon_layout.addWidget(self.provider_lbl)
        mon_layout.addWidget(self.risk_lbl)
        mon_layout.addWidget(self.token_lbl)
        mon_layout.addStretch()
        
        # Config Tab
        self.config_edit = QTextEdit()
        self.config_edit.setPlainText(yaml.dump(self.config))
        
        right_panel.addTab(mon_tab, "Monitor")
        right_panel.addTab(self.config_edit, "Config")
        
        layout.addWidget(left_panel, 3)
        layout.addWidget(right_panel, 1)

    def update_stats(self):
        self.cpu_bar.setValue(int(psutil.cpu_percent()))
        self.ram_bar.setValue(int(psutil.virtual_memory().percent))
        self.token_lbl.setText(f"Tokens: {self.loop.memory_system.get_token_count()}")

    def send_goal(self):
        goal = self.input_field.text().strip()
        if not goal: return
        self.chat_display.append(f"<b>USER:</b> {goal}")
        self.input_field.clear()
        self.worker = AgentWorker(self.loop, goal)
        self.worker.finished.connect(self.handle_result)
        self.worker.start()

    def handle_result(self, result):
        self.chat_display.append(f"<b>LUNA:</b> {result.content}")
        row = self.timeline.rowCount()
        self.timeline.insertRow(row)
        self.timeline.setItem(row, 0, QTableWidgetItem(time.strftime("%H:%M:%S")))
        self.timeline.setItem(row, 1, QTableWidgetItem("Task Execution"))
        self.timeline.setItem(row, 2, QTableWidgetItem(result.status))

def run_gui(config):
    app = QApplication(sys.argv)
    win = MonitorWindow(config)
    win.show()
    sys.exit(app.exec())
