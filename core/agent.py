"""
LUNA AI Agent - Main Agent
Author: IRFAN

Main LUNA agent orchestrator.
"""

from typing import Dict, Any, Optional
from .task_result import TaskResult
from llm.llm_manager import LLMManager
from llm.intent_parser import IntentParser
from llm.continuation import ContinuationHandler
from engine.executor import Executor
from safety.guardrails import Guardrails
from config.config_loader import get_config


class LunaAgent:
    """LUNA AI Agent - Main orchestrator."""
    
    def __init__(self):
        """Initialize LUNA agent."""
        self.config = get_config()
        self.llm_manager = LLMManager()
        self.intent_parser = IntentParser(self.llm_manager)
        self.continuation_handler = ContinuationHandler(self.llm_manager)
        self.executor = Executor()
        self.guardrails = Guardrails()
        
        self.agent_config = self.config.get_agent_config()
        self.name = self.agent_config.get("name", "LUNA")
        self.personality = self.agent_config.get("personality", "calm_confident")
        
        self.conversation_history = []
    
    def process_input(self, user_input: str) -> TaskResult:
        """
        Process user input and execute if needed.
        
        Args:
            user_input: User's natural language input
            
        Returns:
            TaskResult with execution result
        """
        try:
            # Parse intent
            intent_result = self.intent_parser.parse(user_input)
            
            if intent_result.status == "failed":
                return intent_result
            
            # Convert intent string to dict
            import ast
            intent = ast.literal_eval(intent_result.content)
            
            # Check if execution is required
            if not intent.get("requires_execution", False):
                # Just a conversation, respond with LLM
                return self._generate_response(user_input, intent)
            
            # Check risk level and guardrails
            risk_level = intent.get("risk_level", "low")
            allowed, reason = self.guardrails.is_operation_allowed(
                intent.get("action", ""), risk_level
            )
            
            if not allowed:
                return TaskResult.failed(
                    error=reason,
                    content=""
                )
            
            # Execute
            result = self.executor.execute(intent)
            
            # Add to conversation history
            self.conversation_history.append({
                "user": user_input,
                "intent": intent,
                "result": result.to_dict()
            })
            
            return result
            
        except Exception as e:
            return TaskResult.failed(
                error=f"Agent processing error: {str(e)}",
                content=""
            )
    
    def _generate_response(self, user_input: str, intent: Dict[str, Any]) -> TaskResult:
        """
        Generate conversational response.
        
        Args:
            user_input: User input
            intent: Parsed intent
            
        Returns:
            TaskResult with response
        """
        try:
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": user_input}
            ]
            
            response = self.llm_manager.chat(messages, temperature=0.7)
            
            return TaskResult.success(
                content=response.content,
                confidence=0.9,
                verified=True,
                execution_used=False,
                risk_level="low"
            )
            
        except Exception as e:
            return TaskResult.failed(
                error=f"Response generation failed: {str(e)}",
                content=""
            )
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for conversational responses."""
        return f"""You are {self.name}, a personal AI operating agent.

Personality: {self.personality}
- Calm and confident
- Minimal verbosity
- Clear and direct communication
- Professional but friendly

When responding:
- Be concise and to the point
- If explaining errors, be clear about the cause
- If suggesting solutions, give step-by-step guidance
- Always be honest about capabilities and limitations"""
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get agent status.
        
        Returns:
            Status dictionary
        """
        return {
            "name": self.name,
            "active_provider": self.llm_manager.get_active_provider_name(),
            "llm_mode": self.llm_manager.mode,
            "guardrails": self.guardrails.get_limits_status(),
            "conversation_count": len(self.conversation_history)
        }
    
    def reset(self) -> None:
        """Reset agent state."""
        self.conversation_history = []
        self.guardrails.reset_planning_iteration()
        self.guardrails.reset_continuation_retry()
