"""
Echo Module — Voice / TTS wrapper for MJ Assistant.
Detects voice-related requests and generates speech output.
"""

import re
import sys
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.base_module import BaseModule


class EchoModule(BaseModule):
    name = "echo"
    display_name = "Echo"
    icon = "🎙"
    description = "Voice output — speaks responses aloud using TTS"
    version = "1.0"
    category = "core"
    enabled = True

    # Internal settings
    _auto_speak = False
    _voice = "en-IN-NeerjaNeural"

    VOICE_KEYWORDS = re.compile(
        r"\b(speak|bolo|say\s+(?:it|this)|padho|read\s*aloud|bol\s+do|sunao|awaaz|voice\s+(?:me|out)|"
        r"padhke\s+sunao|zor\s+se\s+bol)\b",
        re.IGNORECASE,
    )

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        if self.VOICE_KEYWORDS.search(text):
            return 0.9
        if intent == "voice_request":
            return 0.85
        if self._auto_speak:
            return 0.2  # low-priority auto-speak baseline
        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        # Strip the voice trigger words to get the actual content to speak
        content = self.VOICE_KEYWORDS.sub("", text).strip()
        if not content:
            content = context.get("last_response", "I have nothing to say right now.")

        return {
            "response": content,
            "data": {
                "should_speak": True,
                "voice": self._voice,
                "text_to_speak": content,
            },
            "action": "speak",
        }

    async def execute_async(self, text: str, context: dict) -> dict:
        result = self.execute(text, context)
        # Attempt TTS generation
        try:
            from voice_layer.tts_engine import generate_speech

            emotion = context.get("emotion", "neutral")
            audio_file = await generate_speech(result["data"]["text_to_speak"], emotion)
            result["data"]["audio_file"] = audio_file
        except Exception as e:
            result["data"]["tts_error"] = str(e)
        return result

    def get_system_prompt_addition(self) -> str:
        if self._auto_speak:
            return "The user has auto-speak enabled. Keep responses concise and natural for voice."
        return ""

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "auto_speak": self._auto_speak,
            "voice": self._voice,
        }

    def update_settings(self, settings: dict):
        super().update_settings(settings)
        if "auto_speak" in settings:
            self._auto_speak = bool(settings["auto_speak"])
        if "voice" in settings:
            self._voice = settings["voice"]

    def get_settings_schema(self) -> list:
        try:
            from voice_layer.voice_config import AVAILABLE_VOICES

            voice_options = [{"label": v, "value": k} for k, v in AVAILABLE_VOICES.items()]
        except ImportError:
            voice_options = [
                {"label": "Neerja (Indian English Female)", "value": "en-IN-NeerjaNeural"},
                {"label": "Swara (Hindi Female)", "value": "hi-IN-SwaraNeural"},
            ]

        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {"key": "auto_speak", "label": "Auto-Speak Responses", "type": "toggle", "value": self._auto_speak},
            {"key": "voice", "label": "Voice", "type": "select", "value": self._voice, "options": voice_options},
        ]
