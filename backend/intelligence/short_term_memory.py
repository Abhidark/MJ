"""
short_term_memory.py -- Session-based Short-Term Memory for MJ-Assistant

Stores recent conversation context, working memory, and temporary data
that expires after a session gap or TTL.

Features:
- Sliding window of recent messages (last N turns)
- Named scratchpad slots for working context (e.g., "current_topic", "last_search_results")
- Auto-expire entries after TTL or session gap
- Entity extraction from recent conversation
- Summarization of conversation so far
"""

import time
import threading
from collections import deque
from datetime import datetime


# Session gap: 30 minutes of inactivity = new session
SESSION_GAP_SECONDS = 30 * 60

# Default TTL for scratchpad entries: 1 hour
DEFAULT_TTL = 3600

# Max conversation turns to keep
MAX_TURNS = 50

# Max entities tracked
MAX_ENTITIES = 100


class ConversationTurn:
    """A single message exchange."""
    __slots__ = ("role", "content", "timestamp", "metadata")

    def __init__(self, role, content, metadata=None):
        self.role = role  # "user" | "assistant"
        self.content = content
        self.timestamp = time.time()
        self.metadata = metadata or {}

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content[:500],  # truncate for API
            "timestamp": self.timestamp,
            "time": datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S"),
            "metadata": self.metadata,
        }


class ShortTermMemory:
    """Session-scoped working memory."""

    def __init__(self):
        self._lock = threading.Lock()
        self._turns = deque(maxlen=MAX_TURNS)
        self._scratchpad = {}  # key -> { value, expires_at, created_at }
        self._entities = {}    # entity_name -> { type, count, last_seen }
        self._session_id = None
        self._session_start = None
        self._last_activity = None
        self._turn_count = 0

    # ─── Session Management ───

    def _check_session(self):
        """Start new session if gap exceeded."""
        now = time.time()
        if self._last_activity and (now - self._last_activity) > SESSION_GAP_SECONDS:
            self._start_new_session()
        elif self._session_id is None:
            self._start_new_session()
        self._last_activity = now

    def _start_new_session(self):
        """Reset for new session, keeping entities (they decay naturally)."""
        self._turns.clear()
        self._scratchpad = {}
        self._session_id = f"s-{int(time.time())}"
        self._session_start = time.time()
        self._turn_count = 0

    # ─── Conversation Turns ───

    def add_turn(self, role, content, metadata=None):
        """Add a conversation turn."""
        with self._lock:
            self._check_session()
            turn = ConversationTurn(role, content, metadata)
            self._turns.append(turn)
            self._turn_count += 1

            # Extract entities from user messages
            if role == "user":
                self._extract_entities(content)

    def get_recent_turns(self, n=10):
        """Get last N conversation turns."""
        with self._lock:
            self._check_session()
            turns = list(self._turns)
            return [t.to_dict() for t in turns[-n:]]

    def get_context_window(self, max_chars=2000):
        """Build a context string from recent turns for LLM prompt."""
        with self._lock:
            self._check_session()
            lines = []
            total = 0
            for turn in reversed(self._turns):
                line = f"{turn.role}: {turn.content[:300]}"
                if total + len(line) > max_chars:
                    break
                lines.insert(0, line)
                total += len(line)
            return "\n".join(lines)

    # ─── Scratchpad (Named Slots) ───

    def set(self, key, value, ttl=DEFAULT_TTL):
        """Set a scratchpad value with TTL."""
        with self._lock:
            self._check_session()
            self._scratchpad[key] = {
                "value": value,
                "created_at": time.time(),
                "expires_at": time.time() + ttl if ttl else None,
            }

    def get(self, key, default=None):
        """Get a scratchpad value (returns None if expired)."""
        with self._lock:
            self._check_session()
            entry = self._scratchpad.get(key)
            if not entry:
                return default
            if entry["expires_at"] and time.time() > entry["expires_at"]:
                del self._scratchpad[key]
                return default
            return entry["value"]

    def delete(self, key):
        """Delete a scratchpad key."""
        with self._lock:
            return self._scratchpad.pop(key, None) is not None

    def get_all_slots(self):
        """Get all non-expired scratchpad entries."""
        with self._lock:
            self._check_session()
            now = time.time()
            active = {}
            expired_keys = []
            for k, v in self._scratchpad.items():
                if v["expires_at"] and now > v["expires_at"]:
                    expired_keys.append(k)
                else:
                    active[k] = {
                        "value": v["value"],
                        "age_seconds": round(now - v["created_at"]),
                        "ttl_remaining": round(v["expires_at"] - now) if v["expires_at"] else None,
                    }
            for k in expired_keys:
                del self._scratchpad[k]
            return active

    # ─── Entity Tracking ───

    def _extract_entities(self, text):
        """Extract and track named entities from text (lightweight regex)."""
        import re
        words = text.split()

        # Track capitalized words as potential entities (simple heuristic)
        for i, word in enumerate(words):
            clean = re.sub(r'[^a-zA-Z]', '', word)
            if len(clean) > 2 and clean[0].isupper() and clean not in (
                "The", "This", "That", "What", "How", "When", "Where", "Who",
                "Can", "Could", "Would", "Should", "Please", "Thanks", "Hello",
                "Hey", "Yes", "No", "Not", "But", "And", "For", "Are", "Was",
            ):
                name = clean
                now = time.time()
                if name in self._entities:
                    self._entities[name]["count"] += 1
                    self._entities[name]["last_seen"] = now
                else:
                    if len(self._entities) >= MAX_ENTITIES:
                        # Evict least recently seen
                        oldest = min(self._entities, key=lambda k: self._entities[k]["last_seen"])
                        del self._entities[oldest]
                    self._entities[name] = {
                        "type": "unknown",
                        "count": 1,
                        "last_seen": now,
                        "first_seen": now,
                    }

    def get_entities(self, min_count=2):
        """Get tracked entities with at least min_count mentions."""
        with self._lock:
            return {
                k: v for k, v in self._entities.items()
                if v["count"] >= min_count
            }

    # ─── Stats / Info ───

    def get_stats(self):
        """Get short-term memory statistics."""
        with self._lock:
            self._check_session()
            now = time.time()
            # Clean expired scratchpad entries
            active_slots = sum(
                1 for v in self._scratchpad.values()
                if not v["expires_at"] or now < v["expires_at"]
            )
            return {
                "session_id": self._session_id,
                "session_start": datetime.fromtimestamp(self._session_start).isoformat() if self._session_start else None,
                "session_duration_seconds": round(now - self._session_start) if self._session_start else 0,
                "turns_in_session": len(self._turns),
                "total_turns": self._turn_count,
                "scratchpad_slots": active_slots,
                "tracked_entities": len(self._entities),
                "last_activity": datetime.fromtimestamp(self._last_activity).isoformat() if self._last_activity else None,
            }

    def clear(self):
        """Clear all short-term memory."""
        with self._lock:
            self._turns.clear()
            self._scratchpad = {}
            self._entities = {}
            self._turn_count = 0


# ─── Singleton ───
short_term = ShortTermMemory()
