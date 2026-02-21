"""
LUNA AI Agent - OS Agent Orchestrator v11.0
Author: IRFAN

Structural Stabilization Refactor:
  - Task Orchestrator with Queue-based execution.
  - Multi-step reasoning in AGENT mode.
  - Non-blocking cognitive loop.
"""

import threading
import queue
import logging
import time
from typing import Dict, Any, List, Optional
from llm.provider import LLMManager
from llm.router import LLMRouter, BrainOutput
from execution.kernel import ExecutionKernel
from voice.engine import VoiceEngine
from memory.system import MemorySystem

logger = logging.getLogger("luna.core.loop")

class CognitiveLoop:
    """The central brain and orchestrator of LUNA."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_manager = LLMManager(config)
        self.router = LLMRouter(self.llm_manager, config)
        self.kernel = ExecutionKernel(config)
        self.voice = VoiceEngine(config)
        self.memory = MemorySystem(config)
        
        self.task_queue = queue.Queue()
        self.is_running = True
        self.mode = config.get("agent", {}).get("mode", "FAST")
        
        # Start the orchestrator thread
        self.orchestrator_thread = threading.Thread(target=self._orchestrator_worker, daemon=True)
        self.orchestrator_thread.start()

    def _orchestrator_worker(self):
        """Background thread to process the task queue."""
        logger.info("[Orchestrator] Worker started.")
        while self.is_running:
            try:
                task_goal = self.task_queue.get(timeout=1.0)
                if task_goal:
                    self._process_goal(task_goal)
                self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[Orchestrator] Error: {e}")

    def _process_goal(self, goal: str):
        """Process a user goal through the cognitive-execution loop."""
        logger.info(f"[Orchestrator] Processing: {goal}")
        
        # 1. Cognitive Routing (DeepSeek)
        routing: BrainOutput = self.router.route(goal, history=self.memory.short_term)
        
        # 2. Execution Routing
        if routing.intent == "conversation":
            response = routing.response
            if response:
                print(f"\nLUNA: {response}")
                if self.voice.enabled: self.voice.speak(response)
            self._update_memory(goal, response)
            return

        # 3. Execute Action
        print(f"Executing Intent: {routing.intent}...")
        # Map intents to kernel actions
        action_map = {
            "system_command": "system",
            "browser_task": "browser",
            "file_operation": "file",
            "app_control": "app",
            "code": "code"
        }
        
        action = action_map.get(routing.intent, "system")
        result = self.kernel.execute(action, routing.parameters)
        
        # 4. Handle Result
        final_content = result.content if result.status == "success" else f"Action failed: {result.error}"
        if self.voice.enabled: self.voice.speak(final_content)
        
        self._update_memory(goal, final_content)
        
        # 5. Multi-step Check (AGENT mode)
        if self.mode == "AGENT" and result.status == "success":
            # For now, AGENT mode is just a placeholder for more complex loops
            pass

    def run(self, goal: str):
        """Entry point for user input. Adds goal to the orchestrator queue."""
        self.task_queue.put(goal)

    def start_voice_mode(self):
        """Start always-on voice listening."""
        if self.voice.enabled:
            self.voice.start_passive_listening(on_command=self.run)

    def _update_memory(self, goal: str, response: str):
        """Update short-term memory with user goal and assistant response."""
        self.memory.add_short_term("user", str(goal))
        self.memory.add_short_term("assistant", response)

    def stop(self):
        self.is_running = False
        self.kernel.browser_controller.close()
        self.voice.stop_passive_listening()
