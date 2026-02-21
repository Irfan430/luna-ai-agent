"""
LUNA AI Agent - Advanced Memory System (AMS) v9.0
Author: IRFAN

Phase 6: Memory System (5 Day Window)
  - Store last 5 days text + voice transcripts.
  - Structured JSON storage.
  - Rolling window cleanup.
  - Load recent context only.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger("luna.memory.system")

class MemorySystem:
    """Intelligent memory management with 5-day persistence."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.memory_dir = "memory_store"
        os.makedirs(self.memory_dir, exist_ok=True)
        self.history_file = os.path.join(self.memory_dir, "history.json")
        
        self.short_term_memory: List[Dict[str, str]] = []
        self.history = self._load_history()
        self._cleanup_old_history()

    @property
    def short_term(self):
        """Return recent context for LLM."""
        return self.short_term_memory[-10:] # Last 10 messages for immediate context

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
        """Phase 6: Delete entries older than 5 days."""
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

    def add_short_term(self, role: str, content: str, is_voice: bool = False):
        if not content: return
        
        # Add to active context
        self.short_term_memory.append({"role": role, "content": content})
        
        # Add to persistent history
        timestamp = datetime.now().isoformat()
        entry = {
            "role": role,
            "content": content,
            "timestamp": timestamp,
            "is_voice": is_voice
        }
        self.history.append(entry)
        self._save_history()

    def get_summarized_history(self) -> str:
        """Inject summarized recent memory into brain prompt."""
        if not self.history:
            return "No previous history."
        
        recent = self.history[-15:]
        summary = "Recent History (Last 5 Days):\n"
        for entry in recent:
            role = "YOU" if entry['role'] == 'user' else "LUNA"
            voice_tag = " (voice)" if entry.get('is_voice') else ""
            summary += f"- [{entry['timestamp'][:16]}] {role}{voice_tag}: {entry['content'][:150]}\n"
        
        return summary
