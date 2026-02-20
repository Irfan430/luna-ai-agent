"""
LUNA AI Agent - Cognitive Loop 7.0
Author: IRFAN

Phase 2: Routing Guard & BrainOutput Integration
  - Use BrainOutput model for routing results.
  - If mode == conversation: bypass execution layer completely.
  - Never enter cognitive loop for numeric input.
  - Structural consistency for all cognitive steps.
"""

import json
import os
import time
import traceback
import logging
from typing import Dict, Any, List, Optional

from llm.provider import LLMManager
from llm.continuation import ContinuationEngine
from llm.router import LLMRouter, BrainOutput, normalize_brain_output, repair_and_parse_json
from execution.kernel import ExecutionKernel
from risk.engine import RiskEngine
from memory.system import MemorySystem
from core.task_result import TaskResult

logger = logging.getLogger("luna.core.loop")

class AgentState:
    """Explicit state object tracking all cognitive loop variables."""
    def __init__(self, goal: str):
        self.goal = goal
        self.iteration = 0
        self.stagnation_counter = 0
        self.repair_counter = 0
        self.current_plan: List[Dict[str, Any]] = []
        self.current_step_index = 0
        self.is_complete = False
        self.last_action: Optional[Dict[str, Any]] = None
        self.last_result: Optional[TaskResult] = None
        self.attempts: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "iteration": self.iteration,
            "is_complete": self.is_complete,
            "last_action": self.last_action,
            "last_result": self.last_result.to_dict() if self.last_result else None,
        }

class CognitiveLoop:
    """Advanced iterative control loop for LUNA's cognitive orchestration."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_manager = LLMManager(config)
        self.continuation_engine = ContinuationEngine(self.llm_manager, config)
        self.execution_kernel = ExecutionKernel()
        self.risk_engine = RiskEngine(config)
        self.memory_system = MemorySystem(config)
        self.router = LLMRouter(self.llm_manager)
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, str]:
        prompt_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
        prompts = {}
        if not os.path.exists(prompt_dir): return prompts
        for filename in os.listdir(prompt_dir):
            if filename.endswith(".prompt"):
                name = filename.replace(".prompt", "")
                try:
                    with open(os.path.join(prompt_dir, filename), "r", encoding="utf-8") as f:
                        prompts[name] = f.read()
                except Exception: pass
        return prompts

    def run(self, goal: str) -> TaskResult:
        """Run the cognitive loop with Phase 2 routing guard."""
        # Phase 2: Never enter cognitive loop for numeric input
        if isinstance(goal, (int, float)) or (isinstance(goal, str) and goal.isdigit()):
            response = f"I received the numeric input: {goal}. How would you like me to use this?"
            return TaskResult(status="success", content=response, verified=True)

        # Phase 1 & 2: Routing Guard
        routing = self.router.route(goal, history=self.memory_system.short_term)
        
        # Ensure we have a BrainOutput object
        if not isinstance(routing, BrainOutput):
            routing = normalize_brain_output(routing)

        # Phase 2: conversation → bypass execution layer completely
        if routing.mode == "conversation":
            response = routing.response
            print(f"\nLUNA: {response}")
            self.memory_system.add_short_term("user", str(goal))
            self.memory_system.add_short_term("assistant", response)
            return TaskResult(status="success", content=response, verified=True)

        # Phase 2: direct_action → single execution pass
        if routing.mode == "direct_action":
            action = routing.action
            params = routing.parameters
            print(f"Direct Action: {action}...")
            result = self.execution_kernel.execute(action, params)
            if result.status == "success":
                return TaskResult(status="success", content=result.content, verified=True)
            
            print(f"Direct action failed: {result.error}. Escalating to cognitive loop.")
            routing.mode = "complex_plan"

        # Complex Plan Iterative Loop
        state = AgentState(str(goal))
        max_iters = 5 if routing.mode == "complex_plan" else 2
        
        if routing.steps:
            state.current_plan = routing.steps

        while not state.is_complete and state.iteration < max_iters:
            state.iteration += 1
            print(f"\n--- LUNA Iteration {state.iteration} ---")

            try:
                if not state.current_plan or (state.last_result and state.last_result.status == "failed"):
                    self._analyze_and_plan(state)

                if not state.current_plan or state.current_step_index >= len(state.current_plan):
                    break

                current_step = state.current_plan[state.current_step_index]
                action_name = current_step.get("action")
                action_params = current_step.get("parameters", {})

                # Risk check
                risk_report = self.risk_engine.get_risk_report(action_name, action_params)
                if risk_report["blocked"]:
                    return TaskResult.failure(f"Action blocked: {risk_report['reason']}")

                # Execute
                result = self.execution_kernel.execute(action_name, action_params)
                state.last_action = {"action": action_name, "parameters": action_params}
                state.last_result = result
                state.attempts.append({"action": state.last_action, "result": result.to_dict()})

                # Reflect
                self._reflect_and_update(state, result)
                if result.status == "success" and not state.is_complete:
                    state.current_step_index += 1

            except Exception as e:
                logger.error(f"Loop error: {e}")
                break

        if state.is_complete and state.last_result:
            return TaskResult(status="success", content=state.last_result.content, verified=True)

        return self._format_failure(state)

    def _analyze_and_plan(self, state: AgentState):
        planning_template = self.prompts.get("planning", "Plan the next steps.")
        planning_prompt = planning_template.replace("{{STATE}}", json.dumps(state.to_dict())).replace("{{GOAL}}", state.goal)
        messages = [{"role": "system", "content": planning_prompt}] + self.memory_system.short_term
        response = self.llm_manager.call(messages, temperature=0.1)
        
        # Use normalization for planning output too
        success, parsed = repair_and_parse_json(response.content)
        if success and parsed:
            state.current_plan = parsed.get("next_steps", [])
            state.current_step_index = 0

    def _reflect_and_update(self, state: AgentState, result: TaskResult):
        reflection_template = self.prompts.get("reflection", "Reflect on the result.")
        reflection_prompt = reflection_template.replace("{{STATE}}", json.dumps(state.to_dict())).replace("{{RESULT}}", json.dumps(result.to_dict()))
        messages = [{"role": "system", "content": reflection_prompt}] + self.memory_system.short_term
        response = self.llm_manager.call(messages, temperature=0.1)
        
        success, parsed = repair_and_parse_json(response.content)
        if success and parsed:
            if parsed.get("outcome_assessment") == "success" or parsed.get("is_complete"):
                state.is_complete = True
            if parsed.get("repair_plan"):
                state.current_plan = parsed["repair_plan"]
                state.current_step_index = 0

    def _format_failure(self, state: AgentState) -> TaskResult:
        last_attempt = state.attempts[-1] if state.attempts else None
        error_msg = f"Task failed after {state.iteration} iterations.\n"
        if last_attempt:
            error_msg += f"Last attempted action: {last_attempt['action']['action']}\n"
            error_msg += f"Error: {last_attempt['result']['error']}\n"
        
        suggestion_prompt = f"The user goal was: {state.goal}. The last attempt failed with: {error_msg}. Suggest a fix."
        try:
            suggestion = self.llm_manager.call([{"role": "user", "content": suggestion_prompt}]).content
            error_msg += f"Suggestion: {suggestion}"
        except: pass
        
        return TaskResult.failure(error_msg)
