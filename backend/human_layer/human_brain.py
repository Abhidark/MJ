from human_layer.emotion_detector import EmotionDetector
from human_layer.intent_detector import IntentDetector
from human_layer.response_builder import ResponseBuilder


class MJHumanBrain:
    def __init__(self):
        self.emotion_detector = EmotionDetector()
        self.intent_detector = IntentDetector()
        self.response_builder = ResponseBuilder()

    def process(self, user_text: str, memory_context: str = "") -> dict:
        emotion = self.emotion_detector.detect(user_text)
        intent = self.intent_detector.detect(user_text)

        response_prompt = self.response_builder.build_response_prompt(
            user_text=user_text,
            intent=intent,
            emotion=emotion,
            memory_context=memory_context
        )

        return {
            "user_text": user_text,
            "intent": intent,
            "emotion": emotion,
            "response_prompt": response_prompt
        }
