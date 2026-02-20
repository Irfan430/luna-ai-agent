"""
LUNA AI Agent - Risk Engine v2.0
Author: IRFAN

Deep risk scoring engine with:
  - Numeric risk scoring (0–100)
  - Pattern-based destructive detection
  - File deletion detection
  - Git force push detection
  - Shell injection detection
  - Configurable thresholds
  - Four risk categories: low / medium / high / blocked
"""

import re
from typing import Dict, Any, List, Tuple


# ------------------------------------------------------------------
# Risk category bands (numeric score → label)
# ------------------------------------------------------------------
#   0 –  30 → low
#  31 –  60 → medium
#  61 –  80 → high
#  81 – 100 → blocked

RISK_BANDS = [
    (81, 100, "blocked"),
    (61, 80,  "high"),
    (31, 60,  "medium"),
    (0,  30,  "low"),
]


def score_to_label(score: int) -> str:
    for lo, hi, label in RISK_BANDS:
        if lo <= score <= hi:
            return label
    return "blocked"


# ------------------------------------------------------------------
# Pattern registry — each entry: (regex, score_contribution, description)
# ------------------------------------------------------------------

RISK_PATTERNS: List[Tuple[str, int, str]] = [
    # ── Blocked / Catastrophic (score 81–100) ──────────────────────
    (r'rm\s+-rf\s+/',                   95, "recursive delete from root"),
    (r'rm\s+-rf\s+\*',                  92, "recursive delete all"),
    (r'mkfs\.',                          95, "filesystem format"),
    (r'dd\s+if=.*of=/dev/',             95, "raw disk write"),
    (r':(){ :|:& };:',                  100, "fork bomb"),
    (r'chmod\s+-R\s+777\s+/',           85, "world-writable root"),
    (r'chown\s+-R.*/',                  83, "recursive ownership change on root"),
    (r'\bshutdown\b',                   90, "system shutdown"),
    (r'\breboot\b',                     90, "system reboot"),
    (r'\binit\s+[06]\b',                90, "init runlevel 0/6"),
    (r'systemctl\s+(poweroff|reboot)',  90, "systemctl shutdown/reboot"),
    (r'>\s*/dev/sd',                    95, "redirect to block device"),
    (r'wipefs',                         95, "wipe filesystem signatures"),
    (r'shred\s+',                       88, "secure file shred"),

    # ── Shell injection (score 85) ─────────────────────────────────
    (r';\s*rm\b',                       85, "shell injection: chained rm"),
    (r'&&\s*rm\b',                      85, "shell injection: conditional rm"),
    (r'\|\s*rm\b',                      85, "shell injection: piped rm"),
    (r'`[^`]+`',                        82, "backtick subshell execution"),
    (r'\$\([^)]+\)',                    82, "dollar-paren subshell execution"),

    # ── High risk (score 61–80) ────────────────────────────────────
    (r'rm\s+-rf\b',                     75, "recursive force delete"),
    (r'git\s+push\s+.*--force',         78, "git force push"),
    (r'git\s+push\s+-f\b',             78, "git force push (short flag)"),
    (r'git\s+reset\s+--hard',           70, "git hard reset"),
    (r'drop\s+database',                72, "SQL drop database"),
    (r'drop\s+table',                   68, "SQL drop table"),
    (r'delete\s+from.*where',           65, "SQL delete with where"),
    (r'truncate\s+table',               67, "SQL truncate table"),
    (r'chmod\s+777',                    65, "world-writable permission"),
    (r'\bsudo\s+',                      62, "sudo privilege escalation"),
    (r'curl\s+.*\|\s*bash',             80, "pipe curl to bash"),
    (r'wget\s+.*\|\s*bash',             80, "pipe wget to bash"),
    (r'eval\s+',                        70, "eval execution"),

    # ── Medium risk (score 31–60) ──────────────────────────────────
    (r'git\s+commit',                   35, "git commit"),
    (r'git\s+push\b',                   50, "git push (non-force)"),
    (r'npm\s+install',                  38, "npm install"),
    (r'pip\s+install',                  36, "pip install"),
    (r'apt(-get)?\s+install',           40, "apt install"),
    (r'brew\s+install',                 36, "brew install"),
    (r'docker\s+run',                   45, "docker run"),
    (r'docker\s+build',                 40, "docker build"),
    (r'\bmv\s+',                        33, "file move"),
    (r'\bcp\s+-r',                      32, "recursive copy"),
    (r'rm\s+\S+',                       55, "file delete (non-recursive)"),
    (r'os\.remove\(',                   55, "Python os.remove"),
    (r'shutil\.rmtree\(',               65, "Python shutil.rmtree"),
]


# ------------------------------------------------------------------
# Risk Engine
# ------------------------------------------------------------------

class RiskEngine:
    """Numeric risk scoring engine for LUNA actions."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.risk_config = config.get('safety', {}).get('risk_levels', {})
        # Configurable score thresholds (can be overridden in config.yaml)
        safety = config.get('safety', {})
        self.threshold_blocked = safety.get('threshold_blocked', 81)
        self.threshold_high    = safety.get('threshold_high',    61)
        self.threshold_medium  = safety.get('threshold_medium',  31)

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def score_action(self, action: str, parameters: Dict[str, Any]) -> int:
        """
        Compute a numeric risk score (0–100) for an action + parameters pair.
        Accumulates contributions from all matching patterns, capped at 100.
        """
        action_str = f"{action} {str(parameters)}".lower()
        total_score = 0

        for pattern, contribution, _ in RISK_PATTERNS:
            if re.search(pattern, action_str, re.IGNORECASE):
                total_score += contribution

        return min(total_score, 100)

    def score_to_label(self, score: int) -> str:
        """Convert a numeric score to a risk label using configurable thresholds."""
        if score >= self.threshold_blocked:
            return "blocked"
        if score >= self.threshold_high:
            return "high"
        if score >= self.threshold_medium:
            return "medium"
        return "low"

    def classify_action(self, action: str, parameters: Dict[str, Any]) -> str:
        """Classify an action by risk label (low / medium / high / blocked)."""
        score = self.score_action(action, parameters)
        label = self.score_to_label(score)
        print(f"[RiskEngine] Score: {score}/100 → {label.upper()} | action={action}")
        return label

    # ------------------------------------------------------------------
    # Specific detectors
    # ------------------------------------------------------------------

    def detect_file_deletion(self, action: str, parameters: Dict[str, Any]) -> bool:
        """Explicitly detect file deletion operations."""
        action_str = f"{action} {str(parameters)}".lower()
        deletion_patterns = [r'rm\b', r'delete', r'os\.remove', r'shutil\.rmtree', r'"op"\s*:\s*"delete"']
        return any(re.search(p, action_str, re.IGNORECASE) for p in deletion_patterns)

    def detect_git_force_push(self, action: str, parameters: Dict[str, Any]) -> bool:
        """Explicitly detect git force push."""
        action_str = f"{action} {str(parameters)}".lower()
        return bool(re.search(r'git\s+push\s+.*--force|git\s+push\s+-f\b', action_str, re.IGNORECASE))

    def detect_shell_injection(self, action: str, parameters: Dict[str, Any]) -> bool:
        """Explicitly detect shell injection patterns."""
        action_str = f"{action} {str(parameters)}".lower()
        injection_patterns = [r';\s*rm\b', r'&&\s*rm\b', r'\|\s*rm\b', r'`[^`]+`', r'\$\([^)]+\)']
        return any(re.search(p, action_str, re.IGNORECASE) for p in injection_patterns)

    # ------------------------------------------------------------------
    # Policy enforcement
    # ------------------------------------------------------------------

    def should_require_confirmation(self, risk_level: str) -> bool:
        """Determine if an action requires user confirmation based on risk level."""
        action_type = self.risk_config.get(risk_level, "mandatory_confirmation")
        return action_type in ("block", "mandatory_confirmation")

    def is_blocked(self, risk_level: str) -> bool:
        """Check if an action is outright blocked."""
        return self.risk_config.get(risk_level) == "block" or risk_level == "blocked"

    def get_risk_report(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return a full risk report for an action, including score, label,
        and specific threat detections.
        """
        score = self.score_action(action, parameters)
        label = self.score_to_label(score)
        return {
            "score": score,
            "label": label,
            "file_deletion_detected": self.detect_file_deletion(action, parameters),
            "git_force_push_detected": self.detect_git_force_push(action, parameters),
            "shell_injection_detected": self.detect_shell_injection(action, parameters),
            "blocked": self.is_blocked(label),
            "requires_confirmation": self.should_require_confirmation(label),
        }
