"""
LUNA AI Agent - Executor
Author: IRFAN

Main execution orchestrator.
"""

from typing import Dict, Any, Optional
from .command_runner import CommandRunner
from .file_manager import FileManager
from .git_manager import GitManager
from .app_launcher import AppLauncher
from core.task_result import TaskResult
from safety.risk_classifier import RiskClassifier
from safety.guardrails import Guardrails


class Executor:
    """Main execution orchestrator."""
    
    def __init__(self):
        """Initialize executor."""
        self.command_runner = CommandRunner()
        self.file_manager = FileManager()
        self.git_manager = GitManager()
        self.app_launcher = AppLauncher()
        self.risk_classifier = RiskClassifier()
        self.guardrails = Guardrails()
    
    def execute(self, intent: Dict[str, Any]) -> TaskResult:
        """
        Execute intent.
        
        Args:
            intent: Parsed intent dictionary
            
        Returns:
            TaskResult
        """
        action = intent.get("action", "")
        parameters = intent.get("parameters", {})
        requires_execution = intent.get("requires_execution", False)
        
        if not requires_execution:
            return TaskResult.success(
                content="No execution required",
                confidence=1.0,
                verified=True,
                execution_used=False
            )
        
        # Route to appropriate handler
        if "command" in parameters:
            return self._execute_command(parameters)
        elif "file_operation" in parameters:
            return self._execute_file_operation(parameters)
        elif "git_operation" in parameters:
            return self._execute_git_operation(parameters)
        elif "app_name" in parameters:
            return self._execute_app_launch(parameters)
        else:
            return TaskResult.failed(
                error=f"Unknown execution type for action: {action}",
                content=""
            )
    
    def _execute_command(self, parameters: Dict[str, Any]) -> TaskResult:
        """Execute shell command."""
        command = parameters.get("command", "")
        cwd = parameters.get("cwd")
        timeout = parameters.get("timeout", 30)
        
        # Validate command
        valid, reason = self.guardrails.validate_command(command)
        if not valid:
            return TaskResult.failed(
                error=f"Command validation failed: {reason}",
                content=""
            )
        
        # Classify risk
        risk_level = self.risk_classifier.classify_command(command)
        
        # Check if allowed
        allowed, reason = self.guardrails.is_operation_allowed(command, risk_level)
        if not allowed:
            return TaskResult.failed(
                error=reason,
                content=""
            )
        
        # Execute command
        result = self.command_runner.run(command, timeout, cwd)
        result.risk_level = risk_level
        
        return result
    
    def _execute_file_operation(self, parameters: Dict[str, Any]) -> TaskResult:
        """Execute file operation."""
        operation = parameters.get("file_operation", "")
        path = parameters.get("path", "")
        content = parameters.get("content", "")
        destination = parameters.get("destination", "")
        
        # Classify risk
        risk_level = self.risk_classifier.classify_file_operation(operation, path)
        
        # Check if allowed
        allowed, reason = self.guardrails.is_operation_allowed(operation, risk_level)
        if not allowed:
            return TaskResult.failed(
                error=reason,
                content=""
            )
        
        # Execute operation
        if operation == "create":
            result = self.file_manager.create_file(path, content)
        elif operation == "read":
            result = self.file_manager.read_file(path)
        elif operation == "edit":
            result = self.file_manager.edit_file(path, content)
        elif operation == "delete":
            result = self.file_manager.delete_file(path)
        elif operation == "move":
            result = self.file_manager.move_file(path, destination)
        else:
            return TaskResult.failed(
                error=f"Unknown file operation: {operation}",
                content=""
            )
        
        result.risk_level = risk_level
        return result
    
    def _execute_git_operation(self, parameters: Dict[str, Any]) -> TaskResult:
        """Execute git operation."""
        operation = parameters.get("git_operation", "")
        cwd = parameters.get("cwd")
        
        # Classify risk
        risk_level = self.risk_classifier.classify_git_operation(operation)
        
        # Check if allowed
        allowed, reason = self.guardrails.is_operation_allowed(operation, risk_level)
        if not allowed:
            return TaskResult.failed(
                error=reason,
                content=""
            )
        
        # Execute operation
        if operation == "init":
            result = self.git_manager.init(cwd or ".")
        elif operation == "clone":
            url = parameters.get("url", "")
            result = self.git_manager.clone(url, cwd)
        elif operation == "add":
            files = parameters.get("files", ".")
            result = self.git_manager.add(files, cwd)
        elif operation == "commit":
            message = parameters.get("message", "Update")
            result = self.git_manager.commit(message, cwd)
        elif operation == "push":
            remote = parameters.get("remote", "origin")
            branch = parameters.get("branch")
            result = self.git_manager.push(remote, branch, cwd)
        elif operation == "pull":
            remote = parameters.get("remote", "origin")
            branch = parameters.get("branch")
            result = self.git_manager.pull(remote, branch, cwd)
        elif operation == "status":
            result = self.git_manager.status(cwd)
        elif operation == "branch":
            name = parameters.get("name")
            result = self.git_manager.branch(name, cwd)
        elif operation == "checkout":
            branch = parameters.get("branch", "")
            create = parameters.get("create", False)
            result = self.git_manager.checkout(branch, create, cwd)
        else:
            return TaskResult.failed(
                error=f"Unknown git operation: {operation}",
                content=""
            )
        
        result.risk_level = risk_level
        return result
    
    def _execute_app_launch(self, parameters: Dict[str, Any]) -> TaskResult:
        """Execute app launch."""
        app_name = parameters.get("app_name", "")
        args = parameters.get("args")
        
        return self.app_launcher.launch(app_name, args)
