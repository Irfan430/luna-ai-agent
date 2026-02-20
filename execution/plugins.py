"""
LUNA AI Agent - Plugin Manager
Author: IRFAN

Dynamic tool discovery and plugin system for LUNA.
"""

import os
import importlib.util
from typing import Dict, Any, List, Optional


class PluginManager:
    """Manages dynamic loading and execution of LUNA plugins."""
    def __init__(self, plugin_dir: str = "plugins"):
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, Any] = {}
        self._load_plugins()

    def _load_plugins(self):
        """Load all plugins from the plugin directory."""
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)
            return

        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                plugin_name = filename[:-3]
                file_path = os.path.join(self.plugin_dir, filename)
                
                spec = importlib.util.spec_from_file_location(plugin_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, "register"):
                        self.plugins[plugin_name] = module.register()
                        print(f"Loaded plugin: {plugin_name}")

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get a list of tools provided by plugins."""
        tools = []
        for name, plugin in self.plugins.items():
            if hasattr(plugin, "get_tools"):
                tools.extend(plugin.get_tools())
        return tools

    def execute_plugin_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a tool from a loaded plugin."""
        for plugin in self.plugins.values():
            if hasattr(plugin, "execute") and tool_name in plugin.get_tool_names():
                return plugin.execute(tool_name, parameters)
        raise ValueError(f"Tool '{tool_name}' not found in any plugin")
