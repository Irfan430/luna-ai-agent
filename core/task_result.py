"""
LUNA AI Agent - Task Result Protocol
Author: IRFAN

Standardized task result format for all operations.
"""

from dataclasses import dataclass
from typing import Optional, Literal


@dataclass
class TaskResult:
    """
    Standard task result format.
    All execution must return this structure.
    """
    status: Literal["success", "failed", "partial"]
    content: str
    error: str = ""
    execution_used: bool = False
    confidence: float = 0.0
    risk_level: Literal["low", "medium", "high", "dangerous"] = "low"
    verified: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status,
            "content": self.content,
            "error": self.error,
            "execution_used": self.execution_used,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "verified": self.verified
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TaskResult':
        """Create TaskResult from dictionary."""
        return cls(
            status=data.get("status", "failed"),
            content=data.get("content", ""),
            error=data.get("error", ""),
            execution_used=data.get("execution_used", False),
            confidence=data.get("confidence", 0.0),
            risk_level=data.get("risk_level", "low"),
            verified=data.get("verified", False)
        )
    
    @staticmethod
    def success(content: str, confidence: float = 1.0, verified: bool = True, 
                execution_used: bool = False, risk_level: str = "low") -> 'TaskResult':
        """Create a success result."""
        return TaskResult(
            status="success",
            content=content,
            confidence=confidence,
            verified=verified,
            execution_used=execution_used,
            risk_level=risk_level
        )
    
    @staticmethod
    def failed(error: str, content: str = "", confidence: float = 0.0) -> 'TaskResult':
        """Create a failed result."""
        return TaskResult(
            status="failed",
            content=content,
            error=error,
            confidence=confidence,
            verified=True
        )
    
    @staticmethod
    def partial(content: str, error: str, confidence: float = 0.5, 
                execution_used: bool = True) -> 'TaskResult':
        """Create a partial result."""
        return TaskResult(
            status="partial",
            content=content,
            error=error,
            confidence=confidence,
            execution_used=execution_used,
            verified=True
        )
