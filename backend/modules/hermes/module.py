"""
Hermes Module v2 — Notifications, Reminders & Alerts for MJ Assistant.
Desktop toast notifications (Windows), scheduled reminders with persistent history,
and reminder management (list, cancel, snooze).
"""

import re
import subprocess
import json
import time
import asyncio
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from modules.base_module import BaseModule

logger = logging.getLogger("mj.hermes")

REMINDERS_FILE = Path(__file__).parent.parent.parent / "hermes_reminders.json"
HISTORY_FILE = Path(__file__).parent.parent.parent / "hermes_history.json"


class HermesModule(BaseModule):
    name = "hermes"
    display_name = "Hermes"
    icon = "📡"
    description = "Notifications & Reminders — desktop alerts, scheduled reminders, notification history"
    version = "2.0"
    category = "utility"
    enabled = True

    _notification_sound = True
    _max_history = 100
    _scheduler_running = False
    _scheduler_thread = None

    NOTIFICATION_KEYWORDS = re.compile(
        r"\b(notify|notification|alert|desktop\s+alert|toast|popup?\s*notification|"
        r"show\s+(?:alert|notification)|send\s+notification|suchit\s+kar|notify\s+kar)\b",
        re.IGNORECASE,
    )

    REMINDER_KEYWORDS = re.compile(
        r"\b(remind\s+me|reminder|set\s+(?:a\s+)?reminder|yaad\s+dila|"
        r"(?:in\s+)?(\d+)\s+(?:min(?:ute)?s?|hour?s?|sec(?:ond)?s?)\s+(?:me|mein|mujhe|baad)|"
        r"(\d+)\s+(?:min(?:ute)?s?|hour?s?)\s+(?:later|after|baad)|"
        r"remind\s+(?:after|in)|"
        r"(?:baad|baje)\s+(?:mein|me)\s+(?:yaad|remind|batana))\b",
        re.IGNORECASE,
    )

    HISTORY_KEYWORDS = re.compile(
        r"\b(notification\s+history|show\s+(?:my\s+)?(?:notifications?|reminders?|alerts?)|"
        r"list\s+(?:my\s+)?(?:reminders?|notifications?)|"
        r"pending\s+reminders?|active\s+reminders?|"
        r"cancel\s+reminder|delete\s+reminder|remove\s+reminder|"
        r"snooze\s+reminder)\b",
        re.IGNORECASE,
    )

    def __init__(self):
        self._reminders = self._load_reminders()
        self._history = self._load_history()
        self._start_scheduler()

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        if self.REMINDER_KEYWORDS.search(text):
            return 0.95

        if self.HISTORY_KEYWORDS.search(text):
            return 0.93

        if self.NOTIFICATION_KEYWORDS.search(text):
            return 0.90

        if intent in ("notification", "reminder", "alert"):
            return 0.85

        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        """Route to appropriate handler."""
        text_lower = text.lower()

        # Reminder management (cancel, list, snooze)
        if self.HISTORY_KEYWORDS.search(text):
            if re.search(r"cancel|delete|remove", text_lower):
                return self._cancel_reminder(text)
            if re.search(r"snooze", text_lower):
                return self._snooze_reminder(text)
            if re.search(r"(list|show|pending|active)\s*(reminder|notification)", text_lower):
                return self._list_reminders()
            if re.search(r"history", text_lower):
                return self._show_history()
            return self._list_reminders()

        # Set a reminder with delay
        if self.REMINDER_KEYWORDS.search(text):
            return self._set_reminder(text)

        # Instant notification
        if self.NOTIFICATION_KEYWORDS.search(text):
            return self._send_instant(text)

        # Fallback
        return self._send_instant(text)

    # ========================
    # INSTANT NOTIFICATION
    # ========================

    def _send_instant(self, text: str, context: dict = None) -> dict:
        title = "MJ Assistant"
        message = text

        match = re.search(
            r"(?:notify|notification|alert|remind me|reminder)[:\s]+(.+)",
            text, re.IGNORECASE,
        )
        if match:
            message = match.group(1).strip()

        success = self._send_toast(title, message)
        self._add_history("notification", message, success)

        return {
            "response": f'Notification sent: "{message}"' if success else "Failed to send notification.",
            "data": {"title": title, "message": message, "sound": self._notification_sound},
            "action": "notification_sent" if success else "error",
        }

    # ========================
    # SCHEDULED REMINDERS
    # ========================

    def _set_reminder(self, text: str) -> dict:
        """Parse and set a scheduled reminder."""
        # Extract delay (minutes, hours, seconds)
        delay_seconds = self._parse_delay(text)
        if delay_seconds is None or delay_seconds <= 0:
            return {
                "response": "I couldn't understand the time. Please say something like 'remind me in 30 minutes to take a break'.",
                "data": None, "action": "error",
            }

        # Extract the reminder message
        message = self._extract_reminder_message(text)
        if not message or len(message) < 2:
            message = "You asked me to remind you!"

        fire_at = time.time() + delay_seconds
        fire_dt = datetime.fromtimestamp(fire_at)

        reminder = {
            "id": f"rem_{int(time.time())}_{len(self._reminders)}",
            "message": message,
            "fire_at": fire_at,
            "fire_at_str": fire_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "created_at": time.time(),
            "status": "pending",
        }
        self._reminders.append(reminder)
        self._save_reminders()

        # Human-readable delay
        delay_str = self._format_duration(delay_seconds)

        return {
            "response": f'Reminder set! I\'ll notify you in {delay_str} (at {fire_dt.strftime("%I:%M %p")}): "{message}"',
            "data": {"reminder": reminder, "delay_seconds": delay_seconds},
            "action": "reminder_set",
        }

    def _parse_delay(self, text: str) -> Optional[int]:
        """Parse time delay from text. Returns seconds."""
        text_lower = text.lower()
        total = 0

        # Match patterns like "30 minutes", "2 hours", "90 seconds"
        time_matches = re.findall(r'(\d+)\s*(sec(?:ond)?s?|min(?:ute)?s?|hour?s?|hr?s?|ghante?|mint?)', text_lower)
        for amount, unit in time_matches:
            n = int(amount)
            if "sec" in unit:
                total += n
            elif "min" in unit or "mint" in unit:
                total += n * 60
            elif "hour" in unit or "hr" in unit or "ghant" in unit:
                total += n * 3600

        if total > 0:
            return total

        # Match "half hour", "half an hour"
        if re.search(r"half\s+(?:an?\s+)?hour", text_lower):
            return 1800

        # Match "quarter hour"
        if re.search(r"quarter\s+(?:an?\s+)?hour", text_lower):
            return 900

        return None

    def _extract_reminder_message(self, text: str) -> str:
        """Extract the reminder message content."""
        # Remove the time part and command words
        msg = text
        # Remove "remind me in X minutes/hours"
        msg = re.sub(r"remind\s+me\s+(?:in\s+)?\d+\s*(?:sec\w*|min\w*|hour?\w*|hr\w*|ghant\w*)\s*(?:to|that|about|se|ke\s+baad)?\s*", "", msg, flags=re.IGNORECASE)
        msg = re.sub(r"(?:in\s+)?\d+\s*(?:sec\w*|min\w*|hour?\w*)\s*(?:baad|later|after|me|mein)\s*(?:mujhe\s+)?(?:remind|yaad|batana)?\s*(?:that|to|ki|ke\s+liye)?\s*", "", msg, flags=re.IGNORECASE)
        msg = re.sub(r"^(?:set\s+(?:a\s+)?reminder\s*(?:to|for|about)?|remind\s+me\s*(?:to|about)?)\s*", "", msg, flags=re.IGNORECASE)
        msg = msg.strip()
        # Clean leading "to", "that", "about"
        msg = re.sub(r"^(to|that|about|ki|ke\s+liye)\s+", "", msg, flags=re.IGNORECASE).strip()
        return msg if msg else ""

    def _format_duration(self, seconds: int) -> str:
        if seconds >= 3600:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            return f"{h} hour{'s' if h > 1 else ''}" + (f" {m} min" if m else "")
        elif seconds >= 60:
            m = seconds // 60
            return f"{m} minute{'s' if m > 1 else ''}"
        else:
            return f"{seconds} second{'s' if seconds > 1 else ''}"

    # ========================
    # REMINDER MANAGEMENT
    # ========================

    def _list_reminders(self) -> dict:
        pending = [r for r in self._reminders if r["status"] == "pending"]
        if not pending:
            return {"response": "No pending reminders.", "data": {"reminders": []}, "action": "reminder_list"}

        lines = [f"**Pending Reminders ({len(pending)}):**"]
        for r in pending:
            fire_dt = datetime.fromtimestamp(r["fire_at"])
            remaining = max(0, r["fire_at"] - time.time())
            remaining_str = self._format_duration(int(remaining))
            lines.append(f'  • [{r["id"]}] "{r["message"]}" — in {remaining_str} (at {fire_dt.strftime("%I:%M %p")})')

        return {"response": "\n".join(lines), "data": {"reminders": pending}, "action": "reminder_list"}

    def _cancel_reminder(self, text: str) -> dict:
        # Try to find reminder ID in text
        id_match = re.search(r'(rem_\d+_\d+)', text)
        if id_match:
            rid = id_match.group(1)
            for r in self._reminders:
                if r["id"] == rid:
                    r["status"] = "cancelled"
                    self._save_reminders()
                    return {"response": f'Reminder cancelled: "{r["message"]}"', "data": {"id": rid}, "action": "reminder_cancelled"}

        # Cancel the most recent pending reminder
        pending = [r for r in self._reminders if r["status"] == "pending"]
        if pending:
            latest = pending[-1]
            latest["status"] = "cancelled"
            self._save_reminders()
            return {"response": f'Cancelled latest reminder: "{latest["message"]}"', "data": {"id": latest["id"]}, "action": "reminder_cancelled"}

        return {"response": "No pending reminders to cancel.", "data": None, "action": "error"}

    def _snooze_reminder(self, text: str) -> dict:
        # Snooze for 5 minutes by default
        snooze_mins = 5
        m = re.search(r'(\d+)\s*min', text, re.IGNORECASE)
        if m:
            snooze_mins = int(m.group(1))

        # Find the most recently fired reminder
        fired = [r for r in self._reminders if r["status"] == "fired"]
        if fired:
            latest = fired[-1]
            latest["fire_at"] = time.time() + snooze_mins * 60
            latest["fire_at_str"] = datetime.fromtimestamp(latest["fire_at"]).strftime("%Y-%m-%d %H:%M:%S")
            latest["status"] = "pending"
            self._save_reminders()
            return {
                "response": f'Snoozed for {snooze_mins} minutes: "{latest["message"]}"',
                "data": {"id": latest["id"], "snooze_minutes": snooze_mins},
                "action": "reminder_snoozed",
            }

        return {"response": "No recent reminder to snooze.", "data": None, "action": "error"}

    def _show_history(self) -> dict:
        if not self._history:
            return {"response": "Notification history is empty.", "data": {"history": []}, "action": "history"}

        recent = self._history[-20:]
        lines = [f"**Recent Notifications ({len(recent)}):**"]
        for h in reversed(recent):
            dt = datetime.fromtimestamp(h["timestamp"]).strftime("%m/%d %I:%M %p")
            status = "✅" if h.get("success") else "❌"
            lines.append(f"  {status} [{dt}] {h['type']}: {h['message'][:60]}")

        return {"response": "\n".join(lines), "data": {"history": recent}, "action": "history"}

    # ========================
    # SCHEDULER (background thread)
    # ========================

    def _start_scheduler(self):
        """Start background thread that checks reminders every 10 seconds."""
        if self._scheduler_running:
            return
        self._scheduler_running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        logger.info("Hermes reminder scheduler started")

    def _scheduler_loop(self):
        while self._scheduler_running:
            try:
                now = time.time()
                for r in self._reminders:
                    if r["status"] == "pending" and r["fire_at"] <= now:
                        # Fire the reminder!
                        success = self._send_toast("MJ Reminder", r["message"])
                        r["status"] = "fired"
                        r["fired_at"] = now
                        self._add_history("reminder", r["message"], success)
                        self._save_reminders()
                        logger.info(f"Reminder fired: {r['message']}")
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
            time.sleep(10)

    # ========================
    # TOAST NOTIFICATION
    # ========================

    def _send_toast(self, title: str, message: str) -> bool:
        """Send a Windows desktop notification via PowerShell."""
        safe_title = title.replace("'", "''")
        safe_message = message.replace("'", "''")

        sound_line = "[System.Media.SystemSounds]::Asterisk.Play();" if self._notification_sound else ""

        ps_script = f"""
Add-Type -AssemblyName System.Windows.Forms
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.BalloonTipTitle = '{safe_title}'
$notify.BalloonTipText = '{safe_message}'
$notify.Visible = $true
$notify.ShowBalloonTip(5000)
{sound_line}
Start-Sleep -Seconds 6
$notify.Dispose()
"""

        try:
            subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
            return True
        except Exception as e:
            logger.warning(f"Toast notification failed: {e}")
            return False

    # ========================
    # PERSISTENCE
    # ========================

    def _load_reminders(self) -> list:
        if REMINDERS_FILE.exists():
            try:
                return json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _save_reminders(self):
        try:
            REMINDERS_FILE.write_text(json.dumps(self._reminders, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save reminders: {e}")

    def _load_history(self) -> list:
        if HISTORY_FILE.exists():
            try:
                return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _save_history(self):
        try:
            HISTORY_FILE.write_text(json.dumps(self._history[-self._max_history:], indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save history: {e}")

    def _add_history(self, ntype: str, message: str, success: bool):
        self._history.append({
            "type": ntype,
            "message": message,
            "success": success,
            "timestamp": time.time(),
        })
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        self._save_history()

    # ========================
    # SYSTEM PROMPT & SETTINGS
    # ========================

    def get_system_prompt_addition(self) -> str:
        return (
            "You can send desktop notifications and set timed reminders. "
            "When the user asks to be reminded in X minutes/hours, extract the time delay and message. "
            "You can also list, cancel, and snooze reminders. "
            "Example: 'remind me in 30 minutes to take a break' or 'cancel reminder'."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        pending = len([r for r in self._reminders if r["status"] == "pending"])
        ctx = "[Hermes Notification Module] "
        if pending:
            ctx += f"{pending} pending reminder(s). "
        ctx += "User wants notification/reminder action."
        return ctx

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "notification_sound": self._notification_sound,
        }

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "notification_sound" in settings:
            self._notification_sound = bool(settings["notification_sound"])

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {"key": "notification_sound", "label": "Notification Sound", "type": "toggle", "value": self._notification_sound},
        ]
