"""
Phantom Module -- Privacy & Data Management
Clears chat history, audio cache, and manages privacy settings.
"""

import re
import json
import sys
import os
import glob as glob_mod
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.base_module import BaseModule

BACKEND_DIR = Path(__file__).parent.parent.parent
CHAT_HISTORY_FILE = BACKEND_DIR / "chat_history.json"
AUDIO_CACHE_DIR = BACKEND_DIR / "audio_cache"
UPLOADS_DIR = BACKEND_DIR / "uploads"
TODOS_FILE = BACKEND_DIR / "todos.json"


class PhantomModule(BaseModule):
    name = "phantom"
    display_name = "Phantom"
    icon = "\U0001f575"  # detective
    description = "Privacy tools -- clear history, manage cache, and protect your data"
    version = "1.0"
    category = "system"
    enabled = True

    KEYWORDS = [
        r"\bclear\s+history\b", r"\bdelete\s+chats?\b", r"\bincognito\b",
        r"\bprivacy\b", r"\bclean\s+data\b", r"\bclear\s+cache\b",
        r"\bdelete\s+data\b", r"\bclear\s+all\b", r"\bsafai\b",
        r"\bsab\s+delete\b", r"\bhistory\s+delete\b", r"\bdata\s+clean\b",
        r"\bprivate\s+mode\b", r"\berase\b", r"\bwipe\b",
        r"\bremove\s+history\b", r"\bclear\s+audio\b",
    ]

    def __init__(self):
        self.auto_clear_audio = False
        self.history_retention_days = 7

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        text_lower = text.lower()
        for pattern in self.KEYWORDS:
            if re.search(pattern, text_lower):
                return 0.9
        if intent in ("clear_history", "privacy", "clear_cache", "delete_data"):
            return 0.95
        return 0.0

    def _detect_action(self, text: str) -> str:
        text_lower = text.lower()
        if re.search(r"\bclear\s+(chat\s+)?history\b|\bdelete\s+chats?\b|\bhistory\s+(delete|clear|hata)\b", text_lower):
            return "clear_history"
        if re.search(r"\bclear\s+(audio\s+)?cache\b|\baudio\s+(delete|clear|hata)\b|\bcache\s+clear\b", text_lower):
            return "clear_audio"
        if re.search(r"\bclear\s+all\b|\bsab\s+delete\b|\bwipe\b|\berase\s+all\b|\bclean\s+all\b", text_lower):
            return "clear_all"
        if re.search(r"\bstatus\b|\bprivacy\b|\bcheck\b|\binfo\b", text_lower):
            return "status"
        if re.search(r"\bclear\b|\bclean\b|\bdelete\b|\bremove\b|\bhata\b|\bsafai\b", text_lower):
            return "clear_all"
        return "status"

    def _get_chat_history_info(self) -> dict:
        """Get info about stored chat history."""
        if not CHAT_HISTORY_FILE.exists():
            return {"exists": False, "count": 0, "size_kb": 0}

        try:
            data = json.loads(CHAT_HISTORY_FILE.read_text(encoding="utf-8"))
            messages = data if isinstance(data, list) else data.get("messages", data.get("history", []))
            size_bytes = CHAT_HISTORY_FILE.stat().st_size
            return {
                "exists": True,
                "count": len(messages) if isinstance(messages, list) else 0,
                "size_kb": round(size_bytes / 1024, 2),
                "path": str(CHAT_HISTORY_FILE),
            }
        except Exception:
            return {"exists": True, "count": 0, "size_kb": 0}

    def _get_audio_cache_info(self) -> dict:
        """Get info about audio cache files."""
        if not AUDIO_CACHE_DIR.exists():
            return {"exists": False, "count": 0, "size_kb": 0}

        audio_files = list(AUDIO_CACHE_DIR.glob("*.*"))
        total_size = sum(f.stat().st_size for f in audio_files if f.is_file())
        return {
            "exists": True,
            "count": len(audio_files),
            "size_kb": round(total_size / 1024, 2),
            "path": str(AUDIO_CACHE_DIR),
        }

    def _get_upload_info(self) -> dict:
        """Get info about uploaded files."""
        if not UPLOADS_DIR.exists():
            return {"exists": False, "count": 0, "size_kb": 0}

        files = list(UPLOADS_DIR.glob("*.*"))
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        return {
            "exists": True,
            "count": len(files),
            "size_kb": round(total_size / 1024, 2),
        }

    def _clear_chat_history(self) -> dict:
        """Clear chat history file."""
        if not CHAT_HISTORY_FILE.exists():
            return {"cleared": False, "message": "No chat history file found."}

        try:
            # Read first for count
            info = self._get_chat_history_info()
            # Write empty history
            CHAT_HISTORY_FILE.write_text(json.dumps([], indent=2), encoding="utf-8")
            return {
                "cleared": True,
                "messages_removed": info["count"],
                "size_freed_kb": info["size_kb"],
            }
        except Exception as e:
            return {"cleared": False, "message": f"Error: {str(e)}"}

    def _clear_audio_cache(self) -> dict:
        """Clear audio cache directory."""
        if not AUDIO_CACHE_DIR.exists():
            return {"cleared": False, "message": "No audio cache directory found.", "count": 0}

        try:
            info = self._get_audio_cache_info()
            count = 0
            for f in AUDIO_CACHE_DIR.glob("*.*"):
                if f.is_file():
                    f.unlink()
                    count += 1
            return {
                "cleared": True,
                "files_removed": count,
                "size_freed_kb": info["size_kb"],
            }
        except Exception as e:
            return {"cleared": False, "message": f"Error: {str(e)}", "count": 0}

    def _clear_old_data(self) -> dict:
        """Clear data older than retention period."""
        cutoff = datetime.now() - timedelta(days=self.history_retention_days)
        cleared_items = 0

        # Clear old audio files
        if AUDIO_CACHE_DIR.exists():
            for f in AUDIO_CACHE_DIR.glob("*.*"):
                if f.is_file():
                    file_time = datetime.fromtimestamp(f.stat().st_mtime)
                    if file_time < cutoff:
                        f.unlink()
                        cleared_items += 1

        return {"cleared": cleared_items, "cutoff_days": self.history_retention_days}

    def execute(self, text: str, context: dict) -> dict:
        action = self._detect_action(text)

        if action == "clear_history":
            result = self._clear_chat_history()
            if result["cleared"]:
                return {
                    "response": (
                        f"\U0001f575 **Chat History Cleared!**\n\n"
                        f"  Messages removed: {result['messages_removed']}\n"
                        f"  Space freed: {result['size_freed_kb']} KB\n\n"
                        f"Your conversation history has been wiped clean."
                    ),
                    "data": result,
                    "action": "history_cleared",
                }
            return {
                "response": f"\U0001f575 {result['message']}",
                "data": result,
                "action": "no_history",
            }

        elif action == "clear_audio":
            result = self._clear_audio_cache()
            if result["cleared"]:
                return {
                    "response": (
                        f"\U0001f575 **Audio Cache Cleared!**\n\n"
                        f"  Files removed: {result['files_removed']}\n"
                        f"  Space freed: {result['size_freed_kb']} KB"
                    ),
                    "data": result,
                    "action": "audio_cleared",
                }
            return {
                "response": f"\U0001f575 {result.get('message', 'No audio cache to clear.')}",
                "data": result,
                "action": "no_audio",
            }

        elif action == "clear_all":
            history_result = self._clear_chat_history()
            audio_result = self._clear_audio_cache()
            old_result = self._clear_old_data()

            lines = ["\U0001f575 **Full Privacy Cleanup Complete!**\n"]

            if history_result["cleared"]:
                lines.append(f"  ✅ Chat history: {history_result['messages_removed']} messages removed")
            else:
                lines.append("  -- Chat history: Nothing to clear")

            if audio_result["cleared"]:
                lines.append(f"  ✅ Audio cache: {audio_result['files_removed']} files removed")
            else:
                lines.append("  -- Audio cache: Nothing to clear")

            if old_result["cleared"]:
                lines.append(f"  ✅ Old data: {old_result['cleared']} expired items removed")

            total_freed = (
                (history_result.get("size_freed_kb", 0) or 0)
                + (audio_result.get("size_freed_kb", 0) or 0)
            )
            if total_freed > 0:
                lines.append(f"\n  Total space freed: {total_freed:.1f} KB")

            lines.append("\nYour data is clean and private.")

            return {
                "response": "\n".join(lines),
                "data": {
                    "history": history_result,
                    "audio": audio_result,
                    "old_data": old_result,
                },
                "action": "all_cleared",
            }

        else:  # status
            history_info = self._get_chat_history_info()
            audio_info = self._get_audio_cache_info()
            upload_info = self._get_upload_info()

            lines = [
                "\U0001f575 **Privacy Status:**\n",
                f"  \U0001f4ac Chat History: {history_info['count']} messages ({history_info['size_kb']} KB)",
                f"  \U0001f50a Audio Cache: {audio_info['count']} files ({audio_info['size_kb']} KB)",
                f"  \U0001f4c1 Uploads: {upload_info['count']} files ({upload_info['size_kb']} KB)",
                f"\n  \U0001f6e1️ Auto-clear audio: {'ON' if self.auto_clear_audio else 'OFF'}",
                f"  \U0001f4c5 History retention: {self.history_retention_days} days",
                "\n**Commands:**",
                '  "Clear history" -- delete chat logs',
                '  "Clear cache" -- delete audio files',
                '  "Clear all" -- full cleanup',
            ]

            return {
                "response": "\n".join(lines),
                "data": {
                    "history": history_info,
                    "audio": audio_info,
                    "uploads": upload_info,
                    "settings": {
                        "auto_clear_audio": self.auto_clear_audio,
                        "retention_days": self.history_retention_days,
                    },
                },
                "action": "privacy_status",
            }

    def get_system_prompt_addition(self) -> str:
        return (
            "You can manage user privacy by clearing chat history, audio cache, and other data. "
            "Respect user privacy and help them manage their data."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        history_info = self._get_chat_history_info()
        audio_info = self._get_audio_cache_info()
        return (
            f"[Phantom] History: {history_info['count']} msgs, "
            f"Audio: {audio_info['count']} files. "
            f"Auto-clear: {self.auto_clear_audio}, Retention: {self.history_retention_days}d"
        )

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "auto_clear_audio": self.auto_clear_audio,
            "history_retention_days": self.history_retention_days,
        }

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "auto_clear_audio" in settings:
            self.auto_clear_audio = bool(settings["auto_clear_audio"])
        if "history_retention_days" in settings:
            self.history_retention_days = max(1, min(30, int(settings["history_retention_days"])))

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "auto_clear_audio", "label": "Auto-clear Audio After Session",
                "type": "toggle", "value": self.auto_clear_audio,
            },
            {
                "key": "history_retention_days", "label": "History Retention (days)",
                "type": "range", "value": self.history_retention_days,
                "min": 1, "max": 30, "step": 1,
            },
        ]
