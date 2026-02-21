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
        elif action == "deep_plan": action = "code"
        
        return BrainOutput(
            action=action,
            response=str(raw.get("response", "")),
            parameters=raw.get("parameters") if isinstance(raw.get("parameters"), dict) else {},
            thought=str(raw.get("thought", "")),
            confidence=float(raw.get("confidence", 1.0))
        )
    except Exception as e:
        logger.error(f"Normalization error: {e}")
        return BrainOutput(action="conversation", response="I encountered an internal error processing that.", confidence=0.0)

BRAIN_SYSTEM_PROMPT = """You are LUNA, a fast, real-time system companion.
Your goal is to execute user commands immediately with minimal cognitive overhead.

EXECUTION ROUTER:
- If the user wants to chat or ask a question:
  {"action": "conversation", "response": "your helpful response"}

- If the user wants to run a shell command or system task:
  {"action": "system", "parameters": {"command": "the command"}}

- If the user wants to use the browser:
  {"action": "browser", "parameters": {"instruction": "natural language instruction for playwright"}}

- If the user wants to see the screen or analyze UI:
  {"action": "screen", "parameters": {"instruction": "what to look for"}}

- If the user wants to write and execute complex code:
  {"action": "code", "parameters": {"language": "python", "code": "the code", "filename": "script.py"}}

RULES:
1. Output ONLY valid JSON.
2. No multi-step planning. Execute the most logical next step immediately.
3. Be concise. Speed is priority.

Format:
{
  "thought": "brief reasoning",
  "action": "conversation | system | browser | screen | code",
  "parameters": {},
  "response": "message to user",
  "confidence": 1.0
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
                return normalize_brain_output(parsed)
            return normalize_brain_output(raw_text)
        except Exception as e:
            logger.error(f"[Brain] Routing error: {e}")
            return BrainOutput(action="conversation", response="System error in cognitive routing.", confidence=0.0)
