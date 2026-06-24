"""
Mnemosyne Module v3 -- Memory system for MJ Assistant (V13 upgrade).
Saves and recalls user facts, preferences, and personal details.
Uses the unified MemoryStore for all operations.
NEW: Episodic memory (event-based recall) + memory compression.
"""

import re
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.base_module import BaseModule
from intelligence.memory_store import memory_store
from intelligence.short_term_memory import short_term

logger = logging.getLogger("mj.mnemosyne")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
EPISODES_FILE = DATA_DIR / "memory_episodes.json"
COMPRESSION_FILE = DATA_DIR / "memory_compressed.json"


def _load_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def _save_json(path, data):
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# ========================
# EPISODIC MEMORY
# ========================

class EpisodicMemory:
    """
    Stores event-based memories with timestamps, emotional weight,
    and context. Enables 'when did I...', 'last time...' style queries.
    """

    def __init__(self):
        self.episodes: list = []
        self._load()

    def _load(self):
        data = _load_json(EPISODES_FILE, [])
        self.episodes = data if isinstance(data, list) else []

    def _save(self):
        _save_json(EPISODES_FILE, self.episodes)

    def record(self, event: str, category: str = "general", importance: float = 0.5,
               context: dict = None) -> dict:
        episode = {
            "id": f"ep_{int(time.time() * 1000)}",
            "event": event,
            "category": category,
            "importance": min(1.0, max(0.0, importance)),
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
            "recall_count": 0,
        }
        self.episodes.append(episode)
        if len(self.episodes) > 500:
            self.episodes = self.episodes[-500:]
        self._save()
        return episode

    def recall(self, query: str = "", limit: int = 10, days_back: int = 30) -> list:
        cutoff = (datetime.now() - timedelta(days=days_back)).isoformat()
        recent = [e for e in self.episodes if e.get("timestamp", "") >= cutoff]

        if query:
            q_lower = query.lower()
            scored = []
            for ep in recent:
                score = 0
                if q_lower in ep.get("event", "").lower():
                    score += 2
                if q_lower in ep.get("category", "").lower():
                    score += 1
                for word in q_lower.split():
                    if word in ep.get("event", "").lower():
                        score += 0.5
                if score > 0:
                    score += ep.get("importance", 0.5)
                    scored.append((ep, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            results = [e for e, _ in scored[:limit]]
        else:
            results = sorted(recent, key=lambda e: e.get("timestamp", ""), reverse=True)[:limit]

        for ep in results:
            ep["recall_count"] = ep.get("recall_count", 0) + 1
        self._save()
        return results

    def get_timeline(self, days: int = 7) -> dict:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent = [e for e in self.episodes if e.get("timestamp", "") >= cutoff]
        by_day = {}
        for ep in recent:
            day = ep["timestamp"][:10]
            by_day.setdefault(day, []).append(ep)
        return {"timeline": by_day, "total_episodes": len(recent)}

    def get_stats(self) -> dict:
        total = len(self.episodes)
        by_cat = {}
        for ep in self.episodes:
            cat = ep.get("category", "general")
            by_cat[cat] = by_cat.get(cat, 0) + 1
        return {"total_episodes": total, "categories": by_cat}


# ========================
# MEMORY COMPRESSION
# ========================

class MemoryCompressor:
    """
    Compresses old memories by grouping and summarizing.
    Keeps important details, discards redundancy.
    """

    def __init__(self):
        self.compressed: list = []
        self.last_compression: str = ""
        self._load()

    def _load(self):
        data = _load_json(COMPRESSION_FILE, {})
        self.compressed = data.get("summaries", [])
        self.last_compression = data.get("last_compression", "")

    def _save(self):
        _save_json(COMPRESSION_FILE, {
            "summaries": self.compressed,
            "last_compression": self.last_compression,
        })

    def compress_old_facts(self, facts: list, category: str = "general") -> dict:
        """Group similar facts and create a compressed summary."""
        if len(facts) < 3:
            return {"success": False, "reason": "Not enough facts to compress"}

        # Group by common keywords
        groups = {}
        for fact in facts:
            words = set(fact.lower().split())
            placed = False
            for key in groups:
                key_words = set(key.lower().split())
                overlap = len(words & key_words) / max(len(words | key_words), 1)
                if overlap > 0.3:
                    groups[key].append(fact)
                    placed = True
                    break
            if not placed:
                groups[fact] = [fact]

        summaries_added = 0
        for key, group in groups.items():
            if len(group) >= 2:
                summary = {
                    "id": f"comp_{int(time.time() * 1000)}_{summaries_added}",
                    "category": category,
                    "original_count": len(group),
                    "summary": f"[{category}] {len(group)} related facts: {'; '.join(g[:80] for g in group[:5])}",
                    "originals": group[:10],
                    "compressed_at": datetime.now().isoformat(),
                }
                self.compressed.append(summary)
                summaries_added += 1

        if summaries_added > 0:
            self.last_compression = datetime.now().isoformat()
            if len(self.compressed) > 200:
                self.compressed = self.compressed[-200:]
            self._save()

        return {
            "success": True,
            "groups_compressed": summaries_added,
            "total_compressed": len(self.compressed),
        }

    def get_compressed(self, limit: int = 20) -> list:
        return self.compressed[-limit:]

    def get_stats(self) -> dict:
        return {
            "total_summaries": len(self.compressed),
            "last_compression": self.last_compression,
            "total_originals": sum(s.get("original_count", 0) for s in self.compressed),
        }


# ========================
# MEMORY DECAY & IMPORTANCE (V13 → 90%+)
# ========================

IMPORTANCE_FILE = DATA_DIR / "memory_importance.json"

class MemoryDecay:
    """
    Implements memory importance scoring and time-based decay.
    High-importance memories persist; low-importance ones fade.
    """

    def __init__(self):
        self.scores: dict = {}
        self._load()

    def _load(self):
        data = _load_json(IMPORTANCE_FILE, {})
        self.scores = data.get("scores", {})

    def _save(self):
        _save_json(IMPORTANCE_FILE, {"scores": self.scores, "updated": datetime.now().isoformat()})

    def score_fact(self, fact_id: str, content: str, access_count: int = 1) -> float:
        """Calculate importance score based on content analysis and access patterns."""
        score = 0.5  # base score

        # Boost for personal info
        personal = re.compile(r"\b(my|i\s+am|i\s+like|i\s+prefer|i\s+hate|favorite|naam|mera)\b", re.IGNORECASE)
        if personal.search(content):
            score += 0.2

        # Boost for factual/reference data
        factual = re.compile(r"\b(password|key|address|phone|email|birthday|api|secret|config)\b", re.IGNORECASE)
        if factual.search(content):
            score += 0.3

        # Boost for emotional significance
        emotional = re.compile(r"\b(love|important|critical|always|never|must|need)\b", re.IGNORECASE)
        if emotional.search(content):
            score += 0.1

        # Access frequency bonus (capped at 0.2)
        score += min(access_count * 0.02, 0.2)

        score = min(score, 1.0)
        self.scores[fact_id] = {"score": score, "access_count": access_count, "last_access": time.time()}
        self._save()
        return score

    def decay(self, half_life_days: int = 30) -> dict:
        """Apply time-based decay to all memory scores."""
        now = time.time()
        decayed = 0
        for fid, data in self.scores.items():
            age_days = (now - data.get("last_access", now)) / 86400
            decay_factor = 0.5 ** (age_days / half_life_days)
            old_score = data["score"]
            data["score"] = max(round(old_score * decay_factor, 3), 0.01)
            if data["score"] < old_score:
                decayed += 1
        self._save()
        return {"decayed": decayed, "total": len(self.scores), "half_life_days": half_life_days}

    def get_important(self, threshold: float = 0.7, limit: int = 20) -> list:
        """Get memories above importance threshold."""
        return sorted(
            [{"id": k, **v} for k, v in self.scores.items() if v["score"] >= threshold],
            key=lambda x: x["score"], reverse=True,
        )[:limit]

    def get_fading(self, threshold: float = 0.3, limit: int = 20) -> list:
        """Get memories that are fading (below threshold)."""
        return sorted(
            [{"id": k, **v} for k, v in self.scores.items() if v["score"] < threshold],
            key=lambda x: x["score"],
        )[:limit]

    def get_stats(self) -> dict:
        scores = [v["score"] for v in self.scores.values()]
        return {
            "total_scored": len(self.scores),
            "avg_score": round(sum(scores) / max(len(scores), 1), 3),
            "high_importance": sum(1 for s in scores if s >= 0.7),
            "medium_importance": sum(1 for s in scores if 0.3 <= s < 0.7),
            "low_importance": sum(1 for s in scores if s < 0.3),
        }


# ========================
# KNOWLEDGE INDEXER (V13 → 90%+)
# ========================

KB_INDEX_FILE = DATA_DIR / "knowledge_index.json"

class KnowledgeIndexer:
    """Auto-categorizes and indexes knowledge for faster retrieval."""

    CATEGORIES = {
        "personal": re.compile(r"\b(my|i\s+am|i\s+like|name\s+is|birthday|age|live\s+in)\b", re.IGNORECASE),
        "technical": re.compile(r"\b(api|code|server|database|python|react|docker|git)\b", re.IGNORECASE),
        "preference": re.compile(r"\b(prefer|like|dislike|favorite|hate|enjoy|avoid)\b", re.IGNORECASE),
        "task": re.compile(r"\b(todo|task|remind|deadline|meeting|schedule|plan)\b", re.IGNORECASE),
        "reference": re.compile(r"\b(password|key|url|link|address|phone|email|ip)\b", re.IGNORECASE),
    }

    def __init__(self):
        self.index: dict = {}
        self._load()

    def _load(self):
        self.index = _load_json(KB_INDEX_FILE, {"categories": {}, "updated": ""})

    def _save(self):
        self.index["updated"] = datetime.now().isoformat()
        _save_json(KB_INDEX_FILE, self.index)

    def categorize(self, fact_id: str, content: str) -> str:
        """Auto-categorize a fact based on content patterns."""
        for cat, pattern in self.CATEGORIES.items():
            if pattern.search(content):
                if cat not in self.index["categories"]:
                    self.index["categories"][cat] = []
                if fact_id not in self.index["categories"][cat]:
                    self.index["categories"][cat].append(fact_id)
                self._save()
                return cat
        # Default category
        if "general" not in self.index["categories"]:
            self.index["categories"]["general"] = []
        if fact_id not in self.index["categories"]["general"]:
            self.index["categories"]["general"].append(fact_id)
        self._save()
        return "general"

    def search_by_category(self, category: str) -> list:
        return self.index.get("categories", {}).get(category, [])

    def get_all_categories(self) -> dict:
        return {cat: len(ids) for cat, ids in self.index.get("categories", {}).items()}

    def rebuild_index(self, facts: list) -> dict:
        """Rebuild the entire index from a list of (id, content) tuples."""
        self.index = {"categories": {}, "updated": ""}
        for fid, content in facts:
            self.categorize(fid, content)
        return {"rebuilt": True, "categories": self.get_all_categories()}

    def get_stats(self) -> dict:
        cats = self.index.get("categories", {})
        return {
            "total_indexed": sum(len(v) for v in cats.values()),
            "categories": self.get_all_categories(),
            "last_updated": self.index.get("updated", "never"),
        }


# Module-level singletons
episodic_memory = EpisodicMemory()
memory_compressor = MemoryCompressor()
memory_decay = MemoryDecay()
knowledge_indexer = KnowledgeIndexer()


class MnemosyneModule(BaseModule):
    name = "mnemosyne"
    display_name = "Mnemosyne"
    icon = "brain"
    description = "Memory -- remembers facts, preferences, personal details, episodes"
    version = "3.0"
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

    EPISODIC_KEYWORDS = re.compile(
        r"\b(when\s+did\s+(?:I|we|you)|last\s+time|do\s+you\s+recall\s+when|"
        r"remember\s+when|what\s+happened\s+(?:yesterday|last\s+week|today)|"
        r"timeline|my\s+history|episode|event\s+log)\b",
        re.IGNORECASE,
    )

    COMPRESS_KEYWORDS = re.compile(
        r"\b(compress\s+memor|cleanup\s+memor|optimize\s+memor|summarize\s+memor|memory\s+stats)\b",
        re.IGNORECASE,
    )

    def can_handle(self, text, intent, context):
        if self.REMEMBER_KEYWORDS.search(text):
            return 0.92
        if self.RECALL_KEYWORDS.search(text):
            return 0.92
        if self.FORGET_KEYWORDS.search(text):
            return 0.90
        if self.EPISODIC_KEYWORDS.search(text):
            return 0.91
        if self.COMPRESS_KEYWORDS.search(text):
            return 0.88
        if intent in ("remember", "recall", "memory", "episode", "timeline"):
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

        # Also record as episodic event
        try:
            episodic_memory.record(text[:200], category="conversation", importance=0.3)
        except Exception:
            pass

        if self.FORGET_KEYWORDS.search(text):
            return self._forget(text)
        if self.EPISODIC_KEYWORDS.search(text):
            return self._recall_episode(text)
        if self.COMPRESS_KEYWORDS.search(text):
            return self._compress_memories(text)
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

    def _recall_episode(self, text):
        """Recall episodic (event-based) memories."""
        query = self.EPISODIC_KEYWORDS.sub("", text).strip()
        if "timeline" in text.lower() or "history" in text.lower():
            timeline = episodic_memory.get_timeline(days=7)
            if not timeline["timeline"]:
                return {"response": "No recent episodes recorded yet.", "data": timeline, "action": "episode_timeline"}
            lines = []
            for day, eps in sorted(timeline["timeline"].items(), reverse=True):
                lines.append(f"**{day}** ({len(eps)} events)")
                for ep in eps[:5]:
                    lines.append(f"  - {ep['event'][:100]}")
            return {
                "response": f"Your recent timeline ({timeline['total_episodes']} events):\n" + "\n".join(lines),
                "data": timeline,
                "action": "episode_timeline",
            }

        episodes = episodic_memory.recall(query, limit=8)
        if not episodes:
            return {"response": "I don't have any episodic memories matching that.", "data": {"episodes": []}, "action": "episode_recall"}

        lines = []
        for ep in episodes:
            ts = ep.get("timestamp", "")[:16].replace("T", " ")
            lines.append(f"  [{ts}] {ep['event'][:120]}")
        return {
            "response": f"Here's what I recall ({len(episodes)} episodes):\n" + "\n".join(lines),
            "data": {"episodes": episodes},
            "action": "episode_recall",
        }

    def _compress_memories(self, text):
        """Compress/summarize old memories to save space."""
        if "stats" in text.lower():
            mem_stats = memory_store.get_stats()
            ep_stats = episodic_memory.get_stats()
            comp_stats = memory_compressor.get_stats()
            return {
                "response": (
                    f"Memory Stats:\n"
                    f"  Facts: {mem_stats['total_facts']} ({len(mem_stats.get('categories', {}))} categories)\n"
                    f"  Episodes: {ep_stats['total_episodes']}\n"
                    f"  Compressed: {comp_stats['total_summaries']} summaries from {comp_stats['total_originals']} originals\n"
                    f"  Last compression: {comp_stats['last_compression'] or 'Never'}"
                ),
                "data": {"memory": mem_stats, "episodes": ep_stats, "compression": comp_stats},
                "action": "memory_stats",
            }

        all_facts = memory_store.get_all()
        if len(all_facts) < 5:
            return {"response": "Not enough memories to compress yet (need 5+).", "data": None, "action": "memory_compress"}

        by_cat = {}
        for f in all_facts:
            by_cat.setdefault(f.category, []).append(f.content)

        total_compressed = 0
        for cat, facts in by_cat.items():
            result = memory_compressor.compress_old_facts(facts, category=cat)
            total_compressed += result.get("groups_compressed", 0)

        return {
            "response": f"Compressed {total_compressed} memory groups. Run 'memory stats' to see updated stats.",
            "data": {"groups_compressed": total_compressed},
            "action": "memory_compress",
        }

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
        ep_stats = episodic_memory.get_stats()
        comp_stats = memory_compressor.get_stats()
        return {
            "enabled": self.enabled,
            "auto_remember": self._auto_remember_enabled,
            "facts_count": stats["total_facts"],
            "categories": stats["categories"],
            "episodes": ep_stats["total_episodes"],
            "compressed_summaries": comp_stats["total_summaries"],
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
