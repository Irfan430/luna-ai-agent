"""
LUNA AI Agent - Guardrails
Author: IRFAN

Safety constraints and limits.
"""

from typing import Dict, Any
from config.config_loader import get_config


class Guardrails:
    """Safety guardrails and constraints."""
    
    def __init__(self):
        """Initialize guardrails."""
        self.config = get_config()
        self.safety_config = self.config.get_safety_config()
        
        self.max_planning_iterations = self.safety_config.get("max_planning_iterations", 5)
        self.max_continuation_retries = self.safety_config.get("max_continuation_retries", 3)
        
        self.planning_iteration_count = 0
        self.continuation_retry_count = 0
    
    def check_planning_limit(self) -> bool:
        """
        Check if planning iteration limit exceeded.
        
        Returns:
            True if limit not exceeded, False otherwise
        """
        return self.planning_iteration_count < self.max_planning_iterations
    
    def increment_planning_iteration(self) -> None:
        """Increment planning iteration counter."""
        self.planning_iteration_count += 1
    
    def reset_planning_iteration(self) -> None:
        """Reset planning iteration counter."""
        self.planning_iteration_count = 0
    
    def check_continuation_limit(self) -> bool:
        """
        Check if continuation retry limit exceeded.
        
        Returns:
            True if limit not exceeded, False otherwise
        """
        return self.continuation_retry_count < self.max_continuation_retries
    
    def increment_continuation_retry(self) -> None:
        """Increment continuation retry counter."""
        self.continuation_retry_count += 1
    
    def reset_continuation_retry(self) -> None:
        """Reset continuation retry counter."""
        self.continuation_retry_count = 0
    
    def is_operation_allowed(self, operation: str, risk_level: str) -> tuple[bool, str]:
        """
        Check if operation is allowed based on risk level.
        
        Args:
            operation: Operation description
            risk_level: Risk level (low, medium, high, dangerous)
            
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        risk_config = self.safety_config.get("risk_levels", {})
        action = risk_config.get(risk_level, "require_confirmation")
        
        if action == "block":
            return False, f"Operation blocked due to {risk_level} risk level"
        
        # All other actions are allowed (with or without confirmation)
        return True, ""
    
    def validate_command(self, command: str) -> tuple[bool, str]:
        """
        Validate command for safety.
        
        Args:
            command: Command to validate
            
        Returns:
            Tuple of (valid: bool, reason: str)
        """
        # Block empty commands
        if not command.strip():
            return False, "Empty command"
        
        # Block commands with suspicious patterns
        suspicious_patterns = [
            "curl | sh",
            "wget | sh",
            "curl | bash",
            "wget | bash",
        ]
        
        command_lower = command.lower()
        for pattern in suspicious_patterns:
            if pattern in command_lower:
                return False, f"Suspicious pattern detected: {pattern}"
        
        return True, ""
    
    def get_limits_status(self) -> Dict[str, Any]:
        """
        Get current status of all limits.
        
        Returns:
            Dictionary with limit statuses
        """
        return {
            "planning_iterations": {
                "current": self.planning_iteration_count,
                "max": self.max_planning_iterations,
                "exceeded": not self.check_planning_limit()
            },
            "continuation_retries": {
                "current": self.continuation_retry_count,
                "max": self.max_continuation_retries,
                "exceeded": not self.check_continuation_limit()
            }
        }
