"""
Base Module Interface — every MJ module must inherit from this.
"""

from pathlib import Path
import json

MODULES_SETTINGS_FILE = Path(__file__).parent.parent / "module_settings.json"


class BaseModule:
    name: str = "base"
    display_name: str = "Base Module"
    icon: str = "🧩"
    description: str = "Base module"
    version: str = "1.0"
    category: str = "core"  # core, utility, creative, system, lifestyle
    enabled: bool = True

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        """
        Return confidence score 0.0 to 1.0 that this module can handle the request.
        0.0 = cannot handle, 1.0 = perfect match.
        """
        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        """
        Execute the module's action.
        Returns: {"response": str, "data": any, "action": str}
        """
        return {"response": "Module not implemented.", "data": None, "action": "none"}

    async def execute_async(self, text: str, context: dict) -> dict:
        """Async version of execute. Override if module needs async ops."""
        return self.execute(text, context)

    def get_system_prompt_addition(self) -> str:
        """Return extra system prompt text when this module is active."""
        return ""

    def get_context_for_llm(self, text: str, context: dict) -> str:
        """Return context string to inject into LLM prompt."""
        return ""

    def get_settings(self) -> dict:
        """Return current module settings."""
        return {"enabled": self.enabled}

    def update_settings(self, settings: dict):
        """Update module settings."""
        if "enabled" in settings:
            self.enabled = settings["enabled"]

    def get_settings_schema(self) -> list:
        """
        Return settings UI schema for the frontend.
        Each item: {"key": str, "label": str, "type": "toggle"|"text"|"select"|"range", "value": any, ...}
        """
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled}
        ]

    def info(self) -> dict:
        """Return module info for UI display."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "icon": self.icon,
            "description": self.description,
            "version": self.version,
            "category": self.category,
            "enabled": self.enabled,
        }
