"""
LUNA AI Agent - Advanced Memory System (AMS) v5.0
Author: IRFAN

Phase 5 Memory Upgrade:
  - Short-term memory (context).
  - Episodic task memory.
  - Token usage tracking.
  - Goal persistence.
  - Last action state.
  - Compression via LLM summarization.
  - Robustness: no crash if fields missing.
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional

from llm.provider import LLMManager

logger = logging.getLogger("luna.memory.system")

class MemorySystem:
    """Intelligent memory management with token tracking and auto-compression."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_manager = LLMManager(config)
        self.short_term_memory: List[Dict[str, str]] = []
        self.episodic_memory: List[Dict[str, Any]] = []
        self.compressed_long_term_memory: str = ""
        self.goal: str = ""
        self.execution_state: Dict[str, Any] = {}
        self.max_tokens = config.get("memory", {}).get("max_tokens", 4000)
        self.compression_threshold = config.get("memory", {}).get("compression_threshold", 0.75)

        self._tiktoken_enc = None
        try:
            import tiktoken
            self._tiktoken_enc = tiktoken.get_encoding("cl100k_base")
        except Exception:
            pass

    @property
    def short_term(self): return self.short_term_memory

    @property
    def episodic(self): return self.episodic_memory

    @property
    def long_term(self): return self.compressed_long_term_memory

    def set_goal(self, goal: str): self.goal = goal

    def add_short_term(self, role: str, content: str):
        if not content: return
        if self.short_term_memory and self.short_term_memory[-1].get("role") == role and self.short_term_memory[-1].get("content") == content:
            return
        self.short_term_memory.append({"role": role, "content": content})
        self._manage_token_pressure()

    def clear_short_term(self):
        self.short_term_memory = []
        self.execution_state = {}

    def add_episodic(self, goal: str, result: Dict[str, Any]):
        self.episodic_memory.append({"goal": goal, "result": result, "timestamp": time.time()})
        self._update_compressed_long_term_memory()

    def update_execution_state(self, key: str, value: Any):
        self.execution_state[key] = value

    def get_token_count(self) -> int:
        if self._tiktoken_enc:
            try:
                return sum(len(self._tiktoken_enc.encode(msg.get("content", ""))) for msg in self.short_term_memory)
            except Exception: pass
        return sum(len(msg.get("content", "")) for msg in self.short_term_memory) // 4

    def _manage_token_pressure(self):
        if self.get_token_count() > (self.max_tokens * self.compression_threshold):
            self._compress()

    def _compress(self):
        print("Compressing short-term memory...")
        summary_prompt = "Summarize the following context concisely, retaining key goals and outcomes:\n\n" + json.dumps(self.short_term_memory)
        messages = [{"role": "system", "content": "You are a helpful assistant that summarizes context."}, {"role": "user", "content": summary_prompt}]
        try:
            response = self.llm_manager.call(messages)
            summary = response.content
            recent = self.short_term_memory[-3:] if len(self.short_term_memory) >= 3 else list(self.short_term_memory)
            self.short_term_memory = [{"role": "system", "content": f"Summary of previous context: {summary}"}]
            if self.goal: self.short_term_memory.append({"role": "system", "content": f"Current Goal: {self.goal}"})
            self.short_term_memory.extend(recent)
        except Exception as e:
            logger.error(f"Compression failed: {e}")

    def _update_compressed_long_term_memory(self):
        if not self.episodic_memory: return
        if len(self.episodic_memory) % 5 == 0: # Summarize every 5 episodes
            print("Updating long-term memory...")
            summary_prompt = "Summarize these past tasks for long-term memory:\n\n" + json.dumps(self.episodic_memory)
            messages = [{"role": "system", "content": "You are a helpful assistant that summarizes task history."}, {"role": "user", "content": summary_prompt}]
            try:
                response = self.llm_manager.call(messages)
                self.compressed_long_term_memory = response.content
            except Exception as e:
                logger.error(f"Long-term memory update failed: {e}")
