"""
LUNA AI Agent - Core Execution Loop v9.0
Author: IRFAN

Structural Stabilization Refactor:
  - Strict single-pass action system.
  - Performance Modes: FAST (default) and AGENT.
  - Central Action Router integration.
  - Return error immediately if action fails.
"""

import json
import os
import time
import logging
from typing import Dict, Any, List, Optional

from llm.provider import LLMManager
from llm.router import LLMRouter, BrainOutput, normalize_brain_output
from execution.kernel import ExecutionKernel
from risk.engine import RiskEngine
from memory.system import MemorySystem
from core.task_result import TaskResult

logger = logging.getLogger("luna.core.loop")

class CognitiveLoop:
    """Fast, single-pass execution loop for LUNA's real-time orchestration."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_manager = LLMManager(config)
        self.execution_kernel = ExecutionKernel()
        self.risk_engine = RiskEngine(config)
        self.memory_system = MemorySystem(config)
        self.router = LLMRouter(self.llm_manager, config)
        # FAST MODE (default): Single LLM call, Direct action, No planning
        # AGENT MODE (optional): Allow complex reasoning
        self.mode = config.get("agent", {}).get("mode", "FAST")

    def run(self, goal: str) -> TaskResult:
        """Run the execution loop based on current performance mode."""
        # Numeric input guard
        if isinstance(goal, (int, float)) or (isinstance(goal, str) and goal.isdigit()):
            response = f"I received the numeric input: {goal}. How would you like me to use this?"
            return TaskResult(status="success", content=response, verified=True)

        # Performance Mode Routing
        if self.mode == "FAST":
            # FAST MODE: Single-pass execution
            return self._execute_single_pass(goal)
        else:
            # AGENT MODE: Allow more complex reasoning (still single-pass for now but with more context)
            return self._execute_agent_mode(goal)

    def _execute_single_pass(self, goal: str) -> TaskResult:
        """INPUT → LLM → ACTION ROUTER → EXECUTE → RETURN"""
        # 1. Routing (Single LLM Call)
        routing = self.router.route(goal, history=self.memory_system.short_term)
        
        if not isinstance(routing, BrainOutput):
            routing = normalize_brain_output(routing)

        # 2. Extract Action and Parameters
        action = routing.action
        params = routing.parameters
        response = routing.response
        thought = routing.thought

        # Log thought if present
        if thought:
            print(f"LUNA Thought: {thought}")

        # 3. Handle Conversation Action
        if action == "conversation":
            print(f"\nLUNA: {response}")
            self._update_memory(goal, response)
            return TaskResult(status="success", content=response, verified=True)

        # 4. Execute Action via Central Router
        print(f"Executing Action: {action}...")
        
        # Risk check
        risk_report = self.risk_engine.get_risk_report(action, params)
        if risk_report["blocked"]:
            return TaskResult.failure(f"Action blocked: {risk_report['label']}")

        # Execute via Kernel (Central Action Router)
        result = self.execution_kernel.execute(action, params)
        
        # 5. Return Result Immediately
        if result.status == "success":
            final_content = f"{response}\n\nExecution Result:\n{result.content}" if response else result.content
            self._update_memory(goal, final_content)
            return TaskResult(status="success", content=final_content, verified=True)
        else:
            # Return error immediately if action fails
            error_msg = f"Execution failed: {result.error}"
            print(f"LUNA Error: {error_msg}")
            return TaskResult.failure(error_msg)

    def _execute_agent_mode(self, goal: str) -> TaskResult:
        """AGENT MODE: Enhanced reasoning version of single-pass."""
        # For now, AGENT mode uses the same single-pass logic but could be expanded 
        # with multi-step reasoning in the future if needed, while staying stable.
        # The key difference is it allows more complex instructions to be passed to LLM.
        return self._execute_single_pass(goal)

    def _update_memory(self, goal: str, response: str):
        """Update short-term memory with user goal and assistant response."""
        self.memory_system.add_short_term("user", str(goal))
        self.memory_system.add_short_term("assistant", response)
