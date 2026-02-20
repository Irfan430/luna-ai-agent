"""
LUNA AI Agent - Advanced GUI Monitoring Interface
Author: IRFAN

Professional monitoring interface for LUNA agent status, activity, and system resources.
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QLineEdit, QPushButton, QLabel,
                             QSplitter, QStatusBar, QProgressBar, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette
import psutil
from core.loop import CognitiveLoop
from execution.kernel import ExecutionResult


class AgentWorker(QThread):
    """Worker thread for cognitive loop processing."""
    finished = pyqtSignal(object)  # ExecutionResult
    
    def __init__(self, loop: CognitiveLoop, goal: str):
        super().__init__()
        self.loop = loop
        self.goal = goal
    
    def run(self):
        """Process goal in background thread."""
        result = self.loop.run(self.goal)
        self.finished.emit(result)


class MonitorWindow(QMainWindow):
    """Advanced GUI monitoring window for LUNA 2.0."""
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.loop = CognitiveLoop(config)
        self.worker = None
        self.init_ui()
        
        # System stats timer
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_system_stats)
        self.stats_timer.start(2000)  # Update every 2 seconds
    
    def init_ui(self):
        """Initialize UI components with a professional dark theme."""
        self.setWindowTitle("LUNA 2.0 - COGNITIVE OPERATING SYSTEM")
        self.setGeometry(100, 100, 1400, 900)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        layout = QVBoxLayout(central)
        
        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #252526; border-bottom: 1px solid #3e3e3e;")
        header_layout = QHBoxLayout(header_frame)
        
        header = QLabel("LUNA 2.0 | ADVANCED COGNITIVE AGENT")
        header.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #007acc; border: none;")
        header_layout.addWidget(header)
        
        self.sys_info_label = QLabel("SYSTEM: READY")
        self.sys_info_label.setFont(QFont("Consolas", 10))
        self.sys_info_label.setStyleSheet("color: #808080; border: none;")
        header_layout.addStretch()
        header_layout.addWidget(self.sys_info_label)
        
        layout.addWidget(header_frame)
        
        # Splitter for chat and status
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Chat area
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Consolas", 11))
        self.chat_display.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3e3e3e;")
        chat_layout.addWidget(self.chat_display)
        
        # Input area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter device automation goal for LUNA...")
        self.input_field.setFont(QFont("Consolas", 11))
        self.input_field.returnPressed.connect(self.send_goal)
        self.input_field.setStyleSheet("background-color: #2d2d2d; color: #ffffff; border: 1px solid #3e3e3e; padding: 8px;")
        input_layout.addWidget(self.input_field)
        
        self.send_button = QPushButton("SEND")
        self.send_button.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.send_button.clicked.connect(self.send_goal)
        self.send_button.setStyleSheet("background-color: #007acc; color: #ffffff; padding: 8px 20px;")
        input_layout.addWidget(self.send_button)
        
        chat_layout.addLayout(input_layout)
        splitter.addWidget(chat_widget)
        
        # Status panel
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        
        # Resource Monitor
        res_label = QLabel("RESOURCE MONITOR")
        res_label.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        res_label.setStyleSheet("color: #007acc;")
        status_layout.addWidget(res_label)
        
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setFormat("CPU: %p%")
        self.cpu_bar.setStyleSheet("QProgressBar { border: 1px solid #3e3e3e; background-color: #1e1e1e; color: white; text-align: center; } QProgressBar::chunk { background-color: #007acc; }")
        status_layout.addWidget(self.cpu_bar)
        
        self.mem_bar = QProgressBar()
        self.mem_bar.setFormat("MEM: %p%")
        self.mem_bar.setStyleSheet("QProgressBar { border: 1px solid #3e3e3e; background-color: #1e1e1e; color: white; text-align: center; } QProgressBar::chunk { background-color: #4ec9b0; }")
        status_layout.addWidget(self.mem_bar)
        
        # Cognitive State
        state_label = QLabel("COGNITIVE STATE")
        state_label.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        state_label.setStyleSheet("color: #007acc; margin-top: 10px;")
        status_layout.addWidget(state_label)
        
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setMaximumWidth(400)
        self.status_display.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3e3e3e;")
        status_layout.addWidget(self.status_display)
        
        # Progress bar for execution
        self.exec_progress = QProgressBar()
        self.exec_progress.setRange(0, 0)
        self.exec_progress.setVisible(False)
        status_layout.addWidget(self.exec_progress)
        
        splitter.addWidget(status_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("LUNA KERNEL READY")
        self.update_status()
    
    def update_system_stats(self):
        """Update live system resource bars."""
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        self.cpu_bar.setValue(int(cpu))
        self.mem_bar.setValue(int(mem))
        self.sys_info_label.setText(f"CPU: {cpu}% | MEM: {mem}% | OS: {self.loop.execution_kernel.system}")

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
        self.statusBar.showMessage("LUNA REASONING...")
        
        self.worker = AgentWorker(self.loop, goal)
        self.worker.finished.connect(self.handle_result)
        self.worker.start()
    
    def handle_result(self, result: ExecutionResult):
        """Handle LUNA result."""
        self.append_agent_message(result)
        self.update_status()
        
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.exec_progress.setVisible(False)
        self.input_field.setFocus()
        self.statusBar.showMessage("LUNA KERNEL READY")
    
    def append_user_message(self, message: str):
        """Append user message to chat."""
        self.chat_display.append(f'<p style="color: #569cd6;"><b>IRFAN:</b> {message}</p>')
    
    def append_agent_message(self, result: ExecutionResult):
        """Append agent message to chat with rich formatting."""
        color = "#4ec9b0" if result.status == "success" else "#f44747"
        html = f'<div style="margin-bottom: 10px; border-left: 3px solid {color}; padding-left: 10px;">'
        html += f'<p style="color: {color}; font-weight: bold;">LUNA [{result.status.upper()}]:</p>'
        
        if result.content:
            html += f'<p style="color: #d4d4d4; white-space: pre-wrap;">{result.content}</p>'
        
        if result.error:
            html += f'<p style="color: #f44747;"><b>ERROR:</b> {result.error}</p>'
        
        html += f'<p style="color: #808080; font-size: 10px;">RISK: {result.risk_level} | CONFIDENCE: {result.confidence:.2f} | VERIFIED: {result.verified}</p>'
        html += '</div>'
        self.chat_display.append(html)
    
    def update_status(self):
        """Update status display with cognitive metrics."""
        status_html = f"""
        <div style="color: #d4d4d4; font-family: Consolas;">
        <p><b style="color: #007acc;">AGENT:</b> {self.config.get('agent', {}).get('name', 'LUNA 2.0')}</p>
        <p><b style="color: #007acc;">LLM MODE:</b> {self.loop.llm_manager.mode}</p>
        <p><b style="color: #007acc;">PROVIDER:</b> {self.loop.llm_manager.default_provider_name}</p>
        <hr style="border: 0.5px solid #3e3e3e;">
        <p><b style="color: #4ec9b0;">MEMORY STATE:</b></p>
        <p>Short-term: {len(self.loop.memory_system.short_term)} steps</p>
        <p>Episodic: {len(self.loop.memory_system.episodic)} tasks</p>
        <p>Token Est: {self.loop.memory_system.get_token_count()}</p>
        <hr style="border: 0.5px solid #3e3e3e;">
        <p><b style="color: #ce9178;">KERNEL CAPABILITIES:</b></p>
        <p>✓ Process Control</p>
        <p>✓ Network Management</p>
        <p>✓ System Automation</p>
        <p>✓ File Operations</p>
        <p>✓ Git Automation</p>
        </div>
        """
        self.status_display.setHtml(status_html)
