"""
LUNA AI Agent - OS Agent Execution Kernel (OAEK) v11.0
Author: IRFAN

Structural Stabilization Refactor:
  - Centralized Action Router: system, browser, file, app.
  - Standardized ExecutionResult for all OS Agent intents.
  - Support for multi-step tasks.
"""

import os
import platform
import psutil
import time
import subprocess
import logging
import shutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from execution.browser import BrowserController

logger = logging.getLogger("luna.execution.kernel")

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
    """The hands of LUNA, executing structured OS Agent intents."""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.system = platform.system()
        self.browser_controller = BrowserController(self.config)
        
        # Central ACTIONS mapping table
        self.ACTIONS = {
            "system": self._handle_system,
            "browser": self._handle_browser,
            "file": self._handle_file,
            "app": self._handle_app,
            "code": self._handle_code
        }

    def get_system_stats(self) -> Dict[str, Any]:
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "os": f"{self.system} {platform.release()}",
        }

    def execute(self, action: str, parameters: Dict[str, Any]) -> ExecutionResult:
        """Route action to appropriate handler using the central ACTIONS mapping."""
        handler = self.ACTIONS.get(action.lower())
        if not handler:
            return ExecutionResult.failure(f"Unknown action: {action}")

        try:
            result = handler(parameters)
            if not isinstance(result, ExecutionResult):
                if result.get("status") == "success":
                    result = ExecutionResult("success", result.get("content", ""), verified=True)
                else:
                    result = ExecutionResult.failure(result.get("error", "Execution failed"))
            
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
        
        # Dangerous command block (Basic)
        dangerous_keywords = ["rm -rf /", "mkfs", ":(){ :|:& };:", "dd if="]
        if any(kw in cmd for kw in dangerous_keywords):
            return ExecutionResult.failure(f"Dangerous command blocked: {cmd}")
            
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
        """Handle browser actions via persistent Playwright worker."""
        try:
            result = self.browser_controller.execute(params)
            if result.get("status") == "success":
                return ExecutionResult("success", result.get("content", ""), verified=True)
            else:
                return ExecutionResult.failure(result.get("error", "Browser execution failed"))
        except Exception as e:
            return ExecutionResult.failure(f"Browser error: {str(e)}")

    def _handle_file(self, params: Dict[str, Any]) -> ExecutionResult:
        """Handle file operations (create, read, delete, list)."""
        op = params.get("op", "read")
        path = params.get("path", ".")
        
        try:
            if op == "create":
                content = params.get("content", "")
                with open(path, 'w') as f:
                    f.write(content)
                return ExecutionResult("success", f"File created: {path}", verified=True)
            
            elif op == "read":
                if not os.path.exists(path):
                    return ExecutionResult.failure(f"File not found: {path}")
                with open(path, 'r') as f:
                    content = f.read()
                return ExecutionResult("success", content, verified=True)
            
            elif op == "delete":
                if os.path.exists(path):
                    if os.path.isdir(path): shutil.rmtree(path)
                    else: os.remove(path)
                    return ExecutionResult("success", f"Path deleted: {path}", verified=True)
                else:
                    return ExecutionResult.failure(f"Path not found: {path}")
            
            elif op == "list":
                files = os.listdir(path)
                return ExecutionResult("success", f"Files in {path}: {', '.join(files)}", verified=True)
            
            return ExecutionResult.failure(f"Unknown file operation: {op}")
        except Exception as e:
            return ExecutionResult.failure(str(e))

    def _handle_app(self, params: Dict[str, Any]) -> ExecutionResult:
        """Handle opening or closing applications."""
        action = params.get("action", "open")
        app_name = params.get("app_name")
        if not app_name:
            return ExecutionResult.failure("No app name provided.")
        
        try:
            if action == "open":
                cmd = f"open -a '{app_name}'" if platform.system() == "Darwin" else f"xdg-open {app_name}" if platform.system() == "Linux" else f"start {app_name}"
                subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return ExecutionResult("success", f"Opening app: {app_name}", verified=True)
            
            elif action == "close":
                for proc in psutil.process_iter(['name']):
                    if app_name.lower() in proc.info['name'].lower():
                        proc.kill()
                return ExecutionResult("success", f"Closed app: {app_name}", verified=True)
                
            return ExecutionResult.failure(f"Unknown app action: {action}")
        except Exception as e:
            return ExecutionResult.failure(str(e))

    def _handle_code(self, params: Dict[str, Any]) -> ExecutionResult:
        """Handle code execution (Python)."""
        code = params.get("code")
        if not code:
            return ExecutionResult.failure("No code provided for code action.")
        
        filename = params.get("filename", "temp_script.py")
        try:
            with open(filename, 'w') as f:
                f.write(code)
            
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
            if filename == "temp_script.py" and os.path.exists(filename):
                try: os.remove(filename)
                except: pass
