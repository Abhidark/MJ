"""
MJ Hermes: Unified Messaging Hub
Send messages across platforms via webhooks and APIs:
  - Discord (webhook URL)
  - Slack (webhook URL)
  - Telegram (Bot API token + chat ID)
  - WhatsApp (Twilio API)
  - SMS (Twilio API)
Config stored in messaging_config.json. No heavy dependencies.
"""

import json
import logging
import time
import re
import httpx
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("mj.hermes.messaging")

CONFIG_FILE = Path(__file__).parent.parent.parent / "messaging_config.json"
MSG_HISTORY_FILE = Path(__file__).parent.parent.parent / "messaging_history.json"

DEFAULT_CONFIG = {
    "discord": {
        "enabled": False,
        "webhook_url": "",
        "username": "MJ Assistant",
    },
    "slack": {
        "enabled": False,
        "webhook_url": "",
        "username": "MJ Assistant",
        "channel": "",
    },
    "telegram": {
        "enabled": False,
        "bot_token": "",
        "chat_id": "",
    },
    "whatsapp": {
        "enabled": False,
        "twilio_sid": "",
        "twilio_token": "",
        "from_number": "",  # Twilio WhatsApp number: whatsapp:+14155238886
        "to_number": "",    # User's WhatsApp: whatsapp:+91XXXXXXXXXX
    },
    "sms": {
        "enabled": False,
        "twilio_sid": "",
        "twilio_token": "",
        "from_number": "",
        "to_number": "",
    },
}


class MessagingHub:
    """Unified messaging across Discord, Slack, Telegram, WhatsApp, SMS."""

    def __init__(self):
        self.config = self._load_config()
        self.history: List[dict] = self._load_history()

    # ========================
    # DISCORD (Webhook)
    # ========================

    async def send_discord(self, message: str, username: str = None) -> dict:
        """Send message to Discord channel via webhook."""
        cfg = self.config.get("discord", {})
        if not cfg.get("enabled") or not cfg.get("webhook_url"):
            return {"success": False, "error": "Discord not configured. Set webhook URL in settings."}

        payload = {
            "content": message,
            "username": username or cfg.get("username", "MJ Assistant"),
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(cfg["webhook_url"], json=payload)
                success = resp.status_code in (200, 204)
                self._log("discord", message, success)
                return {
                    "success": success,
                    "platform": "discord",
                    "status_code": resp.status_code,
                    "message": message[:100],
                }
        except Exception as e:
            self._log("discord", message, False, str(e))
            return {"success": False, "error": str(e)}

    # ========================
    # SLACK (Webhook)
    # ========================

    async def send_slack(self, message: str, channel: str = None) -> dict:
        """Send message to Slack channel via webhook."""
        cfg = self.config.get("slack", {})
        if not cfg.get("enabled") or not cfg.get("webhook_url"):
            return {"success": False, "error": "Slack not configured. Set webhook URL in settings."}

        payload = {
            "text": message,
            "username": cfg.get("username", "MJ Assistant"),
        }
        if channel or cfg.get("channel"):
            payload["channel"] = channel or cfg["channel"]

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(cfg["webhook_url"], json=payload)
                success = resp.status_code == 200 and resp.text == "ok"
                self._log("slack", message, success)
                return {
                    "success": success,
                    "platform": "slack",
                    "status_code": resp.status_code,
                    "message": message[:100],
                }
        except Exception as e:
            self._log("slack", message, False, str(e))
            return {"success": False, "error": str(e)}

    # ========================
    # TELEGRAM (Bot API)
    # ========================

    async def send_telegram(self, message: str, chat_id: str = None) -> dict:
        """Send message via Telegram Bot API."""
        cfg = self.config.get("telegram", {})
        if not cfg.get("enabled") or not cfg.get("bot_token"):
            return {"success": False, "error": "Telegram not configured. Set bot_token and chat_id in settings."}

        target_chat = chat_id or cfg.get("chat_id", "")
        if not target_chat:
            return {"success": False, "error": "No Telegram chat_id configured."}

        url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage"
        payload = {
            "chat_id": target_chat,
            "text": message,
            "parse_mode": "Markdown",
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                data = resp.json()
                success = data.get("ok", False)
                self._log("telegram", message, success)
                return {
                    "success": success,
                    "platform": "telegram",
                    "message_id": data.get("result", {}).get("message_id"),
                    "message": message[:100],
                }
        except Exception as e:
            self._log("telegram", message, False, str(e))
            return {"success": False, "error": str(e)}

    # ========================
    # WHATSAPP (Twilio API)
    # ========================

    async def send_whatsapp(self, message: str, to_number: str = None) -> dict:
        """Send WhatsApp message via Twilio API."""
        cfg = self.config.get("whatsapp", {})
        if not cfg.get("enabled") or not cfg.get("twilio_sid"):
            return {"success": False, "error": "WhatsApp not configured. Set Twilio credentials in settings."}

        to = to_number or cfg.get("to_number", "")
        from_num = cfg.get("from_number", "")
        if not to or not from_num:
            return {"success": False, "error": "WhatsApp from/to numbers not configured."}

        # Ensure whatsapp: prefix
        if not to.startswith("whatsapp:"):
            to = f"whatsapp:{to}"
        if not from_num.startswith("whatsapp:"):
            from_num = f"whatsapp:{from_num}"

        url = f"https://api.twilio.com/2010-04-01/Accounts/{cfg['twilio_sid']}/Messages.json"
        payload = {
            "From": from_num,
            "To": to,
            "Body": message,
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    url, data=payload,
                    auth=(cfg["twilio_sid"], cfg["twilio_token"]),
                )
                data = resp.json()
                success = resp.status_code in (200, 201)
                self._log("whatsapp", message, success)
                return {
                    "success": success,
                    "platform": "whatsapp",
                    "sid": data.get("sid", ""),
                    "message": message[:100],
                }
        except Exception as e:
            self._log("whatsapp", message, False, str(e))
            return {"success": False, "error": str(e)}

    # ========================
    # SMS (Twilio API)
    # ========================

    async def send_sms(self, message: str, to_number: str = None) -> dict:
        """Send SMS via Twilio API."""
        cfg = self.config.get("sms", {})
        if not cfg.get("enabled") or not cfg.get("twilio_sid"):
            return {"success": False, "error": "SMS not configured. Set Twilio credentials in settings."}

        to = to_number or cfg.get("to_number", "")
        from_num = cfg.get("from_number", "")
        if not to or not from_num:
            return {"success": False, "error": "SMS from/to numbers not configured."}

        url = f"https://api.twilio.com/2010-04-01/Accounts/{cfg['twilio_sid']}/Messages.json"
        payload = {
            "From": from_num,
            "To": to,
            "Body": message,
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    url, data=payload,
                    auth=(cfg["twilio_sid"], cfg["twilio_token"]),
                )
                data = resp.json()
                success = resp.status_code in (200, 201)
                self._log("sms", message, success)
                return {
                    "success": success,
                    "platform": "sms",
                    "sid": data.get("sid", ""),
                    "message": message[:100],
                }
        except Exception as e:
            self._log("sms", message, False, str(e))
            return {"success": False, "error": str(e)}

    # ========================
    # UNIFIED SEND
    # ========================

    async def send(self, platform: str, message: str, **kwargs) -> dict:
        """Send message to any platform by name."""
        senders = {
            "discord": self.send_discord,
            "slack": self.send_slack,
            "telegram": self.send_telegram,
            "whatsapp": self.send_whatsapp,
            "sms": self.send_sms,
        }
        sender = senders.get(platform.lower())
        if not sender:
            return {"success": False, "error": f"Unknown platform: {platform}. Options: {', '.join(senders.keys())}"}
        return await sender(message, **kwargs)

    async def broadcast(self, message: str, platforms: List[str] = None) -> dict:
        """Send message to multiple platforms at once."""
        if not platforms:
            platforms = [p for p, cfg in self.config.items() if cfg.get("enabled")]

        results = {}
        for platform in platforms:
            results[platform] = await self.send(platform, message)

        return {
            "broadcast": True,
            "results": results,
            "sent": sum(1 for r in results.values() if r.get("success")),
            "failed": sum(1 for r in results.values() if not r.get("success")),
        }

    def detect_platform(self, text: str) -> Optional[str]:
        """Detect which messaging platform the user wants from text."""
        text_lower = text.lower()
        platform_patterns = {
            "discord": r"\bdiscord\b",
            "slack": r"\bslack\b",
            "telegram": r"\btelegram\b",
            "whatsapp": r"\bwhatsapp\b|\bwa\b",
            "sms": r"\bsms\b|\btext\s+message\b|\bmessage\s+send\b",
        }
        for platform, pattern in platform_patterns.items():
            if re.search(pattern, text_lower):
                return platform
        return None

    def extract_message(self, text: str) -> str:
        """Extract the message content from user text."""
        # Remove platform names and command words
        msg = text
        msg = re.sub(
            r"(?:send|post|message|msg|bhej|bhejo|likh|likho)\s+"
            r"(?:on|to|via|through|pe|par|me|mein)?\s*"
            r"(?:discord|slack|telegram|whatsapp|sms|wa)\s*[:\-]?\s*",
            "", msg, flags=re.IGNORECASE
        )
        msg = re.sub(
            r"(?:discord|slack|telegram|whatsapp|sms|wa)\s+"
            r"(?:pe|par|me|mein|on|to)?\s*"
            r"(?:send|post|message|msg|bhej|bhejo|likh|likho)\s*[:\-]?\s*",
            "", msg, flags=re.IGNORECASE
        )
        msg = re.sub(r"^(?:send|post|bhej|bhejo)\s+(?:message|msg)?\s*[:\-]?\s*", "", msg, flags=re.IGNORECASE)
        msg = msg.strip().strip('"').strip("'")
        return msg if msg else "Hello from MJ Assistant!"

    # ========================
    # CONFIG & HISTORY
    # ========================

    def get_config(self) -> dict:
        """Get config (masks sensitive fields)."""
        safe = {}
        for platform, cfg in self.config.items():
            safe[platform] = {}
            for k, v in cfg.items():
                if k in ("twilio_token", "twilio_sid", "bot_token") and v:
                    safe[platform][k] = v[:4] + "..." + v[-4:] if len(v) > 8 else "***"
                elif k == "webhook_url" and v:
                    safe[platform][k] = v[:30] + "..."
                else:
                    safe[platform][k] = v
        return safe

    def update_config(self, platform: str, settings: dict) -> dict:
        """Update config for a specific platform."""
        if platform not in self.config:
            return {"success": False, "error": f"Unknown platform: {platform}"}
        self.config[platform].update(settings)
        self._save_config()
        return {"success": True, "platform": platform}

    def get_enabled_platforms(self) -> List[str]:
        """Get list of enabled platforms."""
        return [p for p, cfg in self.config.items() if cfg.get("enabled")]

    def get_history(self, limit: int = 50, platform: str = None) -> List[dict]:
        """Get messaging history."""
        h = self.history
        if platform:
            h = [m for m in h if m.get("platform") == platform]
        return h[-limit:]

    def get_stats(self) -> dict:
        """Get messaging statistics."""
        by_platform = {}
        for m in self.history:
            p = m.get("platform", "unknown")
            if p not in by_platform:
                by_platform[p] = {"total": 0, "success": 0, "failed": 0}
            by_platform[p]["total"] += 1
            if m.get("success"):
                by_platform[p]["success"] += 1
            else:
                by_platform[p]["failed"] += 1

        return {
            "total_messages": len(self.history),
            "enabled_platforms": self.get_enabled_platforms(),
            "by_platform": by_platform,
        }

    # ========================
    # INTERNAL
    # ========================

    def _log(self, platform: str, message: str, success: bool, error: str = ""):
        self.history.append({
            "platform": platform,
            "message": message[:200],
            "success": success,
            "error": error,
            "timestamp": time.time(),
            "time_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        if len(self.history) > 500:
            self.history = self.history[-500:]
        self._save_history()

    def _load_config(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                # Merge with defaults for any missing platforms
                merged = {**DEFAULT_CONFIG}
                for k, v in data.items():
                    if k in merged and isinstance(v, dict):
                        merged[k] = {**merged[k], **v}
                    else:
                        merged[k] = v
                return merged
            except Exception:
                pass
        return {**DEFAULT_CONFIG}

    def _save_config(self):
        try:
            CONFIG_FILE.write_text(json.dumps(self.config, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save messaging config: {e}")

    def _load_history(self) -> list:
        if MSG_HISTORY_FILE.exists():
            try:
                return json.loads(MSG_HISTORY_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _save_history(self):
        try:
            MSG_HISTORY_FILE.write_text(
                json.dumps(self.history[-500:], indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"Failed to save messaging history: {e}")


# Singleton
messaging_hub = MessagingHub()
