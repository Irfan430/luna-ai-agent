"""
LUNA AI Agent - Cognitive Loop 5.0
Author: IRFAN

Phase 1 Architectural Stabilization:
  - Unified LLM Brain contract: always returns mode, confidence, response, and steps.
  - If mode == conversation: return response immediately, no cognitive loop.
  - If mode == action or plan: dispatch through structured execution engine.
  - Remove infinite retry loops.
  - JSON repair fallback (1 retry max).
  - No 'action' key required if mode == conversation.
"""

import json
import os
import time
import traceback
import logging
from typing import Dict, Any, List, Optional

from llm.provider import LLMManager
from llm.continuation import ContinuationEngine
from llm.router import LLMRouter, repair_and_parse_json
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
        self.step_graph: List[Dict[str, Any]] = []
        self.current_plan: List[Dict[str, Any]] = []
        self.current_step_index = 0
        self.is_complete = False
        self.last_action: Optional[Dict[str, Any]] = None
        self.last_result: Optional[TaskResult] = None
        self.environment_snapshot: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "iteration": self.iteration,
            "stagnation_counter": self.stagnation_counter,
            "repair_counter": self.repair_counter,
            "step_graph_length": len(self.step_graph),
            "current_plan_length": len(self.current_plan),
            "current_step_index": self.current_step_index,
            "is_complete": self.is_complete,
            "last_action": self.last_action,
            "last_result": self.last_result.to_dict() if self.last_result else None,
            "environment_snapshot": self.environment_snapshot,
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
        self.max_iterations = config.get("cognitive", {}).get("max_iterations", 5)
        self.max_repair_attempts = config.get("cognitive", {}).get("max_repair_attempts", 2)
        self.prompts = self._load_prompts()

    def _safe_fill_prompt(self, template: str, replacements: Dict[str, str]) -> str:
        result = template
        for key, value in replacements.items():
            result = result.replace("{{" + key + "}}", value)
        return result

    def _load_prompts(self) -> Dict[str, str]:
        prompt_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
        prompts = {}
        if not os.path.exists(prompt_dir):
            return prompts
        for filename in os.listdir(prompt_dir):
            if filename.endswith(".prompt"):
                name = filename.replace(".prompt", "")
                try:
                    with open(os.path.join(prompt_dir, filename), "r", encoding="utf-8") as f:
                        prompts[name] = f.read()
                except Exception as e:
                    logger.error(f"Failed to load prompt {filename}: {e}")
        return prompts

    def run(self, goal: str) -> TaskResult:
        """Run the cognitive loop with Phase 1 stabilization."""
        # Step 0: Route the input through the Unified Brain
        routing = self.router.route(goal, history=self.memory_system.short_term)
        mode = routing.get("mode", "conversation")
        confidence = routing.get("confidence", 1.0)
        response_text = routing.get("response", "")
        steps = routing.get("steps", [])

        # Rule 3: If mode == conversation, return response immediately
        if mode == "conversation":
            print(f"\nLUNA: {response_text}")
            self.memory_system.add_short_term("user", goal)
            self.memory_system.add_short_term("assistant", response_text)
            return TaskResult(
                status="success",
                content=response_text,
                error="",
                execution_used=False,
                confidence=confidence,
                risk_level="low",
                verified=True,
            )

        # Rule 4: If mode == action or plan, enter cognitive loop
        state = AgentState(goal)
        self.memory_system.clear_short_term()
        self.memory_system.set_goal(goal)
        self.memory_system.add_short_term("user", "Goal: " + goal)
        
        # Initialize plan from brain routing
        if steps:
            state.current_plan = steps
            print(f"Brain generated initial plan with {len(steps)} steps.")

        while not state.is_complete and state.iteration < self.max_iterations:
            state.iteration += 1
            print(f"\n--- LUNA Iteration {state.iteration} ---")

            try:
                state.environment_snapshot = self.execution_kernel.get_system_stats()
                self.memory_system.update_execution_state("environment_snapshot", state.environment_snapshot)

                # 1. Analyze and Plan (if no plan exists or current step failed)
                if not state.current_plan or (state.last_result and state.last_result.status == "failed"):
                    self._analyze_and_plan(state)

                if not state.current_plan or state.current_step_index >= len(state.current_plan):
                    if state.iteration < self.max_iterations: continue
                    return TaskResult.failure("Cognitive loop failed: No valid plan remaining.")

                # 2. Get current step
                current_step = state.current_plan[state.current_step_index]
                
                # Rule 2: Unified Brain contract handling
                action_data = {
                    "action": current_step.get("action"),
                    "parameters": current_step.get("parameters", {}),
                    "thought": current_step.get("description", ""),
                    "risk_level": current_step.get("risk_estimate", "low"),
                }

                # 3. Validate and Assess
                action_data = self._validate_and_assess(state, action_data)
                if not action_data: continue

                # 4. Execute
                result = self._execute_action(state, action_data)

                # 5. Reflect and Update
                self._reflect_and_update(state, result)

                # 6. Check Completion
                if result.status == "success" and not state.is_complete:
                    state.current_step_index += 1

            except Exception as e:
                logger.error(f"Critical error in cognitive loop: {e}")
                state.repair_counter += 1
                if state.repair_counter >= self.max_repair_attempts:
                    return TaskResult.failure(f"Max repair attempts reached. Last error: {e}")
                state.current_plan = [] # Force replan

        if state.is_complete and state.last_result:
            return state.last_result

        return TaskResult.failure(f"Max iterations ({self.max_iterations}) reached.")

    def _analyze_and_plan(self, state: AgentState):
        """Re-plan using the unified brain logic."""
        print("Generating/Revising plan...")
        planning_template = self.prompts.get("planning", "Plan the next steps.")
        planning_prompt = self._safe_fill_prompt(
            planning_template,
            {
                "STATE": json.dumps(state.to_dict(), indent=2),
                "GOAL": state.goal,
                "MEMORY": self.memory_system.long_term or "No long-term memory yet.",
            },
        )
        messages = [
            {"role": "system", "content": self.prompts.get("identity", "You are LUNA AI Agent.")},
            {"role": "system", "content": planning_prompt}
        ] + self.memory_system.short_term
        
        plan_response = self.continuation_engine.call_with_continuation(messages)
        success, raw_plan = repair_and_parse_json(plan_response)
        
        if success and raw_plan:
            state.current_plan = raw_plan.get("next_steps", [])
            state.current_step_index = 0
            print(f"New plan generated with {len(state.current_plan)} steps.")
        else:
            state.current_plan = []

    def _validate_and_assess(self, state: AgentState, action_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate action schema and assess risk."""
        action = action_data.get("action")
        params = action_data.get("parameters", {})
        risk_report = self.risk_engine.get_risk_report(action, params)
        risk_level = risk_report["label"]
        action_data["risk_level"] = risk_level

        if risk_report["blocked"]:
            print(f"Action blocked due to risk level: {risk_level}")
            return None

        if risk_report["requires_confirmation"]:
            print(f"\n[RISK: {risk_level.upper()}] Action: {action} {params}")
            confirm = input("Confirm execution? (y/n): ").lower()
            if confirm != "y": return None

        return action_data

    def _execute_action(self, state: AgentState, action_data: Dict[str, Any]) -> TaskResult:
        """Execute the action."""
        action = action_data.get("action")
        params = action_data.get("parameters", {})
        print(f"Executing: {action}...")
        
        try:
            result = self.execution_kernel.execute(action, params)
        except Exception as e:
            result = TaskResult.failure(f"Execution failed: {e}")
            
        result.risk_level = action_data.get("risk_level", "low")
        state.last_action = action_data
        state.step_graph.append({
            "iteration": state.iteration,
            "step_index": state.current_step_index,
            "action": action_data,
            "result": result.to_dict(),
        })
        self.memory_system.update_execution_state("last_action", action_data)
        self.memory_system.update_execution_state("last_result_status", result.status)
        return result

    def _reflect_and_update(self, state: AgentState, result: TaskResult):
        """Reflect on the result and update state."""
        print("Reflecting on result...")
        state.last_result = result
        reflection_template = self.prompts.get("reflection", "")
        reflection_prompt = self._safe_fill_prompt(
            reflection_template,
            {
                "STATE": json.dumps(state.to_dict(), indent=2),
                "GOAL": state.goal,
                "ACTION": json.dumps(state.last_action, indent=2) if state.last_action else "None",
                "RESULT": json.dumps(result.to_dict(), indent=2),
            },
        )
        messages = [
            {"role": "system", "content": self.prompts.get("identity", "")},
            {"role": "system", "content": reflection_prompt}
        ] + self.memory_system.short_term
        
        reflect_response = self.continuation_engine.call_with_continuation(messages)
        success, raw_reflect = repair_and_parse_json(reflect_response)
        
        if success and raw_reflect:
            if raw_reflect.get("outcome_assessment") == "success" or raw_reflect.get("is_complete"):
                state.is_complete = True
            if raw_reflect.get("repair_plan"):
                state.current_plan = raw_reflect["repair_plan"]
                state.current_step_index = 0
