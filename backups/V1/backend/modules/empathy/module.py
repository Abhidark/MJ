"""
Empathy Module — Emotional Intelligence layer for MJ Assistant.
Wraps emotion detection, intent detection, response building, and personality.
Provides emotional context to every conversation.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.base_module import BaseModule


class EmpathyModule(BaseModule):
    name = "empathy"
    display_name = "Empathy"
    icon = "😊"
    description = "Emotional intelligence — detects emotions, intent, and adapts personality"
    version = "1.0"
    category = "core"
    enabled = True

    def __init__(self):
        try:
            from human_layer.emotion_detector import EmotionDetector
            self._emotion_detector = EmotionDetector()
        except ImportError:
            self._emotion_detector = None

        try:
            from human_layer.intent_detector import IntentDetector
            self._intent_detector = IntentDetector()
        except ImportError:
            self._intent_detector = None

        try:
            from human_layer.response_builder import ResponseBuilder
            self._response_builder = ResponseBuilder()
        except ImportError:
            self._response_builder = None

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        """Always returns 0.3 — empathy adds emotional context to everything."""
        return 0.3

    def execute(self, text: str, context: dict) -> dict:
        emotion = self._detect_emotion(text)
        intent = self._detect_intent(text)

        # Build emotional context data
        data = {
            "emotion": emotion,
            "intent": intent,
            "emotional_context": self._build_emotional_context(emotion, intent, text),
        }

        # Generate empathetic response hint
        response_hints = {
            "happy": "User seems happy! Match their energy.",
            "sad": "User seems down. Be gentle and supportive.",
            "angry": "User seems frustrated. Stay calm and helpful.",
            "confused": "User seems confused. Explain clearly.",
            "excited": "User is excited! Share their enthusiasm.",
            "tired": "User seems tired. Be concise and efficient.",
            "neutral": "User is in a neutral mood. Be friendly and helpful.",
        }

        return {
            "response": response_hints.get(emotion, ""),
            "data": data,
            "action": "context_enrichment",
        }

    def _detect_emotion(self, text: str) -> str:
        if self._emotion_detector:
            try:
                return self._emotion_detector.detect(text)
            except Exception:
                pass
        return self._fallback_emotion_detect(text)

    def _detect_intent(self, text: str) -> str:
        if self._intent_detector:
            try:
                return self._intent_detector.detect(text)
            except Exception:
                pass
        return "general"

    def _fallback_emotion_detect(self, text: str) -> str:
        """Simple keyword-based emotion detection as fallback."""
        lower = text.lower()
        emotion_map = {
            "happy": ["great", "awesome", "mast", "nice", "perfect", "amazing", "yay", "badhiya", "sahi", "love it", "khush"],
            "sad": ["sad", "dukhi", "upset", "down", "miss", "cry", "alone", "udaas", "bura"],
            "angry": ["angry", "gussa", "hate", "annoying", "stupid", "idiot", "worst", "frustrated", "irritated"],
            "confused": ["confused", "samajh nahi", "what", "kya", "how", "kaise", "don't understand", "explain"],
            "excited": ["wow", "omg", "can't wait", "exciting", "let's go", "chalo", "maza", "dhamaal"],
            "tired": ["tired", "thak", "exhausted", "sleepy", "neend", "bore", "lazy"],
        }
        for emotion, keywords in emotion_map.items():
            if any(kw in lower for kw in keywords):
                return emotion
        return "neutral"

    def _build_emotional_context(self, emotion: str, intent: str, text: str) -> str:
        """Build a context string describing the emotional state."""
        parts = [f"Detected emotion: {emotion}", f"Detected intent: {intent}"]

        # Add emotional guidance
        guidance = {
            "happy": "Respond with warmth and shared positivity.",
            "sad": "Be empathetic, supportive, and gentle.",
            "angry": "Acknowledge frustration, stay calm, focus on solutions.",
            "confused": "Break things down simply, offer step-by-step help.",
            "excited": "Match energy, be enthusiastic and encouraging.",
            "tired": "Be efficient and concise, reduce cognitive load.",
        }
        if emotion in guidance:
            parts.append(f"Guidance: {guidance[emotion]}")

        return " | ".join(parts)

    def get_context_for_llm(self, text: str, context: dict) -> str:
        """Return emotion/intent context string for LLM prompt injection."""
        emotion = self._detect_emotion(text)
        intent = self._detect_intent(text)
        return self._build_emotional_context(emotion, intent, text)

    def get_system_prompt_addition(self) -> str:
        return (
            "You are emotionally intelligent. Pay attention to the user's mood and adjust your tone. "
            "If they're happy, be upbeat. If they're sad, be gentle. If they're frustrated, be patient. "
            "Always be empathetic and human-like in your responses."
        )

    def get_settings(self) -> dict:
        return {"enabled": self.enabled}

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
        ]
