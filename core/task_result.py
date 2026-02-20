"""
LUNA AI Agent - Global TaskResult Enforcement
Author: IRFAN

All execution paths — GUI, Voice, CLI — MUST return a TaskResult object.
No raw strings, no ad-hoc dicts, no partial returns are permitted.

Schema:
{
  "status":          "success | failed | partial",
  "content":         "<output content or summary>",
  "error":           "<technical error description or empty string>",
  "execution_used":  true | false,
  "confidence":      0.0 – 1.0,
  "risk_level":      "low | medium | high | blocked",
  "verified":        true | false
}
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional


VALID_STATUSES = {"success", "failed", "partial"}
VALID_RISK_LEVELS = {"low", "medium", "high", "blocked"}


@dataclass
class TaskResult:
    """
    Canonical result object for ALL LUNA execution paths.
    GUI and Voice layers MUST consume ONLY this object — never raw strings.
    """
    status: str                          # success | failed | partial
    content: str                         # Output content or summary
    error: str = ""                      # Technical error description (empty on success)
    execution_used: bool = True          # Whether the execution kernel was invoked
    confidence: float = 1.0             # Confidence score 0.0–1.0
    risk_level: str = "low"             # low | medium | high | blocked
    verified: bool = False              # Whether the output was independently verified
    system_state: Optional[Dict[str, Any]] = field(default=None)  # Snapshot of system stats

    def __post_init__(self):
        self._validate()

    def _validate(self):
        if self.status not in VALID_STATUSES:
            raise ValueError(
                f"TaskResult.status must be one of {VALID_STATUSES}, got '{self.status}'"
            )
        if self.risk_level not in VALID_RISK_LEVELS:
            raise ValueError(
                f"TaskResult.risk_level must be one of {VALID_RISK_LEVELS}, got '{self.risk_level}'"
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"TaskResult.confidence must be between 0.0 and 1.0, got {self.confidence}"
            )
        # Enforce: success without verification is demoted to partial
        if self.status == "success" and not self.verified:
            object.__setattr__(self, 'status', 'partial')
            object.__setattr__(self, 'error',
                'Status demoted from success to partial: output was not independently verified.')

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to canonical dict for GUI, Voice, and logging layers."""
        return {
            "status":         self.status,
            "content":        self.content,
            "error":          self.error,
            "execution_used": self.execution_used,
            "confidence":     self.confidence,
            "risk_level":     self.risk_level,
            "verified":       self.verified,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskResult":
        """Deserialize from a dict (e.g., from JSON response)."""
        return cls(
            status=data.get("status", "failed"),
            content=data.get("content", ""),
            error=data.get("error", ""),
            execution_used=data.get("execution_used", True),
            confidence=float(data.get("confidence", 0.0)),
            risk_level=data.get("risk_level", "low"),
            verified=bool(data.get("verified", False)),
            system_state=data.get("system_state"),
        )

    @classmethod
    def failure(cls, error: str, risk_level: str = "low") -> "TaskResult":
        """Convenience constructor for a failed result."""
        return cls(
            status="failed",
            content="",
            error=error,
            execution_used=False,
            confidence=0.0,
            risk_level=risk_level,
            verified=False,
        )

    @classmethod
    def success(cls, content: str, confidence: float = 1.0, risk_level: str = "low") -> "TaskResult":
        """Convenience constructor for a verified successful result."""
        return cls(
            status="success",
            content=content,
            error="",
            execution_used=True,
            confidence=confidence,
            risk_level=risk_level,
            verified=True,
        )

    def __repr__(self):
        return (
            f"TaskResult(status={self.status!r}, verified={self.verified}, "
            f"confidence={self.confidence:.2f}, risk={self.risk_level!r})"
        )
