"""
LUNA AI Agent - Risk Classifier
Author: IRFAN

Classifies operations by risk level.
"""

from typing import Dict, Any, List, Literal
import re


RiskLevel = Literal["low", "medium", "high", "dangerous"]


class RiskClassifier:
    """Classify operations by risk level."""
    
    # Dangerous patterns that should be blocked
    DANGEROUS_PATTERNS = [
        r'rm\s+-rf\s+/',
        r'rm\s+-rf\s+\*',
        r'mkfs\.',
        r'dd\s+if=.*of=/dev/',
        r':(){ :|:& };:',  # Fork bomb
        r'chmod\s+-R\s+777\s+/',
        r'chown\s+-R.*/',
        r'shutdown',
        r'reboot',
        r'init\s+0',
        r'init\s+6',
        r'systemctl\s+poweroff',
        r'systemctl\s+reboot',
    ]
    
    # High risk patterns requiring confirmation
    HIGH_RISK_PATTERNS = [
        r'rm\s+-rf',
        r'git\s+push',
        r'git\s+force',
        r'git\s+reset\s+--hard',
        r'drop\s+database',
        r'drop\s+table',
        r'delete\s+from.*where',
        r'truncate\s+table',
        r'chmod\s+777',
        r'sudo\s+',
    ]
    
    # Medium risk patterns with optional confirmation
    MEDIUM_RISK_PATTERNS = [
        r'git\s+commit',
        r'npm\s+install',
        r'pip\s+install',
        r'apt\s+install',
        r'brew\s+install',
        r'docker\s+run',
        r'docker\s+build',
        r'mv\s+',
        r'cp\s+-r',
    ]
    
    def __init__(self):
        """Initialize risk classifier."""
        pass
    
    def classify_command(self, command: str) -> RiskLevel:
        """
        Classify a shell command by risk level.
        
        Args:
            command: Shell command to classify
            
        Returns:
            Risk level: low, medium, high, or dangerous
        """
        command_lower = command.lower().strip()
        
        # Check dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command_lower, re.IGNORECASE):
                return "dangerous"
        
        # Check high risk patterns
        for pattern in self.HIGH_RISK_PATTERNS:
            if re.search(pattern, command_lower, re.IGNORECASE):
                return "high"
        
        # Check medium risk patterns
        for pattern in self.MEDIUM_RISK_PATTERNS:
            if re.search(pattern, command_lower, re.IGNORECASE):
                return "medium"
        
        # Default to low risk
        return "low"
    
    def classify_file_operation(self, operation: str, path: str) -> RiskLevel:
        """
        Classify a file operation by risk level.
        
        Args:
            operation: Operation type (create, edit, delete, move)
            path: File path
            
        Returns:
            Risk level
        """
        # Dangerous: operations on system directories
        system_paths = ['/etc', '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/boot', '/sys']
        for sys_path in system_paths:
            if path.startswith(sys_path):
                return "dangerous"
        
        # High risk: delete operations
        if operation == "delete":
            return "high"
        
        # Medium risk: move operations
        if operation == "move":
            return "medium"
        
        # Low risk: create and edit
        return "low"
    
    def classify_git_operation(self, operation: str, remote: bool = False) -> RiskLevel:
        """
        Classify a git operation by risk level.
        
        Args:
            operation: Git operation (commit, push, pull, clone, etc.)
            remote: Whether operation affects remote repository
            
        Returns:
            Risk level
        """
        dangerous_ops = ["reset --hard", "force push", "push --force"]
        high_risk_ops = ["push", "force"]
        medium_risk_ops = ["commit", "merge", "rebase"]
        
        operation_lower = operation.lower()
        
        for op in dangerous_ops:
            if op in operation_lower:
                return "dangerous"
        
        for op in high_risk_ops:
            if op in operation_lower:
                return "high"
        
        for op in medium_risk_ops:
            if op in operation_lower:
                return "medium"
        
        return "low"
    
    def should_require_confirmation(self, risk_level: RiskLevel, 
                                   risk_config: Dict[str, str]) -> bool:
        """
        Determine if operation requires user confirmation.
        
        Args:
            risk_level: Classified risk level
            risk_config: Risk configuration from config.yaml
            
        Returns:
            True if confirmation required
        """
        action = risk_config.get(risk_level, "require_confirmation")
        
        if action == "block":
            return True  # Will be blocked, but confirmation can override
        elif action == "require_confirmation":
            return True
        elif action == "optional_confirmation":
            return False  # Can be made optional in GUI
        elif action == "auto_execute":
            return False
        
        return True  # Default to safe side
