"""
LUNA AI Agent - Professional GUI v9.0
Author: IRFAN

Phase 7 & 8: Performance Mode & GUI Upgrade
  - FAST / AGENT mode switch.
  - Voice On/Off toggle.
  - Live voice transcription.
  - Action log & execution result.
  - Minimize without killing voice.
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
    QGroupBox, QCheckBox, QSystemTrayIcon, QMenu, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor, QIcon, QAction

from core.loop import CognitiveLoop
from core.task_result import TaskResult
from voice.engine import VoiceEngine

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
        self._is_running = True

    def run(self):
        try:
            result = self.loop.run(self.goal)
            if self._is_running:
                self.finished.emit(result)
        except Exception as e:
            logger.error(f"Cognitive error: {e}")
            if self._is_running:
                self.finished.emit(TaskResult.failure(f"Cognitive Engine Error: {str(e)}"))

    def stop(self):
        self._is_running = False
        self.terminate()
        self.wait()

class MonitorWindow(QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.loop = CognitiveLoop(config)
        self.voice_engine = VoiceEngine(config)
        self.worker = None
        self.setStyleSheet(DARK_STYLE)
        self.init_ui()
        self.init_tray()
        
        if self.voice_engine.enabled:
            QTimer.singleShot(1000, self.start_voice_system)
        
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(2000)

    def init_ui(self):
        self.setWindowTitle("LUNA 9.0 — REAL-TIME SYSTEM COMPANION")
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
        self.input_field.returnPressed.connect(self.handle_action)
        
        self.action_btn = QPushButton("Send")
        self.action_btn.clicked.connect(self.handle_action)
        self.action_btn.setStyleSheet("background-color: #007acc; color: white; padding: 8px 20px;")
        
        self.voice_btn = QPushButton("🎤")
        self.voice_btn.setCheckable(True)
        self.voice_btn.toggled.connect(self.toggle_voice)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.voice_btn)
        input_layout.addWidget(self.action_btn)
        chat_layout.addLayout(input_layout)
        
        # Timeline / Action Log
        self.timeline = QTableWidget(0, 4)
        self.timeline.setHorizontalHeaderLabels(["Timestamp", "Action", "Status", "Result"])
        self.timeline.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        left_panel.addWidget(chat_widget)
        left_panel.addWidget(self.timeline)
        
        # Right: Monitors & Settings
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
        
        # Mode Switch
        mon_layout.addWidget(QLabel("PERFORMANCE MODE"))
        self.mode_switch = QComboBox()
        self.mode_switch.addItems(["FAST", "AGENT"])
        self.mode_switch.currentTextChanged.connect(self.change_mode)
        mon_layout.addWidget(self.mode_switch)
        
        # Voice Toggle
        self.voice_toggle = QCheckBox("Always-on Voice")
        self.voice_toggle.setChecked(self.voice_engine.enabled)
        self.voice_toggle.stateChanged.connect(self.toggle_voice_system)
        mon_layout.addWidget(self.voice_toggle)
        
        self.voice_status_lbl = QLabel("Voice: Passive Mode")
        self.voice_status_lbl.setStyleSheet("color: gray;")
        mon_layout.addWidget(self.voice_status_lbl)
        
        mon_layout.addStretch()
        
        # Config Tab
        self.config_edit = QTextEdit()
        self.config_edit.setPlainText(yaml.dump(self.config))
        
        right_panel.addTab(mon_tab, "Monitor")
        right_panel.addTab(self.config_edit, "Config")
        
        layout.addWidget(left_panel, 3)
        layout.addWidget(right_panel, 1)

    def init_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = "architecture.png"
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        self.tray_icon.setToolTip("LUNA AI Agent")
        menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.showNormal)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(show_action)
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def update_stats(self):
        self.cpu_bar.setValue(int(psutil.cpu_percent()))
        self.ram_bar.setValue(int(psutil.virtual_memory().percent))

    def change_mode(self, mode):
        self.loop.mode = mode
        self.chat_display.append(f"<i>System: Switched to {mode} mode.</i>")

    def toggle_voice_system(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.voice_engine.enabled = enabled
        if enabled:
            self.start_voice_system()
        else:
            self.voice_engine.stop_passive_listening()
            self.voice_status_lbl.setText("Voice: Disabled")

    def handle_action(self):
        if self.action_btn.text() == "Send":
            self.send_goal()
        else:
            self.stop_task()

    def send_goal(self):
        goal = self.input_field.text().strip()
        if not goal: return
        self.chat_display.append(f"<b>YOU:</b> {goal}")
        self.input_field.clear()
        self.input_field.setEnabled(False)
        self.action_btn.setText("STOP")
        self.action_btn.setStyleSheet("background-color: #d13438; color: white; padding: 8px 20px;")
        self.worker = AgentWorker(self.loop, goal)
        self.worker.finished.connect(self.handle_result)
        self.worker.start()

    def stop_task(self):
        if self.worker:
            self.worker.stop()
            self.chat_display.append("<i>Task interrupted by user.</i>")
            self.reset_ui()

    def handle_result(self, result):
        self.chat_display.append(f"<b>LUNA:</b> {result.content}")
        row = self.timeline.rowCount()
        self.timeline.insertRow(row)
        timestamp = time.strftime("%H:%M:%S")
        self.timeline.setItem(row, 0, QTableWidgetItem(timestamp))
        self.timeline.setItem(row, 1, QTableWidgetItem("Action"))
        self.timeline.setItem(row, 2, QTableWidgetItem(result.status.upper()))
        self.timeline.setItem(row, 3, QTableWidgetItem(result.content[:50] + "..."))
        self.reset_ui()

    def reset_ui(self):
        self.input_field.setEnabled(True)
        self.action_btn.setText("Send")
        self.action_btn.setStyleSheet("background-color: #007acc; color: white; padding: 8px 20px;")

    def start_voice_system(self):
        self.voice_engine.start_passive_listening(self.handle_voice_command)
        self.voice_status_lbl.setText("Voice: Passive Mode")

    def handle_voice_command(self, command):
        self.chat_display.append(f"<b>YOU (voice):</b> {command}")
        self.input_field.setText(command)
        self.send_goal()

    def toggle_voice(self, checked):
        if checked:
            self.voice_btn.setStyleSheet("background-color: #28a745; color: white;")
            self.voice_status_lbl.setText("Voice: Listening...")
            self.chat_display.append("<i>Voice system: Active Listening...</i>")
        else:
            self.voice_btn.setStyleSheet("")
            self.voice_status_lbl.setText("Voice: Passive Mode")

def run_gui(config):
    app = QApplication(sys.argv)
    win = MonitorWindow(config)
    win.show()
    sys.exit(app.exec())
