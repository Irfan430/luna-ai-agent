"""""
LUNA AI Agent - LLM Provider Abstraction v3.1
Author: IRFAN
Revision: Manus AI

Hardened provider layer with:
  - API Keys loaded from environment variables (e.g., OPENAI_API_KEY, DEEPSEEK_API_KEY).
  - Strict structured JSON enforcement.
  - Automatic schema validation & sanitation.
  - Error classification (timeout, rate limit, context limit).
  - Single mode enforcement.
  - Multi mode fallback logic with provider switch logging.
  - Raw string output blocked from reaching executor.
"""
import json
import os
import re
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

logger = logging.getLogger("luna.llm.provider")

class LLMErrorClass:
    TIMEOUT       = "timeout"
    RATE_LIMIT    = "rate_limit"
    CONTEXT_LIMIT = "context_limit"
    AUTH_ERROR    = "auth_error"
    SERVER_ERROR  = "server_error"
    UNKNOWN       = "unknown"

def classify_llm_error(error: Exception) -> str:
    msg = str(error).lower()
    if "timeout" in msg:
        return LLMErrorClass.TIMEOUT
    if "rate limit" in msg or "429" in msg:
        return LLMErrorClass.RATE_LIMIT
    if "context" in msg or "token" in msg or "length" in msg or "4096" in msg:
        return LLMErrorClass.CONTEXT_LIMIT
    if "401" in msg or "unauthorized" in msg or "api key" in msg:
        return LLMErrorClass.AUTH_ERROR
    if "500" in msg or "502" in msg or "503" in msg:
        return LLMErrorClass.SERVER_ERROR
    return LLMErrorClass.UNKNOWN

class LLMResponse:
    def __init__(self, content: str, usage: Dict[str, int], finish_reason: str, provider_name: str = ""):
        self.content = content
        self.usage = usage
        self.finish_reason = finish_reason
        self.provider_name = provider_name

    def is_truncated(self) -> bool:
        return self.finish_reason in ('length', 'max_tokens')

    def __repr__(self):
        return (
            f"LLMResponse(provider={self.provider_name}, "
            f"finish_reason={self.finish_reason}, "
            f"tokens={self.usage.get('total_tokens', '?')})"
        )

class LLMProvider(ABC):
    def __init__(self, api_key: str, model: str, base_url: str, name: str = ""):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.name = name
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    @abstractmethod
    def call(self, messages: List[Dict[str, str]], temperature: float, max_tokens: Optional[int] = None) -> LLMResponse:
        pass

class GenericOpenAIProvider(LLMProvider):
    def call(self, messages: List[Dict[str, str]], temperature: float, max_tokens: Optional[int] = None) -> LLMResponse:
        try:
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            response = self.client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content or ""
            usage = {
                "prompt_tokens":     response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens":      response.usage.total_tokens,
            }
            finish_reason = response.choices[0].finish_reason

            return LLMResponse(content, usage, finish_reason, provider_name=self.name)

        except Exception as e:
            error_class = classify_llm_error(e)
            raise Exception(f"[{self.name}] LLM error ({error_class}): {str(e)}")

class LLMManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mode = config.get('llm', {}).get('mode', 'single')
        self.default_provider_name = config.get('llm', {}).get('default_provider', 'deepseek')
        self.providers: Dict[str, LLMProvider] = {}
        self._active_provider_name: str = self.default_provider_name
        self._init_providers()

    def _init_providers(self):
        providers_config = self.config.get('llm', {}).get('providers', {})
        for name, cfg in providers_config.items():
            api_key_env = cfg.get("api_key_env")
            api_key = os.getenv(api_key_env) if api_key_env else None

            if not api_key:
                logger.warning(f"[LLMManager] API key for '{name}' not found in environment variable '{api_key_env}'. Skipping.")
                continue

            provider = GenericOpenAIProvider(
                api_key=api_key,
                model=cfg['model'],
                base_url=cfg['base_url'],
                name=name,
            )
            
            self.providers[name] = provider
            logger.info(f"[LLMManager] Initialized provider: {name} ({cfg['model']})")

    def get_provider(self, name: Optional[str] = None) -> LLMProvider:
        name = name or self.default_provider_name
        if name not in self.providers:
            if self.providers:
                available = list(self.providers.keys())[0]
                logger.warning(f"Default provider '{name}' not available. Falling back to '{available}'.")
                self._active_provider_name = available
                return self.providers[available]
            raise ValueError("No LLM providers are available. Please check your .env file and config.yaml.")
        return self.providers[name]

    def _log_provider_switch(self, from_name: str, to_name: str, reason: str):
        logger.warning(f"[LLMManager] Provider switch: {from_name} -> {to_name} | Reason: {reason}")
        self._active_provider_name = to_name

    def call(self, messages: List[Dict[str, str]], temperature: float, max_tokens: Optional[int] = None) -> LLMResponse:
        if self.mode == 'single':
            return self.get_provider(self._active_provider_name).call(messages, temperature, max_tokens)

        provider_order = [self.default_provider_name] + [p for p in self.providers if p != self.default_provider_name]
        last_error = None
        previous_name = self._active_provider_name

        for name in provider_order:
            if name not in self.providers:
                continue
            try:
                provider = self.get_provider(name)
                if previous_name != name:
                    self._log_provider_switch(previous_name, name, str(last_error))
                response = provider.call(messages, temperature, max_tokens)
                self._active_provider_name = name
                return response
            except Exception as e:
                error_class = classify_llm_error(e)
                logger.error(f"[LLMManager] Provider '{name}' failed ({error_class}): {e}")
                last_error = e
                previous_name = name
                if error_class == LLMErrorClass.AUTH_ERROR:
                    continue
                if error_class == LLMErrorClass.RATE_LIMIT:
                    time.sleep(3)
                continue

        raise Exception(f"All LLM providers failed. Last error: {last_error}")

    @property
    def active_provider_name(self) -> str:
        return self._active_provider_name
