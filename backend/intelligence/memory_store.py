"""
memory_store.py -- Unified Memory Store for MJ-Assistant
Single source of truth for all core memory operations.

Features:
- Structured facts with id, content, category, confidence, timestamps
- Thread-safe read/write with file locking
- Category-based organization
- Backward compatible with old flat array format
- Embedding storage for vector search
- Auto-migration from legacy core_memory.json
"""

import json
import uuid
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

# --- Constants ---
MEMORY_DIR = Path(__file__).parent.parent
STORE_FILE = MEMORY_DIR / "memory_store.json"
LEGACY_FILE = MEMORY_DIR / "core_memory.json"

CATEGORIES = [
    "personal",      # name, age, birthday
    "preference",    # likes, dislikes, habits
    "project",       # work projects, tasks
    "skill",         # programming, languages
    "location",      # city, country, address
    "relationship",  # family, friends, colleagues
    "work",          # job, company, role
    "device",        # PC specs, laptop, phone
    "instruction",   # how user wants MJ to behave
    "general",       # anything else
]


class Fact:
    """Single memory fact with metadata."""

    def __init__(self, content, category="general", source="user",
                 confidence=1.0, fact_id=None, created_at=None,
                 updated_at=None, access_count=0, embedding=None):
        self.id = fact_id or str(uuid.uuid4())[:8]
        self.content = content
        self.category = category if category in CATEGORIES else "general"
        self.source = source  # "user" | "auto" | "llm"
        self.confidence = min(1.0, max(0.0, confidence))
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or self.created_at
        self.access_count = access_count
        self.embedding = embedding  # list[float] or None

    def to_dict(self):
        d = {
            "id": self.id,
            "content": self.content,
            "category": self.category,
            "source": self.source,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "access_count": self.access_count,
        }
        if self.embedding:
            d["embedding"] = self.embedding
        return d

    @classmethod
    def from_dict(cls, d):
        return cls(
            content=d["content"],
            category=d.get("category", "general"),
            source=d.get("source", "user"),
            confidence=d.get("confidence", 1.0),
            fact_id=d.get("id"),
            created_at=d.get("created_at"),
            updated_at=d.get("updated_at"),
            access_count=d.get("access_count", 0),
            embedding=d.get("embedding"),
        )

    @classmethod
    def from_legacy_string(cls, text):
        """Convert old flat string fact to structured Fact."""
        return cls(
            content=text.strip(),
            category="general",
            source="user",
            confidence=0.8,
        )

    def __repr__(self):
        return f"Fact(id={self.id}, cat={self.category}, content={self.content[:40]})"


class MemoryStore:
    """Thread-safe unified memory store."""

    def __init__(self):
        self._lock = threading.Lock()
        self._facts = []  # list[Fact]
        self._loaded = False

    # --- Load / Save ---

    def _ensure_loaded(self):
        if not self._loaded:
            self._load()

    def _load(self):
        """Load from memory_store.json, or migrate from legacy core_memory.json."""
        if STORE_FILE.exists():
            try:
                data = json.loads(STORE_FILE.read_text(encoding="utf-8"))
                self._facts = [Fact.from_dict(f) for f in data.get("facts", [])]
                self._loaded = True
                return
            except (json.JSONDecodeError, KeyError):
                pass

        # Migrate from legacy format
        if LEGACY_FILE.exists():
            try:
                legacy = json.loads(LEGACY_FILE.read_text(encoding="utf-8"))
                if isinstance(legacy, list):
                    self._facts = [Fact.from_legacy_string(s) for s in legacy if isinstance(s, str) and s.strip()]
                    self._save()  # persist in new format
            except (json.JSONDecodeError, TypeError):
                self._facts = []

        self._loaded = True

    def _save(self):
        """Persist to disk."""
        data = {
            "version": 2,
            "updated_at": datetime.now().isoformat(),
            "count": len(self._facts),
            "facts": [f.to_dict() for f in self._facts],
        }
        STORE_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        # Also write legacy format for backward compat
        legacy = [f.content for f in self._facts]
        LEGACY_FILE.write_text(
            json.dumps(legacy, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # --- CRUD Operations ---

    def add(self, content, category="general", source="user",
            confidence=1.0, embedding=None):
        """Add a new fact. Returns the Fact object."""
        with self._lock:
            self._ensure_loaded()

            # Check for duplicates
            if self._is_duplicate(content):
                return None

            fact = Fact(
                content=content,
                category=category,
                source=source,
                confidence=confidence,
                embedding=embedding,
            )
            self._facts.append(fact)
            self._save()
            return fact

    def add_batch(self, facts_data):
        """Add multiple facts at once. facts_data: list of dicts with content, category, etc."""
        with self._lock:
            self._ensure_loaded()
            added = []
            for fd in facts_data:
                content = fd.get("content", "").strip()
                if not content or self._is_duplicate(content):
                    continue
                fact = Fact(
                    content=content,
                    category=fd.get("category", "general"),
                    source=fd.get("source", "llm"),
                    confidence=fd.get("confidence", 0.9),
                    embedding=fd.get("embedding"),
                )
                self._facts.append(fact)
                added.append(fact)
            if added:
                self._save()
            return added

    def get_all(self):
        """Return all facts."""
        with self._lock:
            self._ensure_loaded()
            return list(self._facts)

    def get_by_category(self, category):
        """Return facts filtered by category."""
        with self._lock:
            self._ensure_loaded()
            return [f for f in self._facts if f.category == category]

    def get_by_id(self, fact_id):
        """Return a single fact by id."""
        with self._lock:
            self._ensure_loaded()
            for f in self._facts:
                if f.id == fact_id:
                    return f
            return None

    def search(self, query, top_k=5):
        """Keyword search across facts. Returns list of (fact, score)."""
        with self._lock:
            self._ensure_loaded()
            query_lower = query.lower()
            query_words = set(query_lower.split())
            results = []
            for f in self._facts:
                content_lower = f.content.lower()
                # Substring match
                if query_lower in content_lower:
                    results.append((f, 1.0))
                    continue
                # Word overlap
                fact_words = set(content_lower.split())
                overlap = query_words & fact_words
                if overlap:
                    score = len(overlap) / max(len(query_words), 1)
                    results.append((f, score))

            results.sort(key=lambda x: x[1], reverse=True)
            # Update access count for retrieved facts
            for fact, _ in results[:top_k]:
                fact.access_count += 1
                fact.updated_at = datetime.now().isoformat()
            if results:
                self._save()
            return results[:top_k]

    def update(self, fact_id, content=None, category=None, confidence=None, embedding=None):
        """Update a fact's fields."""
        with self._lock:
            self._ensure_loaded()
            for f in self._facts:
                if f.id == fact_id:
                    if content is not None:
                        f.content = content
                    if category is not None:
                        f.category = category
                    if confidence is not None:
                        f.confidence = confidence
                    if embedding is not None:
                        f.embedding = embedding
                    f.updated_at = datetime.now().isoformat()
                    self._save()
                    return f
            return None

    def delete(self, fact_id):
        """Delete a fact by id."""
        with self._lock:
            self._ensure_loaded()
            before = len(self._facts)
            self._facts = [f for f in self._facts if f.id != fact_id]
            if len(self._facts) < before:
                self._save()
                return True
            return False

    def forget(self, query):
        """Delete facts matching a query string."""
        with self._lock:
            self._ensure_loaded()
            query_lower = query.lower()
            before = len(self._facts)
            self._facts = [f for f in self._facts if query_lower not in f.content.lower()]
            removed = before - len(self._facts)
            if removed > 0:
                self._save()
            return removed

    def clear(self):
        """Delete all facts."""
        with self._lock:
            self._facts = []
            self._save()

    # --- Query helpers ---

    def get_flat_list(self):
        """Return facts as flat string list (legacy compat)."""
        with self._lock:
            self._ensure_loaded()
            return [f.content for f in self._facts]

    def get_context_string(self, max_facts=30):
        """Build a context string for LLM system prompt."""
        with self._lock:
            self._ensure_loaded()
            if not self._facts:
                return ""

            # Group by category
            by_cat = {}
            for f in self._facts:
                by_cat.setdefault(f.category, []).append(f)

            lines = []
            count = 0
            for cat in CATEGORIES:
                if cat not in by_cat:
                    continue
                cat_facts = sorted(by_cat[cat], key=lambda x: x.confidence, reverse=True)
                for f in cat_facts:
                    if count >= max_facts:
                        break
                    lines.append(f"- [{cat}] {f.content}")
                    count += 1

            return "\n".join(lines)

    def get_stats(self):
        """Return memory statistics."""
        with self._lock:
            self._ensure_loaded()
            by_cat = {}
            for f in self._facts:
                by_cat[f.category] = by_cat.get(f.category, 0) + 1

            return {
                "total_facts": len(self._facts),
                "categories": by_cat,
                "sources": {
                    "user": sum(1 for f in self._facts if f.source == "user"),
                    "auto": sum(1 for f in self._facts if f.source == "auto"),
                    "llm": sum(1 for f in self._facts if f.source == "llm"),
                },
                "avg_confidence": round(
                    sum(f.confidence for f in self._facts) / max(len(self._facts), 1), 2
                ),
                "has_embeddings": sum(1 for f in self._facts if f.embedding),
            }

    # --- Duplicate detection ---

    def _is_duplicate(self, new_content):
        """Check if a fact is duplicate using substring + word overlap."""
        new_lower = new_content.lower().strip()
        new_words = set(new_lower.split())

        for f in self._facts:
            existing_lower = f.content.lower()
            # Exact or substring match
            if new_lower in existing_lower or existing_lower in new_lower:
                return True
            # High word overlap (>= 70%)
            existing_words = set(existing_lower.split())
            if not new_words or not existing_words:
                continue
            overlap = new_words & existing_words
            ratio = len(overlap) / min(len(new_words), len(existing_words))
            if ratio >= 0.7:
                return True

        return False


# --- Singleton ---
memory_store = MemoryStore()
