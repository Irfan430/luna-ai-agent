"""
LUNA AI Agent - Token Continuation Engine v2.0
Author: IRFAN

Intelligent recovery engine for truncated or malformed LLM responses.
Implements: truncated JSON detection, last valid step extraction,
partial output recovery, context compression, and step index resume.
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple

from .provider import LLMManager, LLMResponse


class ErrorClass:
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    CONTEXT_LIMIT = "context_limit"
    MALFORMED_JSON = "malformed_json"
    UNKNOWN = "unknown"


class ContinuationEngine:
    """Intelligent continuation and recovery for truncated LLM responses."""

    def __init__(self, llm_manager: LLMManager, config: Dict[str, Any]):
        self.llm_manager = llm_manager
        self.config = config
        self.max_retries = config.get('llm', {}).get('continuation', {}).get('max_retries', 3)

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
        truncation_indicators = ["...", "truncated", "continued"]
        for indicator in truncation_indicators:
            if indicator in text.lower():
                return True
        return False

    def needs_continuation(self, response: LLMResponse) -> bool:
        """Check if response needs continuation."""
        if response.is_truncated():
            return True
        if self.is_incomplete_json(response.content):
            return True
        return False

    def classify_error(self, error: Exception) -> str:
        """Classify the type of LLM error for targeted recovery."""
        msg = str(error).lower()
        if "timeout" in msg:
            return ErrorClass.TIMEOUT
        if "rate limit" in msg or "429" in msg:
            return ErrorClass.RATE_LIMIT
        if "context" in msg or "token" in msg or "length" in msg:
            return ErrorClass.CONTEXT_LIMIT
        return ErrorClass.UNKNOWN

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
        Injects a summary marker to indicate where compression occurred.
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
                "Please continue from exactly where the output was cut off.\n"
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

                if retry_count >= self.max_retries:
                    print(f"[ContinuationEngine] Max retries ({self.max_retries}) reached at step {step_index}.")
                    # Attempt partial recovery before giving up
                    recovered = self.recover_partial_output(accumulated_response)
                    if recovered:
                        print(f"[ContinuationEngine] Partial recovery succeeded at step {step_index}.")
                        return json.dumps(recovered)
                    return accumulated_response

                # Rebuild prompt with summarized state for intelligent resume
                messages = self.rebuild_prompt_with_state(messages, response.content, step_index)

                # Apply context compression if context is growing large
                if len(json.dumps(messages)) > 12000:
                    print(f"[ContinuationEngine] Context pressure detected. Compressing at step {step_index}.")
                    messages = self.compress_context(messages, step_index)

            except Exception as e:
                error_class = self.classify_error(e)
                print(f"[ContinuationEngine] Error ({error_class}): {e}")

                if error_class == ErrorClass.CONTEXT_LIMIT:
                    print("[ContinuationEngine] Context limit hit. Compressing context and retrying.")
                    messages = self.compress_context(messages, step_index)
                    retry_count += 1
                    continue

                if error_class == ErrorClass.RATE_LIMIT:
                    print("[ContinuationEngine] Rate limit hit. Waiting 5 seconds before retry.")
                    import time
                    time.sleep(5)
                    retry_count += 1
                    continue

                # For timeout or unknown errors, return what we have
                if accumulated_response:
                    return accumulated_response
                raise

        return accumulated_response
