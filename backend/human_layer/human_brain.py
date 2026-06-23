"""
MJ Human Brain — orchestrates emotion detection, intent classification,
personality adaptation, and response prompt building.
"""

from human_layer.emotion_detector import EmotionDetector
from human_layer.intent_detector import IntentDetector
from human_layer.response_builder import ResponseBuilder
from human_layer.conversation_modes import get_temperature


class MJHumanBrain:
    def __init__(self):
        self.emotion_detector = EmotionDetector()
        self.intent_detector = IntentDetector()
        self.response_builder = ResponseBuilder()

    def process(self, user_text: str, memory_context: str = "") -> dict:
        """
        Full human-layer processing pipeline.
        Returns enriched context dict for the LLM call.
        """
        emotion_detail = self.emotion_detector.detect_detailed(user_text)
        intent_detail = self.intent_detector.detect_detailed(user_text)

        emotion = emotion_detail["emotion"]
        intent = intent_detail["intent"]

        # Use quick prompt for fast-response intents
        if intent in ("command", "data_query", "file_ops"):
            response_prompt = self.response_builder.build_quick_prompt(
                user_text=user_text,
                intent=intent,
                emotion=emotion,
            )
        else:
            response_prompt = self.response_builder.build_response_prompt(
                user_text=user_text,
                intent=intent,
                emotion=emotion,
                memory_context=memory_context,
                emotion_detail=emotion_detail,
                intent_detail=intent_detail,
            )

        return {
            "user_text": user_text,
            "intent": intent,
            "emotion": emotion,
            "emotion_confidence": emotion_detail.get("confidence", 0),
            "emotion_intensity": emotion_detail.get("intensity", "medium"),
            "sub_intent": intent_detail.get("sub_intent"),
            "intent_confidence": intent_detail.get("confidence", 0),
            "temperature": get_temperature(intent),
            "response_prompt": response_prompt,
        }
