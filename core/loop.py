"""
LUNA AI Agent - Cognitive Loop 3.0
Author: IRFAN

Advanced iterative control loop with multi-step reasoning and self-healing.
Implements: explicit AgentState, iteration counter, stagnation detection,
repair loop counter, graph-based subgoal tracking, semantic result validation,
environment state introspection, dynamic plan revision, and completion detection logic.
"""

import json
import os
import time
from typing import Dict, Any, List, Optional

from llm.provider import LLMManager
from llm.continuation import ContinuationEngine
from execution.kernel import ExecutionKernel
from risk.engine import RiskEngine
from memory.system import MemorySystem
from core.task_result import TaskResult


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
        self.max_iterations = config.get("cognitive", {}).get("max_iterations", 5)
        self.max_repair_attempts = config.get("cognitive", {}).get("max_repair_attempts", 3)
        self.stagnation_threshold = config.get("cognitive", {}).get("stagnation_threshold", 3)
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, str]:
        """Load modular prompt packs from the prompts directory."""
        prompt_dir = os.path.join(os.path.dirname(__file__), "..", "prompts")
        prompts = {}
        for filename in os.listdir(prompt_dir):
            if filename.endswith(".prompt"):
                name = filename.replace(".prompt", "")
                with open(os.path.join(prompt_dir, filename), "r", encoding="utf-8") as f:
                    prompts[name] = f.read()
        return prompts

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self, goal: str) -> TaskResult:
        """
        Run the cognitive loop to achieve a goal with self-healing.
        Returns a canonical TaskResult object.

        Loop structure:
            while not goal_completed:
                analyze_state()
                plan_next_step()
                validate_schema()
                risk_assessment()
                execute_deterministically()
                capture_output()
                reflect_on_result()
                update_state()
                detect_stagnation()
        """
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
                    return TaskResult.failure("Cognitive loop failed: No valid plan or steps remaining.")

                current_step = state.current_plan[state.current_step_index]
                action_data = current_step.get("action")

                if not action_data:
                    return TaskResult.failure("Cognitive loop failed: Current plan step has no action data.")

                # 4. Validate Schema and Assess Risk
                action_data = self._validate_and_assess(state, action_data)
                if not action_data:
                    # If validation/risk fails, the plan needs revision, handled by reflection
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
                print(f"Cognitive loop error: {e}")
                state.repair_counter += 1
                if state.repair_counter >= self.max_repair_attempts:
                    return TaskResult.failure(
                        f"Max repair attempts ({self.max_repair_attempts}) reached. Last error: {e}"
                    )
                # If an error occurs, force replanning in the next iteration
                state.current_plan = []
                state.current_step_index = 0
                self.memory_system.add_short_term("system", f"Error encountered: {e}. Re-evaluating plan.")

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
        if not state.current_plan or state.last_result and state.last_result.status == "failed":
            print("Generating/Revising plan...")
            system_stats = self.execution_kernel.get_system_stats()
            plan_messages = [
                {"role": "system", "content": self.prompts["identity"]},
                {"role": "system", "content": self.prompts["planning"].format(
                    state=json.dumps(state.to_dict(), indent=2),
                    goal=state.goal,
                    memory=self.memory_system.compressed_long_term_memory,
                )}
            ] + self.memory_system.get_context()
            plan_response = self.continuation_engine.call_with_continuation(plan_messages)
            self.memory_system.add_short_term("assistant", plan_response)

            try:
                plan_data = self.llm_manager.get_provider().extract_json(plan_response)
                if plan_data and "next_steps" in plan_data:
                    state.current_plan = plan_data["next_steps"]
                    state.current_step_index = 0
                    print(f"New plan generated with {len(state.current_plan)} steps.")
                else:
                    print("Failed to extract a valid plan from LLM response.")
                    state.current_plan = [] # Clear plan to force replan
            except Exception as e:
                print(f"Error parsing plan: {e}")
                state.current_plan = [] # Clear plan to force replan

    def _validate_and_assess(self, state: AgentState, action_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Step 4: Validate schema and assess risk for the next action."""
        print("Validating schema and assessing risk...")

        # Schema validation
        is_valid, schema_error = self.llm_manager.get_provider().validate_action_schema(action_data)
        if not is_valid:
            print(f"Schema validation failed: {schema_error}")
            state.repair_counter += 1
            self.memory_system.add_short_term("system", f"Schema validation failed for action: {schema_error}. Re-evaluating.")
            return None

        # Risk assessment
        action = action_data.get("action")
        params = action_data.get("parameters", {})
        risk_report = self.risk_engine.get_risk_report(action, params)
        risk_level = risk_report["label"]
        action_data["risk_level"] = risk_level

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

        return action_data

    def _execute_action(self, state: AgentState, action_data: Dict[str, Any]) -> TaskResult:
        """Step 5: Execute the action deterministically."""
        action = action_data.get("action")
        params = action_data.get("parameters", {})
        print(f"Executing: {action}...")
        result = self.execution_kernel.execute(action, params)
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
        """Step 6: Reflect on the result and update memory state, potentially revising the plan."""
        print("Reflecting on result and updating state...")
        state.last_result = result
        reflect_messages = [
            {"role": "system", "content": self.prompts["identity"]},
            {"role": "system", "content": self.prompts["reflection"].format(
                goal=state.goal,
                action=json.dumps(state.last_action),
                result=json.dumps(result.to_dict()),
                current_plan=json.dumps(state.current_plan[state.current_step_index:] if state.current_plan else [], indent=2)
            )}
        ] + self.memory_system.get_context()
        reflect_response = self.continuation_engine.call_with_continuation(reflect_messages)
        self.memory_system.add_short_term("assistant", reflect_response)

        # Memory compression if threshold exceeded
        if self.memory_system.needs_compression():
            print("Memory threshold reached. Compressing...")
            summary = self.memory_system.auto_summarize_context()
            self.memory_system.compress(summary)

        # Dynamic plan revision based on reflection (if needed)
        try:
            reflection_data = self.llm_manager.get_provider().extract_json(reflect_response)
            if reflection_data and reflection_data.get("plan_revision_needed", False):
                print("Plan revision recommended by reflection. Re-planning...")
                state.current_plan = [] # Clear current plan to force replan in next iteration
                state.current_step_index = 0
        except Exception as e:
            print(f"Error parsing reflection for plan revision: {e}")

    def _detect_stagnation(self, state: AgentState, result: TaskResult):
        """Step 7: Detect stagnation and inject recovery signal if needed."""
        if result.status == "failed":
            state.stagnation_counter += 1
            print(f"Execution failed. Stagnation counter: {state.stagnation_counter}")
            if state.stagnation_counter >= self.stagnation_threshold:
                print("Stagnation detected. Injecting recovery signal.")
                self.memory_system.add_short_term(
                    "system",
                    f"STAGNATION DETECTED: The previous {self.stagnation_threshold} attempts all failed. "
                    "Re-evaluate the plan from scratch. Try a fundamentally different approach."
                )
                state.stagnation_counter = 0
                state.current_plan = [] # Force replan on stagnation
                state.current_step_index = 0
        else:
            state.stagnation_counter = 0

    def _check_completion(self, state: AgentState, result: TaskResult):
        """Step 8: Verify whether the goal has been fully achieved."""
        verify_messages = [
            {"role": "system", "content": self.prompts["identity"]},
            {"role": "system", "content": self.prompts["verification"].format(
                goal=state.goal,
                action=json.dumps(state.last_action),
                result=json.dumps(result.to_dict()),
            )}
        ] + self.memory_system.get_context()
        verify_response = self.continuation_engine.call_with_continuation(verify_messages)
        verify_data = self.llm_manager.get_provider().extract_json(verify_response)

        if verify_data and verify_data.get("status") == "success" and verify_data.get("goal_complete", False):
            print("Goal achieved and verified!")
            state.is_complete = True
            result.verified = True
            self.memory_system.add_episodic(state.goal, result.to_dict())
            state.last_result = result # Update last_result with verified status
