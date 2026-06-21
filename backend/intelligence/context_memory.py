"""
MJ Intelligence: Context Memory System
- Tracks conversation patterns and topics
- Learns user preferences over time
- Time-aware context (morning/evening behavior)
- Personality adaptation based on interaction history
- Long-term learning with decay
"""

import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
from typing import Optional


MEMORY_DIR = Path(__file__).parent.parent / "context_memory"
MEMORY_DIR.mkdir(exist_ok=True)

PREFERENCES_FILE = MEMORY_DIR / "preferences.json"
PATTERNS_FILE = MEMORY_DIR / "patterns.json"
TOPICS_FILE = MEMORY_DIR / "topics.json"
INTERACTIONS_FILE = MEMORY_DIR / "interactions.json"


def _load_json(filepath: Path) -> dict:
    if filepath.exists():
        try:
            return json.loads(filepath.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_json(filepath: Path, data: dict):
    filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def record_interaction(message: str, response: str, emotion: str = "neutral"):
    """Record a user interaction for pattern learning."""
    interactions = _load_json(INTERACTIONS_FILE)
    if "history" not in interactions:
        interactions["history"] = []
        interactions["stats"] = {
            "total_messages": 0,
            "sessions": 0,
            "avg_msg_length": 0,
            "languages": {},
            "time_distribution": {}
        }

    now = datetime.now()
    hour = now.hour
    time_slot = "morning" if 5 <= hour < 12 else "afternoon" if 12 <= hour < 17 else "evening" if 17 <= hour < 22 else "night"
    day_name = now.strftime("%A").lower()

    entry = {
        "timestamp": now.isoformat(),
        "hour": hour,
        "time_slot": time_slot,
        "day": day_name,
        "message_length": len(message),
        "emotion": emotion,
        "topics": _extract_topics(message),
        "language": _detect_language(message),
        "is_command": _is_command(message)
    }

    interactions["history"].append(entry)
    # Keep last 500 interactions
    interactions["history"] = interactions["history"][-500:]

    # Update stats
    stats = interactions["stats"]
    stats["total_messages"] = stats.get("total_messages", 0) + 1
    stats["avg_msg_length"] = (
        (stats.get("avg_msg_length", 0) * (stats["total_messages"] - 1) + len(message))
        / stats["total_messages"]
    )

    # Time distribution
    time_dist = stats.get("time_distribution", {})
    time_dist[time_slot] = time_dist.get(time_slot, 0) + 1
    stats["time_distribution"] = time_dist

    # Language tracking
    lang = entry["language"]
    langs = stats.get("languages", {})
    langs[lang] = langs.get(lang, 0) + 1
    stats["languages"] = langs

    _save_json(INTERACTIONS_FILE, interactions)

    # Update topic memory
    _update_topics(entry["topics"])

    # Update preferences
    _update_preferences(message, time_slot, emotion)


def _extract_topics(text: str) -> list:
    """Extract topic keywords from text."""
    lower = text.lower()
    topics = []

    topic_map = {
        "coding": ["code", "python", "javascript", "program", "debug", "function", "api", "error", "bug"],
        "music": ["music", "song", "play", "spotify", "gaana", "playlist", "artist"],
        "weather": ["weather", "mausam", "temperature", "rain", "barish", "garmi", "sardi"],
        "news": ["news", "khabar", "update", "latest", "trending"],
        "email": ["email", "mail", "inbox", "send", "reply"],
        "files": ["file", "folder", "download", "open", "save", "delete", "move", "copy"],
        "system": ["cpu", "ram", "memory", "disk", "battery", "process", "kill", "restart"],
        "entertainment": ["movie", "show", "game", "youtube", "video", "watch", "film"],
        "productivity": ["task", "todo", "reminder", "schedule", "meeting", "deadline", "calendar"],
        "learning": ["learn", "explain", "teach", "tutorial", "how to", "guide", "kaise"],
        "creative": ["image", "generate", "create", "design", "draw", "write", "story"],
        "health": ["health", "exercise", "sleep", "calories", "weight", "steps", "medicine"],
        "social": ["message", "chat", "call", "whatsapp", "instagram", "facebook"],
    }

    for topic, keywords in topic_map.items():
        if any(kw in lower for kw in keywords):
            topics.append(topic)

    return topics


def _detect_language(text: str) -> str:
    """Simple language detection: Hindi, English, or Mixed."""
    hindi_chars = len(re.findall(r'[ऀ-ॿ]', text))
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    hinglish_words = ["hai", "karo", "kya", "kaise", "bata", "kar", "ho", "nahi",
                      "acha", "theek", "haan", "nahi", "abhi", "kuch", "mujhe"]
    has_hinglish = any(w in text.lower().split() for w in hinglish_words)

    if hindi_chars > english_chars:
        return "hindi"
    elif has_hinglish and hindi_chars == 0:
        return "hinglish"
    else:
        return "english"


def _is_command(text: str) -> bool:
    """Check if message is a command vs conversation."""
    command_indicators = [
        "open", "close", "start", "stop", "play", "pause", "set",
        "search", "find", "show", "create", "delete", "run",
        "karo", "kholo", "band karo", "dikhao", "hatao", "chalo"
    ]
    lower = text.lower().strip()
    return any(lower.startswith(c) or f" {c} " in f" {lower} " for c in command_indicators)


def _update_topics(topics: list):
    """Update topic frequency and trends."""
    topic_data = _load_json(TOPICS_FILE)
    if "frequency" not in topic_data:
        topic_data = {"frequency": {}, "recent": [], "trends": {}}

    for t in topics:
        topic_data["frequency"][t] = topic_data["frequency"].get(t, 0) + 1

    topic_data["recent"] = (topics + topic_data.get("recent", []))[:50]
    _save_json(TOPICS_FILE, topic_data)


def _update_preferences(message: str, time_slot: str, emotion: str):
    """Learn user preferences from interactions."""
    prefs = _load_json(PREFERENCES_FILE)
    if "response_style" not in prefs:
        prefs = {
            "response_style": {
                "prefers_hindi": 0,
                "prefers_english": 0,
                "prefers_hinglish": 0,
                "prefers_brief": 0,
                "prefers_detailed": 0,
            },
            "active_times": {},
            "common_emotions": {},
            "favorite_topics": [],
            "personality_notes": []
        }

    # Language preference
    lang = _detect_language(message)
    prefs["response_style"][f"prefers_{lang}"] = prefs["response_style"].get(f"prefers_{lang}", 0) + 1

    # Message length preference
    if len(message) < 30:
        prefs["response_style"]["prefers_brief"] = prefs["response_style"].get("prefers_brief", 0) + 1
    elif len(message) > 100:
        prefs["response_style"]["prefers_detailed"] = prefs["response_style"].get("prefers_detailed", 0) + 1

    # Active time tracking
    active = prefs.get("active_times", {})
    active[time_slot] = active.get(time_slot, 0) + 1
    prefs["active_times"] = active

    # Emotion tracking
    emotions = prefs.get("common_emotions", {})
    emotions[emotion] = emotions.get(emotion, 0) + 1
    prefs["common_emotions"] = emotions

    _save_json(PREFERENCES_FILE, prefs)


def get_context_prompt() -> str:
    """
    Generate a context-aware prompt addition based on learned patterns.
    This adapts MJ's personality to the user's style.
    """
    prefs = _load_json(PREFERENCES_FILE)
    interactions = _load_json(INTERACTIONS_FILE)
    topics = _load_json(TOPICS_FILE)

    if not prefs or not interactions.get("stats"):
        return ""

    parts = []
    stats = interactions.get("stats", {})
    now = datetime.now()
    hour = now.hour
    time_slot = "morning" if 5 <= hour < 12 else "afternoon" if 12 <= hour < 17 else "evening" if 17 <= hour < 22 else "night"

    # Language preference
    style = prefs.get("response_style", {})
    lang_scores = {
        "hinglish": style.get("prefers_hinglish", 0),
        "hindi": style.get("prefers_hindi", 0),
        "english": style.get("prefers_english", 0),
    }
    preferred_lang = max(lang_scores, key=lang_scores.get)
    if lang_scores[preferred_lang] > 5:
        if preferred_lang == "hinglish":
            parts.append("User prefers Hinglish (mix of Hindi + English). Reply in Hinglish naturally.")
        elif preferred_lang == "hindi":
            parts.append("User prefers Hindi. Reply in Hindi when possible.")

    # Brevity preference
    if style.get("prefers_brief", 0) > style.get("prefers_detailed", 0) * 2:
        parts.append("User prefers brief, concise replies. Keep answers short.")
    elif style.get("prefers_detailed", 0) > style.get("prefers_brief", 0) * 2:
        parts.append("User likes detailed explanations. Give thorough answers.")

    # Time-aware greeting context
    active_times = prefs.get("active_times", {})
    most_active = max(active_times, key=active_times.get) if active_times else None
    if most_active:
        parts.append(f"User is most active during {most_active}. Current time: {time_slot}.")

    # Topic interests
    freq = topics.get("frequency", {})
    if freq:
        top_topics = sorted(freq, key=freq.get, reverse=True)[:5]
        parts.append(f"User's top interests: {', '.join(top_topics)}.")

    # Interaction maturity
    total = stats.get("total_messages", 0)
    if total > 100:
        parts.append("You know this user well. Be warm and familiar, like a close friend.")
    elif total > 30:
        parts.append("You're getting to know this user. Be friendly and remember their patterns.")

    # Emotion context
    emotions = prefs.get("common_emotions", {})
    if emotions:
        dominant_emotion = max(emotions, key=emotions.get)
        if dominant_emotion == "stressed":
            parts.append("User often seems stressed. Be extra supportive and calming.")
        elif dominant_emotion == "happy":
            parts.append("User is generally in a good mood. Match their energy.")

    if not parts:
        return ""

    return "\n\nCONTEXT MEMORY (learned from past interactions):\n" + "\n".join(f"- {p}" for p in parts)


def get_memory_stats() -> dict:
    """Get context memory statistics."""
    prefs = _load_json(PREFERENCES_FILE)
    interactions = _load_json(INTERACTIONS_FILE)
    topics = _load_json(TOPICS_FILE)

    stats = interactions.get("stats", {})
    freq = topics.get("frequency", {})
    top_topics = sorted(freq, key=freq.get, reverse=True)[:5] if freq else []

    style = prefs.get("response_style", {})
    lang_scores = {
        "hinglish": style.get("prefers_hinglish", 0),
        "hindi": style.get("prefers_hindi", 0),
        "english": style.get("prefers_english", 0),
    }
    preferred_lang = max(lang_scores, key=lang_scores.get) if any(lang_scores.values()) else "unknown"

    return {
        "total_interactions": stats.get("total_messages", 0),
        "avg_message_length": round(stats.get("avg_msg_length", 0)),
        "preferred_language": preferred_lang,
        "top_topics": top_topics,
        "active_times": prefs.get("active_times", {}),
        "common_emotions": prefs.get("common_emotions", {}),
        "learning_status": "active" if stats.get("total_messages", 0) > 0 else "not started"
    }
