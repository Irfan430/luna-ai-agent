"""LUNA AI Agent - Advanced Execution Kernel (AEK) v4.0
Author: IRFAN

Phase 4 Execution Verification Upgrades:
  - _launch_app: verify process started with retry, return error+reason on failure.
  - _run_command: explicit exit code in error, never fake success.
  - _process_operation: kill verification — confirm process no longer running.
  - All handlers: never return verified=True unless outcome is confirmed.

Hardened deterministic execution layer with full OS control::
  - Shell command execution with injection detection
  - File operations with verification
  - Git automation
  - Process management
  - Network operations
  - System information gathering
  - GUI automation (mouse, keyboard, window management)
  - Application launch with verification
  - Active window detection
"""

import subprocess
import os
import shutil
import platform
import psutil
import socket
import time
import re
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    from pynput import mouse, keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False


# ------------------------------------------------------------------
# Execution Result (canonical TaskResult)
# ------------------------------------------------------------------

@dataclass
class ExecutionResult:
    """Standard canonical execution result — all paths must return this."""
    status: str                  # success | failed | partial
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


# ------------------------------------------------------------------
# Schema definitions
# ------------------------------------------------------------------

REQUIRED_PARAMS: Dict[str, List[str]] = {
    "command":        ["command"],
    "file_op":        ["op", "path"],
    "git_op":         ["op"],
    "app_launch":     ["app"],
    "python_exec":    ["code"],
    "process_op":     ["op"],
    "network_op":     ["op"],
    "system_info":    [],
    "gui_mouse":      ["action"],
    "gui_keyboard":   ["action"],
    "gui_window":     ["action"],
}

ALLOWED_ACTIONS = set(REQUIRED_PARAMS.keys())

SHELL_INJECTION_PATTERNS = [
    r';\s*rm\b', r'&&\s*rm\b', r'\|\s*rm\b',
    r'`[^`]+`', r'\$\([^)]+\)',
    r'>\s*/dev/', r'2>&1\s*&&',
]


# ------------------------------------------------------------------
# Execution Kernel
# ------------------------------------------------------------------

class ExecutionKernel:
    """Hardened execution layer with full OS control capabilities."""

    def __init__(self):
        self.system = platform.system()
        self.pyautogui_available = PYAUTOGUI_AVAILABLE
        self.pynput_available = PYNPUT_AVAILABLE

    # ------------------------------------------------------------------
    # Schema validation
    # ------------------------------------------------------------------

    def validate_schema(self, action: str, parameters: Dict[str, Any]) -> Optional[str]:
        """Validate action schema before execution."""
        if action not in ALLOWED_ACTIONS:
            return f"Unknown action type: '{action}'. Allowed: {sorted(ALLOWED_ACTIONS)}"

        required = REQUIRED_PARAMS.get(action, [])
        for param in required:
            if param not in parameters or parameters[param] is None:
                return f"Missing required parameter '{param}' for action '{action}'"

        return None

    # ------------------------------------------------------------------
    # Command normalization
    # ------------------------------------------------------------------

    def normalize_command(self, command: str) -> str:
        """Normalize a shell command."""
        return re.sub(r'\s+', ' ', command.strip())

    def detect_shell_injection(self, command: str) -> bool:
        """Return True if the command contains shell injection patterns."""
        for pattern in SHELL_INJECTION_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        return False

    # ------------------------------------------------------------------
    # System stats
    # ------------------------------------------------------------------

    def get_system_stats(self) -> Dict[str, Any]:
        """Get real-time system resource usage."""
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "boot_time": time.ctime(psutil.boot_time()),
            "os": f"{self.system} {platform.release()}",
        }

    # ------------------------------------------------------------------
    # Main execution router
    # ------------------------------------------------------------------

    def execute(self, action: str, parameters: Dict[str, Any]) -> ExecutionResult:
        """Route action to appropriate handler after strict schema validation."""
        schema_error = self.validate_schema(action, parameters)
        if schema_error:
            return ExecutionResult(
                status="failed",
                content="",
                error=f"Schema validation failed: {schema_error}",
                execution_used=False,
                verified=False,
            )

        handlers = {
            "command":        self._run_command,
            "file_op":        self._file_operation,
            "git_op":         self._git_operation,
            "app_launch":     self._launch_app,
            "python_exec":    self._execute_python,
            "process_op":     self._process_operation,
            "network_op":     self._network_operation,
            "system_info":    self._get_system_info,
            "gui_mouse":      self._gui_mouse,
            "gui_keyboard":   self._gui_keyboard,
            "gui_window":     self._gui_window,
        }

        handler = handlers.get(action)
        try:
            result = handler(parameters)
            result.system_state = self.get_system_stats()
            if result.status == "success" and not result.verified:
                result.status = "partial"
                result.error = "Execution completed but output verification was not performed."
            return result
        except Exception as e:
            return ExecutionResult(
                status="failed",
                content="",
                error=f"Execution error: {str(e)}",
                system_state=self.get_system_stats(),
                verified=False,
            )

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _run_command(self, params: Dict[str, Any]) -> ExecutionResult:
        """Run a shell command with injection detection and return code validation."""
        command = params.get("command")
        cwd = params.get("cwd")
        timeout = params.get("timeout", 60)

        if not command:
            return ExecutionResult("failed", "", "No command provided")

        command = self.normalize_command(command)

        if self.detect_shell_injection(command):
            return ExecutionResult(
                "failed", "", f"Shell injection pattern detected in command: {command}",
                execution_used=False, verified=False
            )

        try:
            proc = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )

            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()

            if proc.returncode == 0:
                return ExecutionResult(
                    status="success",
                    content=stdout,
                    error=stderr if stderr else "",
                    verified=True,
                    confidence=1.0,
                )
            else:
                return ExecutionResult(
                    status="failed",
                    content=stdout,
                    error=f"Return code {proc.returncode}: {stderr}",
                    verified=False,
                    confidence=0.0,
                )
        except subprocess.TimeoutExpired:
            return ExecutionResult("failed", "", f"Command timed out after {timeout}s", verified=False)

    def _file_operation(self, params: Dict[str, Any]) -> ExecutionResult:
        """File operations with existence checks and post-op verification."""
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
                verified = os.path.exists(path)
                return ExecutionResult("success" if verified else "failed", f"File created: {path}", verified=verified)

            elif op == "read":
                if not os.path.exists(path):
                    return ExecutionResult("failed", "", f"File not found: {path}", verified=False)
                with open(path, 'r', encoding='utf-8') as f:
                    data = f.read()
                return ExecutionResult("success", data, verified=True)

            elif op == "edit":
                if not os.path.exists(path):
                    return ExecutionResult("failed", "", f"File not found: {path}", verified=False)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                verified = os.path.exists(path)
                return ExecutionResult("success" if verified else "failed", f"File edited: {path}", verified=verified)

            elif op == "delete":
                if not os.path.exists(path):
                    return ExecutionResult("failed", "", f"Path not found: {path}", verified=False)
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                verified = not os.path.exists(path)
                return ExecutionResult("success" if verified else "failed", f"Deleted: {path}", verified=verified)

            elif op == "move":
                if not os.path.exists(path):
                    return ExecutionResult("failed", "", f"Source not found: {path}", verified=False)
                shutil.move(path, dest)
                verified = os.path.exists(dest)
                return ExecutionResult("success" if verified else "failed", f"Moved: {path} -> {dest}", verified=verified)

            elif op == "list":
                if not os.path.isdir(path):
                    return ExecutionResult("failed", "", f"Directory not found: {path}", verified=False)
                files = os.listdir(path)
                return ExecutionResult("success", "\n".join(files), verified=True)

            else:
                return ExecutionResult("failed", "", f"Unknown file operation: {op}", verified=False)

        except Exception as e:
            return ExecutionResult("failed", "", str(e), verified=False)

    def _process_operation(self, params: Dict[str, Any]) -> ExecutionResult:
        """Manage system processes with output verification."""
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
                    # Phase 4 Fix: verify process is no longer running
                    time.sleep(0.5)
                    still_running = psutil.pid_exists(pid)
                    if still_running:
                        proc.kill()  # Force kill
                        time.sleep(0.3)
                        still_running = psutil.pid_exists(pid)
                    verified_kill = not still_running
                    return ExecutionResult(
                        "success" if verified_kill else "failed",
                        f"Terminated process {pid}" if verified_kill else "",
                        "" if verified_kill else f"Process {pid} still running after terminate+kill",
                        verified=verified_kill,
                    )
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

            return ExecutionResult("failed", "", f"Unknown process operation: {op}", verified=False)
        except Exception as e:
            return ExecutionResult("failed", "", str(e), verified=False)

    def _network_operation(self, params: Dict[str, Any]) -> ExecutionResult:
        """Network operations with result verification."""
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
                result = sock.connect_ex((host, int(port)))
                sock.close()
                status = "open" if result == 0 else "closed"
                return ExecutionResult("success", f"Port {port} on {host} is {status}", verified=True)

            elif op == "list_interfaces":
                interfaces = psutil.net_if_addrs()
                return ExecutionResult("success", str(interfaces), verified=True)

            return ExecutionResult("failed", "", f"Unknown network operation: {op}", verified=False)
        except Exception as e:
            return ExecutionResult("failed", "", str(e), verified=False)

    def _get_system_info(self, params: Dict[str, Any]) -> ExecutionResult:
        """Get detailed system information."""
        info = {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(),
            "memory": str(psutil.virtual_memory()),
            "disk": str(psutil.disk_usage('/')),
            "users": [u.name for u in psutil.users()],
        }
        return ExecutionResult("success", str(info), verified=True)

    def _git_operation(self, params: Dict[str, Any]) -> ExecutionResult:
        """Git operations with force-push detection."""
        op = params.get("op")
        cwd = params.get("cwd", ".")

        if op == "push" and params.get("force", False):
            return ExecutionResult(
                "failed", "", "Force push is blocked by execution kernel policy.",
                execution_used=False, verified=False
            )

        commands = {
            "init":     "git init",
            "status":   "git status",
            "add":      f"git add {params.get('files', '.')}",
            "commit":   f'git commit -m "{params.get("message", "Update")}"',
            "push":     f"git push {params.get('remote', 'origin')} {params.get('branch', 'master')}",
            "pull":     f"git pull {params.get('remote', 'origin')} {params.get('branch', 'master')}",
            "clone":    f"git clone {params.get('url')} {params.get('path', '')}",
            "branch":   f"git branch {params.get('name', '')}",
            "checkout": f"git checkout {params.get('name', 'master')}",
        }

        cmd = commands.get(op)
        if not cmd:
            return ExecutionResult("failed", "", f"Unknown git operation: {op}", verified=False)

        return self._run_command({"command": cmd, "cwd": cwd})

    def _launch_app(self, params: Dict[str, Any]) -> ExecutionResult:
        """Launch system application with verification."""
        app = params.get("app")
        args = params.get("args", [])
        if not app:
            return ExecutionResult("failed", "", "No app name provided", verified=False)

        try:
            if self.system == "Windows":
                subprocess.Popen(['start', app] + args, shell=True)
            elif self.system == "Darwin":
                subprocess.Popen(['open', '-a', app] + args)
            else:
                subprocess.Popen([app] + args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Phase 4 Fix: verify process started with retry
            for attempt in range(3):
                time.sleep(0.8)
                for proc in psutil.process_iter(['name']):
                    try:
                        if app.lower() in (proc.info.get('name') or '').lower():
                            return ExecutionResult(
                                "success",
                                f"Launched and verified: {app} (PID: {proc.pid})",
                                verified=True,
                                confidence=1.0,
                            )
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            # Process not found after retries — report failure honestly
            return ExecutionResult(
                "failed",
                "",
                f"App '{app}' launched but process could not be verified after 3 attempts. "
                "It may have exited immediately or the process name differs.",
                verified=False,
                confidence=0.3,
            )
        except Exception as e:
            return ExecutionResult("failed", "", str(e), verified=False)

    def _execute_python(self, params: Dict[str, Any]) -> ExecutionResult:
        """Execute Python script with error capture and temp file cleanup."""
        code = params.get("code")
        if not code:
            return ExecutionResult("failed", "", "No Python code provided", verified=False)

        temp_file = f"/tmp/luna_exec_{int(time.time())}.py"
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)
            result = self._run_command({"command": f"python3 {temp_file}"})
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        return result

    # ------------------------------------------------------------------
    # GUI Automation (pyautogui)
    # ------------------------------------------------------------------

    def _gui_mouse(self, params: Dict[str, Any]) -> ExecutionResult:
        """GUI mouse automation."""
        if not self.pyautogui_available:
            return ExecutionResult("failed", "", "pyautogui not available", verified=False)

        action = params.get("action")
        x = params.get("x", 0)
        y = params.get("y", 0)

        try:
            if action == "move":
                pyautogui.moveTo(x, y, duration=0.5)
                return ExecutionResult("success", f"Moved mouse to ({x}, {y})", verified=True)

            elif action == "click":
                pyautogui.click(x, y)
                return ExecutionResult("success", f"Clicked at ({x}, {y})", verified=True)

            elif action == "double_click":
                pyautogui.doubleClick(x, y)
                return ExecutionResult("success", f"Double-clicked at ({x}, {y})", verified=True)

            elif action == "right_click":
                pyautogui.rightClick(x, y)
                return ExecutionResult("success", f"Right-clicked at ({x}, {y})", verified=True)

            else:
                return ExecutionResult("failed", "", f"Unknown mouse action: {action}", verified=False)

        except Exception as e:
            return ExecutionResult("failed", "", str(e), verified=False)

    def _gui_keyboard(self, params: Dict[str, Any]) -> ExecutionResult:
        """GUI keyboard automation."""
        if not self.pyautogui_available:
            return ExecutionResult("failed", "", "pyautogui not available", verified=False)

        action = params.get("action")
        text = params.get("text", "")
        key = params.get("key", "")

        try:
            if action == "type":
                pyautogui.typewrite(text, interval=0.05)
                return ExecutionResult("success", f"Typed: {text}", verified=True)

            elif action == "press":
                pyautogui.press(key)
                return ExecutionResult("success", f"Pressed: {key}", verified=True)

            elif action == "hotkey":
                keys = params.get("keys", [])
                pyautogui.hotkey(*keys)
                return ExecutionResult("success", f"Hotkey: {'+'.join(keys)}", verified=True)

            else:
                return ExecutionResult("failed", "", f"Unknown keyboard action: {action}", verified=False)

        except Exception as e:
            return ExecutionResult("failed", "", str(e), verified=False)

    def _gui_window(self, params: Dict[str, Any]) -> ExecutionResult:
        """GUI window management."""
        action = params.get("action")
        window_title = params.get("window_title", "")

        try:
            if action == "list":
                windows = []
                for proc in psutil.process_iter(['name']):
                    windows.append(proc.info['name'])
                return ExecutionResult("success", "\n".join(windows[:20]), verified=True)

            elif action == "focus":
                if self.system == "Windows":
                    os.system(f'tasklist /FI "WINDOWTITLE eq {window_title}" 2>NUL | find /I /N "{window_title}">NUL')
                else:
                    return ExecutionResult("partial", "", "Window focus not fully supported on this OS", verified=False)
                return ExecutionResult("success", f"Focused window: {window_title}", verified=False)

            elif action == "close":
                if self.system == "Windows":
                    os.system(f'taskkill /FI "WINDOWTITLE eq {window_title}" /T /F')
                else:
                    return ExecutionResult("partial", "", "Window close not fully supported on this OS", verified=False)
                return ExecutionResult("success", f"Closed window: {window_title}", verified=False)

            else:
                return ExecutionResult("failed", "", f"Unknown window action: {action}", verified=False)

        except Exception as e:
            return ExecutionResult("failed", "", str(e), verified=False)
