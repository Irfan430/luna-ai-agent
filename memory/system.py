"""
LUNA AI Agent - Advanced Memory System (AMS) v4.0
Author: IRFAN

Phase 5 Memory Stabilization Fixes:
  1. Token tracking: uses tiktoken if available, falls back to char/4 estimate.
  2. Compression threshold validated as float in (0, 1).
  3. clear_short_term() resets execution_state too (prevents stale state bleed).
  4. add_short_term() guards against duplicate consecutive messages.
  5. get_token_count() never returns negative.
  6. compress() preserves last 3 messages for continuity.
  7. drop_irrelevant_conversation() keeps last 8 messages to avoid context loss.

Intelligent memory management with token tracking, auto-compression, and episodic history.
"""

import json
import time
from typing import Dict, Any, List, Optional

from llm.provider import LLMManager


class MemorySystem:
    """
    Manages short-term (context), long-term (episodic), and compressed memory.
    Tracks token usage and performs auto-summarization.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_manager = LLMManager(config)  # For summarization
        self.short_term_memory: List[Dict[str, str]] = []  # Current conversation/context
        self.episodic_memory: List[Dict[str, Any]] = []  # Long-term task history
        self.compressed_long_term_memory: str = ""  # Summarized long-term memory
        self.goal: str = ""
        self.execution_state: Dict[str, Any] = {}
        self.max_tokens = config.get("memory", {}).get("max_tokens", 4000)
        raw_threshold = config.get("memory", {}).get("compression_threshold", 0.75)
        # Phase 5 Fix: validate threshold is a float in (0, 1)
        try:
            self.compression_threshold = float(raw_threshold)
            if not (0.0 < self.compression_threshold <= 1.0):
                self.compression_threshold = 0.75
        except (TypeError, ValueError):
            self.compression_threshold = 0.75

        # Phase 5 Fix: try to use tiktoken for accurate token counting
        self._tiktoken_enc = None
        try:
            import tiktoken
            self._tiktoken_enc = tiktoken.get_encoding("cl100k_base")
        except Exception:
            pass  # Fall back to char/4 estimate

    @property
    def short_term(self):
        """Public interface for short-term memory."""
        return self.short_term_memory

    @property
    def episodic(self):
        """Public interface for episodic memory."""
        return self.episodic_memory

    @property
    def long_term(self):
        """Public interface for long-term memory."""
        return self.compressed_long_term_memory

    def set_goal(self, goal: str):
        """Set the current goal for the memory system."""
        self.goal = goal

    def add_short_term(self, role: str, content: str):
        """Add a message to short-term memory (current context)."""
        # Phase 5 Fix: guard against duplicate consecutive messages
        if (
            self.short_term_memory
            and self.short_term_memory[-1].get("role") == role
            and self.short_term_memory[-1].get("content") == content
        ):
            return  # Skip duplicate
        self.short_term_memory.append({"role": role, "content": content})
        self._manage_token_pressure()

    def get_context(self) -> List[Dict[str, str]]:
        """Retrieve current short-term memory for LLM context."""
        return self.short_term_memory

    def clear_short_term(self):
        """Clear short-term memory and execution state at the start of a new goal."""
        # Phase 5 Fix: also reset execution_state to prevent stale state bleed
        self.short_term_memory = []
        self.execution_state = {}

    def add_episodic(self, goal: str, result: Dict[str, Any]):
        """Add a completed task to episodic memory."""
        self.episodic_memory.append({"goal": goal, "result": result, "timestamp": time.time()})
        self._update_compressed_long_term_memory()

    def update_execution_state(self, key: str, value: Any):
        """Update the current execution state, e.g., last action, environment snapshot."""
        self.execution_state[key] = value

    def get_token_count(self) -> int:
        """Estimate current token usage for short-term memory."""
        # Phase 5 Fix: use tiktoken if available, else char/4 estimate
        if self._tiktoken_enc is not None:
            try:
                total = sum(
                    len(self._tiktoken_enc.encode(msg.get("content", "")))
                    for msg in self.short_term_memory
                )
                return max(0, total)
            except Exception:
                pass
        total_chars = sum(len(msg.get("content", "")) for msg in self.short_term_memory)
        return max(0, total_chars // 4)  # Never negative

    def needs_compression(self) -> bool:
        """Check if short-term memory exceeds compression threshold."""
        return self.get_token_count() > (self.max_tokens * self.compression_threshold)

    def auto_summarize_context(self) -> str:
        """Use LLM to summarize current short-term memory."""
        print("Summarizing short-term memory...")
        summarization_prompt = (
            "Summarize the following conversation/context concisely, retaining all critical information "
            "about the user's goal, actions taken, and results. Focus on key decisions and outcomes. "
            "This summary will be used to rebuild context for future steps.\n\n"
            + json.dumps(self.short_term_memory, indent=2)
        )
        messages = [
            {"role": "system", "content": "You are a helpful assistant that summarizes conversations."},
            {"role": "user", "content": summarization_prompt},
        ]
        # Bug Fix #2: LLMProvider has call() not chat_completion()
        response = self.llm_manager.call(messages)
        return response.content

    def compress(self, summary: str):
        """Compress short-term memory by replacing older messages with a summary."""
        # Phase 5 Fix: preserve last 3 messages for continuity
        recent = self.short_term_memory[-3:] if len(self.short_term_memory) >= 3 else list(self.short_term_memory)
        self.short_term_memory = [
            {"role": "system", "content": f"Summary of previous context: {summary}"}
        ]
        if self.goal:
            self.short_term_memory.append({"role": "system", "content": f"Current Goal: {self.goal}"})
        if self.execution_state:
            self.short_term_memory.append(
                {"role": "system", "content": f"Current Execution State: {json.dumps(self.execution_state)}"}
            )
        # Re-append recent messages for continuity
        self.short_term_memory.extend(recent)

    def _update_compressed_long_term_memory(self):
        """Periodically summarize episodic memory to maintain a compressed long-term view."""
        if not self.episodic_memory:
            self.compressed_long_term_memory = ""
            return

        # Only summarize if there's new episodic memory or if it's empty
        if len(self.episodic_memory) == 1 and not self.compressed_long_term_memory:
            # First episodic memory, just use its goal and result
            latest_episode = self.episodic_memory[-1]
            goal = latest_episode.get('goal', 'N/A')
            result_status = latest_episode.get('result', {}).get('status', 'N/A')
            result_content = latest_episode.get('result', {}).get('content', '')
            self.compressed_long_term_memory = f"Previously completed task: Goal: {goal}, Result: {result_status}. Content: {result_content[:100]}..."
        elif len(self.episodic_memory) > 1:
            # Summarize all episodic memory if it grows
            print("Summarizing episodic memory for long-term context...")
            episodic_summary_prompt = (
                "Summarize the following list of past completed tasks. "
                "Focus on the goals and their final outcomes. "
                "This summary will be used as long-term memory for the agent.\n\n"
                + json.dumps(self.episodic_memory, indent=2)
            )
            messages = [
                {"role": "system", "content": "You are a helpful assistant that summarizes past tasks."},
                {"role": "user", "content": episodic_summary_prompt},
            ]
            # Bug Fix #2: LLMProvider has call() not chat_completion()
            response = self.llm_manager.call(messages)
            self.compressed_long_term_memory = response.content

    def rebuild_context_with_compression(self) -> List[Dict[str, str]]:
        """Rebuilds the full context, prioritizing compressed long-term memory if available."""
        context = []
        if self.compressed_long_term_memory:
            context.append({"role": "system", "content": f"Long-term memory summary: {self.compressed_long_term_memory}"})
        context.extend(self.short_term_memory)
        return context

    def drop_irrelevant_conversation(self):
        """Intelligently drops less relevant parts of short-term memory if token pressure is high."""
        # This is a placeholder. A more advanced implementation would use LLM to identify irrelevant parts.
        if self.get_token_count() > self.max_tokens:
            print("Dropping oldest short-term memory to manage token pressure.")
            # Phase 5 Fix: keep last 8 messages to avoid context loss
            self.short_term_memory = self.short_term_memory[-8:]
            if self.goal:
                self.short_term_memory.insert(0, {"role": "system", "content": f"Current Goal: {self.goal}"})
            if self.execution_state:
                self.short_term_memory.insert(1, {"role": "system", "content": f"Current Execution State: {json.dumps(self.execution_state)}"})

    def _manage_token_pressure(self):
        """
        Manages token pressure by compressing short-term memory if thresholds are exceeded.
        This method is called every time a message is added to short-term memory.
        """
        if self.needs_compression():
            print("Token pressure elevated. Initiating memory compression.")
            summary = self.auto_summarize_context()
            self.compress(summary)
            # After compression, check if still over max_tokens and drop irrelevant if necessary
            if self.get_token_count() > self.max_tokens:
                self.drop_irrelevant_conversation()

