"""
LUNA AI Agent - Unified LLM Brain & Routing Layer
Author: IRFAN

Phase 1 Architectural Stabilization:
  - Unified LLM Brain contract: always returns mode, confidence, response, and steps.
  - Routing modes: conversation, action, plan.
  - JSON repair fallback (1 retry max).
  - No 'action' key required if mode == conversation.
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
- "action": For a single, immediate OS/file/app task.
- "plan": For complex, multi-step goals.

Rules:
- If mode is "conversation", provide a direct "response". "steps" can be empty.
- If mode is "action" or "plan", "steps" must contain the structured actions.
- NEVER enter planning for simple greetings.

Output ONLY valid JSON.

Format:
{
  "mode": "conversation | action | plan",
  "confidence": 0.0-1.0,
  "response": "string",
  "steps": [
    {
      "action": "string",
      "parameters": {},
      "description": "string"
    }
  ]
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
            response = self.llm_manager.call(messages, temperature=0.2)
            raw_text = response.content

            success, parsed = repair_and_parse_json(raw_text)

            if success and parsed:
                # Ensure all required keys exist per contract
                return {
                    "mode": parsed.get("mode", "conversation"),
                    "confidence": float(parsed.get("confidence", 0.0)),
                    "response": parsed.get("response", ""),
                    "steps": parsed.get("steps", []),
                }

            # Fallback if parsing fails after repair
            return {
                "mode": "conversation",
                "confidence": 0.5,
                "response": raw_text.strip() if raw_text else "I encountered an error processing that.",
                "steps": [],
            }

        except Exception as e:
            logger.error(f"[Brain] Routing error: {e}")
            return {
                "mode": "conversation",
                "confidence": 0.0,
                "response": "System error in cognitive routing.",
                "steps": [],
            }
