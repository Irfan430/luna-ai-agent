"""
LUNA AI Agent - Local LLM Provider
Author: IRFAN

Local LLM provider implementation (Ollama compatible).
"""

from typing import Dict, Any, Optional, List
from openai import OpenAI
from ..llm_client import LLMClient, LLMResponse


class LocalProvider(LLMClient):
    """Local LLM provider (Ollama compatible)."""
    
    def __init__(self, api_key: str = "", model: str = "llama3", 
                 base_url: str = "http://localhost:11434"):
        """Initialize Local provider."""
        super().__init__(api_key, model, base_url)
        # Ollama doesn't require API key but OpenAI client needs one
        self.client = OpenAI(api_key="ollama", base_url=f"{base_url}/v1")
    
    def chat(self, messages: List[Dict[str, str]], 
             temperature: float = 0.7,
             max_tokens: Optional[int] = None) -> LLMResponse:
        """Send chat request to local LLM."""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature
            }
            
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            
            response = self.client.chat.completions.create(**kwargs)
            
            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }
            finish_reason = response.choices[0].finish_reason if response.choices[0].finish_reason else "stop"
            
            return LLMResponse(
                content=content,
                usage=usage,
                finish_reason=finish_reason,
                raw_response=response
            )
            
        except Exception as e:
            raise Exception(f"Local LLM error: {str(e)}")
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from local LLM response."""
        json_data = self.extract_json(response)
        if json_data is None:
            raise ValueError(f"Failed to parse JSON from response: {response[:200]}")
        return json_data
