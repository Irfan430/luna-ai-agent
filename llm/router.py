"""
LUNA AI Agent - Unified LLM Routing Layer
Author: IRFAN

Phase 1 Fix: Unified routing layer that classifies every user input
before entering the cognitive loop.

Routing modes:
  - conversation : Simple reply, no planning loop entered.
  - action       : Single deterministic action required.
  - plan         : Multi-step planning loop required.

JSON repair fallback:
  - Detect malformed JSON.
  - Extract first valid JSON block.
  - Retry once.
  - If still invalid → fallback to conversation mode.
"""

import json
import re
import logging
from typing import Dict, Any, Optional, Tuple

from llm.provider import LLMManager

logger = logging.getLogger("luna.llm.router")

# ------------------------------------------------------------------
# Routing prompt
# ------------------------------------------------------------------
ROUTING_SYSTEM_PROMPT = """You are LUNA's routing brain.
Your ONLY job is to classify the user's input and return a JSON object.

Rules:
- If the input is a greeting, question, or conversational statement → mode = "conversation"
- If the input requires a single OS/file/app action → mode = "action"
- If the input requires multiple steps or planning → mode = "plan"

NEVER enter planning for simple greetings like "hello", "hi", "how are you", "thanks".

Output ONLY valid JSON. No prose. No markdown.

Format:
{
  "mode": "conversation | action | plan",
  "response": "<direct reply if mode is conversation, empty string otherwise>",
  "steps": []
}
"""


# ------------------------------------------------------------------
# JSON repair utilities
# ------------------------------------------------------------------

def _extract_first_json_block(text: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to extract the first valid JSON object from arbitrary text.
    Handles markdown code fences, inline JSON, and partial objects.
    """
    # 1. Markdown code fence
    fence_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # 2. Whole text
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # 3. Outermost braces
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None


def repair_and_parse_json(text: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Attempt to parse JSON from LLM output with repair fallback.
    Returns (success, parsed_dict).
    """
    result = _extract_first_json_block(text)
    if result is not None:
        return True, result

    # Repair attempt: strip common LLM artifacts
    cleaned = text.strip()
    cleaned = re.sub(r'^[^{]*', '', cleaned)   # drop leading non-JSON text
    cleaned = re.sub(r'[^}]*$', '', cleaned)   # drop trailing non-JSON text
    result = _extract_first_json_block(cleaned)
    if result is not None:
        logger.info("[JSONRepair] Recovered JSON after stripping artifacts.")
        return True, result

    logger.warning("[JSONRepair] Could not recover valid JSON. Falling back to conversation mode.")
    return False, None


# ------------------------------------------------------------------
# Router
# ------------------------------------------------------------------

class LLMRouter:
    """
    Unified LLM routing layer.

    Before entering the cognitive loop, every user input is sent here.
    The router returns a routing decision dict:
      {
        "mode": "conversation | action | plan",
        "response": "<text if conversation>",
        "steps": []
      }
    """

    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager

    def route(self, user_input: str) -> Dict[str, Any]:
        """
        Classify user input and return routing decision.
        Falls back to conversation mode on any failure.
        """
        messages = [
            {"role": "system", "content": ROUTING_SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]

        try:
            response = self.llm_manager.call(messages, temperature=0.2)
            raw_text = response.content

            success, parsed = repair_and_parse_json(raw_text)

            if success and parsed:
                mode = parsed.get("mode", "conversation")
                if mode not in ("conversation", "action", "plan"):
                    logger.warning(f"[Router] Unknown mode '{mode}'. Defaulting to conversation.")
                    mode = "conversation"
                return {
                    "mode": mode,
                    "response": parsed.get("response", ""),
                    "steps": parsed.get("steps", []),
                }

            # JSON repair failed — fallback
            logger.warning("[Router] JSON repair failed. Falling back to conversation mode.")
            return {
                "mode": "conversation",
                "response": raw_text.strip(),
                "steps": [],
            }

        except Exception as e:
            logger.error(f"[Router] Routing error: {e}. Defaulting to conversation mode.")
            return {
                "mode": "conversation",
                "response": "I'm here. How can I help you?",
                "steps": [],
            }
