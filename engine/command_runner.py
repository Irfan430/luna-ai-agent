"""
LUNA AI Agent - Command Runner
Author: IRFAN

Execute terminal commands with validation.
"""

import subprocess
import shlex
from typing import Dict, Any, Optional
from core.task_result import TaskResult


class CommandRunner:
    """Execute terminal commands safely."""
    
    def __init__(self):
        """Initialize command runner."""
        self.last_command = None
        self.last_result = None
    
    def run(self, command: str, timeout: int = 30, 
            cwd: Optional[str] = None) -> TaskResult:
        """
        Run a shell command.
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
            cwd: Working directory
            
        Returns:
            TaskResult with command output
        """
        self.last_command = command
        
        try:
            # Run command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            
            # Check return code
            if result.returncode == 0:
                self.last_result = TaskResult.success(
                    content=result.stdout,
                    confidence=1.0,
                    verified=True,
                    execution_used=True,
                    risk_level="low"
                )
            else:
                self.last_result = TaskResult.failed(
                    error=f"Command failed with code {result.returncode}: {result.stderr}",
                    content=result.stdout,
                    confidence=1.0
                )
            
            return self.last_result
            
        except subprocess.TimeoutExpired:
            self.last_result = TaskResult.failed(
                error=f"Command timed out after {timeout} seconds",
                content="",
                confidence=1.0
            )
            return self.last_result
            
        except Exception as e:
            self.last_result = TaskResult.failed(
                error=f"Command execution error: {str(e)}",
                content="",
                confidence=1.0
            )
            return self.last_result
    
    def run_async(self, command: str, cwd: Optional[str] = None) -> subprocess.Popen:
        """
        Run command asynchronously (non-blocking).
        
        Args:
            command: Command to execute
            cwd: Working directory
            
        Returns:
            Popen process object
        """
        self.last_command = command
        
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd
        )
        
        return process
    
    def get_last_command(self) -> Optional[str]:
        """Get last executed command."""
        return self.last_command
    
    def get_last_result(self) -> Optional[TaskResult]:
        """Get last command result."""
        return self.last_result
