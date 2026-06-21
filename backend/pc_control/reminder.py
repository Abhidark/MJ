"""
Reminder/Timer system for MJ.
Supports: "5 min baad yaad dila", "3 baje remind kar", "timer 10 minutes"
Uses threading for background timers + Windows notifications.
"""

import re
import threading
import subprocess
from datetime import datetime, timedelta

# Active reminders list
active_reminders = []


def send_windows_notification(title: str, message: str):
    """Send a Windows toast notification."""
    ps = f'''
Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.Visible = $true
$n.ShowBalloonTip(10000, "{title}", "{message}", [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Seconds 11
$n.Dispose()
'''
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps],
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
    except Exception:
        pass


def reminder_callback(reminder_id: str, message: str):
    """Called when a reminder fires."""
    send_windows_notification("MJ Reminder", message)
    # Remove from active list
    global active_reminders
    active_reminders = [r for r in active_reminders if r["id"] != reminder_id]


def parse_reminder(text: str) -> dict | None:
    """
    Parse reminder/timer commands from user text.
    Returns: {"delay_seconds": int, "message": str, "time_desc": str} or None
    """
    lower = text.lower().strip()

    # ---- TIMER: "timer 5 minutes", "10 min timer" ----
    timer_patterns = [
        r"(?:timer|alarm)\s+(?:for\s+)?(\d+)\s*(min(?:ute)?s?|sec(?:ond)?s?|hour?s?|ghante?|mint?)",
        r"(\d+)\s*(min(?:ute)?s?|sec(?:ond)?s?|hour?s?|ghante?|mint?)\s+(?:ka\s+)?(?:timer|alarm)",
    ]
    for pat in timer_patterns:
        m = re.search(pat, lower)
        if m:
            amount = int(m.group(1))
            unit = m.group(2)
            seconds = _to_seconds(amount, unit)
            return {
                "delay_seconds": seconds,
                "message": f"Timer done! {amount} {unit} ho gaye.",
                "time_desc": f"{amount} {unit}"
            }

    # ---- REMIND IN: "5 min baad yaad dila", "remind me in 10 minutes to call" ----
    remind_in_patterns = [
        r"(\d+)\s*(min(?:ute)?s?|sec(?:ond)?s?|hour?s?|ghante?|mint?)\s+(?:baad|me|mein|bad|later)\s+(.+)",
        r"(?:remind|yaad|reminder)\s+(?:me\s+)?(?:in\s+)?(\d+)\s*(min(?:ute)?s?|sec(?:ond)?s?|hour?s?|ghante?|mint?)\s*(?:to\s+|ke liye\s+|ka\s+)?(.+)?",
        r"(\d+)\s*(min(?:ute)?s?|sec(?:ond)?s?|hour?s?|ghante?|mint?)\s+(?:baad|bad|ke baad)\s*(.+)?",
    ]
    for pat in remind_in_patterns:
        m = re.search(pat, lower)
        if m:
            amount = int(m.group(1))
            unit = m.group(2)
            msg = m.group(3).strip() if m.group(3) else "Reminder time!"
            # Clean up message
            for filler in ["yaad dila", "yaad dilao", "remind", "reminder", "bata", "bol"]:
                msg = msg.replace(filler, "").strip()
            if not msg or len(msg) < 2:
                msg = "Reminder time!"
            seconds = _to_seconds(amount, unit)
            return {
                "delay_seconds": seconds,
                "message": msg,
                "time_desc": f"{amount} {unit}"
            }

    # ---- REMIND AT: "3 baje remind kar", "remind at 5:30 pm" ----
    at_patterns = [
        r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|baje)\s+(?:ko\s+)?(?:remind|yaad|reminder|bol|bata)\s*(.+)?",
        r"(?:remind|yaad|reminder)\s+(?:me\s+)?(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm|baje)\s*(?:to\s+|ke liye\s+)?(.+)?",
    ]
    for pat in at_patterns:
        m = re.search(pat, lower)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2)) if m.group(2) else 0
            period = m.group(3)
            msg = m.group(4).strip() if m.group(4) else "Reminder time!"

            # Convert to 24h
            if period in ["pm"] and hour < 12:
                hour += 12
            elif period in ["am"] and hour == 12:
                hour = 0
            elif period == "baje":
                # Assume PM if hour <= 6 (evening context)
                if hour <= 6:
                    hour += 12

            now = datetime.now()
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)

            seconds = int((target - now).total_seconds())
            time_str = target.strftime("%I:%M %p")

            if not msg or len(msg) < 2:
                msg = "Reminder time!"

            return {
                "delay_seconds": seconds,
                "message": msg,
                "time_desc": f"{time_str}"
            }

    # ---- Simple: "yaad dila X", "remind me X" (default 5 min) ----
    simple_patterns = [
        r"(?:yaad dila|yaad dilao|remind me|reminder set)\s+(.+)",
    ]
    for pat in simple_patterns:
        m = re.search(pat, lower)
        if m:
            msg = m.group(1).strip()
            for filler in ["karo", "kar", "do", "please", "to"]:
                msg = msg.replace(filler, "").strip()
            if msg and len(msg) > 2:
                return {
                    "delay_seconds": 300,  # default 5 min
                    "message": msg,
                    "time_desc": "5 minutes"
                }

    return None


def set_reminder(delay_seconds: int, message: str) -> str:
    """Set a reminder that fires after delay_seconds."""
    reminder_id = f"rem_{datetime.now().strftime('%H%M%S')}_{len(active_reminders)}"
    fire_time = datetime.now() + timedelta(seconds=delay_seconds)

    timer = threading.Timer(delay_seconds, reminder_callback, args=[reminder_id, message])
    timer.daemon = True
    timer.start()

    reminder_info = {
        "id": reminder_id,
        "message": message,
        "fire_time": fire_time.strftime("%I:%M %p"),
        "timer": timer
    }
    active_reminders.append(reminder_info)
    return reminder_id


def get_active_reminders() -> list:
    """Get list of active reminders."""
    return [{"id": r["id"], "message": r["message"], "fire_time": r["fire_time"]} for r in active_reminders]


def cancel_reminder(reminder_id: str) -> bool:
    """Cancel a reminder by ID."""
    global active_reminders
    for r in active_reminders:
        if r["id"] == reminder_id:
            r["timer"].cancel()
            active_reminders = [x for x in active_reminders if x["id"] != reminder_id]
            return True
    return False


def _to_seconds(amount: int, unit: str) -> int:
    """Convert amount + unit to seconds."""
    unit = unit.lower()
    if unit.startswith("sec"):
        return amount
    elif unit.startswith("min") or unit.startswith("mint"):
        return amount * 60
    elif unit.startswith("hour") or unit.startswith("ghant"):
        return amount * 3600
    return amount * 60  # default minutes
