"""
LUNA AI Agent - LLM Provider Abstraction
Author: IRFAN

Abstract interface and provider implementations for LLM services.
"""

import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from openai import OpenAI


class LLMResponse:
    """Structured LLM response."""
    def __init__(self, content: str, usage: Dict[str, int], finish_reason: str):
        self.content = content
        self.usage = usage
        self.finish_reason = finish_reason

    def is_truncated(self) -> bool:
        return self.finish_reason in ['length', 'max_tokens']


class LLMProvider(ABC):
    """Abstract LLM provider interface."""
    def __init__(self, api_key: str, model: str, base_url: str):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    @abstractmethod
    def call(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: Optional[int] = None) -> LLMResponse:
        pass

    def extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from text that may contain markdown code blocks."""
        # Try to find JSON in code blocks
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
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


class GenericOpenAIProvider(LLMProvider):
    """Generic OpenAI-compatible provider."""
    def call(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: Optional[int] = None) -> LLMResponse:
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
            
            return LLMResponse(content, usage, finish_reason)
        except Exception as e:
            raise Exception(f"LLM Provider error: {str(e)}")


class LLMManager:
    """Manages LLM provider selection and fallback."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mode = config.get('llm', {}).get('mode', 'single')
        self.default_provider_name = config.get('llm', {}).get('default_provider', 'deepseek')
        self.providers: Dict[str, LLMProvider] = {}
        self._init_providers()

    def _init_providers(self):
        providers_config = self.config.get('llm', {}).get('providers', {})
        for name, cfg in providers_config.items():
            if cfg.get('api_key'):
                self.providers[name] = GenericOpenAIProvider(
                    api_key=cfg['api_key'],
                    model=cfg['model'],
                    base_url=cfg['base_url']
                )

    def get_provider(self, name: Optional[str] = None) -> LLMProvider:
        name = name or self.default_provider_name
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' not configured or initialized")
        return self.providers[name]

    def call(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: Optional[int] = None) -> LLMResponse:
        if self.mode == 'single':
            return self.get_provider().call(messages, temperature, max_tokens)
        
        # Multi-mode fallback
        provider_order = [self.default_provider_name] + [p for p in self.providers if p != self.default_provider_name]
        last_error = None
        for name in provider_order:
            try:
                return self.get_provider(name).call(messages, temperature, max_tokens)
            except Exception as e:
                last_error = e
                continue
        raise Exception(f"All LLM providers failed. Last error: {last_error}")
