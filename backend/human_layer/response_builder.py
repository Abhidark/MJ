"""
Response Builder for MJ Human Layer.
Constructs the full system + user prompt with personality, emotion, intent, memory, and mode context.
"""

from human_layer.conversation_modes import get_mode, get_transition_message
from human_layer.personality import build_system_prompt, EMOTION_RESPONSES


class ResponseBuilder:
    def __init__(self):
        self._last_intent: str = "casual"

    def build_response_prompt(
        self,
        user_text: str,
        intent: str,
        emotion: str,
        memory_context: str = "",
        emotion_detail: dict | None = None,
        intent_detail: dict | None = None,
    ) -> str:
        """Build enriched prompt with full human-layer context."""
        mode = get_mode(intent)

        # Build system prompt with personality
        system_prompt = build_system_prompt(
            emotion=emotion,
            intent=intent,
            mode_style=mode,
            memory_context=memory_context,
        )

        # Add format/length guidance
        parts = [system_prompt]
        parts.append(f"\n--- Response Guidelines ---")
        parts.append(f"Format: {mode.get('format', 'natural')}")
        parts.append(f"Length: {mode.get('max_length', 'medium')}")
        if mode.get("system_hint"):
            parts.append(f"Hint: {mode['system_hint']}")

        # Emotion context for nuance
        if emotion_detail and emotion != "neutral":
            conf = emotion_detail.get("confidence", 0)
            intensity = emotion_detail.get("intensity", "medium")
            if conf > 0.7:
                parts.append(f"\nEmotion detected strongly ({emotion}, {intensity} intensity, {conf} confidence). Adjust tone accordingly.")
            secondary = emotion_detail.get("emotions", [])
            if len(secondary) > 1:
                sec_list = ", ".join(f"{e}({s})" for e, s in secondary[1:])
                parts.append(f"Secondary emotions: {sec_list}")

        # Intent detail for sub-context
        if intent_detail:
            sub = intent_detail.get("sub_intent")
            if sub:
                parts.append(f"\nSub-intent: {sub}")
            secondary_intents = intent_detail.get("intents", [])
            if len(secondary_intents) > 1:
                sec_list = ", ".join(f"{i}({s})" for i, s in secondary_intents[1:])
                parts.append(f"Secondary intents: {sec_list}")

        # Mode transition message
        transition = get_transition_message(self._last_intent, intent)
        if transition and self._last_intent != intent:
            parts.append(f"\n[Mode transition: {transition}]")
        self._last_intent = intent

        # Final user message
        parts.append(f"\n--- User Message ---\n{user_text}")

        return "\n".join(parts)

    def build_quick_prompt(self, user_text: str, intent: str, emotion: str) -> str:
        """Lightweight prompt for fast responses (commands, data queries)."""
        mode = get_mode(intent)
        return (
            f"[MJ | intent={intent} | emotion={emotion} | tone={mode['tone']} | length={mode['max_length']}]\n"
            f"{user_text}"
        )
