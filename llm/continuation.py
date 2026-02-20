"""
LUNA AI Agent - Token Continuation Engine v3.0
Author: IRFAN

Intelligent recovery engine for truncated or malformed LLM responses.
Implements: truncated JSON detection, last valid step extraction,
partial output recovery, context compression, and step index resume.
"""

import json
import re
import time
from typing import Dict, Any, List, Optional, Tuple

from .provider import LLMManager, LLMResponse, LLMErrorClass


class ContinuationEngine:
    """Intelligent continuation and recovery for truncated LLM responses."""

    def __init__(self, llm_manager: LLMManager, config: Dict[str, Any]):
        self.llm_manager = llm_manager
        self.config = config
        self.max_retries = config.get('llm', {}).get('continuation', {}).get('max_retries', 3)
        self.continuation_prompt = config.get('prompts', {}).get('continuation', "Please continue your previous response exactly where you left off.")

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------

    def is_incomplete_json(self, text: str) -> bool:
        """Check if JSON response is incomplete (unclosed braces/brackets)."""
        text = text.strip()
        open_braces = text.count('{')
        close_braces = text.count('}')
        open_brackets = text.count('[')
        close_brackets = text.count(']')
        
        if open_braces > close_braces or open_brackets > close_brackets:
            return True
            
        # Check if it ends abruptly (e.g., in the middle of a key or value)
        if re.search(r'[:,"\[\{]\s*$', text):
            return True
            
        truncation_indicators = ["...", "truncated", "continued"]
        for indicator in truncation_indicators:
            if indicator in text.lower()[-20:]: # Only check the end
                return True
        return False

    def needs_continuation(self, response: LLMResponse) -> bool:
        """Check if response needs continuation."""
        if response.is_truncated():
            return True
        if self.is_incomplete_json(response.content):
            return True
        return False

    # ------------------------------------------------------------------
    # Partial output recovery
    # ------------------------------------------------------------------

    def extract_last_valid_step(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract the last valid JSON object from a partially truncated response.
        Scans backwards through the text to find the deepest complete JSON block.
        """
        # Find all JSON-like blocks
        candidates = []
        for match in re.finditer(r'\{', text):
            start = match.start()
            depth = 0
            for i in range(start, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        candidate = text[start:i + 1]
                        try:
                            parsed = json.loads(candidate)
                            candidates.append(parsed)
                        except json.JSONDecodeError:
                            pass
                        break
        return candidates[-1] if candidates else None

    def recover_partial_output(self, accumulated: str) -> Optional[Dict[str, Any]]:
        """Attempt to recover a usable step from partial output."""
        # Try direct parse first
        try:
            return json.loads(accumulated.strip())
        except json.JSONDecodeError:
            pass
        # Try to extract last valid step
        return self.extract_last_valid_step(accumulated)

    # ------------------------------------------------------------------
    # Context compression
    # ------------------------------------------------------------------

    def compress_context(self, messages: List[Dict[str, str]], step_index: int) -> List[Dict[str, str]]:
        """
        Compress conversation context to reduce token pressure.
        Retains system messages, the original goal, and the last few exchanges.
        """
        system_messages = [m for m in messages if m["role"] == "system"]
        user_messages = [m for m in messages if m["role"] != "system"]

        # Keep only the last 4 non-system messages to reduce context
        recent = user_messages[-4:] if len(user_messages) > 4 else user_messages

        compressed_summary = {
            "role": "system",
            "content": (
                f"[CONTEXT COMPRESSED at step {step_index}] "
                "Earlier conversation history has been summarized. "
                "Continue execution from the current state. "
                "Focus on completing the goal with the remaining steps."
            )
        }

        return system_messages + [compressed_summary] + recent

    # ------------------------------------------------------------------
    # Prompt reconstruction
    # ------------------------------------------------------------------

    def rebuild_prompt_with_state(
        self,
        messages: List[Dict[str, str]],
        partial_content: str,
        step_index: int
    ) -> List[Dict[str, str]]:
        """
        Reconstruct a continuation prompt with summarized state.
        Injects the partial response and step index for targeted resume.
        """
        continuation_prompt = {
            "role": "user",
            "content": (
                f"[CONTINUATION REQUEST — Step Index: {step_index}]\n"
                f"The previous response was truncated or incomplete.\n"
                f"Partial output received:\n{partial_content}\n\n"
                f"{self.continuation_prompt}\n"
                "If the output was JSON, complete the JSON structure properly.\n"
                "Do NOT restart from the beginning. Resume from the last valid state.\n"
                "Output ONLY the continuation — no preamble."
            )
        }
        return messages + [
            {"role": "assistant", "content": partial_content},
            continuation_prompt
        ]

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def call_with_continuation(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Send chat request with automatic intelligent continuation on truncation.
        Implements: partial recovery, context compression, and step index resume.
        """
        retry_count = 0
        accumulated_response = ""
        step_index = 0

        while retry_count < self.max_retries:
            try:
                response = self.llm_manager.call(messages, temperature, max_tokens)

                if not self.needs_continuation(response):
                    return accumulated_response + response.content

                # Response needs continuation
                accumulated_response += response.content
                retry_count += 1
                step_index += 1

                print(f"[ContinuationEngine] Response truncated. Requesting continuation {retry_count}/{self.max_retries}...")

                # Rebuild prompt with summarized state for intelligent resume
                messages = self.rebuild_prompt_with_state(messages, response.content, step_index)

                # Apply context compression if context is growing large
                if len(json.dumps(messages)) > 12000:
                    print(f"[ContinuationEngine] Context pressure detected. Compressing at step {step_index}.")
                    messages = self.compress_context(messages, step_index)

            except Exception as e:
                # Error handling is now delegated to LLMManager, but we catch it here for continuation logic
                msg = str(e).lower()
                if "context" in msg or "token" in msg or "length" in msg:
                    print("[ContinuationEngine] Context limit hit. Compressing context and retrying.")
                    messages = self.compress_context(messages, step_index)
                    retry_count += 1
                    continue
                
                if "rate limit" in msg:
                    print("[ContinuationEngine] Rate limit hit. Waiting 5 seconds before retry.")
                    time.sleep(5)
                    retry_count += 1
                    continue

                # For other errors, return what we have if any
                if accumulated_response:
                    return accumulated_response
                raise

        print(f"[ContinuationEngine] Max retries ({self.max_retries}) reached. Returning accumulated response.")
        return accumulated_response
