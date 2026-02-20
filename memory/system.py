"""
LUNA AI Agent - Advanced Memory System (AMS) v8.0
Author: IRFAN

Phase 8: 5-Day Persistent Memory
  - Store user text, voice transcript, luna response, and timestamp.
  - Exclude screenshots, system state, file contents.
  - Delete entries older than 5 days on startup.
  - Inject summarized recent memory into brain prompt.
"""

import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from llm.provider import LLMManager

logger = logging.getLogger("luna.memory.system")

class MemorySystem:
    """Intelligent memory management with 5-day persistence and token tracking."""

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

        # Phase 8: Persistent History
        self.memory_dir = "memory_store"
        os.makedirs(self.memory_dir, exist_ok=True)
        self.history_file = os.path.join(self.memory_dir, "history.json")
        self.history = self._load_history()
        self._cleanup_old_history()

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

    def _load_history(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading history: {e}")
        return []

    def _save_history(self):
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving history: {e}")

    def _cleanup_old_history(self):
        """Phase 8: Delete entries older than 5 days."""
        now = datetime.now()
        five_days_ago = now - timedelta(days=5)
        
        original_count = len(self.history)
        self.history = [
            entry for entry in self.history 
            if datetime.fromisoformat(entry['timestamp']) > five_days_ago
        ]
        
        if len(self.history) < original_count:
            logger.info(f"Cleaned up {original_count - len(self.history)} old memory entries.")
            self._save_history()

    def set_goal(self, goal: str): self.goal = goal

    def add_short_term(self, role: str, content: str, is_voice: bool = False):
        if not content: return
        if self.short_term_memory and self.short_term_memory[-1].get("role") == role and self.short_term_memory[-1].get("content") == content:
            return
        
        # Add to short-term (active context)
        self.short_term_memory.append({"role": role, "content": content})
        
        # Phase 8: Add to persistent history (text + voice only)
        timestamp = datetime.now().isoformat()
        entry = {
            "role": role,
            "content": content,
            "timestamp": timestamp,
            "is_voice": is_voice
        }
        self.history.append(entry)
        self._save_history()
        
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

    def get_summarized_history(self) -> str:
        """Phase 8: Inject summarized recent memory into brain prompt."""
        if not self.history:
            return "No previous history."
        
        recent = self.history[-10:]
        summary = "Recent History:\n"
        for entry in recent:
            role = "YOU" if entry['role'] == 'user' else "LUNA"
            voice_tag = " (voice)" if entry.get('is_voice') else ""
            summary += f"- {entry['timestamp'][:16]} {role}{voice_tag}: {entry['content'][:100]}...\n"
        
        return summary
