"""
LUNA AI Agent - OpenAI Provider
Author: IRFAN

OpenAI LLM provider implementation.
"""

from typing import Dict, Any, Optional, List
from openai import OpenAI as OpenAIClient
from ..llm_client import LLMClient, LLMResponse


class OpenAIProvider(LLMClient):
    """OpenAI LLM provider."""
    
    def __init__(self, api_key: str, model: str = "gpt-4", 
                 base_url: str = "https://api.openai.com/v1"):
        """Initialize OpenAI provider."""
        super().__init__(api_key, model, base_url)
        self.client = OpenAIClient(api_key=api_key, base_url=base_url)
    
    def chat(self, messages: List[Dict[str, str]], 
             temperature: float = 0.7,
             max_tokens: Optional[int] = None) -> LLMResponse:
        """Send chat request to OpenAI."""
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
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            finish_reason = response.choices[0].finish_reason
            
            return LLMResponse(
                content=content,
                usage=usage,
                finish_reason=finish_reason,
                raw_response=response
            )
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from OpenAI response."""
        json_data = self.extract_json(response)
        if json_data is None:
            raise ValueError(f"Failed to parse JSON from response: {response[:200]}")
        return json_data
