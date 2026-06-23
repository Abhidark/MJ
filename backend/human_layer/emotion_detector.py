"""
Emotion Detector for MJ Human Layer.
Detects user emotion with confidence scores, intensity, and multi-emotion support.
"""

import re
from typing import Dict, List, Tuple


class EmotionDetector:
    def __init__(self):
        # keyword → (emotion, base_weight)
        # Higher weight = stronger signal
        self.emotion_keywords: Dict[str, List[Tuple[str, float]]] = {
            "happy": [
                ("great", 0.7), ("awesome", 0.8), ("mast", 0.7), ("nice", 0.5),
                ("finally", 0.6), ("done", 0.4), ("perfect", 0.8), ("amazing", 0.9),
                ("yay", 0.9), ("love it", 0.8), ("badhiya", 0.7), ("sahi", 0.5),
                ("khushi", 0.8), ("happy", 0.9), ("glad", 0.6), ("wonderful", 0.8),
                ("fantastic", 0.8), ("excellent", 0.7), ("maza aa gaya", 0.9),
            ],
            "sad": [
                ("sad", 0.9), ("tired", 0.5), ("alone", 0.7), ("bad", 0.5),
                ("low", 0.5), ("hurt", 0.7), ("thak gaya", 0.6), ("dukhi", 0.8),
                ("bura", 0.6), ("down", 0.5), ("depressed", 0.9), ("miss", 0.5),
                ("lonely", 0.7), ("heartbroken", 0.9), ("rona", 0.8), ("udas", 0.8),
            ],
            "angry": [
                ("angry", 0.9), ("irritated", 0.7), ("frustrated", 0.8),
                ("fed up", 0.8), ("gussa", 0.9), ("annoyed", 0.7), ("hate", 0.8),
                ("bakwas", 0.7), ("stupid", 0.5), ("worst", 0.6), ("pagal", 0.5),
                ("nonsense", 0.6), ("useless", 0.6), ("crap", 0.6), ("damn", 0.5),
            ],
            "confused": [
                ("confused", 0.9), ("samajh nahi", 0.9), ("kaise", 0.5),
                ("what to do", 0.7), ("kya karu", 0.8), ("lost", 0.5),
                ("unclear", 0.7), ("pata nahi", 0.8), ("how", 0.3),
                ("don't understand", 0.8), ("makes no sense", 0.7),
            ],
            "stressed": [
                ("stress", 0.9), ("pressure", 0.7), ("deadline", 0.6),
                ("tension", 0.8), ("too much", 0.6), ("bahut kaam", 0.7),
                ("overwhelmed", 0.9), ("anxiety", 0.8), ("panic", 0.8),
                ("overloaded", 0.7), ("burnout", 0.9), ("hectic", 0.6),
            ],
            "excited": [
                ("excited", 0.9), ("let's go", 0.8), ("crazy idea", 0.7),
                ("chalo", 0.5), ("maza", 0.6), ("awesome plan", 0.8),
                ("cant wait", 0.9), ("can't wait", 0.9), ("pumped", 0.8),
                ("fired up", 0.8), ("woohoo", 0.9), ("josh", 0.7), ("ready", 0.4),
            ],
            "grateful": [
                ("thanks", 0.7), ("thank you", 0.8), ("shukriya", 0.8),
                ("dhanyavaad", 0.8), ("appreciate", 0.7), ("grateful", 0.9),
                ("helped a lot", 0.8), ("lifesaver", 0.9), ("you're the best", 0.9),
            ],
            "curious": [
                ("interesting", 0.6), ("tell me more", 0.7), ("how does", 0.5),
                ("what if", 0.6), ("wonder", 0.6), ("curious", 0.9),
                ("batao na", 0.7), ("aur batao", 0.7),
            ],
        }

        # Intensity amplifiers and dampeners
        self.amplifiers = ["very", "really", "so", "bahut", "bohot", "extremely", "super", "totally"]
        self.dampeners = ["little", "bit", "slightly", "thoda", "kinda", "somewhat"]

        # Negation words that flip emotion
        self.negations = ["not", "nahi", "don't", "doesn't", "didn't", "won't", "never", "na", "mat", "no"]

    def detect(self, text: str) -> str:
        """Detect primary emotion. Returns emotion label string."""
        result = self.detect_detailed(text)
        return result["emotion"]

    def detect_detailed(self, text: str) -> dict:
        """
        Full emotion analysis with confidence, intensity, and secondary emotions.
        Returns: {emotion, confidence, intensity, emotions: [(emotion, score), ...]}
        """
        text_lower = text.lower()
        words = text_lower.split()
        scores: Dict[str, float] = {}

        # Check for negation context
        has_negation = any(neg in words for neg in self.negations)

        # Score each emotion
        for emotion, keywords in self.emotion_keywords.items():
            total = 0.0
            hits = 0
            for keyword, weight in keywords:
                if keyword in text_lower:
                    hits += 1
                    total += weight

            if hits > 0:
                # Bonus for multiple keyword hits (stronger signal)
                multi_bonus = min(hits * 0.1, 0.3)
                scores[emotion] = min(total + multi_bonus, 1.0)

        # Apply intensity modifiers
        intensity = "medium"
        if any(amp in words for amp in self.amplifiers):
            intensity = "high"
            scores = {k: min(v * 1.3, 1.0) for k, v in scores.items()}
        elif any(damp in words for damp in self.dampeners):
            intensity = "low"
            scores = {k: v * 0.7 for k, v in scores.items()}

        # Punctuation-based intensity boost
        if text.count("!") >= 2 or text.count("?") >= 2:
            intensity = "high"
            scores = {k: min(v * 1.2, 1.0) for k, v in scores.items()}
        if text.isupper() and len(text) > 5:
            intensity = "high"
            scores = {k: min(v * 1.2, 1.0) for k, v in scores.items()}

        # Handle negation: flip positive↔negative
        if has_negation and scores:
            flip_map = {"happy": "sad", "sad": "happy", "excited": "sad",
                        "angry": "neutral", "stressed": "neutral"}
            flipped = {}
            for emo, score in scores.items():
                new_emo = flip_map.get(emo, emo)
                flipped[new_emo] = flipped.get(new_emo, 0) + score
            scores = flipped

        if not scores:
            return {"emotion": "neutral", "confidence": 0.5, "intensity": "medium", "emotions": []}

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = ranked[0]

        return {
            "emotion": primary[0],
            "confidence": round(primary[1], 2),
            "intensity": intensity,
            "emotions": [(e, round(s, 2)) for e, s in ranked[:3]],
        }
