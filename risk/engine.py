"""
LUNA AI Agent - Risk Engine
Author: IRFAN

Risk classification and safety guardrails for autonomous actions.
"""

import re
from typing import Dict, Any, List, Literal


RiskLevel = Literal["low", "medium", "high", "dangerous"]


class RiskEngine:
    """Classify and score actions based on potential impact."""
    
    DANGEROUS_PATTERNS = [
        r'rm\s+-rf\s+/', r'rm\s+-rf\s+\*', r'mkfs\.', r'dd\s+if=.*of=/dev/',
        r':(){ :|:& };:', r'chmod\s+-R\s+777\s+/', r'chown\s+-R.*/',
        r'shutdown', r'reboot', r'init\s+0', r'init\s+6',
        r'systemctl\s+poweroff', r'systemctl\s+reboot'
    ]
    
    HIGH_RISK_PATTERNS = [
        r'rm\s+-rf', r'git\s+push', r'git\s+force', r'git\s+reset\s+--hard',
        r'drop\s+database', r'drop\s+table', r'delete\s+from.*where',
        r'truncate\s+table', r'chmod\s+777', r'sudo\s+'
    ]
    
    MEDIUM_RISK_PATTERNS = [
        r'git\s+commit', r'npm\s+install', r'pip\s+install', r'apt\s+install',
        r'brew\s+install', r'docker\s+run', r'docker\s+build', r'mv\s+', r'cp\s+-r'
    ]

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.risk_config = config.get('safety', {}).get('risk_levels', {})

    def classify_action(self, action: str, parameters: Dict[str, Any]) -> RiskLevel:
        """Classify an action by risk level."""
        # Combine action and parameters into a single string for pattern matching
        action_str = f"{action} {str(parameters)}".lower()
        
        # Check dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, action_str, re.IGNORECASE):
                return "dangerous"
        
        # Check high risk patterns
        for pattern in self.HIGH_RISK_PATTERNS:
            if re.search(pattern, action_str, re.IGNORECASE):
                return "high"
        
        # Check medium risk patterns
        for pattern in self.MEDIUM_RISK_PATTERNS:
            if re.search(pattern, action_str, re.IGNORECASE):
                return "medium"
        
        # Default to low risk
        return "low"

    def should_require_confirmation(self, risk_level: RiskLevel) -> bool:
        """Determine if an action requires user confirmation."""
        action_type = self.risk_config.get(risk_level, "mandatory_confirmation")
        
        if action_type == "block":
            return True  # Will be blocked, but confirmation can override
        elif action_type == "mandatory_confirmation":
            return True
        elif action_type == "optional_confirmation":
            return False  # Can be made optional in GUI
        elif action_type == "auto_execute":
            return False
        
        return True  # Default to safe side

    def is_blocked(self, risk_level: RiskLevel) -> bool:
        """Check if an action is blocked by default."""
        return self.risk_config.get(risk_level) == "block"
