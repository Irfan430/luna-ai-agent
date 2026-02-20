"""
LUNA AI Agent - GUI Main Window
Author: IRFAN

Main GUI window for LUNA agent.
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTextEdit, QLineEdit, QPushButton, QLabel,
                             QSplitter, QStatusBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from core.agent import LunaAgent
from core.task_result import TaskResult


class AgentWorker(QThread):
    """Worker thread for agent processing."""
    
    finished = pyqtSignal(object)  # TaskResult
    
    def __init__(self, agent: LunaAgent, user_input: str):
        super().__init__()
        self.agent = agent
        self.user_input = user_input
    
    def run(self):
        """Process input in background thread."""
        result = self.agent.process_input(self.user_input)
        self.finished.emit(result)


class MainWindow(QMainWindow):
    """Main GUI window."""
    
    def __init__(self):
        super().__init__()
        self.agent = None
        self.worker = None
        self.init_ui()
        self.init_agent()
    
    def init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("LUNA AI Agent")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        layout = QVBoxLayout(central)
        
        # Header
        header = QLabel("LUNA AI Agent")
        header.setFont(QFont("Arial", 18, QFont.Weight.Bold))
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
        chat_layout.addWidget(self.chat_display)
        
        # Input area
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field)
        
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)
        
        chat_layout.addLayout(input_layout)
        splitter.addWidget(chat_widget)
        
        # Status panel
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        
        status_label = QLabel("Status")
        status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        status_layout.addWidget(status_label)
        
        self.status_display = QTextEdit()
        self.status_display.setReadOnly(True)
        self.status_display.setMaximumWidth(300)
        status_layout.addWidget(self.status_display)
        
        splitter.addWidget(status_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
    
    def init_agent(self):
        """Initialize LUNA agent."""
        try:
            self.agent = LunaAgent()
            self.append_system_message(f"✓ {self.agent.name} initialized successfully")
            self.update_status()
        except Exception as e:
            self.append_system_message(f"✗ Failed to initialize agent: {e}")
            self.append_system_message("Please check your config.yaml and API keys.")
    
    def send_message(self):
        """Send user message."""
        if not self.agent:
            self.append_system_message("Agent not initialized")
            return
        
        user_input = self.input_field.text().strip()
        if not user_input:
            return
        
        # Display user message
        self.append_user_message(user_input)
        self.input_field.clear()
        
        # Disable input while processing
        self.input_field.setEnabled(False)
        self.send_button.setEnabled(False)
        self.statusBar.showMessage("Processing...")
        
        # Process in background thread
        self.worker = AgentWorker(self.agent, user_input)
        self.worker.finished.connect(self.handle_result)
        self.worker.start()
    
    def handle_result(self, result: TaskResult):
        """Handle agent result."""
        # Display result
        self.append_agent_message(result)
        
        # Update status
        self.update_status()
        
        # Re-enable input
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()
        self.statusBar.showMessage("Ready")
    
    def append_user_message(self, message: str):
        """Append user message to chat."""
        self.chat_display.append(f'<p style="color: #2196F3;"><b>You:</b> {message}</p>')
    
    def append_agent_message(self, result: TaskResult):
        """Append agent message to chat."""
        status_color = {
            "success": "#4CAF50",
            "failed": "#F44336",
            "partial": "#FF9800"
        }
        color = status_color.get(result.status, "#666")
        
        html = f'<p style="color: {color};"><b>LUNA [{result.status}]:</b></p>'
        
        if result.content:
            html += f'<p>{result.content}</p>'
        
        if result.error:
            html += f'<p style="color: #F44336;">Error: {result.error}</p>'
        
        html += f'<p style="color: #999; font-size: 9px;">Risk: {result.risk_level} | Confidence: {result.confidence:.2f} | Verified: {result.verified}</p>'
        
        self.chat_display.append(html)
    
    def append_system_message(self, message: str):
        """Append system message to chat."""
        self.chat_display.append(f'<p style="color: #999;"><i>{message}</i></p>')
    
    def update_status(self):
        """Update status display."""
        if not self.agent:
            return
        
        status = self.agent.get_status()
        
        status_html = f"""
        <p><b>Agent:</b> {status['name']}</p>
        <p><b>Provider:</b> {status['active_provider']}</p>
        <p><b>LLM Mode:</b> {status['llm_mode']}</p>
        <p><b>Conversations:</b> {status['conversation_count']}</p>
        <hr>
        <p><b>Guardrails:</b></p>
        <p>Planning: {status['guardrails']['planning_iterations']['current']}/{status['guardrails']['planning_iterations']['max']}</p>
        <p>Continuation: {status['guardrails']['continuation_retries']['current']}/{status['guardrails']['continuation_retries']['max']}</p>
        """
        
        self.status_display.setHtml(status_html)
