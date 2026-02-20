"""
LUNA AI Agent - GUI Monitoring Interface
Author: IRFAN

Professional monitoring interface for LUNA agent status and activity.
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QLineEdit, QPushButton, QLabel,
                             QSplitter, QStatusBar, QProgressBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
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
    """Main GUI monitoring window."""
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.loop = CognitiveLoop(config)
        self.worker = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("LUNA COGNITIVE MONITOR")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        layout = QVBoxLayout(central)
        
        # Header
        header = QLabel("LUNA COGNITIVE OPERATING SYSTEM")
        header.setFont(QFont("Consolas", 18, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Splitter for chat and status
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Chat area
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Consolas", 10))
        self.chat_display.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        chat_layout.addWidget(self.chat_display)
        
        # Input area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter goal for LUNA...")
        self.input_field.returnPressed.connect(self.send_goal)
        self.input_field.setStyleSheet("background-color: #2d2d2d; color: #ffffff; border: 1px solid #3e3e3e;")
        input_layout.addWidget(self.input_field)
        
        self.send_button = QPushButton("EXECUTE")
        self.send_button.clicked.connect(self.send_goal)
        self.send_button.setStyleSheet("background-color: #007acc; color: #ffffff; font-weight: bold;")
        input_layout.addWidget(self.send_button)
        
        chat_layout.addLayout(input_layout)
        splitter.addWidget(chat_widget)
        
        # Status panel
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        
        status_label = QLabel("COGNITIVE STATE")
        status_label.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        status_layout.addWidget(status_label)
        
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setMaximumWidth(350)
        self.status_display.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        status_layout.addWidget(self.status_display)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        splitter.addWidget(status_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("LUNA KERNEL READY")
        self.update_status()
    
    def send_goal(self):
        """Send goal to LUNA."""
        goal = self.input_field.text().strip()
        if not goal:
            return
        
        self.append_user_message(goal)
        self.input_field.clear()
        
        # Disable input while processing
        self.input_field.setEnabled(False)
        self.send_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.statusBar.showMessage("LUNA REASONING...")
        
        # Process in background thread
        self.worker = AgentWorker(self.loop, goal)
        self.worker.finished.connect(self.handle_result)
        self.worker.start()
    
    def handle_result(self, result: ExecutionResult):
        """Handle LUNA result."""
        self.append_agent_message(result)
        self.update_status()
        
        # Re-enable input
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.input_field.setFocus()
        self.statusBar.showMessage("LUNA KERNEL READY")
    
    def append_user_message(self, message: str):
        """Append user message to chat."""
        self.chat_display.append(f'<p style="color: #569cd6;"><b>IRFAN:</b> {message}</p>')
    
    def append_agent_message(self, result: ExecutionResult):
        """Append agent message to chat."""
        color = "#4ec9b0" if result.status == "success" else "#f44747"
        html = f'<p style="color: {color};"><b>LUNA [{result.status.upper()}]:</b></p>'
        
        if result.content:
            html += f'<p style="color: #d4d4d4;">{result.content}</p>'
        
        if result.error:
            html += f'<p style="color: #f44747;"><b>ERROR:</b> {result.error}</p>'
        
        html += f'<p style="color: #808080; font-size: 9px;">RISK: {result.risk_level} | CONFIDENCE: {result.confidence:.2f} | VERIFIED: {result.verified}</p>'
        self.chat_display.append(html)
    
    def update_status(self):
        """Update status display."""
        status_html = f"""
        <p><b>AGENT:</b> {self.config.get('agent', {}).get('name', 'LUNA')}</p>
        <p><b>LLM MODE:</b> {self.loop.llm_manager.mode}</p>
        <p><b>PROVIDER:</b> {self.loop.llm_manager.default_provider_name}</p>
        <hr>
        <p><b>MEMORY STATE:</b></p>
        <p>Short-term: {len(self.loop.memory_system.short_term)} msgs</p>
        <p>Episodic: {len(self.loop.memory_system.episodic)} tasks</p>
        <p>Token Est: {self.loop.memory_system.get_token_count()}</p>
        <hr>
        <p><b>KERNEL:</b></p>
        <p>Max Iter: {self.loop.max_iterations}</p>
        <p>Repair Limit: {self.loop.max_repair_attempts}</p>
        """
        self.status_display.setHtml(status_html)
