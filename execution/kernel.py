"""
LUNA AI Agent - Advanced Execution Kernel (AEK) v9.0
Author: IRFAN

Structural Stabilization Refactor:
  - Central ACTIONS mapping table.
  - Strict action routing: system, browser, screen, code.
  - Removed open_browser and other dynamic action names.
  - Integrated persistent browser controller.
"""

import os
import platform
import psutil
import time
import re
import subprocess
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# Import OS adapters
from os_adapters.linux import LinuxAdapter
from os_adapters.windows import WindowsAdapter
from os_adapters.mac import MacAdapter
from execution.browser import BrowserController

logger = logging.getLogger("luna.execution.kernel")

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    from PIL import ImageGrab
    SCREEN_CAPTURE_AVAILABLE = True
except ImportError:
    SCREEN_CAPTURE_AVAILABLE = False

@dataclass
class ExecutionResult:
    status: str
    content: str
    error: str = ""
    execution_used: bool = True
    confidence: float = 1.0
    risk_level: str = "low"
    verified: bool = False
    system_state: Optional[Dict[str, Any]] = field(default=None)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "content": self.content,
            "error": self.error,
            "execution_used": self.execution_used,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "verified": self.verified,
            "system_state": self.system_state,
        }

    @classmethod
    def failure(cls, error: str):
        return cls(status="failed", content="", error=error, verified=False)

class ExecutionKernel:
    """Hardened execution layer with OS abstraction and interaction engine."""

    def __init__(self):
        self.system = platform.system()
        self.adapter = self._get_adapter()
        self.pyautogui_available = PYAUTOGUI_AVAILABLE
        self.browser_controller = BrowserController()
        
        # Central ACTIONS mapping table
        self.ACTIONS = {
            "system": self._handle_system,
            "browser": self._handle_browser,
            "screen": self._handle_screen,
            "code": self._handle_code
        }

    def _get_adapter(self):
        if self.system == "Linux": return LinuxAdapter()
        elif self.system == "Windows": return WindowsAdapter()
        elif self.system == "Darwin": return MacAdapter()
        return LinuxAdapter()

    def get_system_stats(self) -> Dict[str, Any]:
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "os": f"{self.system} {platform.release()}",
        }

    def execute(self, action: str, parameters: Dict[str, Any]) -> ExecutionResult:
        """Route action to appropriate handler using the central ACTIONS mapping."""
        handler = self.ACTIONS.get(action)
        if not handler:
            return ExecutionResult.failure(f"Unknown action: {action}")

        try:
            result = handler(parameters)
            result.system_state = self.get_system_stats()
            return result
        except Exception as e:
            logger.error(f"Execution error in {action}: {e}")
            return ExecutionResult.failure(str(e))

    # --- Central Handlers ---

    def _handle_system(self, params: Dict[str, Any]) -> ExecutionResult:
        """Handle shell commands or system tasks."""
        cmd = params.get("command")
        if not cmd:
            return ExecutionResult.failure("No command provided for system action.")
        
        cwd = params.get("cwd")
        try:
            process = subprocess.Popen(
                cmd, shell=True, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            exit_code = process.returncode
            
            if exit_code == 0:
                return ExecutionResult("success", stdout, verified=True)
            else:
                return ExecutionResult("failed", stdout, f"Exit code: {exit_code}. Error: {stderr}", verified=False)
        except Exception as e:
            return ExecutionResult.failure(str(e))

    def _handle_browser(self, params: Dict[str, Any]) -> ExecutionResult:
        """Handle browser actions via Playwright."""
        task = params.get("task")
        if not task:
            return ExecutionResult.failure("No task provided for browser action.")
        
        try:
            result = self.browser_controller.execute_instruction(task)
            return ExecutionResult("success", result, verified=True)
        except Exception as e:
            return ExecutionResult.failure(f"Browser error: {str(e)}")

    def _handle_screen(self, params: Dict[str, Any]) -> ExecutionResult:
        """Handle screen capture and analysis."""
        if not SCREEN_CAPTURE_AVAILABLE:
            return ExecutionResult.failure("Screen capture (PIL) not available.")
        
        instruction = params.get("instruction", "capture")
        path = "screen_capture.png"
        
        try:
            screenshot = ImageGrab.grab()
            screenshot.thumbnail((1280, 720))
            screenshot.save(path)
            return ExecutionResult("success", f"Screen captured and saved to {path}. Instruction: {instruction}", verified=True)
        except Exception as e:
            return ExecutionResult.failure(f"Screen capture error: {str(e)}")

    def _handle_code(self, params: Dict[str, Any]) -> ExecutionResult:
        """Handle code execution (Python)."""
        code = params.get("code")
        if not code:
            return ExecutionResult.failure("No code provided for code action.")
        
        filename = params.get("filename", "temp_script.py")
        try:
            # Write code to file
            with open(filename, 'w') as f:
                f.write(code)
            
            # Execute code
            process = subprocess.Popen(
                ["python3", filename],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            exit_code = process.returncode
            
            if exit_code == 0:
                return ExecutionResult("success", stdout, verified=True)
            else:
                return ExecutionResult("failed", stdout, f"Exit code: {exit_code}. Error: {stderr}", verified=False)
        except Exception as e:
            return ExecutionResult.failure(str(e))
        finally:
            # Cleanup temp file if it's the default one
            if filename == "temp_script.py" and os.path.exists(filename):
                try: os.remove(filename)
                except: pass
