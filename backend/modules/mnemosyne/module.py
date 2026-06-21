"""
Mnemosyne Module — Memory system for MJ Assistant.
Saves and recalls user facts, preferences, and personal details.
"""

import re
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.base_module import BaseModule

CORE_MEMORY_FILE = Path(__file__).parent.parent.parent / "core_memory.json"


class MnemosyneModule(BaseModule):
    name = "mnemosyne"
    display_name = "Mnemosyne"
    icon = "🧠"
    description = "Memory — remembers facts, preferences, and personal details"
    version = "1.0"
    category = "core"
    enabled = True

    # Auto-remember: silently extract facts from every message
    _auto_remember_enabled = True

    REMEMBER_KEYWORDS = re.compile(
        r"\b(remember\s+(?:this|that)|yaad\s+rakh|yaad\s+rakho|/remember|save\s+(?:this|that)|note\s+(?:this|that|down)|"
        r"don'?t\s+forget|mat\s+bhoolna)\b",
        re.IGNORECASE,
    )

    RECALL_KEYWORDS = re.compile(
        r"\b(what\s+do\s+you\s+(?:know|remember)\s+about\s+me|"
        r"kya\s+yaad\s+hai|do\s+you\s+remember|yaad\s+hai\s+kya|"
        r"what\s+(?:is|are)\s+my|mera\s+(?:naam|name)|"
        r"tell\s+me\s+(?:about\s+myself|what\s+you\s+know)|/recall|/memory)\b",
        re.IGNORECASE,
    )

    FORGET_KEYWORDS = re.compile(
        r"\b(forget\s+(?:about|that|everything)|bhool\s+ja|clear\s+memory|/forget)\b",
        re.IGNORECASE,
    )

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        if self.REMEMBER_KEYWORDS.search(text):
            return 0.92
        if self.RECALL_KEYWORDS.search(text):
            return 0.92
        if self.FORGET_KEYWORDS.search(text):
            return 0.90
        if intent in ("remember", "recall", "memory"):
            return 0.85
        # Auto-remember runs at low priority on every message
        if self._auto_remember_enabled:
            return 0.1
        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        # Determine operation type
        if self.FORGET_KEYWORDS.search(text):
            return self._forget(text)
        if self.RECALL_KEYWORDS.search(text):
            return self._recall(text)
        if self.REMEMBER_KEYWORDS.search(text):
            return self._remember_explicit(text)

        # Auto-remember: silently extract and save facts
        return self._auto_remember(text)

    def _load_memory(self) -> list:
        if CORE_MEMORY_FILE.exists():
            try:
                return json.loads(CORE_MEMORY_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save_memory(self, facts: list):
        CORE_MEMORY_FILE.write_text(
            json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _remember_explicit(self, text: str) -> dict:
        """Explicitly asked to remember something."""
        # Strip trigger words to get the fact
        fact = self.REMEMBER_KEYWORDS.sub("", text).strip()
        fact = re.sub(r"^(that|ki|ke)\s+", "", fact, flags=re.IGNORECASE).strip()

        if not fact or len(fact) < 3:
            return {
                "response": "What should I remember? Tell me the fact!",
                "data": None,
                "action": "memory_prompt",
            }

        facts = self._load_memory()
        # Check duplicate
        lower_fact = fact.lower()
        for existing in facts:
            if lower_fact in existing.lower() or existing.lower() in lower_fact:
                return {
                    "response": f"I already know that: '{existing}'",
                    "data": {"existing_fact": existing},
                    "action": "memory_duplicate",
                }

        facts.append(fact)
        self._save_memory(facts)

        return {
            "response": f"Got it! I'll remember: '{fact}'",
            "data": {"saved_fact": fact, "total_facts": len(facts)},
            "action": "memory_save",
        }

    def _recall(self, text: str) -> dict:
        """Recall stored facts."""
        facts = self._load_memory()
        if not facts:
            return {
                "response": "I don't have any saved memories about you yet. Tell me about yourself!",
                "data": {"facts": []},
                "action": "memory_recall",
            }

        # Check if asking about something specific
        query = self.RECALL_KEYWORDS.sub("", text).strip().lower()
        if query and len(query) > 2:
            matching = [f for f in facts if query in f.lower()]
            if matching:
                facts_str = "\n".join(f"  - {f}" for f in matching)
                return {
                    "response": f"Here's what I know about '{query}':\n{facts_str}",
                    "data": {"facts": matching, "query": query},
                    "action": "memory_recall",
                }

        # Return all facts
        facts_str = "\n".join(f"  - {f}" for f in facts)
        return {
            "response": f"Here's everything I remember about you ({len(facts)} facts):\n{facts_str}",
            "data": {"facts": facts, "total": len(facts)},
            "action": "memory_recall",
        }

    def _forget(self, text: str) -> dict:
        """Clear memory."""
        if "everything" in text.lower() or "sab" in text.lower():
            self._save_memory([])
            return {
                "response": "Done, I've cleared all memories. Starting fresh!",
                "data": {"cleared": True},
                "action": "memory_clear",
            }

        # Remove specific fact
        query = self.FORGET_KEYWORDS.sub("", text).strip().lower()
        if query and len(query) > 2:
            facts = self._load_memory()
            remaining = [f for f in facts if query not in f.lower()]
            removed = len(facts) - len(remaining)
            if removed > 0:
                self._save_memory(remaining)
                return {
                    "response": f"Forgotten {removed} fact(s) about '{query}'.",
                    "data": {"removed": removed},
                    "action": "memory_forget",
                }
            return {
                "response": f"I don't have anything about '{query}' to forget.",
                "data": None,
                "action": "memory_forget",
            }

        return {
            "response": "What should I forget? Say 'forget everything' to clear all, or specify what to remove.",
            "data": None,
            "action": "memory_prompt",
        }

    def _auto_remember(self, text: str) -> dict:
        """Silently extract facts using auto_remember."""
        try:
            from human_layer.auto_memory import auto_remember

            new_facts = auto_remember(text)
            if new_facts:
                return {
                    "response": "",
                    "data": {"auto_saved": new_facts},
                    "action": "memory_auto",
                }
        except ImportError:
            pass

        return {"response": "", "data": None, "action": "none"}

    def get_context_for_llm(self, text: str, context: dict) -> str:
        """Inject memory context into LLM prompt."""
        facts = self._load_memory()
        if not facts:
            return ""
        facts_str = "; ".join(facts[:20])  # Limit to 20 facts for context size
        return f"[User Memory] Known facts about the user: {facts_str}"

    def get_system_prompt_addition(self) -> str:
        return (
            "You have memory capabilities. You remember facts about the user across sessions. "
            "Use stored facts to personalize responses. If the user shares personal info, "
            "acknowledge it and use it naturally in conversation."
        )

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "auto_remember": self._auto_remember_enabled,
            "facts_count": len(self._load_memory()),
        }

    def update_settings(self, settings: dict):
        super().update_settings(settings)
        if "auto_remember" in settings:
            self._auto_remember_enabled = bool(settings["auto_remember"])

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {"key": "auto_remember", "label": "Auto-Remember Facts", "type": "toggle", "value": self._auto_remember_enabled},
        ]
