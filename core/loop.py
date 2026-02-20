"""
LUNA AI Agent - Cognitive Loop
Author: IRFAN

Iterative control loop: Analyze → Plan → Execute → Reflect.
"""

import json
import os
from typing import Dict, Any, List, Optional
from llm.provider import LLMManager
from llm.continuation import ContinuationEngine
from execution.kernel import ExecutionKernel, ExecutionResult
from risk.engine import RiskEngine
from memory.system import MemorySystem


class CognitiveLoop:
    """Iterative control loop for LUNA's cognitive orchestration."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_manager = LLMManager(config)
        self.continuation_engine = ContinuationEngine(self.llm_manager, config)
        self.execution_kernel = ExecutionKernel()
        self.risk_engine = RiskEngine(config)
        self.memory_system = MemorySystem(config)
        self.max_iterations = config.get('cognitive', {}).get('max_iterations', 5)
        self.max_repair_attempts = config.get('cognitive', {}).get('max_repair_attempts', 3)
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, str]:
        """Load modular prompt packs."""
        prompt_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
        prompts = {}
        for filename in os.listdir(prompt_dir):
            if filename.endswith('.prompt'):
                name = filename.replace('.prompt', '')
                with open(os.path.join(prompt_dir, filename), 'r', encoding='utf-8') as f:
                    prompts[name] = f.read()
        return prompts

    def run(self, goal: str) -> ExecutionResult:
        """Run the cognitive loop to achieve a goal."""
        iteration = 0
        self.memory_system.clear_short_term()
        self.memory_system.add_short_term("user", goal)
        
        while iteration < self.max_iterations:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")
            
            # 1. Analyze & Plan
            plan_messages = [
                {"role": "system", "content": self.prompts['identity']},
                {"role": "system", "content": self.prompts['planning'].format(
                    state="Initial analysis", goal=goal, memory=self.memory_system.long_term
                )}
            ] + self.memory_system.get_context()
            
            plan_response = self.continuation_engine.call_with_continuation(plan_messages)
            self.memory_system.add_short_term("assistant", plan_response)
            
            # 2. Generate Action
            action_messages = [
                {"role": "system", "content": self.prompts['identity']},
                {"role": "system", "content": self.prompts['execution']}
            ] + self.memory_system.get_context()
            
            action_response = self.continuation_engine.call_with_continuation(action_messages)
            action_data = self.llm_manager.get_provider().extract_json(action_response)
            
            if not action_data:
                print("Failed to extract structured action. Retrying...")
                continue
            
            # 3. Risk Assessment
            action = action_data.get("action")
            params = action_data.get("parameters", {})
            risk_level = self.risk_engine.classify_action(action, params)
            
            if self.risk_engine.is_blocked(risk_level):
                return ExecutionResult("failed", "", f"Action blocked due to {risk_level} risk level")
            
            if self.risk_engine.should_require_confirmation(risk_level):
                print(f"\n[RISK: {risk_level.upper()}] Action: {action} {params}")
                confirm = input("Confirm execution? (y/n): ").lower()
                if confirm != 'y':
                    return ExecutionResult("failed", "", "Execution cancelled by user")
            
            # 4. Execute
            print(f"Executing: {action}...")
            result = self.execution_kernel.execute(action, params)
            result.risk_level = risk_level
            
            # 5. Reflect & Verify
            reflect_messages = [
                {"role": "system", "content": self.prompts['identity']},
                {"role": "system", "content": self.prompts['reflection'].format(
                    goal=goal, action=action, result=result.to_dict()
                )}
            ] + self.memory_system.get_context()
            
            reflect_response = self.continuation_engine.call_with_continuation(reflect_messages)
            self.memory_system.add_short_term("assistant", reflect_response)
            
            # 6. Verification
            verify_messages = [
                {"role": "system", "content": self.prompts['identity']},
                {"role": "system", "content": self.prompts['verification'].format(
                    goal=goal, action=action, result=result.to_dict()
                )}
            ] + self.memory_system.get_context()
            
            verify_response = self.continuation_engine.call_with_continuation(verify_messages)
            verify_data = self.llm_manager.get_provider().extract_json(verify_response)
            
            if verify_data and verify_data.get("status") == "success":
                print("Goal achieved!")
                self.memory_system.add_episodic(goal, result.to_dict())
                return result
            
            # 7. Self-Healing (if failed)
            if result.status == "failed":
                print(f"Execution failed: {result.error}. Attempting self-healing...")
                # Self-healing logic could be more complex, but for now, we just continue the loop
                # The reflection and next planning step will handle the error
            
            # 8. Memory Compression
            if self.memory_system.needs_compression():
                print("Memory threshold reached. Compressing...")
                # Summarization logic would go here
                # self.memory_system.compress(summary)
                pass
                
        return ExecutionResult("failed", "", f"Max iterations ({self.max_iterations}) reached without success")
