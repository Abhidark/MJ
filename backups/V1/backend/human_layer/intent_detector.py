class IntentDetector:
    def detect(self, text: str) -> str:
        text_lower = text.lower()

        # Command intent
        if any(word in text_lower for word in ["open", "play", "start", "close", "run", "launch", "kholo", "band karo", "chalu"]):
            return "command"

        # Coding intent
        if any(word in text_lower for word in ["code", "bug", "error", "fix", "python", "react", "function", "api", "debug", "syntax"]):
            return "coding"

        # Planning intent
        if any(word in text_lower for word in ["plan", "roadmap", "structure", "steps", "strategy", "organize", "arrange"]):
            return "planning"

        # Emotional support intent
        if any(word in text_lower for word in ["sad", "tired", "low", "stress", "angry", "frustrated", "alone", "hurt", "thak", "tension"]):
            return "emotional_support"

        # Learning intent
        if any(word in text_lower for word in ["explain", "learn", "teach", "how", "what is", "kya hai", "samjhao", "sikha"]):
            return "learning"

        # Casual intent
        return "casual"
