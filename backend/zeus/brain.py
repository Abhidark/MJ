"""
Zeus — Master Brain. Orchestrates all MJ modules.
Routes user input to the right module based on confidence scores.
"""

import json
from pathlib import Path
from typing import Optional

SETTINGS_FILE = Path(__file__).parent.parent / "module_settings.json"


class Zeus:
    def __init__(self):
        self.modules = {}
        self._load_settings()

    def register(self, module):
        """Register a module with Zeus."""
        self.modules[module.name] = module
        # Apply saved settings
        saved = self._saved_settings.get(module.name, {})
        if saved:
            module.update_settings(saved)

    def _load_settings(self):
        """Load saved module settings."""
        if SETTINGS_FILE.exists():
            self._saved_settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        else:
            self._saved_settings = {}

    def _save_settings(self):
        """Save all module settings."""
        settings = {}
        for name, mod in self.modules.items():
            settings[name] = mod.get_settings()
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    def route(self, text: str, intent: str, context: dict) -> Optional[tuple]:
        """
        Route request to the best module.
        Returns: (module, confidence) or None if no module matches.
        """
        best_module = None
        best_score = 0.0

        for name, module in self.modules.items():
            if not module.enabled:
                continue
            try:
                score = module.can_handle(text, intent, context)
                if score > best_score:
                    best_score = score
                    best_module = module
            except Exception:
                continue

        if best_module and best_score > 0.1:
            return (best_module, best_score)
        return None

    def get_module(self, name: str):
        """Get a specific module by name."""
        return self.modules.get(name)

    def get_all_modules(self) -> list:
        """Get info for all registered modules."""
        return [mod.info() for mod in self.modules.values()]

    def get_active_modules(self) -> list:
        """Get only enabled modules."""
        return [mod for mod in self.modules.values() if mod.enabled]

    def update_module_settings(self, module_name: str, settings: dict) -> bool:
        """Update settings for a specific module."""
        mod = self.modules.get(module_name)
        if not mod:
            return False
        mod.update_settings(settings)
        self._save_settings()
        return True

    def get_module_settings(self, module_name: str) -> dict:
        """Get settings schema for a module."""
        mod = self.modules.get(module_name)
        if not mod:
            return {}
        return {
            "info": mod.info(),
            "settings": mod.get_settings_schema(),
        }

    def get_extra_system_prompt(self) -> str:
        """Collect system prompt additions from all active modules."""
        parts = []
        for mod in self.get_active_modules():
            addition = mod.get_system_prompt_addition()
            if addition:
                parts.append(addition)
        return "\n".join(parts)

    def get_context_for_request(self, text: str, context: dict) -> str:
        """Collect context from modules that want to add to the LLM prompt."""
        parts = []
        for mod in self.get_active_modules():
            ctx = mod.get_context_for_llm(text, context)
            if ctx:
                parts.append(ctx)
        return "\n".join(parts)
