"""
LUNA AI Agent - Token Continuation Handler
Author: IRFAN

Handles token limit exceeded scenarios with auto-resume.
"""

from typing import Dict, Any, List, Optional
from .llm_manager import LLMManager
from .llm_client import LLMResponse
from config.config_loader import get_config


class ContinuationHandler:
    """Handle token limit exceeded with continuation."""
    
    def __init__(self, llm_manager: LLMManager):
        """Initialize continuation handler."""
        self.llm_manager = llm_manager
        self.config = get_config()
        self.max_retries = self.config.get("llm.continuation.max_retries", 3)
    
    def is_incomplete_json(self, text: str) -> bool:
        """Check if JSON response is incomplete."""
        text = text.strip()
        
        # Check for unclosed braces
        open_braces = text.count('{')
        close_braces = text.count('}')
        if open_braces > close_braces:
            return True
        
        # Check for unclosed brackets
        open_brackets = text.count('[')
        close_brackets = text.count(']')
        if open_brackets > close_brackets:
            return True
        
        # Check for truncation indicators
        truncation_indicators = [
            "...",
            "truncated",
            "continued",
        ]
        for indicator in truncation_indicators:
            if indicator in text.lower():
                return True
        
        return False
    
    def needs_continuation(self, response: LLMResponse) -> bool:
        """Check if response needs continuation."""
        # Check if truncated by token limit
        if response.is_truncated():
            return True
        
        # Check if JSON is incomplete
        if self.is_incomplete_json(response.content):
            return True
        
        return False
    
    def continue_response(self, messages: List[Dict[str, str]], 
                         partial_response: str,
                         temperature: float = 0.7) -> Optional[str]:
        """
        Continue from partial response.
        
        Args:
            messages: Original message history
            partial_response: Incomplete response to continue from
            temperature: Sampling temperature
            
        Returns:
            Continued response or None if failed
        """
        continuation_prompt = f"""The previous response was truncated. Here's what was generated so far:

{partial_response}

Please continue from where it left off and complete the response. If it was JSON, complete the JSON structure properly."""
        
        # Add continuation prompt to messages
        continue_messages = messages + [
            {"role": "assistant", "content": partial_response},
            {"role": "user", "content": continuation_prompt}
        ]
        
        try:
            response = self.llm_manager.chat(continue_messages, temperature=temperature)
            return response.content
        except Exception as e:
            print(f"Continuation failed: {e}")
            return None
    
    def chat_with_continuation(self, messages: List[Dict[str, str]], 
                               temperature: float = 0.7,
                               max_tokens: Optional[int] = None) -> str:
        """
        Send chat request with automatic continuation on truncation.
        
        Args:
            messages: Message history
            temperature: Sampling temperature
            max_tokens: Maximum tokens per request
            
        Returns:
            Complete response (possibly continued)
        """
        retry_count = 0
        accumulated_response = ""
        
        while retry_count < self.max_retries:
            try:
                response = self.llm_manager.chat(messages, temperature, max_tokens)
                
                if not self.needs_continuation(response):
                    # Response is complete
                    return response.content
                
                # Response needs continuation
                accumulated_response += response.content
                retry_count += 1
                
                if retry_count >= self.max_retries:
                    print(f"Max continuation retries ({self.max_retries}) reached")
                    return accumulated_response
                
                # Continue from partial response
                continued = self.continue_response(messages, accumulated_response, temperature)
                if continued:
                    accumulated_response += continued
                    # Check if continuation is complete
                    if not self.is_incomplete_json(accumulated_response):
                        return accumulated_response
                else:
                    return accumulated_response
                    
            except Exception as e:
                print(f"Chat with continuation error: {e}")
                if accumulated_response:
                    return accumulated_response
                raise
        
        return accumulated_response
