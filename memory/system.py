"""
LUNA AI Agent - Advanced Memory System (AMS) v3.0
Author: IRFAN

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
        self.compression_threshold = config.get("memory", {}).get("compression_threshold", 0.75) # % of max_tokens

    def set_goal(self, goal: str):
        """Set the current goal for the memory system."""
        self.goal = goal

    def add_short_term(self, role: str, content: str):
        """Add a message to short-term memory (current context)."""
        self.short_term_memory.append({"role": role, "content": content})
        self._manage_token_pressure()

    def get_context(self) -> List[Dict[str, str]]:
        """Retrieve current short-term memory for LLM context."""
        return self.short_term_memory

    def clear_short_term(self):
        """Clear short-term memory, typically at the start of a new goal."""
        self.short_term_memory = []

    def add_episodic(self, goal: str, result: Dict[str, Any]):
        """Add a completed task to episodic memory."""
        self.episodic_memory.append({"goal": goal, "result": result, "timestamp": time.time()})
        self._update_compressed_long_term_memory()

    def update_execution_state(self, key: str, value: Any):
        """Update the current execution state, e.g., last action, environment snapshot."""
        self.execution_state[key] = value

    def get_token_count(self) -> int:
        """Estimate current token usage for short-term memory."""
        # This is a simplified estimation. A real implementation would use a tokenizer.
        total_chars = sum(len(msg["content"]) for msg in self.short_term_memory)
        return total_chars // 4  # Rough estimate: 1 token ~ 4 characters

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
        summary_response = self.llm_manager.get_provider().chat_completion(messages)
        return summary_response.get("content", "")

    def compress(self, summary: str):
        """Compress short-term memory by replacing older messages with a summary."""
        # Keep the most recent messages and prepend the summary
        # This is a basic strategy; more advanced methods could be used.
        self.short_term_memory = [
            {"role": "system", "content": f"Summary of previous context: {summary}"}
        ]
        # Ensure goal and execution state are always present after compression
        if self.goal:
            self.short_term_memory.append({"role": "system", "content": f"Current Goal: {self.goal}"})
        if self.execution_state:
            self.short_term_memory.append({"role": "system", "content": f"Current Execution State: {json.dumps(self.execution_state)}"})

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
            summary_response = self.llm_manager.get_provider().chat_completion(messages)
            self.compressed_long_term_memory = summary_response.get("content", "")

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
            # Keep the last few messages and the goal/execution state
            self.short_term_memory = self.short_term_memory[-5:] # Keep last 5 messages
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

