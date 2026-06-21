"""
Athena Module — Knowledge & Learning for MJ Assistant.
Handles explanations, definitions, teaching, and knowledge queries.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.base_module import BaseModule


class AthenaModule(BaseModule):
    name = "athena"
    display_name = "Athena"
    icon = "📚"
    description = "Knowledge & Learning — explains concepts, teaches, and answers knowledge queries"
    version = "1.0"
    category = "utility"
    enabled = True

    _detail_level = "normal"  # brief, normal, detailed

    KNOWLEDGE_KEYWORDS = re.compile(
        r"\b(explain|what\s+is|what\s+are|how\s+does|how\s+do|teach\s+me|"
        r"kya\s+hai|kya\s+hota\s+hai|samjhao|samjha\s+do|batao|"
        r"define|meaning\s+of|difference\s+between|compare|"
        r"tell\s+me\s+about|what\s+does\s+.+\s+mean|"
        r"why\s+(?:is|are|does|do|did)|how\s+(?:to|can\s+I)|"
        r"tutorial|guide|concept|theory|principle)\b",
        re.IGNORECASE,
    )

    LEARNING_PATTERNS = re.compile(
        r"\b(learn|study|understand|sikho|sikhao|padhao|seekhna|"
        r"walk\s+me\s+through|step\s+by\s+step|basics\s+of|"
        r"introduction\s+to|beginner|fundamentals|overview)\b",
        re.IGNORECASE,
    )

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        if self.KNOWLEDGE_KEYWORDS.search(text):
            return 0.85

        if self.LEARNING_PATTERNS.search(text):
            return 0.82

        if intent in ("explain", "define", "teach", "knowledge", "learn"):
            return 0.80

        # Questions starting with interrogative words (but not commands)
        if re.match(r"^(what|why|how|when|where|who|which)\b", text, re.IGNORECASE):
            # Avoid claiming general questions too aggressively
            return 0.4

        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        """
        Athena doesn't generate answers directly — she provides context and instructions
        for the LLM to generate the best knowledge response.
        """
        topic = self._extract_topic(text)

        detail_instruction = {
            "brief": "Give a concise 2-3 sentence answer.",
            "normal": "Explain clearly with an example. Keep it under a paragraph.",
            "detailed": "Give a thorough explanation with multiple examples, analogies, and related concepts.",
        }

        return {
            "response": f"Let me explain about {topic}..." if topic else "Let me help you understand that...",
            "data": {
                "topic": topic,
                "detail_level": self._detail_level,
                "instruction": detail_instruction.get(self._detail_level, ""),
                "type": "knowledge_query",
            },
            "action": "knowledge_response",
        }

    def _extract_topic(self, text: str) -> str:
        """Extract the topic being asked about."""
        # Remove common question prefixes
        topic = re.sub(
            r"^(explain|what\s+(?:is|are)|how\s+(?:does|do)|teach\s+me\s+about|"
            r"tell\s+me\s+about|define|kya\s+hai|samjhao|batao\s+(?:ki)?)\s+",
            "", text, flags=re.IGNORECASE,
        ).strip()
        # Remove trailing question marks and filler
        topic = re.sub(r"\?+$", "", topic).strip()
        topic = re.sub(r"^(a|an|the|ye|yeh|wo|woh)\s+", "", topic, flags=re.IGNORECASE).strip()
        return topic if len(topic) > 1 else text

    def get_system_prompt_addition(self) -> str:
        detail_prompts = {
            "brief": (
                "When explaining concepts, be concise and to the point. "
                "Give the core answer in 2-3 sentences. No fluff."
            ),
            "normal": (
                "When explaining concepts, be clear and helpful. "
                "Use a simple analogy or example to make it stick. "
                "Structure: definition, then example, then one key insight."
            ),
            "detailed": (
                "When explaining concepts, be thorough and educational. "
                "Structure: simple definition, real-world analogy, 2-3 examples, "
                "common misconceptions, and related concepts. "
                "Make it feel like a mini-lesson."
            ),
        }
        return detail_prompts.get(self._detail_level, detail_prompts["normal"])

    def get_context_for_llm(self, text: str, context: dict) -> str:
        topic = self._extract_topic(text)
        if topic and topic != text:
            return f"[Knowledge Query] Topic: {topic} | Detail level: {self._detail_level}"
        return ""

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "detail_level": self._detail_level,
        }

    def update_settings(self, settings: dict):
        super().update_settings(settings)
        if "detail_level" in settings and settings["detail_level"] in ("brief", "normal", "detailed"):
            self._detail_level = settings["detail_level"]

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "detail_level",
                "label": "Detail Level",
                "type": "select",
                "value": self._detail_level,
                "options": [
                    {"label": "Brief (2-3 sentences)", "value": "brief"},
                    {"label": "Normal (with examples)", "value": "normal"},
                    {"label": "Detailed (full lesson)", "value": "detailed"},
                ],
            },
        ]
