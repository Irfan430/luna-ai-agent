"""
LUNA AI Agent - Intent Routing Layer v6.0
Author: IRFAN

Phase 1 Intent Routing Fix:
  - Classify request into: conversation, direct_action, complex_plan.
  - conversation → no planning loop.
  - direct_action → single execution pass.
  - complex_plan → iterative cognitive loop.
  - JSON repair fallback (1 retry max).
"""

import json
import re
import logging
from typing import Dict, Any, Optional, Tuple, List

from llm.provider import LLMManager

logger = logging.getLogger("luna.llm.router")

# ------------------------------------------------------------------
# Unified Brain Prompt
# ------------------------------------------------------------------
BRAIN_SYSTEM_PROMPT = """You are LUNA's cognitive brain.
Your job is to classify the user's input and decide the execution mode.

Modes:
- "conversation": For greetings, simple questions, or general talk.
- "direct_action": For a single, immediate OS/file/app task (e.g., "open chrome", "create file x.txt").
- "complex_plan": For complex, multi-step goals requiring reasoning.

Rules:
- If mode is "conversation", provide a direct "response".
- If mode is "direct_action", provide the "action" and "parameters".
- If mode is "complex_plan", provide the initial "steps".

Output ONLY valid JSON.

Format:
{
  "mode": "conversation | direct_action | complex_plan",
  "confidence": 0.0-1.0,
  "response": "string (for conversation)",
  "action": "string (for direct_action)",
  "parameters": {} (for direct_action),
  "steps": [
    {
      "action": "string",
      "parameters": {},
      "description": "string"
    }
  ] (for complex_plan)
}
"""

# ------------------------------------------------------------------
# JSON repair utilities
# ------------------------------------------------------------------

def _extract_first_json_block(text: str) -> Optional[Dict[str, Any]]:
    """Extract the first valid JSON object from arbitrary text."""
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
    """Attempt to parse JSON with 1 repair retry fallback."""
    result = _extract_first_json_block(text)
    if result is not None:
        return True, result

    # Repair attempt: strip common artifacts
    cleaned = text.strip()
    cleaned = re.sub(r'^[^{]*', '', cleaned)
    cleaned = re.sub(r'[^}]*$', '', cleaned)
    result = _extract_first_json_block(cleaned)
    if result is not None:
        return True, result

    return False, None

# ------------------------------------------------------------------
# Router / Brain
# ------------------------------------------------------------------

class LLMRouter:
    """Unified LLM Brain routing layer."""

    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager

    def route(self, user_input: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Classify input and return unified brain decision."""
        messages = [{"role": "system", "content": BRAIN_SYSTEM_PROMPT}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_input})

        try:
            response = self.llm_manager.call(messages, temperature=0.1)
            raw_text = response.content

            success, parsed = repair_and_parse_json(raw_text)

            if success and parsed:
                return {
                    "mode": parsed.get("mode", "conversation"),
                    "confidence": float(parsed.get("confidence", 0.0)),
                    "response": parsed.get("response", ""),
                    "action": parsed.get("action", ""),
                    "parameters": parsed.get("parameters", {}),
                    "steps": parsed.get("steps", []),
                }

            return {
                "mode": "conversation",
                "confidence": 0.5,
                "response": raw_text.strip() if raw_text else "I encountered an error processing that.",
                "action": "",
                "parameters": {},
                "steps": [],
            }

        except Exception as e:
            logger.error(f"[Brain] Routing error: {e}")
            return {
                "mode": "conversation",
                "confidence": 0.0,
                "response": "System error in cognitive routing.",
                "action": "",
                "parameters": {},
                "steps": [],
            }
