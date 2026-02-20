"""
LUNA AI Agent - Configuration Loader
Author: IRFAN

Loads and manages configuration from config.yaml.
"""

import yaml
import os
from typing import Dict, Any, Optional


class ConfigLoader:
    """Configuration loader and manager."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize config loader."""
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> None:
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        Example: get("llm.mode") returns config["llm"]["mode"]
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        return self.config.get("llm", {})
    
    def get_safety_config(self) -> Dict[str, Any]:
        """Get safety configuration."""
        return self.config.get("safety", {})
    
    def get_agent_config(self) -> Dict[str, Any]:
        """Get agent configuration."""
        return self.config.get("agent", {})
    
    def get_gui_config(self) -> Dict[str, Any]:
        """Get GUI configuration."""
        return self.config.get("gui", {})
    
    def get_voice_config(self) -> Dict[str, Any]:
        """Get voice configuration."""
        return self.config.get("voice", {})
    
    def get_provider_config(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get specific provider configuration."""
        providers = self.get("llm.providers", {})
        return providers.get(provider)
    
    def get_default_provider(self) -> str:
        """Get default LLM provider."""
        return self.get("llm.default_provider", "deepseek")
    
    def get_llm_mode(self) -> str:
        """Get LLM mode (single or multi)."""
        return self.get("llm.mode", "single")


# Global config instance
_config_instance: Optional[ConfigLoader] = None


def get_config(config_path: str = "config.yaml") -> ConfigLoader:
    """Get global config instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader(config_path)
    return _config_instance
