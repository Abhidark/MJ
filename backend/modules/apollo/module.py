"""
Apollo Module v2 — Creative Arts for MJ Assistant.
Creative writing, poetry, stories, captions, artistic expression.
Now integrated with image generation via Pollinations.ai.
"""

import re
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.base_module import BaseModule

logger = logging.getLogger("mj.apollo")


class ApolloModule(BaseModule):
    name = "apollo"
    display_name = "Apollo"
    icon = "🎨"
    description = "Creative Arts — writing, poetry, stories, image generation, artistic expression"
    version = "2.0"
    category = "creative"
    enabled = True

    _creativity_level = "medium"   # low, medium, high
    _style_preference = "modern"   # classic, modern, poetic, casual
    _default_image_style = ""      # user's preferred image style

    WRITING_KEYWORDS = re.compile(
        r"\b(write\s+(?:a\s+)?(?:poem|poetry|story|essay|caption|lyrics|shayari|haiku|sonnet|limerick|ballad)|"
        r"(?:poem|poetry|story|creative\s+writing|kavita|shayari|haiku|sonnet|fiction|narrative)|"
        r"compose|rhyme|verse|write\s+me|creative\s+(?:content|piece|text))\b",
        re.IGNORECASE,
    )

    IMAGE_KEYWORDS = re.compile(
        r"\b(generate\s+(?:a\s+|an\s+)?(?:image|photo|picture|pic|img|art|illustration)|"
        r"create\s+(?:a\s+|an\s+)?(?:image|photo|picture|pic|art)|"
        r"draw\s+(?:a\s+|an\s+)?|make\s+(?:a\s+|an\s+)?(?:image|picture|art)|"
        r"(?:image|photo|picture|tasveer|pic|img)\s+(?:bana|banao|generate|create)|"
        r"bana(?:o)?\s+(?:ek\s+)?(?:image|photo|tasveer|picture)|"
        r"show\s+(?:generated\s+)?images|image\s+list|meri\s+images)\b",
        re.IGNORECASE,
    )

    IMAGE_STYLE_MAP = {
        "realistic": "photorealistic, 8k",
        "cartoon": "cartoon style, colorful",
        "anime": "anime style, detailed",
        "painting": "oil painting style",
        "sketch": "pencil sketch style",
        "watercolor": "watercolor painting",
        "3d": "3D render, detailed",
        "pixel": "pixel art style",
        "cyberpunk": "cyberpunk style, neon",
        "fantasy": "fantasy art, magical",
        "minimalist": "minimalist, clean, simple",
        "abstract": "abstract art, colorful",
        "vintage": "vintage style, retro",
        "dark": "dark theme, moody lighting",
    }

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        # Image generation gets highest priority
        if self.IMAGE_KEYWORDS.search(text):
            return 0.95

        if intent == "image_generation":
            return 0.93

        if self.WRITING_KEYWORDS.search(text):
            return 0.90

        if intent in ("creative_writing", "poetry", "storytelling"):
            return 0.85

        if re.search(r"\b(imagine|describe\s+creatively|paint\s+a\s+picture)\b", text, re.IGNORECASE):
            return 0.6

        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        """Route to image generation or creative writing."""
        if self.IMAGE_KEYWORDS.search(text):
            return self._handle_image(text, context)

        return self._handle_writing(text, context)

    # ========================
    # IMAGE GENERATION
    # ========================

    def _handle_image(self, text: str, context: dict) -> dict:
        """Handle image generation requests using Pollinations.ai."""
        text_lower = text.lower().strip()

        # List images command
        if re.search(r"(show|list|meri)\s+(generated\s+)?images?", text_lower):
            return self._list_images()

        # Parse the image prompt
        prompt = self._extract_image_prompt(text)
        if not prompt or len(prompt) < 3:
            return {
                "response": "Please describe what image you want me to generate. Example: 'generate image of a cyberpunk city at night'",
                "data": None, "action": "image_generate",
            }

        # Detect style
        style = self._detect_image_style(text_lower) or self._default_image_style

        # Return async action — main.py will call generate_image()
        return {
            "response": f"Generating image: {prompt[:80]}...",
            "data": {
                "type": "image_generation",
                "prompt": prompt,
                "style": style,
                "action_required": "generate_image",
            },
            "action": "image_generate",
        }

    async def execute_async(self, text: str, context: dict) -> dict:
        """Async execution — actually generates the image."""
        if self.IMAGE_KEYWORDS.search(text):
            return await self._generate_image_async(text, context)
        return self.execute(text, context)

    async def _generate_image_async(self, text: str, context: dict) -> dict:
        """Actually call image generation API."""
        text_lower = text.lower().strip()

        if re.search(r"(show|list|meri)\s+(generated\s+)?images?", text_lower):
            return self._list_images()

        prompt = self._extract_image_prompt(text)
        if not prompt or len(prompt) < 3:
            return {
                "response": "Please describe what image you want. Example: 'generate image of a sunset over mountains'",
                "data": None, "action": "image_generate",
            }

        style = self._detect_image_style(text_lower) or self._default_image_style

        try:
            from pc_control.image_gen import generate_image
            result = await generate_image(prompt, style)

            if result.get("success"):
                return {
                    "response": result["message"],
                    "data": {
                        "type": "image_generated",
                        "filename": result.get("filename"),
                        "path": result.get("path"),
                        "url": result.get("url"),
                        "size_kb": result.get("size_kb"),
                        "prompt": prompt,
                        "style": style,
                    },
                    "action": "image_generated",
                }
            else:
                return {
                    "response": result.get("message", "Image generation failed."),
                    "data": {"type": "image_error", "prompt": prompt},
                    "action": "error",
                }
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            return {
                "response": f"Image generation error: {e}",
                "data": None, "action": "error",
            }

    def _extract_image_prompt(self, text: str) -> str:
        """Extract the image description/prompt from user text."""
        # Try structured patterns
        patterns = [
            r"(?:generate|create|bana|banao|draw|make)\s+(?:a\s+|an\s+|ek\s+)?(?:image|photo|picture|tasveer|pic|img|art|illustration)\s+(?:of\s+|ki\s+|about\s+)?(.+)",
            r"(?:image|photo|picture|tasveer|pic)\s+(?:bana|banao|generate|create|draw)\s+(.+)",
            r"(?:ek\s+)?(.+)\s+(?:ki|ka|ke)\s+(?:image|photo|picture|tasveer)\s+(?:bana|banao|generate)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                prompt = m.group(1).strip()
                # Clean fillers
                for filler in ["please", "karo", "do", "na", "de", "dedo", "for me"]:
                    prompt = re.sub(r'\b' + filler + r'\b', '', prompt, flags=re.IGNORECASE).strip()
                if prompt and len(prompt) > 2:
                    return prompt

        # Fallback: remove just the image command words
        cleaned = self.IMAGE_KEYWORDS.sub("", text).strip()
        cleaned = re.sub(r"^(of|about|for|a|an|the)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        return cleaned if len(cleaned) > 2 else ""

    def _detect_image_style(self, text: str) -> str:
        """Detect image style from text."""
        for key, val in self.IMAGE_STYLE_MAP.items():
            if key in text:
                return val
        return ""

    def _list_images(self) -> dict:
        """List recently generated images."""
        try:
            from pc_control.image_gen import list_generated_images
            result = list_generated_images()
            return {
                "response": result.get("message", "No images found."),
                "data": {"type": "image_list"},
                "action": "image_list",
            }
        except Exception as e:
            return {"response": f"Error listing images: {e}", "data": None, "action": "error"}

    # ========================
    # CREATIVE WRITING
    # ========================

    def _handle_writing(self, text: str, context: dict) -> dict:
        """Prepare context for LLM to generate creative content."""
        tone_map = {
            "low": "structured and restrained",
            "medium": "balanced and expressive",
            "high": "wildly imaginative and vivid",
        }
        tone = tone_map.get(self._creativity_level, "balanced and expressive")

        # Detect content type
        content_type = "creative writing"
        if re.search(r"\b(poem|poetry|kavita|shayari|haiku|sonnet)\b", text, re.IGNORECASE):
            content_type = "poetry"
        elif re.search(r"\b(story|narrative|fiction|kahani)\b", text, re.IGNORECASE):
            content_type = "story"
        elif re.search(r"\b(caption|tagline)\b", text, re.IGNORECASE):
            content_type = "caption"
        elif re.search(r"\b(lyrics|song|gana)\b", text, re.IGNORECASE):
            content_type = "lyrics"
        elif re.search(r"\b(essay|article|blog)\b", text, re.IGNORECASE):
            content_type = "essay"

        return {
            "response": f"Apollo is creating {content_type}! Creativity: {self._creativity_level} ({tone}), style: {self._style_preference}.",
            "data": {
                "type": "creative_writing",
                "content_type": content_type,
                "creativity_level": self._creativity_level,
                "style_preference": self._style_preference,
                "request": text,
            },
            "action": "creative_generate",
        }

    # ========================
    # SYSTEM PROMPT & SETTINGS
    # ========================

    def get_system_prompt_addition(self) -> str:
        level_prompts = {
            "low": "Be creative but keep language clear and structured.",
            "medium": "Be creative, imaginative, use vivid language and metaphors.",
            "high": (
                "Be wildly creative, use rich imagery, unexpected metaphors, "
                "poetic language, and artistic flair. Push boundaries."
            ),
        }
        base = level_prompts.get(self._creativity_level, level_prompts["medium"])
        base += f" Write in a {self._style_preference} style."
        base += (
            "\n\nYou also have image generation capabilities via Pollinations.ai. "
            "When a user asks to generate/create/draw an image, the system will handle the API call. "
            "Describe what you're creating before generating."
        )
        return base

    def get_context_for_llm(self, text: str, context: dict) -> str:
        if self.IMAGE_KEYWORDS.search(text):
            return "[Apollo Image Generation] User requesting AI-generated image."
        return (
            f"[Apollo Creative Module] Creativity: {self._creativity_level}, "
            f"Style: {self._style_preference}. "
            "User is requesting creative/artistic content."
        )

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "creativity_level": self._creativity_level,
            "style_preference": self._style_preference,
            "default_image_style": self._default_image_style,
        }

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "creativity_level" in settings:
            self._creativity_level = settings["creativity_level"]
        if "style_preference" in settings:
            self._style_preference = settings["style_preference"]
        if "default_image_style" in settings:
            self._default_image_style = settings["default_image_style"]

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "creativity_level",
                "label": "Creativity Level",
                "type": "select",
                "value": self._creativity_level,
                "options": [
                    {"label": "Low (structured)", "value": "low"},
                    {"label": "Medium (balanced)", "value": "medium"},
                    {"label": "High (wild)", "value": "high"},
                ],
            },
            {
                "key": "style_preference",
                "label": "Writing Style",
                "type": "select",
                "value": self._style_preference,
                "options": [
                    {"label": "Classic", "value": "classic"},
                    {"label": "Modern", "value": "modern"},
                    {"label": "Poetic", "value": "poetic"},
                    {"label": "Casual", "value": "casual"},
                ],
            },
            {
                "key": "default_image_style",
                "label": "Default Image Style",
                "type": "select",
                "value": self._default_image_style,
                "options": [
                    {"label": "None (auto)", "value": ""},
                    {"label": "Realistic", "value": "photorealistic, 8k"},
                    {"label": "Anime", "value": "anime style, detailed"},
                    {"label": "Cyberpunk", "value": "cyberpunk style, neon"},
                    {"label": "Fantasy", "value": "fantasy art, magical"},
                    {"label": "Minimalist", "value": "minimalist, clean"},
                ],
            },
        ]
