"""
LUNA AI Agent - Intent Parser
Author: IRFAN

Parses natural language input into structured JSON intent.
"""

from typing import Dict, Any, List
from .llm_manager import LLMManager
from core.task_result import TaskResult


class IntentParser:
    """Parse natural language into structured intent."""
    
    INTENT_PROMPT = """You are LUNA's intent parser. Your job is to understand user requests and convert them into structured JSON.

Analyze the user's request and return ONLY a JSON object with this structure:
{
    "intent_type": "command|query|conversation",
    "action": "specific action to take",
    "parameters": {
        "key": "value"
    },
    "risk_level": "low|medium|high|dangerous",
    "requires_execution": true/false,
    "confidence": 0.0-1.0
}

Intent types:
- command: User wants to execute something (run app, create file, git operations)
- query: User wants information (what is, how to, explain)
- conversation: General chat, no action needed

Risk levels:
- low: Read operations, safe queries
- medium: File creation, non-destructive changes
- high: File deletion, system changes, git push
- dangerous: rm -rf, system shutdown, destructive operations

Return ONLY the JSON, no explanations."""
    
    def __init__(self, llm_manager: LLMManager):
        """Initialize intent parser."""
        self.llm_manager = llm_manager
    
    def parse(self, user_input: str) -> TaskResult:
        """
        Parse user input into structured intent.
        
        Args:
            user_input: Natural language user request
            
        Returns:
            TaskResult with parsed intent as JSON in content
        """
        try:
            messages = [
                {"role": "system", "content": self.INTENT_PROMPT},
                {"role": "user", "content": user_input}
            ]
            
            response = self.llm_manager.chat(messages, temperature=0.3)
            
            # Parse JSON from response
            provider = self.llm_manager.get_provider()
            intent_data = provider.parse_json_response(response.content)
            
            # Validate required fields
            required_fields = ["intent_type", "action", "risk_level", "requires_execution", "confidence"]
            for field in required_fields:
                if field not in intent_data:
                    return TaskResult.failed(
                        error=f"Missing required field in intent: {field}",
                        content=response.content
                    )
            
            return TaskResult.success(
                content=str(intent_data),
                confidence=intent_data.get("confidence", 0.8),
                verified=True,
                risk_level=intent_data.get("risk_level", "low")
            )
            
        except Exception as e:
            return TaskResult.failed(
                error=f"Intent parsing failed: {str(e)}",
                content=""
            )
    
    def parse_dict(self, user_input: str) -> Dict[str, Any]:
        """
        Parse user input and return intent as dictionary.
        
        Args:
            user_input: Natural language user request
            
        Returns:
            Intent dictionary
        """
        result = self.parse(user_input)
        if result.status == "success":
            import ast
            return ast.literal_eval(result.content)
        else:
            raise Exception(result.error)
