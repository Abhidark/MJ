"""
Apollo Module -- Creative Writing & Artistic Expression
"""

import re
from modules.base_module import BaseModule


class ApolloModule(BaseModule):
    name = "apollo"
    display_name = "Apollo"
    icon = "\U0001f3a8"
    description = "Creative writing, poetry, stories, captions, and artistic expression"
    version = "1.0"
    category = "creative"
    enabled = True

    KEYWORDS = [
        "write poem", "poem", "poetry", "story", "creative", "kavita",
        "lyrics", "caption", "shayari", "haiku", "sonnet", "fiction",
        "write a story", "creative writing", "write me", "compose",
        "rhyme", "verse", "ballad", "limerick", "narrative",
    ]

    def __init__(self):
        self.creativity_level = "medium"   # low, medium, high
        self.style_preference = "modern"   # classic, modern, poetic, casual

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        lower = text.lower()

        # Strong keyword matches
        for kw in self.KEYWORDS:
            if kw in lower:
                return 0.9

        # Intent-based matching
        if intent in ("creative_writing", "poetry", "storytelling"):
            return 0.85

        # Weaker signals
        if re.search(r"\b(imagine|describe creatively|paint a picture)\b", lower):
            return 0.6

        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        tone_map = {
            "low": "structured and restrained",
            "medium": "balanced and expressive",
            "high": "wildly imaginative and vivid",
        }
        tone = tone_map.get(self.creativity_level, "balanced and expressive")

        return {
            "response": (
                f"Apollo is ready to create! Creativity set to '{self.creativity_level}' "
                f"({tone}), style: {self.style_preference}. "
                f"Let the LLM weave your request into art."
            ),
            "data": {
                "creativity_level": self.creativity_level,
                "style_preference": self.style_preference,
                "request": text,
            },
            "action": "creative_generate",
        }

    def get_system_prompt_addition(self) -> str:
        level_prompts = {
            "low": "Be creative but keep language clear and structured.",
            "medium": "Be creative, imaginative, use vivid language and metaphors.",
            "high": (
                "Be wildly creative, use rich imagery, unexpected metaphors, "
                "poetic language, and artistic flair. Push boundaries."
            ),
        }
        base = level_prompts.get(self.creativity_level, level_prompts["medium"])
        style_hint = f" Write in a {self.style_preference} style."
        return base + style_hint

    def get_context_for_llm(self, text: str, context: dict) -> str:
        return (
            f"[Apollo Creative Module] Creativity: {self.creativity_level}, "
            f"Style: {self.style_preference}. "
            "User is requesting creative/artistic content."
        )

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "creativity_level": self.creativity_level,
            "style_preference": self.style_preference,
        }

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "creativity_level" in settings:
            self.creativity_level = settings["creativity_level"]
        if "style_preference" in settings:
            self.style_preference = settings["style_preference"]

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "creativity_level",
                "label": "Creativity Level",
                "type": "select",
                "value": self.creativity_level,
                "options": ["low", "medium", "high"],
            },
            {
                "key": "style_preference",
                "label": "Style Preference",
                "type": "select",
                "value": self.style_preference,
                "options": ["classic", "modern", "poetic", "casual"],
            },
        ]
