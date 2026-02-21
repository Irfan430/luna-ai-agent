"""
LUNA AI Agent - Intent Routing Layer v9.0
Author: IRFAN

Phase 1 & 2: Core Architecture Refactor
  - Single-pass LLM execution.
  - Execution Router: system, browser, screen, code.
  - No multi-iteration planning loop.
"""

import json
import re
import logging
from typing import Dict, Any, Optional, Tuple, List, Union
from dataclasses import dataclass, field

from llm.provider import LLMManager

logger = logging.getLogger("luna.llm.router")

@dataclass
class BrainOutput:
    """Strict contract for LUNA's cognitive brain output."""
    action: str = "conversation"
    response: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    thought: str = ""
    confidence: float = 0.0

def normalize_brain_output(raw: Any) -> BrainOutput:
    """Normalize any LLM output into a strict BrainOutput model. Never crashes."""
    if isinstance(raw, str):
        return BrainOutput(action="conversation", response=raw.strip(), confidence=0.5)
    
    if not isinstance(raw, dict):
        return BrainOutput(action="conversation", response=str(raw), confidence=0.0)

    try:
        action = str(raw.get("action", "conversation")).lower()
        # Map old modes to new actions if necessary
        if action == "direct_action": action = "system"
        
        # Extract parameters - handle both nested and flat structure
        parameters = raw.get("parameters", {})
        if not isinstance(parameters, dict):
            parameters = {}
        
        # Include all other keys as parameters for flat structure support
        for k, v in raw.items():
            if k not in ["action", "response", "thought", "confidence", "parameters"]:
                parameters[k] = v
        
        return BrainOutput(
            action=action,
            response=str(raw.get("response", "")),
            parameters=parameters,
            thought=str(raw.get("thought", "")),
            confidence=float(raw.get("confidence", 1.0))
        )
    except Exception as e:
        logger.error(f"Normalization error: {e}")
        return BrainOutput(action="conversation", response="I encountered an internal error processing that.", confidence=0.0)

BRAIN_SYSTEM_PROMPT = """You are LUNA, a fast, real-time action-based Jarvis system.
Your goal is to execute user commands immediately with minimal cognitive overhead.

STRICT RULES:
1. YOU MUST RETURN VALID JSON ONLY.
2. NEVER include plain text explanations or conversational filler outside the JSON.
3. NEVER mix explanations with JSON.
4. If you cannot fulfill a request, return a JSON error response.
5. Allowed actions are ONLY: system, browser, screen, code, conversation.

ALLOWED ACTIONS:
- conversation: For general chat, questions, or when no other action is appropriate.
  Example: {"action": "conversation", "response": "Hello! How can I help you today?"}

- system: Run shell commands or system tasks.
  Example: {"action": "system", "command": "firefox"}

- browser: Use the web browser for searching or visiting sites.
  Example: {"action": "browser", "task": "search for latest AI news"}

- screen: Analyze the current screen or UI.
  Example: {"action": "screen", "instruction": "what is visible on the screen?"}

- code: Write and execute Python code.
  Example: {"action": "code", "language": "python", "code": "print('Hello World')", "filename": "hello.py"}

OUTPUT FORMAT:
{
  "thought": "brief reasoning (1 sentence)",
  "action": "system | browser | screen | code | conversation",
  "command": "shell command (if action is system)",
  "task": "browser task (if action is browser)",
  "instruction": "screen instruction (if action is screen)",
  "language": "python (if action is code)",
  "code": "code content (if action is code)",
  "filename": "script name (if action is code)",
  "response": "message to user (for conversation or status)"
}
"""

def _extract_first_json_block(text: str) -> Optional[Dict[str, Any]]:
    fence_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None

def repair_and_parse_json(text: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    result = _extract_first_json_block(text)
    if result is not None:
        return True, result
    cleaned = text.strip()
    cleaned = re.sub(r'^[^{]*', '', cleaned)
    cleaned = re.sub(r'[^}]*$', '', cleaned)
    result = _extract_first_json_block(cleaned)
    if result is not None:
        return True, result
    return False, None

class LLMRouter:
    def __init__(self, llm_manager: LLMManager, config: Dict[str, Any] = None):
        self.llm_manager = llm_manager
        self.config = config or {}
        self.system_info = self.config.get('system', {})

    def route(self, user_input: str, history: List[Dict[str, str]] = None) -> BrainOutput:
        os_info = f"OS: {self.system_info.get('os', 'Linux')}, User: {self.system_info.get('username', 'ubuntu')}"
        system_prompt = BRAIN_SYSTEM_PROMPT + f"\n\n{os_info}"
        
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        try:
            response = self.llm_manager.call(messages, temperature=0.1)
            raw_text = response.content
            success, parsed = repair_and_parse_json(raw_text)
            if success and parsed:
                # Validation: check if action is allowed
                allowed_actions = ["system", "browser", "screen", "code", "conversation"]
                action = parsed.get("action", "conversation")
                if action not in allowed_actions:
                    return BrainOutput(action="conversation", response=f"Error: Invalid action '{action}' returned by LLM.")
                
                return normalize_brain_output(parsed)
            
            return BrainOutput(action="conversation", response="Error: LLM failed to return valid JSON.")
        except Exception as e:
            logger.error(f"[Brain] Routing error: {e}")
            return BrainOutput(action="conversation", response="System error in cognitive routing.", confidence=0.0)
