class EmotionDetector:
    def __init__(self):
        self.emotion_keywords = {
            "happy": ["great", "awesome", "mast", "nice", "finally", "done", "perfect", "amazing", "yay", "love it", "badhiya", "sahi"],
            "sad": ["sad", "tired", "alone", "bad", "low", "hurt", "thak gaya", "dukhi", "bura", "down"],
            "angry": ["angry", "irritated", "frustrated", "fed up", "gussa", "annoyed", "hate", "bakwas"],
            "confused": ["confused", "samajh nahi", "kaise", "what to do", "kya karu", "lost", "unclear", "pata nahi"],
            "stressed": ["stress", "pressure", "deadline", "tension", "too much", "bahut kaam", "overwhelmed"],
            "excited": ["excited", "let's go", "amazing", "crazy idea", "chalo", "maza", "awesome plan", "cant wait"]
        }

    def detect(self, text: str) -> str:
        text_lower = text.lower()

        for emotion, keywords in self.emotion_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return emotion

        return "neutral"
