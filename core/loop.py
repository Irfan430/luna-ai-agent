"""
LUNA AI Agent - Core Execution Loop v10.0
Author: IRFAN

Structural Stabilization Refactor:
  - Clean non-blocking architecture.
  - Strict JSON thought filtering (thoughts never reach user).
  - Integrated Action-based Jarvis flow.
"""

import json
import os
import time
import logging
import threading
from typing import Dict, Any, List, Optional

from llm.provider import LLMManager
from llm.router import LLMRouter, BrainOutput, normalize_brain_output
from execution.kernel import ExecutionKernel, ExecutionResult
from risk.engine import RiskEngine
from memory.system import MemorySystem
from voice.engine import VoiceEngine

logger = logging.getLogger("luna.core.loop")

class CognitiveLoop:
    """The central brain of LUNA, managing the non-blocking execution loop."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_manager = LLMManager(config)
        self.execution_kernel = ExecutionKernel(config)
        self.risk_engine = RiskEngine(config)
        self.memory_system = MemorySystem(config)
        self.router = LLMRouter(self.llm_manager, config)
        self.voice = VoiceEngine(config)
        
        # FAST MODE (default): Single LLM call, Direct action, No planning
        self.mode = config.get("agent", {}).get("mode", "FAST")
        self.is_running = False
        self._lock = threading.Lock()

    def run(self, goal: str) -> ExecutionResult:
        """Single-pass execution of a user goal."""
        logger.info(f"[Loop] New Goal: {goal}")
        
        # 1. Routing (Single LLM Call)
        routing = self.router.route(goal, history=self.memory_system.short_term)
        
        if not isinstance(routing, BrainOutput):
            routing = normalize_brain_output(routing)

        # 2. Extract Action and Parameters
        action = routing.action
        params = routing.parameters
        response = routing.response
        thought = routing.thought

        # 3. Internal Thought Filtering (Log but don't show to user)
        if thought:
            logger.debug(f"[Brain Thought] {thought}")

        # 4. Handle Conversation Action
        if action == "conversation":
            if response:
                print(f"\nLUNA: {response}")
                if self.voice.enabled:
                    self.voice.speak(response)
            self._update_memory(goal, response)
            return ExecutionResult("success", response, verified=True)

        # 5. Execute Action via Central Router
        print(f"Executing Action: {action}...")
        
        # Risk check
        risk_report = self.risk_engine.get_risk_report(action, params)
        if risk_report["blocked"]:
            return ExecutionResult.failure(f"Action blocked: {risk_report['label']}")

        # Execute via Kernel (Central Action Router)
        result = self.execution_kernel.execute(action, params)
        
        # 6. Speak result if voice enabled
        if self.voice.enabled:
            speech_content = result.content if result.status == "success" else f"Action failed: {result.error}"
            self.voice.speak(speech_content)
        
        # 7. Update Memory and Return
        final_content = result.content if result.status == "success" else f"Error: {result.error}"
        self._update_memory(goal, final_content)
        return result

    def run_async(self, goal: str):
        """Run goal in a separate thread to avoid blocking GUI/Voice."""
        threading.Thread(target=self.run, args=(goal,), daemon=True).start()

    def start_voice_mode(self):
        """Start always-on voice listening."""
        if self.voice.enabled:
            self.voice.start_passive_listening(on_wake=self.run_async)

    def _update_memory(self, goal: str, response: str):
        """Update short-term memory with user goal and assistant response."""
        self.memory_system.add_short_term("user", str(goal))
        self.memory_system.add_short_term("assistant", response)
