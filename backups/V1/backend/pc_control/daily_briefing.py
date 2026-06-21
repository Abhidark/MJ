"""
Daily Briefing for MJ.
Triggered by greetings like "good morning", "namaste", "hello MJ".
Returns a briefing string with weather, system health, memory, reminders.
"""

import re
from datetime import datetime


def is_greeting(text: str) -> bool:
    """Check if user's message is a greeting that should trigger briefing."""
    lower = text.lower().strip()
    greetings = [
        "good morning", "good evening", "good afternoon", "good night",
        "namaste", "namaskar", "suprabhat",
        "subah ho gayi", "uth gaya", "uth gayi",
    ]
    return any(g in lower for g in greetings)


async def generate_briefing() -> str:
    """Generate a daily briefing string."""
    from pc_control.system_stats import get_system_stats
    from pc_control.reminder import get_active_reminders
    import json
    from pathlib import Path

    now = datetime.now()
    time_of_day = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
    greeting = {
        "morning": "Good morning",
        "afternoon": "Good afternoon",
        "evening": "Good evening"
    }[time_of_day]

    parts = [f"{greeting}, boss!"]
    parts.append(f"Today is {now.strftime('%A, %d %B %Y')}. Time: {now.strftime('%I:%M %p')}.")

    # System stats
    try:
        stats = get_system_stats()
        cpu = stats.get("cpu", -1)
        ram = stats.get("ram_percent", -1)
        disk = stats.get("disk_percent", -1)
        battery = stats.get("battery", -1)

        health = []
        if cpu >= 0:
            health.append(f"CPU {cpu}%")
        if ram >= 0:
            health.append(f"RAM {ram}%")
        if disk >= 0:
            health.append(f"Disk {disk}%")
        if battery >= 0:
            charging = " (charging)" if stats.get("charging") else ""
            health.append(f"Battery {battery}%{charging}")

        if health:
            parts.append("System: " + ", ".join(health) + ".")

        # Warnings
        if cpu > 80:
            parts.append("CPU load high hai — kuch heavy chal raha hai.")
        if ram > 85:
            parts.append("RAM almost full — kuch apps band karo.")
        if battery >= 0 and battery < 20 and not stats.get("charging"):
            parts.append("Battery low! Charger lagao.")
    except Exception:
        pass

    # Core memory count
    try:
        mem_file = Path(__file__).parent.parent / "core_memory.json"
        if mem_file.exists():
            facts = json.loads(mem_file.read_text(encoding="utf-8"))
            parts.append(f"Memory me {len(facts)} facts saved hain.")
    except Exception:
        pass

    # Active reminders
    try:
        reminders = get_active_reminders()
        if reminders:
            parts.append(f"{len(reminders)} active reminder(s):")
            for r in reminders[:3]:
                parts.append(f"  - {r['message']} at {r['fire_time']}")
    except Exception:
        pass

    # Uptime
    try:
        if stats.get("uptime") and stats["uptime"] != "unknown":
            parts.append(f"System uptime: {stats['uptime']}.")
    except Exception:
        pass

    parts.append("Kuch aur chahiye toh batao!")
    return " ".join(parts)
