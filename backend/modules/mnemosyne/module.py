"""
Mnemosyne Module -- Memory system for MJ Assistant.
Saves and recalls user facts, preferences, and personal details.
Uses the unified MemoryStore for all operations.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.base_module import BaseModule
from intelligence.memory_store import memory_store
from intelligence.short_term_memory import short_term


class MnemosyneModule(BaseModule):
    name = "mnemosyne"
    display_name = "Mnemosyne"
    icon = "brain"
    description = "Memory -- remembers facts, preferences, and personal details"
    version = "2.0"
    category = "core"
    enabled = True

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

    def can_handle(self, text, intent, context):
        if self.REMEMBER_KEYWORDS.search(text):
            return 0.92
        if self.RECALL_KEYWORDS.search(text):
            return 0.92
        if self.FORGET_KEYWORDS.search(text):
            return 0.90
        if intent in ("remember", "recall", "memory"):
            return 0.85
        if self._auto_remember_enabled:
            return 0.1
        return 0.0

    def execute(self, text, context):
        # Log user turn to short-term memory
        try:
            short_term.add_turn("user", text)
        except Exception:
            pass

        if self.FORGET_KEYWORDS.search(text):
            return self._forget(text)
        if self.RECALL_KEYWORDS.search(text):
            return self._recall(text)
        if self.REMEMBER_KEYWORDS.search(text):
            return self._remember_explicit(text)
        return self._auto_remember(text)

    def _remember_explicit(self, text):
        """Explicitly asked to remember something."""
        fact_text = self.REMEMBER_KEYWORDS.sub("", text).strip()
        fact_text = re.sub(r"^(that|ki|ke)\s+", "", fact_text, flags=re.IGNORECASE).strip()

        if not fact_text or len(fact_text) < 3:
            return {
                "response": "What should I remember? Tell me the fact!",
                "data": None,
                "action": "memory_prompt",
            }

        fact = memory_store.add(fact_text, source="user")
        if fact is None:
            # Duplicate
            return {
                "response": "I already know that!",
                "data": {"duplicate": True},
                "action": "memory_duplicate",
            }

        stats = memory_store.get_stats()
        return {
            "response": "Got it! I'll remember: '" + fact.content + "'",
            "data": {"saved_fact": fact.content, "total_facts": stats["total_facts"]},
            "action": "memory_save",
        }

    def _recall(self, text):
        """Recall stored facts. Uses hybrid search (semantic + keyword) when available."""
        all_facts = memory_store.get_all()
        if not all_facts:
            return {
                "response": "I don't have any saved memories about you yet. Tell me about yourself!",
                "data": {"facts": []},
                "action": "memory_recall",
            }

        # Check if asking about something specific
        query = self.RECALL_KEYWORDS.sub("", text).strip().lower()
        if query and len(query) > 2:
            # Try hybrid search (semantic + keyword) first
            results = None
            search_mode = "keyword"
            try:
                import asyncio
                from intelligence.memory_embeddings import hybrid_search, is_ollama_embed_available
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're inside an async context — create a task
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        results = pool.submit(
                            lambda: asyncio.run(hybrid_search(query, top_k=10))
                        ).result(timeout=5)
                else:
                    results = asyncio.run(hybrid_search(query, top_k=10))
                if results:
                    search_mode = "hybrid"
            except Exception:
                pass

            # Fallback to keyword search
            if not results:
                results = memory_store.search(query, top_k=10)

            if results:
                matching = [f.content for f, _ in results]
                facts_str = "\n".join("  - " + f for f in matching)
                return {
                    "response": "Here's what I know about '" + query + "':\n" + facts_str,
                    "data": {"facts": matching, "query": query, "search_mode": search_mode},
                    "action": "memory_recall",
                }

        # Return all facts grouped by category
        by_cat = {}
        for f in all_facts:
            by_cat.setdefault(f.category, []).append(f.content)

        lines = []
        for cat, facts in by_cat.items():
            lines.append("[" + cat + "]")
            for fc in facts:
                lines.append("  - " + fc)

        return {
            "response": "Here's everything I remember about you (" + str(len(all_facts)) + " facts):\n" + "\n".join(lines),
            "data": {"facts": [f.content for f in all_facts], "total": len(all_facts)},
            "action": "memory_recall",
        }

    def _forget(self, text):
        """Clear memory."""
        if "everything" in text.lower() or "sab" in text.lower():
            memory_store.clear()
            return {
                "response": "Done, I've cleared all memories. Starting fresh!",
                "data": {"cleared": True},
                "action": "memory_clear",
            }

        query = self.FORGET_KEYWORDS.sub("", text).strip().lower()
        if query and len(query) > 2:
            removed = memory_store.forget(query)
            if removed > 0:
                return {
                    "response": "Forgotten " + str(removed) + " fact(s) about '" + query + "'.",
                    "data": {"removed": removed},
                    "action": "memory_forget",
                }
            return {
                "response": "I don't have anything about '" + query + "' to forget.",
                "data": None,
                "action": "memory_forget",
            }

        return {
            "response": "What should I forget? Say 'forget everything' to clear all, or specify what to remove.",
            "data": None,
            "action": "memory_prompt",
        }

    def _auto_remember(self, text):
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

    def get_context_for_llm(self, text, context):
        """Inject memory context + user profile + short-term context into LLM prompt."""
        parts = []

        # Long-term facts
        ctx = memory_store.get_context_string(max_facts=20)
        if ctx:
            parts.append("[User Memory] Known facts:\n" + ctx)

        # User profile prompt
        try:
            from intelligence.user_profile import get_profile_prompt
            profile_prompt = get_profile_prompt(max_lines=10)
            if profile_prompt:
                parts.append(profile_prompt)
        except Exception:
            pass

        # Short-term conversation context
        try:
            stm_ctx = short_term.get_context_window(max_chars=800)
            if stm_ctx:
                parts.append("[Recent Conversation]\n" + stm_ctx)
        except Exception:
            pass

        return "\n\n".join(parts) if parts else ""

    def get_system_prompt_addition(self):
        return (
            "You have memory capabilities. You remember facts about the user across sessions. "
            "Use stored facts to personalize responses. If the user shares personal info, "
            "acknowledge it and use it naturally in conversation."
        )

    def get_settings(self):
        stats = memory_store.get_stats()
        return {
            "enabled": self.enabled,
            "auto_remember": self._auto_remember_enabled,
            "facts_count": stats["total_facts"],
            "categories": stats["categories"],
        }

    def update_settings(self, settings):
        super().update_settings(settings)
        if "auto_remember" in settings:
            self._auto_remember_enabled = bool(settings["auto_remember"])

    def get_settings_schema(self):
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {"key": "auto_remember", "label": "Auto-Remember Facts", "type": "toggle", "value": self._auto_remember_enabled},
        ]
