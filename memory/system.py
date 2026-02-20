"""
LUNA AI Agent - Memory Compression System v2.0
Author: IRFAN

Three-layer active memory management:
  1. short_term_context   — current task messages
  2. episodic_memory      — recent completed task records
  3. compressed_long_term_memory — summarized project state

Implements: token_pressure_detection, auto_summarize_context,
goal + execution state retention, and irrelevant conversation pruning.
"""

import json
from typing import Dict, Any, List, Optional


class MemorySystem:
    """Three-layer active memory management for LUNA."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Layer 1: Short-term context — live task messages
        self.short_term_context: List[Dict[str, str]] = []

        # Layer 2: Episodic memory — completed task records (capped)
        self.episodic_memory: List[Dict[str, Any]] = []

        # Layer 3: Compressed long-term memory — summarized project state
        self.compressed_long_term_memory: str = ""

        # Retained goal and execution state (always preserved through compression)
        self.current_goal: str = ""
        self.execution_state: Dict[str, Any] = {}

        # Token pressure thresholds
        self.compression_threshold: int = config.get('cognitive', {}).get('memory_compression_threshold', 4000)
        self.critical_threshold: int = self.compression_threshold * 2
        self.max_episodic_entries: int = 10

    # ------------------------------------------------------------------
    # Layer 1: Short-term context
    # ------------------------------------------------------------------

    def add_short_term(self, role: str, content: str):
        """Add a message to short-term context."""
        self.short_term_context.append({"role": role, "content": content})

    def clear_short_term(self):
        """Clear short-term context (e.g., at the start of a new goal)."""
        self.short_term_context = []

    # ------------------------------------------------------------------
    # Layer 2: Episodic memory
    # ------------------------------------------------------------------

    def add_episodic(self, task: str, result: Dict[str, Any]):
        """Record a completed task in episodic memory."""
        self.episodic_memory.append({"task": task, "result": result})
        # Prune oldest entry when cap is exceeded
        if len(self.episodic_memory) > self.max_episodic_entries:
            self.episodic_memory.pop(0)

    # ------------------------------------------------------------------
    # Layer 3: Compressed long-term memory
    # ------------------------------------------------------------------

    def compress(self, summary: str):
        """
        Compress short-term context into long-term memory.
        Retains current goal and execution state; drops irrelevant conversation.
        """
        # Preserve goal and execution state before wiping short-term
        goal_entry = f"Goal: {self.current_goal}" if self.current_goal else ""
        state_entry = f"Execution State: {json.dumps(self.execution_state)}" if self.execution_state else ""

        retained = "\n".join(filter(None, [goal_entry, state_entry, summary]))
        self.compressed_long_term_memory = retained
        self.short_term_context = []
        print("[MemorySystem] Short-term context compressed into long-term memory.")

    def auto_summarize_context(self) -> str:
        """
        Automatically generate a concise summary of the current short-term context.
        Drops irrelevant assistant chatter; retains action outcomes and errors.
        """
        relevant_entries = []
        for msg in self.short_term_context:
            role = msg.get("role", "")
            content = msg.get("content", "")
            # Retain user goals, system messages, and assistant messages containing
            # structured data (JSON-like) or error/failure indicators
            if role in ("user", "system"):
                relevant_entries.append(f"[{role.upper()}] {content}")
            elif role == "assistant":
                if any(kw in content.lower() for kw in ["{", "error", "fail", "success", "result", "status"]):
                    relevant_entries.append(f"[ASSISTANT] {content[:500]}")  # cap at 500 chars
        return "\n".join(relevant_entries) if relevant_entries else "No significant context."

    # ------------------------------------------------------------------
    # Token pressure detection
    # ------------------------------------------------------------------

    def get_token_count(self) -> int:
        """Estimate token count across all memory layers (4 chars ≈ 1 token)."""
        text = (
            json.dumps(self.short_term_context)
            + self.compressed_long_term_memory
            + json.dumps(self.episodic_memory)
        )
        return len(text) // 4

    def token_pressure_detection(self) -> str:
        """
        Classify current token pressure level.
        Returns: 'normal' | 'elevated' | 'critical'
        """
        count = self.get_token_count()
        if count >= self.critical_threshold:
            return "critical"
        if count >= self.compression_threshold:
            return "elevated"
        return "normal"

    def needs_compression(self) -> bool:
        """Check if memory needs compression."""
        return self.token_pressure_detection() in ("elevated", "critical")

    # ------------------------------------------------------------------
    # Goal and execution state management
    # ------------------------------------------------------------------

    def set_goal(self, goal: str):
        """Set the current goal (retained through compression)."""
        self.current_goal = goal

    def update_execution_state(self, key: str, value: Any):
        """Update a key in the execution state (retained through compression)."""
        self.execution_state[key] = value

    # ------------------------------------------------------------------
    # Context assembly for LLM
    # ------------------------------------------------------------------

    def get_context(self) -> List[Dict[str, str]]:
        """
        Assemble the full context for the LLM.
        Priority order: long-term memory → episodic memory → short-term context.
        Drops irrelevant conversation if token pressure is critical.
        """
        pressure = self.token_pressure_detection()
        context: List[Dict[str, str]] = []

        # Long-term compressed memory
        if self.compressed_long_term_memory:
            context.append({
                "role": "system",
                "content": f"[Long-Term Memory]\n{self.compressed_long_term_memory}"
            })

        # Episodic memory
        if self.episodic_memory:
            episodic_str = json.dumps(self.episodic_memory, indent=2)
            context.append({
                "role": "system",
                "content": f"[Episodic Memory — Recent Tasks]\n{episodic_str}"
            })

        # Short-term context — prune aggressively if critical
        if pressure == "critical":
            print("[MemorySystem] Critical token pressure. Pruning short-term context.")
            # Keep only the last 4 messages
            context.extend(self.short_term_context[-4:])
        else:
            context.extend(self.short_term_context)

        return context
