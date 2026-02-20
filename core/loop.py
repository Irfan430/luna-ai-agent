"""
LUNA AI Agent - Cognitive Loop 2.0
Author: IRFAN

Advanced iterative control loop with multi-step reasoning and self-healing.
Implements: explicit AgentState, iteration counter, stagnation detection,
repair loop counter, step graph tracking, and completion detection logic.
"""

import json
import os
import time
from typing import Dict, Any, List, Optional

from llm.provider import LLMManager
from llm.continuation import ContinuationEngine
from execution.kernel import ExecutionKernel, ExecutionResult
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
        self.step_graph: List[Dict[str, Any]] = []
        self.is_complete = False
        self.last_action: Optional[Dict[str, Any]] = None
        self.last_result: Optional[ExecutionResult] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "iteration": self.iteration,
            "stagnation_counter": self.stagnation_counter,
            "repair_counter": self.repair_counter,
            "step_count": len(self.step_graph),
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
        self.max_iterations = config.get('cognitive', {}).get('max_iterations', 5)
        self.max_repair_attempts = config.get('cognitive', {}).get('max_repair_attempts', 3)
        self.stagnation_threshold = config.get('cognitive', {}).get('stagnation_threshold', 3)
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, str]:
        """Load modular prompt packs from the prompts directory."""
        prompt_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
        prompts = {}
        for filename in os.listdir(prompt_dir):
            if filename.endswith('.prompt'):
                name = filename.replace('.prompt', '')
                with open(os.path.join(prompt_dir, filename), 'r', encoding='utf-8') as f:
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
            print("\n--- LUNA Iteration " + str(state.iteration) + " ---")

            try:
                # 1. Analyze state and plan next step
                self._analyze_and_plan(state)

                # 2. Validate schema and assess risk
                action_data = self._validate_and_assess(state)
                if not action_data:
                    continue

                # 3. Execute deterministically
                result = self._execute_action(state, action_data)

                # 4. Capture output and reflect
                self._reflect_and_update(state, result)

                # 5. Detect stagnation
                self._detect_stagnation(state, result)

                # 6. Check completion
                self._check_completion(state, result)

            except Exception as e:
                print("Cognitive loop error: " + str(e))
                state.repair_counter += 1
                if state.repair_counter >= self.max_repair_attempts:
                    return TaskResult.failure(
                        "Max repair attempts (" + str(self.max_repair_attempts) + ") reached. Last error: " + str(e)
                    )

        if state.is_complete and state.last_result:
            r = state.last_result
            return TaskResult(
                status=r.status,
                content=r.content,
                error=r.error,
                execution_used=r.execution_used,
                confidence=r.confidence,
                risk_level=r.risk_level,
                verified=r.verified,
                system_state=r.system_state,
            )

        return TaskResult.failure(
            "Max iterations (" + str(self.max_iterations) + ") reached without goal completion."
        )

    # ------------------------------------------------------------------
    # Sub-steps
    # ------------------------------------------------------------------

    def _analyze_and_plan(self, state: AgentState):
        """Step 1: Analyze current state and plan the next action."""
        print("Analyzing state and planning next step...")
        plan_messages = [
            {"role": "system", "content": self.prompts['identity']},
            {"role": "system", "content": self.prompts['planning'].format(
                state=json.dumps(state.to_dict(), indent=2),
                goal=state.goal,
                memory=self.memory_system.compressed_long_term_memory,
            )}
        ] + self.memory_system.get_context()
        plan_response = self.continuation_engine.call_with_continuation(plan_messages)
        self.memory_system.add_short_term("assistant", plan_response)

    def _validate_and_assess(self, state: AgentState) -> Optional[Dict[str, Any]]:
        """Step 2: Generate, validate schema, and assess risk for the next action."""
        print("Validating schema and assessing risk...")
        action_messages = [
            {"role": "system", "content": self.prompts['identity']},
            {"role": "system", "content": self.prompts['execution']}
        ] + self.memory_system.get_context()

        action_response = self.continuation_engine.call_with_continuation(action_messages)
        action_data = self.llm_manager.get_provider().extract_json(action_response)

        if not action_data or "action" not in action_data:
            print("Failed to extract structured action. Attempting repair.")
            state.repair_counter += 1
            return None

        # Schema validation
        is_valid, schema_error = self.llm_manager.get_provider().validate_action_schema(action_data)
        if not is_valid:
            print("Schema validation failed: " + schema_error)
            state.repair_counter += 1
            return None

        # Risk assessment
        action = action_data.get("action")
        params = action_data.get("parameters", {})
        risk_report = self.risk_engine.get_risk_report(action, params)
        risk_level = risk_report["label"]
        action_data["risk_level"] = risk_level

        if risk_report["blocked"]:
            print("Action blocked due to risk level: " + risk_level)
            return None

        if risk_report["requires_confirmation"]:
            print("\n[RISK: " + risk_level.upper() + "] Action: " + str(action) + " " + str(params))
            confirm = input("Confirm execution? (y/n): ").lower()
            if confirm != 'y':
                print("Execution cancelled by user.")
                return None

        return action_data

    def _execute_action(self, state: AgentState, action_data: Dict[str, Any]) -> ExecutionResult:
        """Step 3: Execute the action deterministically."""
        action = action_data.get("action")
        params = action_data.get("parameters", {})
        print("Executing: " + str(action) + "...")
        result = self.execution_kernel.execute(action, params)
        result.risk_level = action_data.get("risk_level", "low")
        state.last_action = action_data
        state.step_graph.append({
            "iteration": state.iteration,
            "action": action_data,
            "result": result.to_dict(),
        })
        self.memory_system.update_execution_state("last_action", action_data)
        self.memory_system.update_execution_state("last_result_status", result.status)
        return result

    def _reflect_and_update(self, state: AgentState, result: ExecutionResult):
        """Step 4: Reflect on the result and update memory state."""
        print("Reflecting on result and updating state...")
        state.last_result = result
        reflect_messages = [
            {"role": "system", "content": self.prompts['identity']},
            {"role": "system", "content": self.prompts['reflection'].format(
                goal=state.goal,
                action=json.dumps(state.last_action),
                result=json.dumps(result.to_dict()),
            )}
        ] + self.memory_system.get_context()
        reflect_response = self.continuation_engine.call_with_continuation(reflect_messages)
        self.memory_system.add_short_term("assistant", reflect_response)

        # Memory compression if threshold exceeded
        if self.memory_system.needs_compression():
            print("Memory threshold reached. Compressing...")
            summary = self.memory_system.auto_summarize_context()
            self.memory_system.compress(summary)

    def _detect_stagnation(self, state: AgentState, result: ExecutionResult):
        """Step 5: Detect stagnation and inject recovery signal if needed."""
        if result.status == "failed":
            state.stagnation_counter += 1
            print("Execution failed. Stagnation counter: " + str(state.stagnation_counter))
            if state.stagnation_counter >= self.stagnation_threshold:
                print("Stagnation detected. Injecting recovery signal.")
                self.memory_system.add_short_term(
                    "system",
                    "STAGNATION DETECTED: The previous " + str(self.stagnation_threshold) +
                    " attempts all failed. Re-evaluate the plan from scratch. "
                    "Try a fundamentally different approach."
                )
                state.stagnation_counter = 0
        else:
            state.stagnation_counter = 0

    def _check_completion(self, state: AgentState, result: ExecutionResult):
        """Step 6: Verify whether the goal has been fully achieved."""
        verify_messages = [
            {"role": "system", "content": self.prompts['identity']},
            {"role": "system", "content": self.prompts['verification'].format(
                goal=state.goal,
                action=json.dumps(state.last_action),
                result=json.dumps(result.to_dict()),
            )}
        ] + self.memory_system.get_context()
        verify_response = self.continuation_engine.call_with_continuation(verify_messages)
        verify_data = self.llm_manager.get_provider().extract_json(verify_response)

        if verify_data and verify_data.get("status") == "success" and verify_data.get("goal_complete"):
            print("Goal achieved and verified!")
            state.is_complete = True
            result.verified = True
            self.memory_system.add_episodic(state.goal, result.to_dict())
