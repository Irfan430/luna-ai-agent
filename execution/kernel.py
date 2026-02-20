"""
LUNA AI Agent - Execution Kernel
Author: IRFAN

Deterministic execution layer for OS automation.
"""

import subprocess
import os
import shutil
import platform
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    """Standard execution result format."""
    status: str  # success | failed | partial
    content: str
    error: str = ""
    execution_used: bool = True
    confidence: float = 1.0
    risk_level: str = "low"
    verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "content": self.content,
            "error": self.error,
            "execution_used": self.execution_used,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "verified": self.verified
        }


class ExecutionKernel:
    """Deterministic execution layer for LUNA."""
    def __init__(self):
        self.system = platform.system()

    def execute(self, action: str, parameters: Dict[str, Any]) -> ExecutionResult:
        """Route action to appropriate handler."""
        handlers = {
            "command": self._run_command,
            "file_op": self._file_operation,
            "git_op": self._git_operation,
            "app_launch": self._launch_app,
            "python_exec": self._execute_python
        }
        
        handler = handlers.get(action)
        if not handler:
            return ExecutionResult("failed", "", f"Unknown action: {action}")
        
        try:
            return handler(parameters)
        except Exception as e:
            return ExecutionResult("failed", "", f"Execution error: {str(e)}")

    def _run_command(self, params: Dict[str, Any]) -> ExecutionResult:
        """Run a shell command."""
        command = params.get("command")
        cwd = params.get("cwd")
        timeout = params.get("timeout", 30)
        
        if not command:
            return ExecutionResult("failed", "", "No command provided")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            
            if result.returncode == 0:
                return ExecutionResult("success", result.stdout, verified=True)
            else:
                return ExecutionResult("failed", result.stdout, result.stderr)
        except subprocess.TimeoutExpired:
            return ExecutionResult("failed", "", f"Command timed out after {timeout}s")

    def _file_operation(self, params: Dict[str, Any]) -> ExecutionResult:
        """Handle file operations (create, read, edit, delete, move)."""
        op = params.get("op")
        path = params.get("path")
        content = params.get("content", "")
        dest = params.get("destination", "")
        
        if not path:
            return ExecutionResult("failed", "", "No path provided")
        
        try:
            if op == "create":
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return ExecutionResult("success", f"File created: {path}", verified=True)
            
            elif op == "read":
                if not os.path.exists(path):
                    return ExecutionResult("failed", "", f"File not found: {path}")
                with open(path, 'r', encoding='utf-8') as f:
                    return ExecutionResult("success", f.read(), verified=True)
            
            elif op == "edit":
                if not os.path.exists(path):
                    return ExecutionResult("failed", "", f"File not found: {path}")
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return ExecutionResult("success", f"File edited: {path}", verified=True)
            
            elif op == "delete":
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                return ExecutionResult("success", f"Deleted: {path}", verified=True)
            
            elif op == "move":
                shutil.move(path, dest)
                return ExecutionResult("success", f"Moved: {path} -> {dest}", verified=True)
            
            else:
                return ExecutionResult("failed", "", f"Unknown file operation: {op}")
        except Exception as e:
            return ExecutionResult("failed", "", str(e))

    def _git_operation(self, params: Dict[str, Any]) -> ExecutionResult:
        """Handle git operations."""
        op = params.get("op")
        cwd = params.get("cwd", ".")
        
        commands = {
            "init": "git init",
            "status": "git status",
            "add": f"git add {params.get('files', '.')}",
            "commit": f'git commit -m "{params.get("message", "Update")}"',
            "push": f"git push {params.get('remote', 'origin')} {params.get('branch', 'master')}",
            "pull": f"git pull {params.get('remote', 'origin')} {params.get('branch', 'master')}",
            "clone": f"git clone {params.get('url')} {params.get('path', '')}"
        }
        
        cmd = commands.get(op)
        if not cmd:
            return ExecutionResult("failed", "", f"Unknown git operation: {op}")
        
        return self._run_command({"command": cmd, "cwd": cwd})

    def _launch_app(self, params: Dict[str, Any]) -> ExecutionResult:
        """Launch system application."""
        app = params.get("app")
        if not app:
            return ExecutionResult("failed", "", "No app name provided")
        
        try:
            if self.system == "Windows":
                subprocess.Popen(['start', app], shell=True)
            elif self.system == "Darwin":
                subprocess.Popen(['open', '-a', app])
            else:
                subprocess.Popen([app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ExecutionResult("success", f"Launched: {app}", verified=False)
        except Exception as e:
            return ExecutionResult("failed", "", str(e))

    def _execute_python(self, params: Dict[str, Any]) -> ExecutionResult:
        """Execute Python script."""
        code = params.get("code")
        if not code:
            return ExecutionResult("failed", "", "No Python code provided")
        
        temp_file = "temp_luna_script.py"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        result = self._run_command({"command": f"python3 {temp_file}"})
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return result
