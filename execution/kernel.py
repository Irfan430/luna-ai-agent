"""
LUNA AI Agent - Advanced Execution Kernel (AEK)
Author: IRFAN

Deterministic execution layer for deep OS automation and device control.
"""

import subprocess
import os
import shutil
import platform
import psutil
import socket
import time
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
    system_state: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "content": self.content,
            "error": self.error,
            "execution_used": self.execution_used,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "verified": self.verified,
            "system_state": self.system_state
        }


class ExecutionKernel:
    """Advanced execution layer for LUNA with full OS control."""
    def __init__(self):
        self.system = platform.system()

    def get_system_stats(self) -> Dict[str, Any]:
        """Get real-time system resource usage."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "boot_time": time.ctime(psutil.boot_time()),
            "os": f"{self.system} {platform.release()}"
        }

    def execute(self, action: str, parameters: Dict[str, Any]) -> ExecutionResult:
        """Route action to appropriate handler."""
        handlers = {
            "command": self._run_command,
            "file_op": self._file_operation,
            "git_op": self._git_operation,
            "app_launch": self._launch_app,
            "python_exec": self._execute_python,
            "process_op": self._process_operation,
            "network_op": self._network_operation,
            "system_info": self._get_system_info
        }
        
        handler = handlers.get(action)
        if not handler:
            return ExecutionResult("failed", "", f"Unknown action: {action}")
        
        try:
            result = handler(parameters)
            result.system_state = self.get_system_stats()
            return result
        except Exception as e:
            return ExecutionResult("failed", "", f"Execution error: {str(e)}", system_state=self.get_system_stats())

    def _run_command(self, params: Dict[str, Any]) -> ExecutionResult:
        """Run a shell command with enhanced validation."""
        command = params.get("command")
        cwd = params.get("cwd")
        timeout = params.get("timeout", 60)
        
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
        """Enhanced file operations."""
        op = params.get("op")
        path = params.get("path")
        content = params.get("content", "")
        dest = params.get("destination", "")
        
        if not path:
            return ExecutionResult("failed", "", "No path provided")
        
        try:
            if op == "create":
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
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
            
            elif op == "list":
                files = os.listdir(path)
                return ExecutionResult("success", "\n".join(files), verified=True)
            
            else:
                return ExecutionResult("failed", "", f"Unknown file operation: {op}")
        except Exception as e:
            return ExecutionResult("failed", "", str(e))

    def _process_operation(self, params: Dict[str, Any]) -> ExecutionResult:
        """Manage system processes."""
        op = params.get("op")
        name = params.get("name")
        pid = params.get("pid")
        
        try:
            if op == "list":
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
                    processes.append(proc.info)
                return ExecutionResult("success", str(processes[:20]), verified=True)
            
            elif op == "kill":
                if pid:
                    proc = psutil.Process(pid)
                    proc.terminate()
                    return ExecutionResult("success", f"Terminated process {pid}", verified=True)
                elif name:
                    count = 0
                    for proc in psutil.process_iter(['name']):
                        if proc.info['name'] == name:
                            proc.terminate()
                            count += 1
                    return ExecutionResult("success", f"Terminated {count} processes named {name}", verified=True)
            
            elif op == "find":
                found = []
                for proc in psutil.process_iter(['pid', 'name']):
                    if name and name.lower() in proc.info['name'].lower():
                        found.append(proc.info)
                return ExecutionResult("success", str(found), verified=True)
                
            return ExecutionResult("failed", "", f"Unknown process operation: {op}")
        except Exception as e:
            return ExecutionResult("failed", "", str(e))

    def _network_operation(self, params: Dict[str, Any]) -> ExecutionResult:
        """Manage network status and connections."""
        op = params.get("op")
        host = params.get("host", "8.8.8.8")
        port = params.get("port", 80)
        
        try:
            if op == "ping":
                cmd = f"ping -c 1 {host}" if self.system != "Windows" else f"ping -n 1 {host}"
                return self._run_command({"command": cmd})
            
            elif op == "check_port":
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                sock.close()
                status = "open" if result == 0 else "closed"
                return ExecutionResult("success", f"Port {port} on {host} is {status}", verified=True)
            
            elif op == "list_interfaces":
                interfaces = psutil.net_if_addrs()
                return ExecutionResult("success", str(interfaces), verified=True)
                
            return ExecutionResult("failed", "", f"Unknown network operation: {op}")
        except Exception as e:
            return ExecutionResult("failed", "", str(e))

    def _get_system_info(self, params: Dict[str, Any]) -> ExecutionResult:
        """Get detailed system information."""
        info = {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "memory": str(psutil.virtual_memory()),
            "disk": str(psutil.disk_usage('/')),
            "users": [u.name for u in psutil.users()]
        }
        return ExecutionResult("success", str(info), verified=True)

    def _git_operation(self, params: Dict[str, Any]) -> ExecutionResult:
        """Enhanced git operations."""
        op = params.get("op")
        cwd = params.get("cwd", ".")
        
        commands = {
            "init": "git init",
            "status": "git status",
            "add": f"git add {params.get('files', '.')}",
            "commit": f'git commit -m "{params.get("message", "Update")}"',
            "push": f"git push {params.get('remote', 'origin')} {params.get('branch', 'master')}",
            "pull": f"git pull {params.get('remote', 'origin')} {params.get('branch', 'master')}",
            "clone": f"git clone {params.get('url')} {params.get('path', '')}",
            "branch": f"git branch {params.get('name', '')}",
            "checkout": f"git checkout {params.get('name', 'master')}"
        }
        
        cmd = commands.get(op)
        if not cmd:
            return ExecutionResult("failed", "", f"Unknown git operation: {op}")
        
        return self._run_command({"command": cmd, "cwd": cwd})

    def _launch_app(self, params: Dict[str, Any]) -> ExecutionResult:
        """Launch system application with non-blocking support."""
        app = params.get("app")
        args = params.get("args", [])
        if not app:
            return ExecutionResult("failed", "", "No app name provided")
        
        try:
            if self.system == "Windows":
                subprocess.Popen(['start', app] + args, shell=True)
            elif self.system == "Darwin":
                subprocess.Popen(['open', '-a', app] + args)
            else:
                subprocess.Popen([app] + args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ExecutionResult("success", f"Launched: {app}", verified=False)
        except Exception as e:
            return ExecutionResult("failed", "", str(e))

    def _execute_python(self, params: Dict[str, Any]) -> ExecutionResult:
        """Execute Python script with error capture."""
        code = params.get("code")
        if not code:
            return ExecutionResult("failed", "", "No Python code provided")
        
        temp_file = f"temp_luna_{int(time.time())}.py"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        result = self._run_command({"command": f"python3 {temp_file}"})
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return result
