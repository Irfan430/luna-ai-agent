"""
LUNA AI Agent - Cognitive Loop 4.0
Author: IRFAN

Phase 1 Stabilization Fixes:
  1. Removed unsafe .format() on prompt strings — uses safe .replace() templating only.
  2. Schema validator: 'action' field is NOT required when mode == 'conversation'.
  3. Unified LLM routing layer: classifies input before entering cognitive loop.
  4. JSON repair fallback: extract first valid block, retry once, fallback to conversation.

Advanced iterative control loop with multi-step reasoning and self-healing.
Implements: explicit AgentState, iteration counter, stagnation detection,
repair loop counter, graph-based subgoal tracking, semantic result validation,
environment state introspection, dynamic plan revision, and completion detection logic.
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
        self.step_graph: List[Dict[str, Any]] = []  # Tracks executed steps and their outcomes
        self.current_plan: List[Dict[str, Any]] = [] # The current dynamic plan
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
        self.max_repair_attempts = config.get("cognitive", {}).get("max_repair_attempts", 3)
        self.stagnation_threshold = config.get("cognitive", {}).get("stagnation_threshold", 3)
        self.prompts = self._load_prompts()

    def _safe_fill_prompt(self, template: str, replacements: Dict[str, str]) -> str:
        """
        Safe prompt templating using explicit .replace() calls.
        Avoids KeyError from .format() when prompt contains JSON braces {}.
        All placeholder tokens use {{KEY}} syntax.
        """
        result = template
        for key, value in replacements.items():
            result = result.replace("{{" + key + "}}", value)
        return result

    def _load_prompts(self) -> Dict[str, str]:
        """Load modular prompt packs from the prompts directory."""
        prompt_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
        prompts = {}
        if not os.path.exists(prompt_dir):
            logger.error(f"Prompt directory not found: {prompt_dir}")
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

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self, goal: str) -> TaskResult:
        """
        Run the cognitive loop to achieve a goal with self-healing.

        Phase 1 Fix: Route input through LLMRouter first.
        - If mode == 'conversation' -> return immediately, no planning.
        - If mode == 'action' or 'plan' -> enter cognitive loop.
        """
        # Step 0: Route the input
        routing = self.router.route(goal)
        mode = routing.get("mode", "plan")

        if mode == "conversation":
            response_text = routing.get("response", "")
            if not response_text:
                response_text = "Understood."
            print(f"\nLUNA: {response_text}")
            return TaskResult(
                status="success",
                content=response_text,
                error="",
                execution_used=False,
                confidence=1.0,
                risk_level="low",
                verified=True,
            )

        # Action or plan mode — enter cognitive loop
        state = AgentState(goal)
        self.memory_system.clear_short_term()
        self.memory_system.set_goal(goal)
        self.memory_system.add_short_term("user", "Goal: " + goal)

        while not state.is_complete and state.iteration < self.max_iterations:
            state.iteration += 1
            print(f"\n--- LUNA Iteration {state.iteration} ---")

            try:
                # 1. Environment State Introspection
                state.environment_snapshot = self.execution_kernel.get_system_stats()
                self.memory_system.update_execution_state("environment_snapshot", state.environment_snapshot)

                # 2. Analyze State and Plan Next Step (or revise current plan)
                self._analyze_and_plan(state)

                # 3. Get current step from plan
                if not state.current_plan or state.current_step_index >= len(state.current_plan):
                    # If no plan, but not complete, try one more iteration or fail
                    if state.iteration < self.max_iterations:
                        continue
                    return TaskResult.failure("Cognitive loop failed: No valid plan or steps remaining.")

                try:
                    current_step = state.current_plan[state.current_step_index]
                    # Bug Fix #1: LLM returns action directly in step dict (not nested under 'action' key)
                    # Support both formats: {"action": {...}} and flat {"action": "type", "parameters": {...}}
                    if isinstance(current_step.get("action"), dict):
                        action_data = current_step.get("action")
                    elif isinstance(current_step.get("action"), str):
                        # Flat format: action type is a string, build action_data from step itself
                        action_data = {
                            "action": current_step.get("action"),
                            "parameters": current_step.get("parameters", {}),
                            "thought": current_step.get("description", ""),
                            "risk_level": current_step.get("risk_estimate", "low"),
                            "expected_outcome": current_step.get("expected_outcome", ""),
                        }
                    else:
                        action_data = None
                except (IndexError, KeyError, AttributeError) as e:
                    logger.error(f"Plan access error: {e}")
                    state.current_plan = [] # Force replan
                    continue

                if not action_data:
                    logger.warning("Current plan step has no action data. Forcing replan.")
                    state.current_plan = []
                    continue

                # 4. Validate Schema and Assess Risk
                action_data = self._validate_and_assess(state, action_data)
                if not action_data:
                    # If validation/risk fails, the plan needs revision
                    continue

                # 5. Execute Deterministically
                result = self._execute_action(state, action_data)

                # 6. Capture Output and Reflect (and potentially revise plan)
                self._reflect_and_update(state, result)

                # 7. Detect Stagnation
                self._detect_stagnation(state, result)

                # 8. Check Completion
                self._check_completion(state, result)

                # Advance step index if current step was successful and not complete
                if result.status == "success" and not state.is_complete:
                    state.current_step_index += 1

            except Exception as e:
                error_trace = traceback.format_exc()
                logger.error(f"Critical error in cognitive loop iteration {state.iteration}:\n{error_trace}")
                print(f"Cognitive loop error: {e}")
                
                state.repair_counter += 1
                if state.repair_counter >= self.max_repair_attempts:
                    return TaskResult.failure(
                        f"Max repair attempts ({self.max_repair_attempts}) reached. Last error: {e}"
                    )
                
                # If an error occurs, force replanning in the next iteration
                state.current_plan = []
                state.current_step_index = 0
                self.memory_system.add_short_term("system", f"Internal error encountered: {e}. Re-evaluating plan.")

        if state.is_complete and state.last_result:
            return state.last_result

        return TaskResult.failure(
            f"Max iterations ({self.max_iterations}) reached without goal completion."
        )

    # ------------------------------------------------------------------
    # Sub-steps
    # ------------------------------------------------------------------

    def _analyze_and_plan(self, state: AgentState):
        """Step 2: Analyze current state and plan the next action or revise existing plan."""
        # Only replan if there's no current plan or if the current step failed
        if not state.current_plan or (state.last_result and state.last_result.status == "failed"):
            print("Generating/Revising plan...")
            
            # Define expected schema for planning
            plan_schema = {
                "required": ["next_steps"],
                "optional": {
                    "reasoning": "No reasoning provided",
                    "status": "planning"
                }
            }
            
            # Phase 1 Fix: safe templating — no .format() on prompt strings
            planning_template = self.prompts.get("planning", "Plan the next steps.")
            planning_prompt = self._safe_fill_prompt(
                planning_template,
                {
                    "STATE": json.dumps(state.to_dict(), indent=2),
                    "GOAL": state.goal,
                    "MEMORY": self.memory_system.long_term or "No long-term memory yet.",
                },
            )

            plan_messages = [
                {"role": "system", "content": self.prompts.get("identity", "You are LUNA AI Agent.")},
                {"role": "system", "content": planning_prompt}
            ] + self.memory_system.short_term
            
            plan_response = self.continuation_engine.call_with_continuation(plan_messages)
            self.memory_system.add_short_term("assistant", plan_response)

            try:
                # Phase 1 Fix: use repair_and_parse_json with fallback
                success, raw_plan = repair_and_parse_json(plan_response)
                if not success or not raw_plan:
                    raise ValueError("No valid JSON found in plan response after repair attempt.")

                is_valid, sanitized_plan = self.llm_manager.get_provider().validate_and_sanitize(raw_plan, plan_schema)
                
                if is_valid:
                    state.current_plan = sanitized_plan["next_steps"]
                    state.current_step_index = 0
                    print(f"New plan generated with {len(state.current_plan)} steps.")
                else:
                    logger.error(f"Plan schema validation failed: {sanitized_plan}")
                    state.current_plan = []
            except Exception as e:
                logger.error(f"Error parsing plan: {e}")
                state.current_plan = []

    def _validate_and_assess(self, state: AgentState, action_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Step 4: Validate schema and assess risk for the next action."""
        print("Validating schema and assessing risk...")

        # Phase 1 Fix: action is required for execution steps
        action_schema = {
            "required": ["action", "parameters"],
            "optional": {
                "thought": "Executing planned action",
                "risk_level": "low",
                "description": "",
                "expected_outcome": "",
                "risk_estimate": "low",
            },
        }

        # Use sanitation layer
        is_valid, sanitized_action = self.llm_manager.get_provider().validate_and_sanitize(action_data, action_schema)
        
        if not is_valid:
            print(f"Action validation failed: {sanitized_action}")
            state.repair_counter += 1
            self.memory_system.add_short_term("system", f"Action validation failed: {sanitized_action}. Re-evaluating.")
            return None

        # Risk assessment
        action = sanitized_action.get("action")
        params = sanitized_action.get("parameters", {})
        risk_report = self.risk_engine.get_risk_report(action, params)
        risk_level = risk_report["label"]
        sanitized_action["risk_level"] = risk_level

        if risk_report["blocked"]:
            print(f"Action blocked due to risk level: {risk_level}")
            self.memory_system.add_short_term("system", f"Action blocked due to {risk_level} risk. Re-evaluating.")
            return None

        if risk_report["requires_confirmation"]:
            print(f"\n[RISK: {risk_level.upper()}] Action: {action} {params}")
            confirm = input("Confirm execution? (y/n): ").lower()
            if confirm != "y":
                print("Execution cancelled by user.")
                self.memory_system.add_short_term("system", "User cancelled execution. Re-evaluating.")
                return None

        return sanitized_action

    def _execute_action(self, state: AgentState, action_data: Dict[str, Any]) -> TaskResult:
        """Step 5: Execute the action deterministically."""
        action = action_data.get("action")
        params = action_data.get("parameters", {})
        print(f"Executing: {action}...")
        
        try:
            result = self.execution_kernel.execute(action, params)
        except Exception as e:
            logger.error(f"Execution kernel error: {e}")
            result = TaskResult.failure(f"Execution failed with internal error: {e}")
            
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
        """Step 6: Reflect on the result and update memory state."""
        print("Reflecting on result and updating state...")
        state.last_result = result
        
        # Reflection schema - Bug Fix #3: Updated to match reflection.prompt output
        reflect_schema = {
            "required": ["outcome_assessment", "reasoning"],
            "optional": {
                "is_complete": False,
                "repair_plan": [],
                "progress_toward_goal": "",
                "errors_detected": "none",
                "stagnation_risk": False,
                "next_step_recommendation": ""
            }
        }
        
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

        reflect_messages = [
            {"role": "system", "content": self.prompts.get("identity", "")},
            {"role": "system", "content": reflection_prompt}
        ] + self.memory_system.short_term
        
        reflect_response = self.continuation_engine.call_with_continuation(reflect_messages)
        self.memory_system.add_short_term("assistant", reflect_response)

        try:
            success, raw_reflect = repair_and_parse_json(reflect_response)
            if success and raw_reflect:
                is_valid, sanitized_reflect = (
                    self.llm_manager.get_provider().validate_and_sanitize(
                        raw_reflect, reflect_schema
                    )
                )
                if is_valid:
                    # Bug Fix #3 & #5: Correctly handle completion detection
                    outcome = sanitized_reflect.get("outcome_assessment")
                    
                    # If LLM explicitly says it's complete
                    if sanitized_reflect.get("is_complete") is True:
                        state.is_complete = True
                    # Or if outcome is success and no further steps are recommended
                    elif outcome == "success" and not sanitized_reflect.get("repair_plan"):
                        state.is_complete = True
                        
                    if sanitized_reflect.get("repair_plan"):
                        state.current_plan = sanitized_reflect["repair_plan"]
                        state.current_step_index = 0
                    
                    # Log reflection for debugging
                    print(f"Reflection: {outcome} | Complete: {state.is_complete}")
                else:
                    logger.error(f"Reflection schema validation failed: {sanitized_reflect}")
        except Exception as e:
            logger.error(f"Error parsing reflection: {e}")

    def _detect_stagnation(self, state: AgentState, result: TaskResult):
        """Step 7: Detect if the agent is making no progress."""
        if result.status == "failed":
            state.stagnation_counter += 1
        else:
            state.stagnation_counter = 0

        if state.stagnation_counter >= self.stagnation_threshold:
            print("Stagnation detected. Forcing plan revision.")
            state.current_plan = []
            state.current_step_index = 0
            self.memory_system.add_short_term("system", "Stagnation detected. Please try a different approach.")

    def _check_completion(self, state: AgentState, result: TaskResult):
        """Step 8: Check if the goal has been achieved."""
        # Completion is primarily handled by reflection, but we can add heuristic checks here
        if result.status == "success" and "goal achieved" in result.content.lower():
            state.is_complete = True
