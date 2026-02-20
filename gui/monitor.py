"""
LUNA AI Agent - Advanced GUI Monitoring Interface v3.0
Author: IRFAN

Phase 3 GUI Professionalization:
  1. Chat panel with proper SEND button (not "Execute").
  2. Execution timeline panel.
  3. Risk level indicator.
  4. Token usage display.
  5. Active LLM provider display.
  6. CPU/RAM live stats.
  7. Process monitor.
  8. Config editor panel (load/edit/save config.yaml).
  9. Voice controls: wake word toggle, mic indicator, passive/active mode.
  10. Fixed MemorySystem attribute error: uses .short_term and .episodic properties.
"""

import os
import yaml
import psutil
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel,
    QSplitter, QStatusBar, QProgressBar, QFrame,
    QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea, QGroupBox, QCheckBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

from core.loop import CognitiveLoop
from execution.kernel import ExecutionResult
from core.task_result import TaskResult

logger = logging.getLogger("luna.gui.monitor")

# ------------------------------------------------------------------
# Stylesheet
# ------------------------------------------------------------------

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
QGroupBox {
    border: 1px solid #3e3e3e;
    margin-top: 8px;
    padding: 6px;
    color: #007acc;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
}
QScrollBar:vertical {
    background: #252526;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: #3e3e3e;
    min-height: 20px;
}
QTableWidget {
    background-color: #1e1e1e;
    gridline-color: #3e3e3e;
    color: #d4d4d4;
}
QHeaderView::section {
    background-color: #252526;
    color: #007acc;
    border: 1px solid #3e3e3e;
    padding: 4px;
}
"""

# ------------------------------------------------------------------
# Worker thread
# ------------------------------------------------------------------

class AgentWorker(QThread):
    """Worker thread for cognitive loop processing."""
    finished = pyqtSignal(object)

    def __init__(self, loop: CognitiveLoop, goal: str):
        super().__init__()
        self.loop = loop
        self.goal = goal

    def run(self):
        """Process goal in background thread."""
        try:
            result = self.loop.run(self.goal)
        except Exception as e:
            logger.error(f"AgentWorker error: {e}")
            result = TaskResult.failure(str(e))
        self.finished.emit(result)


# ------------------------------------------------------------------
# Monitor Window
# ------------------------------------------------------------------

class MonitorWindow(QMainWindow):
    """
    Advanced GUI monitoring window for LUNA 3.0.

    Phase 3 Fix: MemorySystem 'short_term' attribute error resolved.
    Uses .short_term (property) and .episodic (property) correctly.
    """

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.config_path = "config.yaml"
        self.loop = CognitiveLoop(config)
        self.worker: Optional[AgentWorker] = None
        self._execution_timeline: list = []

        self.setStyleSheet(DARK_STYLE)
        self.init_ui()

        # System stats timer
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_system_stats)
        self.stats_timer.start(2000)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def init_ui(self):
        """Initialize all UI panels."""
        self.setWindowTitle("LUNA 3.0 — COGNITIVE OPERATING SYSTEM")
        self.setGeometry(100, 100, 1600, 950)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Header
        root_layout.addWidget(self._build_header())

        # Main splitter: left (chat + timeline) | right (status panels)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: tabbed chat + timeline
        left_tabs = QTabWidget()
        left_tabs.addTab(self._build_chat_panel(), "Chat")
        left_tabs.addTab(self._build_timeline_panel(), "Execution Timeline")
        left_tabs.addTab(self._build_process_panel(), "Process Monitor")
        left_tabs.addTab(self._build_config_panel(), "Config Editor")
        main_splitter.addWidget(left_tabs)

        # Right: status panels
        main_splitter.addWidget(self._build_status_panel())

        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 1)
        root_layout.addWidget(main_splitter)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("LUNA KERNEL READY")

        self.update_status()

    def _build_header(self) -> QFrame:
        """Build top header bar."""
        frame = QFrame()
        frame.setStyleSheet(
            "background-color: #252526; border-bottom: 2px solid #007acc;"
        )
        frame.setFixedHeight(48)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 0, 12, 0)

        title = QLabel("LUNA 3.0  |  ADVANCED COGNITIVE AGENT")
        title.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #007acc; border: none;")
        layout.addWidget(title)

        layout.addStretch()

        self.provider_label = QLabel("PROVIDER: —")
        self.provider_label.setFont(QFont("Consolas", 10))
        self.provider_label.setStyleSheet("color: #4ec9b0; border: none; margin-right: 16px;")
        layout.addWidget(self.provider_label)

        self.sys_info_label = QLabel("CPU: 0% | MEM: 0%")
        self.sys_info_label.setFont(QFont("Consolas", 10))
        self.sys_info_label.setStyleSheet("color: #808080; border: none;")
        layout.addWidget(self.sys_info_label)

        return frame

    def _build_chat_panel(self) -> QWidget:
        """Build chat panel with input and SEND button."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Consolas", 11))
        self.chat_display.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3e3e3e;"
        )
        layout.addWidget(self.chat_display)

        # Risk indicator bar
        risk_row = QHBoxLayout()
        risk_label = QLabel("RISK LEVEL:")
        risk_label.setStyleSheet("color: #808080; font-size: 10px;")
        risk_row.addWidget(risk_label)
        self.risk_indicator = QLabel("LOW")
        self.risk_indicator.setStyleSheet(
            "color: #4ec9b0; font-weight: bold; font-size: 10px; "
            "border: 1px solid #4ec9b0; padding: 2px 8px;"
        )
        risk_row.addWidget(self.risk_indicator)
        risk_row.addStretch()
        self.token_label = QLabel("TOKENS: 0")
        self.token_label.setStyleSheet("color: #808080; font-size: 10px;")
        risk_row.addWidget(self.token_label)
        layout.addLayout(risk_row)

        # Input row
        input_row = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter a goal or message for LUNA...")
        self.input_field.setFont(QFont("Consolas", 11))
        self.input_field.returnPressed.connect(self.send_goal)
        self.input_field.setStyleSheet(
            "background-color: #2d2d2d; color: #ffffff; "
            "border: 1px solid #3e3e3e; padding: 8px;"
        )
        input_row.addWidget(self.input_field)

        self.send_button = QPushButton("SEND")
        self.send_button.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.send_button.clicked.connect(self.send_goal)
        self.send_button.setStyleSheet(
            "background-color: #007acc; color: #ffffff; "
            "padding: 8px 20px; border: none;"
        )
        input_row.addWidget(self.send_button)

        layout.addLayout(input_row)
        return widget

    def _build_timeline_panel(self) -> QWidget:
        """Build execution timeline panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        label = QLabel("EXECUTION TIMELINE")
        label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        label.setStyleSheet("color: #007acc;")
        layout.addWidget(label)

        self.timeline_table = QTableWidget(0, 4)
        self.timeline_table.setHorizontalHeaderLabels(
            ["Iteration", "Action", "Status", "Risk"]
        )
        self.timeline_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.timeline_table.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3e3e3e;"
        )
        layout.addWidget(self.timeline_table)

        clear_btn = QPushButton("Clear Timeline")
        clear_btn.clicked.connect(lambda: self.timeline_table.setRowCount(0))
        clear_btn.setStyleSheet(
            "background-color: #3e3e3e; color: #d4d4d4; padding: 4px 12px; border: none;"
        )
        layout.addWidget(clear_btn)
        return widget

    def _build_process_panel(self) -> QWidget:
        """Build process monitor panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        label = QLabel("PROCESS MONITOR")
        label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        label.setStyleSheet("color: #007acc;")
        layout.addWidget(label)

        self.process_table = QTableWidget(0, 4)
        self.process_table.setHorizontalHeaderLabels(["PID", "Name", "CPU%", "MEM%"])
        self.process_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.process_table)

        refresh_btn = QPushButton("Refresh Processes")
        refresh_btn.clicked.connect(self.refresh_processes)
        refresh_btn.setStyleSheet(
            "background-color: #007acc; color: #ffffff; padding: 4px 12px; border: none;"
        )
        layout.addWidget(refresh_btn)
        self.refresh_processes()
        return widget

    def _build_config_panel(self) -> QWidget:
        """Build config editor panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        label = QLabel("CONFIG EDITOR  (config.yaml)")
        label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        label.setStyleSheet("color: #007acc;")
        layout.addWidget(label)

        self.config_editor = QTextEdit()
        self.config_editor.setFont(QFont("Consolas", 10))
        self.config_editor.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3e3e3e;"
        )
        self._load_config_into_editor()
        layout.addWidget(self.config_editor)

        btn_row = QHBoxLayout()
        reload_btn = QPushButton("Reload")
        reload_btn.clicked.connect(self._load_config_into_editor)
        reload_btn.setStyleSheet(
            "background-color: #3e3e3e; color: #d4d4d4; padding: 4px 12px; border: none;"
        )
        btn_row.addWidget(reload_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_config_from_editor)
        save_btn.setStyleSheet(
            "background-color: #007acc; color: #ffffff; padding: 4px 12px; border: none;"
        )
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)
        return widget

    def _build_status_panel(self) -> QWidget:
        """Build right-side status panel."""
        widget = QWidget()
        widget.setMaximumWidth(380)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        # Resource monitor
        res_group = QGroupBox("RESOURCE MONITOR")
        res_layout = QVBoxLayout(res_group)

        self.cpu_bar = QProgressBar()
        self.cpu_bar.setFormat("CPU: %p%")
        self.cpu_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #3e3e3e; background-color: #1e1e1e; "
            "color: white; text-align: center; } "
            "QProgressBar::chunk { background-color: #007acc; }"
        )
        res_layout.addWidget(self.cpu_bar)

        self.mem_bar = QProgressBar()
        self.mem_bar.setFormat("MEM: %p%")
        self.mem_bar.setStyleSheet(
            "QProgressBar { border: 1px solid #3e3e3e; background-color: #1e1e1e; "
            "color: white; text-align: center; } "
            "QProgressBar::chunk { background-color: #4ec9b0; }"
        )
        res_layout.addWidget(self.mem_bar)
        layout.addWidget(res_group)

        # Voice controls
        voice_group = QGroupBox("VOICE CONTROLS")
        voice_layout = QVBoxLayout(voice_group)

        self.wake_toggle = QCheckBox("Wake Word Active")
        self.wake_toggle.setStyleSheet("color: #d4d4d4;")
        self.wake_toggle.toggled.connect(self._toggle_wake_word)
        voice_layout.addWidget(self.wake_toggle)

        self.mic_indicator = QLabel("MIC: INACTIVE")
        self.mic_indicator.setStyleSheet(
            "color: #808080; font-size: 10px; border: 1px solid #3e3e3e; padding: 2px 6px;"
        )
        voice_layout.addWidget(self.mic_indicator)

        self.voice_mode_label = QLabel("MODE: PASSIVE")
        self.voice_mode_label.setStyleSheet("color: #808080; font-size: 10px;")
        voice_layout.addWidget(self.voice_mode_label)
        layout.addWidget(voice_group)

        # Cognitive state
        state_group = QGroupBox("COGNITIVE STATE")
        state_layout = QVBoxLayout(state_group)

        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setStyleSheet(
            "background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3e3e3e;"
        )
        state_layout.addWidget(self.status_display)
        layout.addWidget(state_group)

        # Execution progress
        self.exec_progress = QProgressBar()
        self.exec_progress.setRange(0, 0)
        self.exec_progress.setVisible(False)
        self.exec_progress.setStyleSheet(
            "QProgressBar { border: 1px solid #3e3e3e; background-color: #1e1e1e; "
            "color: white; text-align: center; } "
            "QProgressBar::chunk { background-color: #ce9178; }"
        )
        layout.addWidget(self.exec_progress)

        layout.addStretch()
        return widget

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def send_goal(self):
        """Send goal to LUNA."""
        goal = self.input_field.text().strip()
        if not goal:
            return

        self.append_user_message(goal)
        self.input_field.clear()
        self.input_field.setEnabled(False)
        self.send_button.setEnabled(False)
        self.exec_progress.setVisible(True)
        self.status_bar.showMessage("LUNA REASONING...")

        self.worker = AgentWorker(self.loop, goal)
        self.worker.finished.connect(self.handle_result)
        self.worker.start()

    def handle_result(self, result):
        """Handle LUNA result."""
        self.append_agent_message(result)
        self._add_timeline_entry(result)
        self.update_status()

        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.exec_progress.setVisible(False)
        self.input_field.setFocus()
        self.status_bar.showMessage("LUNA KERNEL READY")

    def append_user_message(self, message: str):
        """Append user message to chat."""
        self.chat_display.append(
            f'<p style="color: #569cd6;"><b>YOU:</b> {message}</p>'
        )

    def append_agent_message(self, result):
        """Append agent message to chat with rich formatting."""
        color = "#4ec9b0" if getattr(result, "status", "") == "success" else "#f44747"
        html = (
            f'<div style="margin-bottom: 10px; border-left: 3px solid {color}; '
            f'padding-left: 10px;">'
        )
        html += (
            f'<p style="color: {color}; font-weight: bold;">'
            f'LUNA [{getattr(result, "status", "?").upper()}]:</p>'
        )
        content = getattr(result, "content", "")
        if content:
            html += (
                f'<p style="color: #d4d4d4; white-space: pre-wrap;">{content}</p>'
            )
        error = getattr(result, "error", "")
        if error:
            html += f'<p style="color: #f44747;"><b>ERROR:</b> {error}</p>'

        risk = getattr(result, "risk_level", "low")
        conf = getattr(result, "confidence", 1.0)
        verified = getattr(result, "verified", False)
        html += (
            f'<p style="color: #808080; font-size: 10px;">'
            f'RISK: {risk} | CONFIDENCE: {conf:.2f} | VERIFIED: {verified}</p>'
        )
        html += "</div>"
        self.chat_display.append(html)

        # Update risk indicator
        risk_colors = {
            "low": "#4ec9b0",
            "medium": "#dcdcaa",
            "high": "#f44747",
            "blocked": "#f44747",
        }
        rc = risk_colors.get(risk, "#4ec9b0")
        self.risk_indicator.setText(risk.upper())
        self.risk_indicator.setStyleSheet(
            f"color: {rc}; font-weight: bold; font-size: 10px; "
            f"border: 1px solid {rc}; padding: 2px 8px;"
        )

    def _add_timeline_entry(self, result):
        """Add an entry to the execution timeline table."""
        row = self.timeline_table.rowCount()
        self.timeline_table.insertRow(row)
        self.timeline_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        action = getattr(result, "content", "")[:40]
        self.timeline_table.setItem(row, 1, QTableWidgetItem(action))
        status = getattr(result, "status", "?")
        self.timeline_table.setItem(row, 2, QTableWidgetItem(status.upper()))
        risk = getattr(result, "risk_level", "low")
        self.timeline_table.setItem(row, 3, QTableWidgetItem(risk.upper()))

    def update_system_stats(self):
        """Update live system resource bars."""
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        self.cpu_bar.setValue(int(cpu))
        self.mem_bar.setValue(int(mem))
        system = getattr(self.loop.execution_kernel, "system", "Unknown")
        self.sys_info_label.setText(f"CPU: {cpu:.1f}% | MEM: {mem:.1f}% | OS: {system}")
        self.provider_label.setText(
            f"PROVIDER: {self.loop.llm_manager.active_provider_name.upper()}"
        )

        # Update token count
        try:
            tokens = self.loop.memory_system.get_token_count()
            self.token_label.setText(f"TOKENS: {tokens}")
        except Exception:
            pass

    def update_status(self):
        """Update cognitive state display."""
        try:
            # Phase 3 Fix: use .short_term and .episodic properties (not .short_term_memory)
            short_term_count = len(self.loop.memory_system.short_term)
            episodic_count = len(self.loop.memory_system.episodic)
            token_count = self.loop.memory_system.get_token_count()
        except Exception:
            short_term_count = 0
            episodic_count = 0
            token_count = 0

        agent_name = self.config.get("agent", {}).get("name", "LUNA")
        llm_mode = self.loop.llm_manager.mode
        provider = self.loop.llm_manager.default_provider_name

        html = f"""
        <div style="color: #d4d4d4; font-family: Consolas; font-size: 11px;">
        <p><b style="color: #007acc;">AGENT:</b> {agent_name}</p>
        <p><b style="color: #007acc;">LLM MODE:</b> {llm_mode}</p>
        <p><b style="color: #007acc;">PROVIDER:</b> {provider}</p>
        <hr style="border: 0.5px solid #3e3e3e;">
        <p><b style="color: #4ec9b0;">MEMORY:</b></p>
        <p>Short-term: {short_term_count} messages</p>
        <p>Episodic: {episodic_count} tasks</p>
        <p>Token Est: {token_count}</p>
        <hr style="border: 0.5px solid #3e3e3e;">
        <p><b style="color: #ce9178;">KERNEL:</b></p>
        <p>&#10003; Process Control</p>
        <p>&#10003; Network Management</p>
        <p>&#10003; System Automation</p>
        <p>&#10003; File Operations</p>
        <p>&#10003; Git Automation</p>
        </div>
        """
        self.status_display.setHtml(html)

    def refresh_processes(self):
        """Refresh process monitor table."""
        self.process_table.setRowCount(0)
        try:
            procs = sorted(
                psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]),
                key=lambda p: p.info.get("cpu_percent", 0) or 0,
                reverse=True,
            )[:30]
            for proc in procs:
                row = self.process_table.rowCount()
                self.process_table.insertRow(row)
                self.process_table.setItem(
                    row, 0, QTableWidgetItem(str(proc.info.get("pid", "")))
                )
                self.process_table.setItem(
                    row, 1, QTableWidgetItem(proc.info.get("name", "") or "")
                )
                self.process_table.setItem(
                    row, 2, QTableWidgetItem(f"{proc.info.get('cpu_percent', 0):.1f}%")
                )
                self.process_table.setItem(
                    row, 3, QTableWidgetItem(f"{proc.info.get('memory_percent', 0):.1f}%")
                )
        except Exception as e:
            logger.error(f"[GUI] Process refresh error: {e}")

    def _load_config_into_editor(self):
        """Load config.yaml into the config editor."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config_editor.setPlainText(f.read())
            else:
                self.config_editor.setPlainText("# config.yaml not found")
        except Exception as e:
            self.config_editor.setPlainText(f"# Error loading config: {e}")

    def _save_config_from_editor(self):
        """Save config editor content to config.yaml safely."""
        content = self.config_editor.toPlainText()
        try:
            # Validate YAML before saving
            yaml.safe_load(content)
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.status_bar.showMessage("Config saved successfully.")
            QMessageBox.information(self, "Config Saved", "config.yaml saved successfully.")
        except yaml.YAMLError as e:
            QMessageBox.critical(self, "YAML Error", f"Invalid YAML:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save config:\n{e}")

    def _toggle_wake_word(self, enabled: bool):
        """Toggle wake word listening."""
        voice_engine = getattr(self.loop, "voice_engine", None)
        if voice_engine is None:
            self.wake_toggle.setChecked(False)
            return

        if enabled:
            voice_engine.start_passive_listening(lambda text: None)
            self.voice_mode_label.setText("MODE: PASSIVE (ACTIVE)")
            self.mic_indicator.setText("MIC: LISTENING")
            self.mic_indicator.setStyleSheet(
                "color: #4ec9b0; font-size: 10px; "
                "border: 1px solid #4ec9b0; padding: 2px 6px;"
            )
        else:
            voice_engine.stop_passive_listening()
            self.voice_mode_label.setText("MODE: PASSIVE")
            self.mic_indicator.setText("MIC: INACTIVE")
            self.mic_indicator.setStyleSheet(
                "color: #808080; font-size: 10px; "
                "border: 1px solid #3e3e3e; padding: 2px 6px;"
            )
