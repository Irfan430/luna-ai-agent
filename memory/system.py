"""
LUNA AI Agent - Memory System
Author: IRFAN

Three-layer memory: Short-term, Episodic, and Compressed Long-term.
"""

import json
from typing import Dict, Any, List, Optional


class MemorySystem:
    """Three-layer memory management for LUNA."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.short_term: List[Dict[str, str]] = []  # Current task context
        self.episodic: List[Dict[str, Any]] = []    # Recent completed tasks
        self.long_term: str = ""                    # Summarized project state
        self.compression_threshold = config.get('cognitive', {}).get('memory_compression_threshold', 4000)

    def add_short_term(self, role: str, content: str):
        """Add a message to short-term memory."""
        self.short_term.append({"role": role, "content": content})

    def add_episodic(self, task: str, result: Dict[str, Any]):
        """Add a completed task to episodic memory."""
        self.episodic.append({"task": task, "result": result})
        # Keep episodic memory manageable
        if len(self.episodic) > 10:
            self.episodic.pop(0)

    def get_context(self) -> List[Dict[str, str]]:
        """Get the current context for the LLM."""
        context = []
        # Add long-term summary if available
        if self.long_term:
            context.append({"role": "system", "content": f"Long-term Project State: {self.long_term}"})
        
        # Add episodic memory as context
        if self.episodic:
            episodic_str = json.dumps(self.episodic, indent=2)
            context.append({"role": "system", "content": f"Recent Tasks History: {episodic_str}"})
        
        # Add short-term memory
        context.extend(self.short_term)
        return context

    def compress(self, summary: str):
        """Compress short-term memory into long-term summary."""
        self.long_term = summary
        self.short_term = []  # Clear short-term after compression

    def clear_short_term(self):
        """Clear short-term memory."""
        self.short_term = []

    def get_token_count(self) -> int:
        """Estimate token count (rough approximation)."""
        text = json.dumps(self.short_term) + self.long_term + json.dumps(self.episodic)
        return len(text) // 4  # Rough estimate: 4 chars per token

    def needs_compression(self) -> bool:
        """Check if memory needs compression."""
        return self.get_token_count() > self.compression_threshold
