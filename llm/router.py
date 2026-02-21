"""
LUNA AI Agent - DeepSeek Cognitive Router v11.0
Author: IRFAN

Structural Stabilization Refactor:
  - Strict JSON only (No thoughts, no explanations).
  - Centralized OS Agent action schema.
  - Removed risk engine and planner dependencies.
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("luna.llm.router")

@dataclass
class BrainOutput:
    """Strict contract for LUNA's cognitive brain output."""
    intent: str = "conversation"
    parameters: Dict[str, Any] = field(default_factory=dict)
    response: str = ""

BRAIN_SYSTEM_PROMPT = """
You are LUNA, a high-performance DeepSeek-powered OS Agent. 
Your goal is to execute user commands with absolute precision using the provided intents.

### STRICT RULES:
1. ALWAYS return valid JSON.
2. NEVER output any explanation, thoughts, or text outside the JSON block.
3. NEVER include conversational filler when executing actions.

### ALLOWED INTENTS & SCHEMA:
1. "system_command": Run shell commands or system tasks.
   - Params: {"command": "string"}
2. "browser_task": Control persistent browser session (DOM-based).
   - Params: {"action": "goto|search|click|type|scroll", "value": "string", "selector": "string"}
3. "file_operation": Create, read, or manage files.
   - Params: {"op": "create|read|delete", "path": "string", "content": "string"}
4. "app_control": Open or close applications.
   - Params: {"action": "open|close", "app_name": "string"}
5. "conversation": Respond to user when no action is needed.
   - Params: {"message": "string"}

### OUTPUT FORMAT:
{
  "intent": "system_command | browser_task | file_operation | app_control | conversation",
  "parameters": { ... }
}
"""

def repair_and_parse_json(text: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Extract and parse JSON from LLM output."""
    fence_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if fence_match:
        try:
            return True, json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass
    try:
        return True, json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return True, json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return False, None

class LLMRouter:
    """Routes natural language goals to structured OS Agent intents."""

    def __init__(self, llm_manager, config: Dict[str, Any] = None):
        self.llm_manager = llm_manager
        self.config = config or {}

    def route(self, goal: str, history: List[Dict[str, str]] = None) -> BrainOutput:
        """Call LLM to determine the next intent."""
        messages = [{"role": "system", "content": BRAIN_SYSTEM_PROMPT}]
        if history:
            messages.extend(history[-10:]) # Load last 10 interactions for context
        messages.append({"role": "user", "content": goal})

        try:
            response = self.llm_manager.call(messages, temperature=0.1)
            raw_content = response.content
            
            success, parsed = repair_and_parse_json(raw_content)
            if success and parsed:
                intent = parsed.get("intent", "conversation")
                params = parsed.get("parameters", {})
                msg = params.get("message", "") if intent == "conversation" else ""
                return BrainOutput(intent=intent, parameters=params, response=msg)
            
            logger.error(f"[Brain] JSON Parse Error: {raw_content}")
            return BrainOutput(intent="conversation", response="Error: I failed to generate a structured response.")

        except Exception as e:
            logger.error(f"[Brain] Routing error: {e}")
            return BrainOutput(intent="conversation", response="System error in cognitive routing.")
