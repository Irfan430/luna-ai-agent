"""
LUNA AI Agent - LLM Client Interface
Author: IRFAN

Abstract interface for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import json


class LLMClient(ABC):
    """Abstract LLM client interface."""
    
    def __init__(self, api_key: str, model: str, base_url: str):
        """Initialize LLM client."""
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], 
             temperature: float = 0.7,
             max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Send chat request to LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dict with 'content', 'usage', 'finish_reason'
        """
        pass
    
    @abstractmethod
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response.
        
        Args:
            response: Raw LLM response text
            
        Returns:
            Parsed JSON dict
        """
        pass
    
    def is_truncated(self, response: Dict[str, Any]) -> bool:
        """Check if response was truncated due to token limit."""
        finish_reason = response.get('finish_reason', '')
        return finish_reason in ['length', 'max_tokens']
    
    def extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from text that may contain markdown code blocks.
        """
        # Try to find JSON in code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                json_text = text[start:end].strip()
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    pass
        
        # Try to parse entire text as JSON
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON object in text
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
        
        return None


class LLMResponse:
    """Structured LLM response."""
    
    def __init__(self, content: str, usage: Dict[str, int], 
                 finish_reason: str, raw_response: Any = None):
        """Initialize LLM response."""
        self.content = content
        self.usage = usage
        self.finish_reason = finish_reason
        self.raw_response = raw_response
    
    def is_truncated(self) -> bool:
        """Check if response was truncated."""
        return self.finish_reason in ['length', 'max_tokens']
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'content': self.content,
            'usage': self.usage,
            'finish_reason': self.finish_reason
        }
