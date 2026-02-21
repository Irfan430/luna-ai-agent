"""
LUNA AI Agent - Core Execution Loop v9.0
Author: IRFAN

Phase 1 & 2: Core Architecture Refactor
  - Single-pass LLM execution.
  - Execution Router: system, browser, screen, code.
  - No multi-iteration planning loop.
  - No repetitive cognitive reflection.
"""

import json
import os
import time
import logging
from typing import Dict, Any, List, Optional

from llm.provider import LLMManager
from llm.router import LLMRouter, BrainOutput, normalize_brain_output, repair_and_parse_json
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
        self.mode = config.get("agent", {}).get("mode", "FAST")

    def run(self, goal: str) -> TaskResult:
        """Run the single-pass execution router."""
        # Numeric input guard
        if isinstance(goal, (int, float)) or (isinstance(goal, str) and goal.isdigit()):
            response = f"I received the numeric input: {goal}. How would you like me to use this?"
            return TaskResult(status="success", content=response, verified=True)

        # FAST MODE: Single-pass execution
        if self.mode == "FAST":
            return self._execute_single_pass(goal)
        
        # AGENT MODE: Multi-step reasoning (Optional, for complex tasks)
        return self._execute_agent_mode(goal)

    def _execute_single_pass(self, goal: str) -> TaskResult:
        """INPUT → LLM → EXECUTION ROUTER → OUTPUT"""
        # 1. Routing (Single LLM Call)
        routing = self.router.route(goal, history=self.memory_system.short_term)
        
        if not isinstance(routing, BrainOutput):
            routing = normalize_brain_output(routing)

        # 2. Execution Router
        action = routing.action
        params = routing.parameters
        response = routing.response

        # Log thought if present
        if routing.thought:
            print(f"LUNA Thought: {routing.thought}")

        # 3. Handle Actions
        if action == "conversation":
            print(f"\nLUNA: {response}")
            self.memory_system.add_short_term("user", str(goal))
            self.memory_system.add_short_term("assistant", response)
            return TaskResult(status="success", content=response, verified=True)

        # Execute Action
        print(f"Executing Action: {action}...")
        
        # Risk check (minimal for simple commands)
        risk_report = self.risk_engine.get_risk_report(action, params)
        if risk_report["blocked"]:
            return TaskResult.failure(f"Action blocked: {risk_report['reason']}")

        # Map action to kernel
        kernel_action = action
        if action == "system": kernel_action = "command"
        elif action == "code": kernel_action = "file_op" # Default to file_op for code, can be refined
        
        # Execute
        result = self.execution_kernel.execute(kernel_action, params)
        
        # 4. Return Result
        if result.status == "success":
            final_content = f"{response}\n\nExecution Result:\n{result.content}" if response else result.content
            self.memory_system.add_short_term("user", str(goal))
            self.memory_system.add_short_term("assistant", final_content)
            return TaskResult(status="success", content=final_content, verified=True)
        else:
            return TaskResult.failure(f"Execution failed: {result.error}")

    def _execute_agent_mode(self, goal: str) -> TaskResult:
        """Legacy multi-step reasoning for complex tasks."""
        # For now, just fallback to single pass or implement a simple 2-step loop
        # The prompt specifically asked to remove slow architecture
        return self._execute_single_pass(goal)
