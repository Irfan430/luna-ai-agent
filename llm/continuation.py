"""
LUNA AI Agent - Token Continuation Engine
Author: IRFAN

Handles truncated LLM responses and ensures complete JSON/text output.
"""

import json
from typing import Dict, Any, List, Optional
from .provider import LLMManager, LLMResponse


class ContinuationEngine:
    """Intelligent continuation for truncated LLM responses."""
    def __init__(self, llm_manager: LLMManager, config: Dict[str, Any]):
        self.llm_manager = llm_manager
        self.config = config
        self.max_retries = config.get('llm', {}).get('continuation', {}).get('max_retries', 3)

    def is_incomplete_json(self, text: str) -> bool:
        """Check if JSON response is incomplete."""
        text = text.strip()
        # Check for unclosed braces or brackets
        open_braces = text.count('{')
        close_braces = text.count('}')
        open_brackets = text.count('[')
        close_brackets = text.count(']')
        
        if open_braces > close_braces or open_brackets > close_brackets:
            return True
        
        # Check for truncation indicators
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

    def call_with_continuation(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: Optional[int] = None) -> str:
        """Send chat request with automatic continuation on truncation."""
        retry_count = 0
        accumulated_response = ""
        
        while retry_count < self.max_retries:
            try:
                response = self.llm_manager.call(messages, temperature, max_tokens)
                
                if not self.needs_continuation(response):
                    return accumulated_response + response.content
                
                # Response needs continuation
                accumulated_response += response.content
                retry_count += 1
                
                if retry_count >= self.max_retries:
                    print(f"Max continuation retries ({self.max_retries}) reached")
                    return accumulated_response
                
                # Add continuation prompt to messages
                messages = messages + [
                    {"role": "assistant", "content": response.content},
                    {"role": "user", "content": "The previous response was truncated. Please continue from where it left off and complete the response properly."}
                ]
                
            except Exception as e:
                print(f"Continuation error: {e}")
                if accumulated_response:
                    return accumulated_response
                raise
        
        return accumulated_response
