"""
Prometheus Module -- Plugin System & Loader
"""

import re
import json
from pathlib import Path
from modules.base_module import BaseModule


class PrometheusModule(BaseModule):
    name = "prometheus"
    display_name = "Prometheus"
    icon = "\U0001f9e9"
    description = "Plugin system: discover, list, and manage plugins"
    version = "1.0"
    category = "system"
    enabled = True

    KEYWORDS = [
        "plugins", "list plugins", "install plugin", "plugin",
        "extensions", "add-on", "addon", "plugin manager",
        "load plugin", "unload plugin", "available plugins",
    ]

    def __init__(self):
        self.auto_load = True
        self.plugins_dir = Path(__file__).parent.parent.parent / "plugins"

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        lower = text.lower()

        for kw in self.KEYWORDS:
            if kw in lower:
                return 0.9

        if intent in ("plugin_management", "extensions"):
            return 0.85

        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        lower = text.lower()

        if "list" in lower or "show" in lower or "available" in lower:
            return self._list_plugins()
        elif "install" in lower or "add" in lower:
            return self._install_info(text)
        elif "info" in lower or "details" in lower:
            return self._plugin_details(text)
        else:
            return self._list_plugins()

    def _list_plugins(self) -> dict:
        """Scan the plugins directory and list all available plugins."""
        if not self.plugins_dir.exists():
            return {
                "response": f"Plugins directory not found at: {self.plugins_dir}",
                "data": {"plugins": [], "directory": str(self.plugins_dir)},
                "action": "plugins_list",
            }

        plugins = []
        for item in self.plugins_dir.iterdir():
            if item.is_dir() and not item.name.startswith(("_", ".")):
                plugin_info = {"name": item.name, "path": str(item)}

                # Check for a manifest/config file
                manifest = item / "plugin.json"
                if manifest.exists():
                    try:
                        with open(manifest, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        plugin_info.update({
                            "display_name": data.get("name", item.name),
                            "description": data.get("description", "No description"),
                            "version": data.get("version", "unknown"),
                            "author": data.get("author", "unknown"),
                        })
                    except (json.JSONDecodeError, OSError):
                        plugin_info["description"] = "Invalid manifest"
                else:
                    plugin_info["description"] = "No manifest file"

                # Check if plugin has an entry point
                has_init = (item / "__init__.py").exists()
                has_main = (item / "main.py").exists()
                plugin_info["has_entry_point"] = has_init or has_main

                plugins.append(plugin_info)

        if plugins:
            lines = [f"Found {len(plugins)} plugin(s):"]
            for p in plugins:
                name = p.get("display_name", p["name"])
                desc = p.get("description", "")
                ver = p.get("version", "")
                entry = "ready" if p.get("has_entry_point") else "no entry point"
                lines.append(f"  - {name} v{ver} ({entry}): {desc}")
            response = "\n".join(lines)
        else:
            response = "No plugins found in the plugins directory."

        return {
            "response": response,
            "data": {"plugins": plugins, "directory": str(self.plugins_dir)},
            "action": "plugins_list",
        }

    def _install_info(self, text: str) -> dict:
        return {
            "response": (
                "To install a plugin, place its folder in the plugins/ directory. "
                "Each plugin should have a plugin.json manifest and a main.py or __init__.py entry point."
            ),
            "data": {"directory": str(self.plugins_dir)},
            "action": "plugin_install_info",
        }

    def _plugin_details(self, text: str) -> dict:
        # Try to extract plugin name from text
        match = re.search(r"(?:info|details|about)\s+(?:plugin\s+)?(\w+)", text, re.IGNORECASE)
        if not match:
            return self._list_plugins()

        plugin_name = match.group(1)
        plugin_path = self.plugins_dir / plugin_name

        if not plugin_path.exists():
            return {
                "response": f"Plugin '{plugin_name}' not found.",
                "data": None,
                "action": "error",
            }

        manifest = plugin_path / "plugin.json"
        if manifest.exists():
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {
                    "response": f"Plugin: {data.get('name', plugin_name)}\n"
                                f"Version: {data.get('version', '?')}\n"
                                f"Author: {data.get('author', '?')}\n"
                                f"Description: {data.get('description', 'N/A')}",
                    "data": data,
                    "action": "plugin_details",
                }
            except (json.JSONDecodeError, OSError):
                pass

        return {
            "response": f"Plugin '{plugin_name}' exists but has no valid manifest.",
            "data": {"name": plugin_name, "path": str(plugin_path)},
            "action": "plugin_details",
        }

    def get_system_prompt_addition(self) -> str:
        return "You can manage plugins. List, inspect, or provide info about available plugins."

    def get_context_for_llm(self, text: str, context: dict) -> str:
        return "[Prometheus Plugin System] User is asking about plugins or extensions."

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "auto_load": self.auto_load,
        }

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "auto_load" in settings:
            self.auto_load = settings["auto_load"]

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "auto_load",
                "label": "Auto-load Plugins on Startup",
                "type": "toggle",
                "value": self.auto_load,
            },
        ]
