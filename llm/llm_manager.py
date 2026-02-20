"""
LUNA AI Agent - LLM Manager
Author: IRFAN

Manages LLM provider selection and fallback.
"""

from typing import Dict, Any, Optional, List
from .llm_client import LLMClient, LLMResponse
from .providers.deepseek import DeepSeekProvider
from .providers.openrouter import OpenRouterProvider
from .providers.openai import OpenAIProvider
from .providers.local import LocalProvider
from config.config_loader import get_config


class LLMManager:
    """LLM provider manager with single/multi mode support."""
    
    def __init__(self):
        """Initialize LLM manager."""
        self.config = get_config()
        self.mode = self.config.get_llm_mode()
        self.default_provider_name = self.config.get_default_provider()
        self.providers: Dict[str, LLMClient] = {}
        self._initialize_providers()
    
    def _initialize_providers(self) -> None:
        """Initialize configured providers."""
        llm_config = self.config.get_llm_config()
        providers_config = llm_config.get("providers", {})
        
        provider_classes = {
            "deepseek": DeepSeekProvider,
            "openrouter": OpenRouterProvider,
            "openai": OpenAIProvider,
            "local": LocalProvider
        }
        
        for provider_name, provider_config in providers_config.items():
            if provider_name in provider_classes:
                try:
                    provider_class = provider_classes[provider_name]
                    self.providers[provider_name] = provider_class(
                        api_key=provider_config.get("api_key", ""),
                        model=provider_config.get("model", ""),
                        base_url=provider_config.get("base_url", "")
                    )
                except Exception as e:
                    print(f"Warning: Failed to initialize {provider_name}: {e}")
    
    def get_provider(self, provider_name: Optional[str] = None) -> LLMClient:
        """Get LLM provider by name or default."""
        if provider_name is None:
            provider_name = self.default_provider_name
        
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not configured or initialized")
        
        return self.providers[provider_name]
    
    def chat(self, messages: List[Dict[str, str]], 
             temperature: float = 0.7,
             max_tokens: Optional[int] = None,
             provider_name: Optional[str] = None) -> LLMResponse:
        """
        Send chat request with fallback support in multi mode.
        """
        if self.mode == "single":
            # Single mode: use only default provider
            provider = self.get_provider(provider_name)
            return provider.chat(messages, temperature, max_tokens)
        
        else:
            # Multi mode: try default first, then fallback
            provider_order = [self.default_provider_name] + [
                p for p in self.providers.keys() 
                if p != self.default_provider_name
            ]
            
            last_error = None
            for prov_name in provider_order:
                try:
                    provider = self.get_provider(prov_name)
                    return provider.chat(messages, temperature, max_tokens)
                except Exception as e:
                    last_error = e
                    print(f"Provider {prov_name} failed: {e}")
                    continue
            
            raise Exception(f"All providers failed. Last error: {last_error}")
    
    def get_active_provider_name(self) -> str:
        """Get the name of the currently active provider."""
        return self.default_provider_name
