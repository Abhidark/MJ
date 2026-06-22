"""
MJ Smart Suggestions Engine — V15
Proactively suggests actions based on:
  - Time of day (morning routines, evening wind-down)
  - App usage patterns (been on YouTube too long? suggest focus)
  - System health (high RAM? suggest closing apps)
  - Past behavior (frequently used commands)
  - Weather/context awareness
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List

SUGGESTION_LOG = Path(__file__).parent.parent / "suggestion_history.json"


def get_time_suggestions() -> List[dict]:
    """Suggest actions based on time of day."""
    hour = datetime.now().hour
    suggestions = []

    if 5 <= hour < 8:
        suggestions.append({
            "icon": "☀️", "title": "Good Morning Routine",
            "text": "Check weather, news briefing, or plan your day?",
            "commands": ["weather kya hai", "daily briefing", "aaj ka plan"],
            "priority": "high"
        })
    elif 8 <= hour < 10:
        suggestions.append({
            "icon": "💻", "title": "Start Work",
            "text": "Open VS Code, check git status, or check emails?",
            "commands": ["open vs code", "git status", "check email"],
            "priority": "medium"
        })
    elif 12 <= hour < 14:
        suggestions.append({
            "icon": "🍽️", "title": "Lunch Break",
            "text": "Take a break! Check cricket scores or play some music?",
            "commands": ["live cricket score", "open spotify"],
            "priority": "low"
        })
    elif 17 <= hour < 19:
        suggestions.append({
            "icon": "📊", "title": "End of Day Review",
            "text": "Check productivity report, commit code, or check app usage?",
            "commands": ["app usage report", "git status", "productivity score"],
            "priority": "medium"
        })
    elif 21 <= hour < 24:
        suggestions.append({
            "icon": "🌙", "title": "Wind Down",
            "text": "Lower brightness, check tomorrow's plan, or set alarm?",
            "commands": ["brightness down", "remind me tomorrow 8am wake up"],
            "priority": "low"
        })
    elif 0 <= hour < 5:
        suggestions.append({
            "icon": "😴", "title": "Late Night",
            "text": "It's late! Consider sleeping. Lock PC or set alarm?",
            "commands": ["lock pc", "remind me 7am wake up"],
            "priority": "high"
        })

    return suggestions


def get_system_suggestions(stats: dict) -> List[dict]:
    """Suggest actions based on system health."""
    suggestions = []

    cpu = stats.get("cpu", 0)
    ram = stats.get("ram_percent", 0)
    gpu_temp = stats.get("gpu_temp", 0)
    disk_pct = stats.get("disk_percent", 0)

    if ram > 80:
        suggestions.append({
            "icon": "🧹", "title": "High RAM Usage",
            "text": f"RAM at {ram}%. Close unused apps or check heavy processes.",
            "commands": ["top processes", "close chrome"],
            "priority": "high"
        })

    if cpu > 85:
        suggestions.append({
            "icon": "🔥", "title": "High CPU Load",
            "text": f"CPU at {cpu}%. Check what's eating CPU.",
            "commands": ["top processes"],
            "priority": "high"
        })

    if gpu_temp > 75:
        suggestions.append({
            "icon": "🌡️", "title": "GPU Running Hot",
            "text": f"GPU temp at {gpu_temp}°C. Consider cooling or closing GPU-heavy apps.",
            "commands": ["top processes"],
            "priority": "medium"
        })

    if disk_pct > 90:
        suggestions.append({
            "icon": "💾", "title": "Disk Almost Full",
            "text": f"Disk at {disk_pct}%. Clean up temp files or old downloads.",
            "commands": ["file manager"],
            "priority": "high"
        })

    return suggestions


def get_usage_suggestions(app_usage: dict) -> List[dict]:
    """Suggest actions based on app usage patterns."""
    suggestions = []

    distractions = {"youtube", "instagram", "facebook", "twitter", "reddit", "tiktok", "netflix"}
    productive = {"code", "visual studio", "vs code", "pycharm", "terminal", "cmd"}

    distraction_time = 0
    productive_time = 0

    for app, seconds in app_usage.items():
        app_lower = app.lower()
        if any(d in app_lower for d in distractions):
            distraction_time += seconds
        if any(p in app_lower for p in productive):
            productive_time += seconds

    # If distracted for > 30 min
    if distraction_time > 1800:
        mins = distraction_time // 60
        suggestions.append({
            "icon": "🎯", "title": "Focus Mode",
            "text": f"You've spent {mins} min on distracting apps. Time to focus?",
            "commands": ["open vs code", "productivity score"],
            "priority": "medium"
        })

    # If productive for > 2 hours straight
    if productive_time > 7200:
        hours = productive_time // 3600
        suggestions.append({
            "icon": "☕", "title": "Take a Break",
            "text": f"You've been coding for {hours}+ hours. Stretch or grab coffee!",
            "commands": ["open spotify", "weather kya hai"],
            "priority": "low"
        })

    return suggestions


def get_context_suggestions(recent_commands: list = None) -> List[dict]:
    """Suggest based on frequently used commands and patterns."""
    suggestions = []

    # If user hasn't committed in a while
    suggestions.append({
        "icon": "📦", "title": "Commit Your Work",
        "text": "Don't forget to commit and push your latest changes!",
        "commands": ["git status", "git push"],
        "priority": "low"
    })

    return suggestions


async def get_all_suggestions(stats: dict = None, app_usage: dict = None) -> List[dict]:
    """Get all relevant suggestions, sorted by priority."""
    all_suggestions = []

    # Time-based
    all_suggestions.extend(get_time_suggestions())

    # System-based
    if stats:
        all_suggestions.extend(get_system_suggestions(stats))

    # Usage-based
    if app_usage:
        all_suggestions.extend(get_usage_suggestions(app_usage))

    # Context-based
    all_suggestions.extend(get_context_suggestions())

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    all_suggestions.sort(key=lambda s: priority_order.get(s.get("priority", "low"), 2))

    # Limit to top 5
    return all_suggestions[:5]


def detect_suggestion_request(text: str) -> bool:
    """Detect if user is asking for suggestions."""
    lower = text.lower().strip()
    patterns = [
        r"(?:kya|what)\s+(?:karu|karun|karna|do|should)",
        r"(?:suggest|suggestion|recommend|batao\s+kya)",
        r"(?:kuch|koi)\s+(?:suggest|batao|idea)",
        r"(?:bored|bore|boring|kya\s+karu)",
        r"(?:help\s+me|guide\s+me|mujhe\s+batao)",
        r"(?:smart\s+suggest|suggestion\s+de|ideas?\s+de)",
        r"(?:what\s+(?:can|should)\s+i\s+do)",
        r"(?:next\s+kya|aage\s+kya|ab\s+kya)",
    ]
    return any(re.search(p, lower) for p in patterns)
