"""
Intent Detector for MJ Human Layer.
Detects user intent with confidence scoring, sub-intents, and multi-intent support.
"""

import re
from typing import Dict, List, Tuple


class IntentDetector:
    def __init__(self):
        # Each intent has keyword patterns with weights
        self.intent_patterns: Dict[str, List[Tuple[str, float]]] = {
            "command": [
                (r"\b(?:open|play|start|close|run|launch|stop|pause|resume)\b", 0.9),
                (r"\b(?:kholo|band karo|chalu|chalao|shuru|baith|ruk)\b", 0.9),
                (r"\b(?:volume|brightness|screenshot|wifi|bluetooth)\b", 0.8),
                (r"\b(?:shutdown|restart|sleep|lock|minimize|maximize)\b", 0.9),
                (r"\b(?:install|uninstall|update|upgrade)\b", 0.7),
                (r"\b(?:set|change|switch|toggle)\s+(?:to|the)\b", 0.6),
            ],
            "coding": [
                (r"\b(?:code|coding|program|script|function|class|method)\b", 0.8),
                (r"\b(?:bug|error|exception|fix|debug|trace|stack)\b", 0.9),
                (r"\b(?:python|javascript|react|html|css|java|rust|go|node)\b", 0.8),
                (r"\b(?:api|endpoint|database|query|sql|mongo|redis)\b", 0.7),
                (r"\b(?:git|commit|push|pull|merge|branch|deploy)\b", 0.7),
                (r"\b(?:syntax|compile|runtime|import|module|package)\b", 0.7),
                (r"\b(?:refactor|optimize|lint|test|unittest)\b", 0.8),
                (r"```", 0.9),  # Code block = definitely coding
            ],
            "planning": [
                (r"\b(?:plan|roadmap|structure|steps|strategy|organize)\b", 0.9),
                (r"\b(?:schedule|timeline|milestone|deadline|priority)\b", 0.8),
                (r"\b(?:arrange|break down|divide|phase|sprint|kanban)\b", 0.7),
                (r"\b(?:what should i|kya karna chahiye|aage kya|next step)\b", 0.7),
                (r"\b(?:todo|task list|checklist|action items)\b", 0.8),
            ],
            "emotional_support": [
                (r"\b(?:sad|tired|low|depressed|lonely|alone|hurt)\b", 0.8),
                (r"\b(?:stress|angry|frustrated|anxious|worried|scared)\b", 0.8),
                (r"\b(?:thak gaya|tension|gussa|dukhi|udas|akela)\b", 0.9),
                (r"\b(?:feeling|feel|mood|vibe|mental)\b", 0.5),
                (r"\b(?:can.t sleep|can.t focus|overwhelmed|burnout)\b", 0.9),
                (r"\b(?:motivat|inspir|cheer|encourage)\b", 0.6),
            ],
            "learning": [
                (r"\b(?:explain|learn|teach|understand|samjhao|sikha)\b", 0.9),
                (r"\b(?:what is|what are|kya hai|kya hota|meaning)\b", 0.8),
                (r"\b(?:how does|how to|how can|kaise|tarika)\b", 0.7),
                (r"\b(?:why does|why is|kyun|kyu)\b", 0.7),
                (r"\b(?:tutorial|guide|example|concept|theory)\b", 0.7),
                (r"\b(?:difference between|compare|vs|versus)\b", 0.6),
            ],
            "creative": [
                (r"\b(?:write|compose|create|generate|draft|likh)\b", 0.6),
                (r"\b(?:poem|story|song|essay|blog|article|letter|email)\b", 0.8),
                (r"\b(?:creative|imagine|brainstorm|idea|concept)\b", 0.7),
                (r"\b(?:name|slogan|tagline|caption|title)\b", 0.6),
            ],
            "data_query": [
                (r"\b(?:weather|mausam|temperature|garmi|sardi|barish)\b", 0.9),
                (r"\b(?:cricket|score|match|ipl|live)\b", 0.8),
                (r"\b(?:stock|share|price|market|nifty|sensex)\b", 0.9),
                (r"\b(?:news|khabar|headlines|samachar)\b", 0.8),
                (r"\b(?:time|date|day|today|kal|aaj)\b", 0.4),
                (r"\b(?:convert|calculate|math|formula)\b", 0.6),
            ],
            "file_ops": [
                (r"\b(?:file|folder|directory|path)\b", 0.6),
                (r"\b(?:list|show|find|search|count)\s+(?:files?|folder)\b", 0.9),
                (r"\b(?:create|delete|rename|move|copy)\s+(?:file|folder)\b", 0.9),
                (r"\b(?:desktop|downloads?|documents?|pictures?)\b", 0.5),
            ],
            "casual": [
                (r"\b(?:hello|hi|hey|sup|yo|namaste|kaise ho)\b", 0.7),
                (r"\b(?:thanks|thank you|shukriya|dhanyavaad)\b", 0.5),
                (r"\b(?:bye|goodbye|alvida|good night|good morning)\b", 0.7),
                (r"\b(?:who are you|what.s your name|naam kya|kaun ho)\b", 0.8),
                (r"\b(?:joke|funny|meme|entertain|bore)\b", 0.6),
            ],
        }

        # Sub-intent mapping for richer context
        self.sub_intents = {
            "command": ["app_control", "system_control", "media_control", "settings"],
            "coding": ["debug", "write_code", "review", "explain_code", "devops"],
            "planning": ["project", "daily", "career", "study"],
            "learning": ["concept", "tutorial", "comparison", "deep_dive"],
        }

    def detect(self, text: str) -> str:
        """Detect primary intent. Returns intent label string."""
        result = self.detect_detailed(text)
        return result["intent"]

    def detect_detailed(self, text: str) -> dict:
        """
        Full intent analysis with confidence and secondary intents.
        Returns: {intent, confidence, sub_intent, intents: [(intent, score), ...]}
        """
        text_lower = text.lower()
        scores: Dict[str, float] = {}

        for intent, patterns in self.intent_patterns.items():
            total = 0.0
            hits = 0
            for pattern, weight in patterns:
                if re.search(pattern, text_lower):
                    hits += 1
                    total += weight

            if hits > 0:
                # Normalize: more hits = more confident
                multi_bonus = min(hits * 0.05, 0.2)
                scores[intent] = min(total / max(hits, 1) + multi_bonus, 1.0)

        if not scores:
            return {"intent": "casual", "confidence": 0.3, "sub_intent": None, "intents": []}

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary_intent = ranked[0][0]
        primary_conf = ranked[0][1]

        # Detect sub-intent
        sub_intent = self._detect_sub_intent(text_lower, primary_intent)

        return {
            "intent": primary_intent,
            "confidence": round(primary_conf, 2),
            "sub_intent": sub_intent,
            "intents": [(i, round(s, 2)) for i, s in ranked[:3]],
        }

    def _detect_sub_intent(self, text: str, intent: str) -> str | None:
        """Detect sub-intent for richer context."""
        if intent == "coding":
            if any(w in text for w in ["bug", "error", "fix", "debug", "trace"]):
                return "debug"
            if any(w in text for w in ["write", "create", "build", "make", "banao"]):
                return "write_code"
            if any(w in text for w in ["review", "check", "audit", "optimize"]):
                return "review"
            if any(w in text for w in ["explain", "samjhao", "how does", "kaise"]):
                return "explain_code"
            if any(w in text for w in ["git", "deploy", "docker", "ci", "pipeline"]):
                return "devops"
        elif intent == "command":
            if any(w in text for w in ["open", "close", "launch", "start", "kholo", "band"]):
                return "app_control"
            if any(w in text for w in ["shutdown", "restart", "sleep", "lock"]):
                return "system_control"
            if any(w in text for w in ["play", "pause", "volume", "next", "previous"]):
                return "media_control"
        elif intent == "planning":
            if any(w in text for w in ["today", "aaj", "tomorrow", "kal", "daily"]):
                return "daily"
            if any(w in text for w in ["project", "sprint", "milestone", "roadmap"]):
                return "project"
        elif intent == "learning":
            if any(w in text for w in ["difference", "compare", "vs"]):
                return "comparison"
            if any(w in text for w in ["tutorial", "step by step", "guide"]):
                return "tutorial"
            if any(w in text for w in ["deep", "detail", "advance", "internal"]):
                return "deep_dive"

        return None
