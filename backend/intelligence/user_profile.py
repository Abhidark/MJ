"""
user_profile.py -- Unified User Profile for MJ-Assistant

Aggregates data from:
  - memory_store.py     (long-term facts: name, age, location, preferences)
  - learning_engine.py  (habits, language, style, topics)
  - context_memory.py   (interaction patterns, emotions, time distribution)
  - short_term_memory.py (current session context, entities)

Produces a single user profile dict and an LLM-ready prompt block.
"""

from datetime import datetime
from typing import Dict, Optional


def build_user_profile() -> Dict:
    """
    Build a complete user profile by aggregating all memory subsystems.
    Returns a dict with sections: identity, preferences, habits, session, stats.
    """
    profile = {
        "identity": {},
        "preferences": {},
        "habits": [],
        "interests": [],
        "session": {},
        "interaction_stats": {},
        "built_at": datetime.now().isoformat(),
    }

    # ── 1. Long-term facts from memory_store ──
    try:
        from intelligence.memory_store import memory_store
        facts = memory_store.get_all()

        identity = {}
        prefs = {}
        for f in facts:
            c = f.content.lower()
            if f.category == "personal":
                if "name is" in c:
                    identity["name"] = f.content.split("is")[-1].strip().rstrip(".")
                elif "age is" in c or "years" in c:
                    import re
                    m = re.search(r"(\d{1,3})", f.content)
                    if m:
                        identity["age"] = int(m.group(1))
                elif "email" in c:
                    identity["email"] = f.content.split(":")[-1].strip() if ":" in f.content else f.content
                elif "phone" in c:
                    identity["phone"] = f.content.split(":")[-1].strip() if ":" in f.content else f.content
            elif f.category == "location":
                identity["location"] = f.content
            elif f.category == "work":
                identity["work"] = f.content
            elif f.category == "preference":
                prefs[f.content] = f.confidence

        profile["identity"] = identity

        # Add all preference facts
        pref_facts = memory_store.get_by_category("preference")
        profile["preferences"]["stored"] = [f.content for f in pref_facts]

        # Memory stats
        stats = memory_store.get_stats()
        profile["interaction_stats"]["memory"] = {
            "total_facts": stats["total_facts"],
            "categories": stats["categories"],
            "has_embeddings": stats["has_embeddings"],
        }
    except Exception:
        pass

    # ── 2. Learning engine: habits, language, style ──
    try:
        from intelligence.learning_engine import learning_engine
        le_prefs = learning_engine.get_preferences()
        le_habits = learning_engine.get_habits()
        le_stats = learning_engine.get_stats()

        inferred = le_prefs.get("inferred", {})
        profile["preferences"]["language"] = inferred.get("language", "unknown")
        profile["preferences"]["detail_level"] = inferred.get("detail", "normal")
        profile["preferences"]["response_style"] = inferred.get("style", "casual")
        profile["preferences"]["top_topics"] = [t[0] for t in inferred.get("top_topics", [])]
        profile["habits"] = le_habits[:10]  # top 10 habits
        profile["interaction_stats"]["learning"] = {
            "habits_detected": le_stats.get("habits_detected", 0),
            "actions_recorded": le_stats.get("actions_recorded", 0),
        }
    except Exception:
        pass

    # ── 3. Context memory: interaction patterns, emotions ──
    try:
        from intelligence.context_memory import get_memory_stats
        ctx = get_memory_stats()
        profile["interaction_stats"]["context"] = {
            "total_interactions": ctx.get("total_interactions", 0),
            "sessions": ctx.get("sessions", 0),
            "avg_message_length": ctx.get("avg_message_length", 0),
            "preferred_language": ctx.get("preferred_language", "unknown"),
            "active_times": ctx.get("active_times", {}),
            "common_emotions": ctx.get("common_emotions", {}),
        }
        profile["interests"] = ctx.get("top_topics", [])
    except Exception:
        pass

    # ── 4. Short-term memory: current session ──
    try:
        from intelligence.short_term_memory import short_term
        stm = short_term.get_stats()
        profile["session"] = {
            "session_id": stm.get("session_id"),
            "turns": stm.get("turns_in_session", 0),
            "duration_seconds": stm.get("session_duration_seconds", 0),
            "entities": list(short_term.get_entities(min_count=1).keys())[:20],
        }
    except Exception:
        pass

    return profile


def get_profile_prompt(max_lines=15) -> str:
    """
    Generate a compact LLM system-prompt block from the user profile.
    Designed to fit in ~500 tokens.
    """
    profile = build_user_profile()
    parts = []

    # Identity
    ident = profile.get("identity", {})
    if ident.get("name"):
        parts.append("User's name: " + ident["name"])
    if ident.get("age"):
        parts.append("Age: " + str(ident["age"]))
    if ident.get("location"):
        parts.append("Location: " + ident["location"])
    if ident.get("work"):
        parts.append("Work: " + ident["work"])

    # Preferences
    prefs = profile.get("preferences", {})
    if prefs.get("language") and prefs["language"] != "unknown":
        parts.append("Preferred language: " + prefs["language"])
    if prefs.get("response_style") and prefs["response_style"] != "casual":
        parts.append("Response style: " + prefs["response_style"])
    if prefs.get("detail_level") and prefs["detail_level"] != "normal":
        parts.append("Detail preference: " + prefs["detail_level"])

    stored_prefs = prefs.get("stored", [])
    if stored_prefs:
        parts.append("Known preferences: " + "; ".join(stored_prefs[:5]))

    # Interests
    interests = profile.get("interests", [])
    if interests:
        parts.append("Top interests: " + ", ".join(interests[:5]))

    # Habits
    habits = profile.get("habits", [])
    if habits:
        habit_strs = []
        for h in habits[:3]:
            if isinstance(h, dict):
                habit_strs.append(h.get("description", str(h)))
            else:
                habit_strs.append(str(h))
        if habit_strs:
            parts.append("Habits: " + "; ".join(habit_strs))

    # Session context
    session = profile.get("session", {})
    entities = session.get("entities", [])
    if entities:
        parts.append("Current conversation mentions: " + ", ".join(entities[:10]))

    # Interaction maturity
    ctx_stats = profile.get("interaction_stats", {}).get("context", {})
    total = ctx_stats.get("total_interactions", 0)
    if total > 100:
        parts.append("Relationship: well-known user (" + str(total) + " interactions)")
    elif total > 30:
        parts.append("Relationship: familiar user (" + str(total) + " interactions)")

    # Emotion
    emotions = ctx_stats.get("common_emotions", {})
    non_neutral = {k: v for k, v in emotions.items() if k != "neutral"}
    if non_neutral:
        dominant = max(non_neutral, key=non_neutral.get)
        if sum(non_neutral.values()) > 5:
            parts.append("Usual mood: " + dominant)

    if not parts:
        return ""

    lines = parts[:max_lines]
    return "\n\nUSER PROFILE:\n" + "\n".join("- " + p for p in lines)


def get_profile_summary() -> Dict:
    """Get a compact summary suitable for API response."""
    profile = build_user_profile()
    return {
        "identity": profile.get("identity", {}),
        "preferences": {
            "language": profile.get("preferences", {}).get("language", "unknown"),
            "style": profile.get("preferences", {}).get("response_style", "casual"),
            "detail": profile.get("preferences", {}).get("detail_level", "normal"),
        },
        "interests": profile.get("interests", [])[:5],
        "habits_count": len(profile.get("habits", [])),
        "session_turns": profile.get("session", {}).get("turns", 0),
        "total_interactions": profile.get("interaction_stats", {}).get("context", {}).get("total_interactions", 0),
        "memory_facts": profile.get("interaction_stats", {}).get("memory", {}).get("total_facts", 0),
    }
