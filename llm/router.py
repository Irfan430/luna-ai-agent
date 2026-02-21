"""
LUNA AI Agent - Cognitive Router v10.0
Author: IRFAN

Structural Stabilization Refactor:
  - Strict JSON output enforcement (No LUNA Thought in output).
  - Centralized action routing mapping.
  - Multi-modal vision support (Screen/Physical).
"""

import json
import logging
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("luna.llm.router")

@dataclass
class BrainOutput:
    """Strict contract for LUNA's cognitive brain output."""
    action: str = "conversation"
    response: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    thought: str = ""
    confidence: float = 1.0

def normalize_brain_output(data: Any) -> BrainOutput:
    """Normalize LLM output into a strict BrainOutput model."""
    if not isinstance(data, dict):
        return BrainOutput(action="conversation", response=str(data))

    action = str(data.get("action", "conversation")).lower()
    thought = str(data.get("thought", ""))
    response = str(data.get("response", ""))
    
    # Extract parameters
    parameters = data.get("parameters", {})
    if not isinstance(parameters, dict):
        parameters = {}
    
    # Flat structure support: include other keys as parameters
    for k, v in data.items():
        if k not in ["action", "response", "thought", "parameters"]:
            parameters[k] = v

    return BrainOutput(
        action=action,
        response=response,
        parameters=parameters,
        thought=thought
    )

BRAIN_SYSTEM_PROMPT = """
You are LUNA, an advanced Action-based AI Jarvis. 
Your goal is to execute user commands with absolute precision using the provided tools.

### STRICT OUTPUT FORMAT:
You MUST respond ONLY with a valid JSON object. 
DO NOT include "LUNA Thought", internal reasoning, or any text outside the JSON block.

### JSON SCHEMA:
{
  "thought": "Brief internal explanation (will be filtered from user view)",
  "action": "system | browser | screen | physical | code | conversation",
  "response": "Message to user (optional for actions, required for conversation)",
  "parameters": { ... }
}

### ALLOWED ACTIONS & PARAMETERS:
1. "system": Execute shell commands.
   - Parameters: {"command": "string"}
2. "browser": Control persistent browser session via Playwright.
   - Parameters: {"task": "Natural language instruction for browser"}
3. "screen": Vision-based screen analysis or capture.
   - Parameters: {"type": "screenshot"}
4. "physical": Physical mouse/keyboard control.
   - Parameters: {"type": "click | type | press", "x": int, "y": int, "text": "string", "key": "string"}
5. "code": Execute Python code.
   - Parameters: {"code": "string"}
6. "conversation": Respond to user when no action is needed.
   - Parameters: {"response": "string"}

### VISION GUIDELINES:
If the user asks to click something on the screen, first use "screen" action to get a screenshot, then analyze coordinates and use "physical" action.

### FINAL RULE:
NO TEXT OUTSIDE JSON. NO REASONING IN THE RESPONSE STREAM.
"""

def repair_and_parse_json(text: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Extract and parse JSON from LLM output."""
    # Try markdown code block
    fence_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if fence_match:
        try:
            return True, json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try entire text
    try:
        return True, json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    # Try outermost brackets
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return True, json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
            
    return False, None

class LLMRouter:
    """Routes natural language goals to structured LUNA actions."""

    def __init__(self, llm_manager, config: Dict[str, Any] = None):
        self.llm_manager = llm_manager
        self.config = config or {}

    def route(self, goal: str, history: List[Dict[str, str]] = None) -> BrainOutput:
        """Call LLM to determine the next action."""
        messages = [
            {"role": "system", "content": BRAIN_SYSTEM_PROMPT},
        ]
        if history:
            messages.extend(history[-5:]) # Last 5 for context
        
        messages.append({"role": "user", "content": goal})

        try:
            response = self.llm_manager.call(messages, temperature=0.1)
            raw_content = response.content
            
            success, parsed = repair_and_parse_json(raw_content)
            if success and parsed:
                return normalize_brain_output(parsed)
            
            logger.error(f"[Brain] Failed to parse JSON: {raw_content}")
            return BrainOutput(action="conversation", response="I encountered an error parsing my own thoughts.")

        except Exception as e:
            logger.error(f"[Brain] Routing error: {e}")
            return BrainOutput(action="conversation", response="System error in cognitive routing.")
