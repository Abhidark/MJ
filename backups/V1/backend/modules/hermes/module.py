"""
Hermes Module -- Desktop Notifications
"""

import re
import subprocess
from modules.base_module import BaseModule


class HermesModule(BaseModule):
    name = "hermes"
    display_name = "Hermes"
    icon = "\U0001f4e1"
    description = "Desktop notifications, alerts, and reminders"
    version = "1.0"
    category = "utility"
    enabled = True

    KEYWORDS = [
        "notify", "notification", "alert", "remind me", "batao",
        "reminder", "send notification", "show alert", "desktop alert",
        "toast", "pop up", "popup notification",
    ]

    def __init__(self):
        self.notification_sound = True

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        lower = text.lower()

        for kw in self.KEYWORDS:
            if kw in lower:
                return 0.9

        if intent in ("notification", "reminder", "alert"):
            return 0.85

        if re.search(r"\b(yaad dila|suchit kar|notify kar)\b", lower):
            return 0.8

        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        # Extract title and message from the text
        title = "MJ Assistant"
        message = text

        # Try to parse "notify: <message>" or "remind me: <message>"
        match = re.search(
            r"(?:notify|notification|alert|remind me|reminder)[:\s]+(.+)",
            text, re.IGNORECASE,
        )
        if match:
            message = match.group(1).strip()

        success = self._send_notification(title, message)

        if success:
            return {
                "response": f"Notification sent: \"{message}\"",
                "data": {"title": title, "message": message, "sound": self.notification_sound},
                "action": "notification_sent",
            }
        else:
            return {
                "response": "Failed to send desktop notification.",
                "data": None,
                "action": "error",
            }

    def _send_notification(self, title: str, message: str) -> bool:
        """Send a Windows desktop notification via PowerShell."""
        # Escape single quotes for PowerShell
        safe_title = title.replace("'", "''")
        safe_message = message.replace("'", "''")

        sound_line = ""
        if self.notification_sound:
            sound_line = "[System.Media.SystemSounds]::Asterisk.Play();"

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
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return True
        except Exception:
            return False

    def get_system_prompt_addition(self) -> str:
        return (
            "You can send desktop notifications. When the user asks to be reminded "
            "or notified, extract the message and send it."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        return "[Hermes Notification Module] User wants a desktop notification or reminder."

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "notification_sound": self.notification_sound,
        }

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "notification_sound" in settings:
            self.notification_sound = settings["notification_sound"]

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "notification_sound",
                "label": "Notification Sound",
                "type": "toggle",
                "value": self.notification_sound,
            },
        ]
