"""
Apollo Module v3 — Creative Arts for MJ Assistant (V10 upgrade).
Creative writing, poetry, stories, captions, artistic expression.
Image generation via Pollinations.ai.
NEW: Video gen stubs, UI mockup generation, logo generation, presentation outlines.
"""

import re
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.base_module import BaseModule

logger = logging.getLogger("mj.apollo")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CREATIVE_LOG_FILE = DATA_DIR / "apollo_creative_log.json"


def _load_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def _save_json(path, data):
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


class ApolloModule(BaseModule):
    name = "apollo"
    display_name = "Apollo"
    icon = "🎨"
    description = "Creative Arts — writing, poetry, images, video, UI mockups, logos, presentations"
    version = "3.0"
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

    VIDEO_KEYWORDS = re.compile(
        r"\b(generate\s+(?:a\s+)?video|create\s+(?:a\s+)?video|make\s+(?:a\s+)?video|"
        r"video\s+(?:bana|banao|generate|create)|animate|animation)\b",
        re.IGNORECASE,
    )

    UI_KEYWORDS = re.compile(
        r"\b(ui\s+(?:mockup|design|wireframe)|mockup|wireframe|"
        r"design\s+(?:a\s+)?(?:screen|page|layout|app|website|interface)|"
        r"create\s+(?:a\s+)?(?:mockup|wireframe|layout))\b",
        re.IGNORECASE,
    )

    LOGO_KEYWORDS = re.compile(
        r"\b(logo|brand\s+(?:design|identity)|icon\s+design|"
        r"create\s+(?:a\s+)?logo|design\s+(?:a\s+)?logo|logo\s+(?:bana|banao))\b",
        re.IGNORECASE,
    )

    PRESENTATION_KEYWORDS = re.compile(
        r"\b(presentation|slide\s*(?:s|deck)?|pitch\s+deck|"
        r"create\s+(?:a\s+)?presentation|make\s+(?:a\s+)?(?:presentation|slides|deck)|"
        r"outline\s+(?:a\s+)?presentation)\b",
        re.IGNORECASE,
    )

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        if self.IMAGE_KEYWORDS.search(text):
            return 0.95
        if self.VIDEO_KEYWORDS.search(text):
            return 0.93
        if self.UI_KEYWORDS.search(text):
            return 0.92
        if self.LOGO_KEYWORDS.search(text):
            return 0.92
        if self.PRESENTATION_KEYWORDS.search(text):
            return 0.88
        if intent == "image_generation":
            return 0.93
        if self.WRITING_KEYWORDS.search(text):
            return 0.90
        if intent in ("creative_writing", "poetry", "storytelling", "video", "ui_design", "logo", "presentation"):
            return 0.85
        if re.search(r"\b(imagine|describe\s+creatively|paint\s+a\s+picture)\b", text, re.IGNORECASE):
            return 0.6
        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        """Route to the appropriate creative handler."""
        if self.VIDEO_KEYWORDS.search(text):
            return self._handle_video(text, context)
        if self.UI_KEYWORDS.search(text):
            return self._handle_ui_mockup(text, context)
        if self.LOGO_KEYWORDS.search(text):
            return self._handle_logo(text, context)
        if self.PRESENTATION_KEYWORDS.search(text):
            return self._handle_presentation(text, context)
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
    # VIDEO GENERATION
    # ========================

    def _handle_video(self, text: str, context: dict) -> dict:
        """Video generation — currently uses image sequence + prompt for future API."""
        prompt = re.sub(r"\b(generate|create|make|bana|banao)\s+(?:a\s+)?video\s*(?:of|about|for)?\s*", "", text, flags=re.I).strip()
        if not prompt or len(prompt) < 3:
            prompt = text

        # Detect video type
        video_type = "general"
        if re.search(r"\b(explainer|tutorial|how.to)\b", text, re.I):
            video_type = "explainer"
        elif re.search(r"\b(promo|ad|commercial|marketing)\b", text, re.I):
            video_type = "promo"
        elif re.search(r"\b(animation|animate|motion)\b", text, re.I):
            video_type = "animation"

        # Log the request
        self._log_creative("video", prompt, video_type)

        return {
            "response": (
                f"🎬 **Video Generation Request**\n\n"
                f"Type: {video_type}\n"
                f"Concept: {prompt[:100]}\n\n"
                f"Video generation will use image sequences from Pollinations.ai to create frames. "
                f"For full video generation, connect a GPU-enabled PC with ffmpeg."
            ),
            "data": {
                "type": "video_generation",
                "video_type": video_type,
                "prompt": prompt,
                "status": "concept_ready",
            },
            "action": "video_generate",
        }

    # ========================
    # UI MOCKUP GENERATION
    # ========================

    UI_TEMPLATES = {
        "dashboard": {"sections": ["header", "sidebar", "main_grid", "stats_bar"], "style": "dark modern"},
        "login": {"sections": ["logo", "form_fields", "submit_button", "social_login"], "style": "clean minimal"},
        "landing": {"sections": ["hero", "features", "testimonials", "cta", "footer"], "style": "modern gradient"},
        "profile": {"sections": ["avatar", "info_card", "activity_feed", "settings"], "style": "card-based"},
        "chat": {"sections": ["message_list", "input_bar", "sidebar_contacts"], "style": "messaging"},
        "settings": {"sections": ["nav_tabs", "form_sections", "save_bar"], "style": "clean form"},
        "ecommerce": {"sections": ["header", "product_grid", "filters", "cart", "footer"], "style": "shop"},
    }

    def _handle_ui_mockup(self, text: str, context: dict) -> dict:
        """Generate UI mockup specifications."""
        # Detect which template
        detected = "dashboard"
        for tpl_name in self.UI_TEMPLATES:
            if tpl_name in text.lower():
                detected = tpl_name
                break

        template = self.UI_TEMPLATES[detected]
        description = re.sub(r"\b(ui|mockup|wireframe|design|create|make|a)\b", "", text, flags=re.I).strip()

        mockup = {
            "template": detected,
            "sections": template["sections"],
            "style": template["style"],
            "description": description or f"A {detected} UI design",
            "colors": {"primary": "#6366f1", "secondary": "#8b5cf6", "bg": "#0f172a", "text": "#e2e8f0"},
            "typography": {"heading": "Inter Bold", "body": "Inter Regular"},
        }

        self._log_creative("ui_mockup", description, detected)

        section_list = ", ".join(template["sections"])
        return {
            "response": (
                f"🎨 **UI Mockup: {detected.title()}**\n\n"
                f"Style: {template['style']}\n"
                f"Sections: {section_list}\n"
                f"Description: {description or 'Standard layout'}\n\n"
                f"The mockup spec is ready. Use 'generate image of {detected} UI' to create a visual."
            ),
            "data": {"type": "ui_mockup", "mockup": mockup},
            "action": "ui_mockup",
        }

    # ========================
    # LOGO GENERATION
    # ========================

    LOGO_STYLES = {
        "wordmark": "text-based logo with stylized typography",
        "lettermark": "initials-based logo (e.g., IBM, HBO)",
        "icon": "symbol/icon-based logo",
        "combination": "icon + text combination mark",
        "emblem": "badge/seal style emblem logo",
        "abstract": "abstract geometric shapes",
        "mascot": "character/mascot-based logo",
    }

    def _handle_logo(self, text: str, context: dict) -> dict:
        """Generate logo design specification + image prompt."""
        brand_name = re.sub(r"\b(logo|design|create|make|bana|banao|for|a|an)\b", "", text, flags=re.I).strip()
        if not brand_name or len(brand_name) < 2:
            brand_name = "Brand"

        # Detect style
        logo_style = "combination"
        for style_name in self.LOGO_STYLES:
            if style_name in text.lower():
                logo_style = style_name
                break

        logo_spec = {
            "brand": brand_name,
            "style": logo_style,
            "style_description": self.LOGO_STYLES[logo_style],
            "colors": ["#6366f1", "#8b5cf6", "#ffffff"],
            "image_prompt": f"professional {logo_style} logo for '{brand_name}', clean vector style, modern, minimalist, white background",
        }

        self._log_creative("logo", brand_name, logo_style)

        return {
            "response": (
                f"🎯 **Logo Design: {brand_name}**\n\n"
                f"Style: {logo_style} — {self.LOGO_STYLES[logo_style]}\n"
                f"Colors: Indigo + Purple + White\n\n"
                f"Use 'generate image of {logo_spec['image_prompt'][:60]}' to create a visual draft."
            ),
            "data": {"type": "logo_design", "logo": logo_spec},
            "action": "logo_design",
        }

    # ========================
    # PRESENTATION OUTLINES
    # ========================

    def _handle_presentation(self, text: str, context: dict) -> dict:
        """Generate a presentation outline with slide structure."""
        topic = re.sub(r"\b(presentation|slides?|deck|pitch|create|make|about|on|for|a|an)\b", "", text, flags=re.I).strip()
        if not topic or len(topic) < 3:
            topic = "General Topic"

        # Detect presentation type
        pres_type = "standard"
        if re.search(r"\b(pitch|investor|startup|funding)\b", text, re.I):
            pres_type = "pitch_deck"
        elif re.search(r"\b(report|quarterly|monthly|review)\b", text, re.I):
            pres_type = "report"
        elif re.search(r"\b(tutorial|training|workshop|lesson)\b", text, re.I):
            pres_type = "training"

        # Generate slide outlines
        slide_templates = {
            "pitch_deck": [
                {"slide": 1, "title": "Title Slide", "content": f"{topic} — Pitch Deck"},
                {"slide": 2, "title": "Problem", "content": "The problem we're solving"},
                {"slide": 3, "title": "Solution", "content": "Our approach and solution"},
                {"slide": 4, "title": "Market Size", "content": "TAM / SAM / SOM analysis"},
                {"slide": 5, "title": "Product", "content": "Product demo / screenshots"},
                {"slide": 6, "title": "Business Model", "content": "How we make money"},
                {"slide": 7, "title": "Traction", "content": "Key metrics and growth"},
                {"slide": 8, "title": "Team", "content": "Founding team and advisors"},
                {"slide": 9, "title": "Ask", "content": "Funding ask and use of funds"},
                {"slide": 10, "title": "Thank You", "content": "Contact information"},
            ],
            "report": [
                {"slide": 1, "title": "Title Slide", "content": f"{topic} — Report"},
                {"slide": 2, "title": "Executive Summary", "content": "Key findings overview"},
                {"slide": 3, "title": "Data Overview", "content": "Charts and key numbers"},
                {"slide": 4, "title": "Analysis", "content": "Detailed analysis"},
                {"slide": 5, "title": "Trends", "content": "Patterns and trends"},
                {"slide": 6, "title": "Recommendations", "content": "Next steps"},
                {"slide": 7, "title": "Q&A", "content": "Discussion"},
            ],
            "training": [
                {"slide": 1, "title": "Title Slide", "content": f"{topic} — Training"},
                {"slide": 2, "title": "Objectives", "content": "What you'll learn"},
                {"slide": 3, "title": "Overview", "content": "Topic introduction"},
                {"slide": 4, "title": "Core Concepts", "content": "Key concepts explained"},
                {"slide": 5, "title": "Demo / Examples", "content": "Practical examples"},
                {"slide": 6, "title": "Hands-On", "content": "Practice exercise"},
                {"slide": 7, "title": "Summary", "content": "Key takeaways"},
                {"slide": 8, "title": "Resources", "content": "Further reading"},
            ],
            "standard": [
                {"slide": 1, "title": "Title Slide", "content": f"{topic}"},
                {"slide": 2, "title": "Introduction", "content": "Topic overview"},
                {"slide": 3, "title": "Key Points", "content": "Main arguments / features"},
                {"slide": 4, "title": "Details", "content": "Deep dive"},
                {"slide": 5, "title": "Examples", "content": "Real-world examples"},
                {"slide": 6, "title": "Summary", "content": "Key takeaways"},
                {"slide": 7, "title": "Q&A", "content": "Questions and discussion"},
            ],
        }

        slides = slide_templates.get(pres_type, slide_templates["standard"])

        self._log_creative("presentation", topic, pres_type)

        lines = [f"📊 **Presentation Outline: {topic}**\n", f"Type: {pres_type.replace('_', ' ').title()} ({len(slides)} slides)\n"]
        for s in slides:
            lines.append(f"  **Slide {s['slide']}:** {s['title']} — {s['content']}")

        return {
            "response": "\n".join(lines),
            "data": {"type": "presentation", "pres_type": pres_type, "topic": topic, "slides": slides},
            "action": "presentation_outline",
        }

    # ========================
    # CREATIVE LOG
    # ========================

    def _log_creative(self, creative_type: str, content: str, subtype: str = ""):
        try:
            log = _load_json(CREATIVE_LOG_FILE, [])
            if not isinstance(log, list):
                log = []
            log.append({
                "type": creative_type,
                "content": content[:200],
                "subtype": subtype,
                "timestamp": datetime.now().isoformat(),
            })
            if len(log) > 200:
                log = log[-200:]
            _save_json(CREATIVE_LOG_FILE, log)
        except Exception:
            pass

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
