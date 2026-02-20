"""
LUNA AI Agent - Intent Routing Layer v8.0
Author: IRFAN

Phase 2 & 3: Speed-First Hybrid Execution & Brain Normalization
  - Classify request into: conversation, direct_action, deep_plan.
  - conversation → no planning loop.
  - direct_action → single execution pass.
  - deep_plan → iterative cognitive loop.
  - BrainOutput model for normalized LLM responses.
  - Strict normalization logic to prevent crashes.
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
    mode: str = "conversation"
    response: str = ""
    action: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0

def normalize_brain_output(raw: Any) -> BrainOutput:
    """Normalize any LLM output into a strict BrainOutput model. Never crashes."""
    if isinstance(raw, str):
        # If it's just a string, treat as conversation
        return BrainOutput(mode="conversation", response=raw.strip(), confidence=0.5)
    
    if isinstance(raw, (int, float)):
        # If it's numeric, treat as conversation
        return BrainOutput(mode="conversation", response=str(raw), confidence=0.5)

    if not isinstance(raw, dict):
        # Fallback for any other type
        return BrainOutput(mode="conversation", response=str(raw), confidence=0.0)

    # Map fields safely from dictionary
    try:
        mode = str(raw.get("mode", "conversation")).lower()
        if mode not in ["conversation", "direct_action", "deep_plan"]:
            # Simple heuristic for mode if not explicitly provided
            if raw.get("action"): mode = "direct_action"
            elif raw.get("steps"): mode = "deep_plan"
            else: mode = "conversation"
            
        return BrainOutput(
            mode=mode,
            response=str(raw.get("response", "")),
            action=raw.get("action"),
            parameters=raw.get("parameters") if isinstance(raw.get("parameters"), dict) else {},
            steps=raw.get("steps") if isinstance(raw.get("steps"), list) else [],
            confidence=float(raw.get("confidence", 0.0))
        )
    except Exception as e:
        logger.error(f"Normalization error: {e}")
        return BrainOutput(mode="conversation", response="I encountered an internal error processing that.", confidence=0.0)

# ------------------------------------------------------------------
# Unified Brain Prompt
# ------------------------------------------------------------------
BRAIN_SYSTEM_PROMPT = """You are LUNA's cognitive brain.
Your job is to classify the user's input and decide the execution mode.

Modes:
- "conversation": For greetings, simple questions, or general talk.
- "direct_action": For a single, immediate OS/file/app task (e.g., "open chrome", "create file x.txt").
- "deep_plan": For complex, multi-step goals requiring reasoning.

Rules:
- If simple command → direct_action
- If short chat → conversation
- Only explicit complex tasks → deep_plan

Output ONLY valid JSON.

Format:
{
  "mode": "conversation | direct_action | deep_plan",
  "confidence": 0.0-1.0,
  "response": "string (for conversation)",
  "action": "string (for direct_action)",
  "parameters": {} (for direct_action),
  "steps": [{"action": "string", "parameters": {}, "description": "string"}] (for deep_plan)
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

    def __init__(self, llm_manager: LLMManager, config: Dict[str, Any] = None):
        self.llm_manager = llm_manager
        self.config = config or {}
        self.system_info = self.config.get('system', {})

    def route(self, user_input: str, history: List[Dict[str, str]] = None) -> BrainOutput:
        """Classify input and return normalized BrainOutput."""
        # Inject OS info into brain prompt via config
        os_info = f"Current OS: {self.system_info.get('os', 'Unknown')}, Architecture: {self.system_info.get('architecture', 'Unknown')}, User: {self.system_info.get('username', 'Unknown')}"
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

            # If parsing fails, treat raw text as conversation
            return normalize_brain_output(raw_text)

        except Exception as e:
            logger.error(f"[Brain] Routing error: {e}")
            return BrainOutput(mode="conversation", response="System error in cognitive routing.", confidence=0.0)
