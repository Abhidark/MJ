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
    # FULL VIDEO PIPELINE (V10 → 90%)
    # ========================

    VIDEO_PIPELINE_FILE = DATA_DIR / "video_pipeline.json"

    def _handle_full_video(self, text: str, context: dict) -> dict:
        """Full video pipeline — storyboard → scenes → frames → timeline."""
        prompt = re.sub(r"\b(full\s+)?video\s+(pipeline|production|project)\b", "", text, flags=re.I).strip()
        if not prompt or len(prompt) < 3:
            prompt = "Untitled Video"

        # Parse duration
        duration = 30  # default seconds
        dur_match = re.search(r"(\d+)\s*(?:sec|second|s\b)", text, re.I)
        if dur_match:
            duration = int(dur_match.group(1))

        pipeline = {
            "id": f"vid_{int(time.time())}",
            "title": prompt[:60],
            "duration_sec": duration,
            "fps": 24,
            "resolution": "1920x1080",
            "status": "storyboard",
            "created": datetime.now().isoformat(),
            "scenes": self._generate_scenes(prompt, duration),
            "audio": {"music": "auto", "voiceover": False, "sfx": True},
        }

        # Save pipeline
        pipelines = _load_json(self.VIDEO_PIPELINE_FILE, [])
        if not isinstance(pipelines, list):
            pipelines = []
        pipelines.append(pipeline)
        _save_json(self.VIDEO_PIPELINE_FILE, pipelines[-50:])
        self._log_creative("full_video", prompt, "pipeline")

        scene_lines = "\n".join(
            f"  Scene {s['scene']}: {s['description']} ({s['duration']}s)"
            for s in pipeline["scenes"]
        )
        return {
            "response": (
                f"🎬 **Video Pipeline Created: {pipeline['title']}**\n\n"
                f"Duration: {duration}s | Resolution: 1920x1080 | FPS: 24\n"
                f"Scenes ({len(pipeline['scenes'])}):\n{scene_lines}\n\n"
                f"Status: Storyboard ready. Use GPU PC to render frames."
            ),
            "data": {"type": "video_pipeline", "pipeline": pipeline},
            "action": "video_pipeline",
        }

    def _generate_scenes(self, prompt: str, duration: int) -> list:
        """Auto-generate scene breakdown from prompt."""
        scene_count = max(3, duration // 10)
        per_scene = duration / scene_count
        scenes = []
        labels = ["Introduction", "Build-up", "Main Action", "Climax", "Resolution"]
        for i in range(scene_count):
            label = labels[i] if i < len(labels) else f"Scene {i + 1}"
            scenes.append({
                "scene": i + 1,
                "label": label,
                "description": f"{label} — {prompt[:40]}",
                "duration": round(per_scene, 1),
                "transition": "fade" if i > 0 else "none",
                "frame_count": int(per_scene * 24),
            })
        return scenes

    def get_video_pipelines(self) -> dict:
        pipelines = _load_json(self.VIDEO_PIPELINE_FILE, [])
        if not isinstance(pipelines, list):
            pipelines = []
        return {"pipelines": pipelines[-10:], "total": len(pipelines)}

    # ========================
    # PRESENTATION GENERATOR V2 (V10 → 90%)
    # ========================

    THEME_PRESETS = {
        "dark": {"bg": "#0f172a", "text": "#e2e8f0", "accent": "#6366f1", "card_bg": "#1e293b"},
        "light": {"bg": "#ffffff", "text": "#1e293b", "accent": "#3b82f6", "card_bg": "#f1f5f9"},
        "neon": {"bg": "#0a0a0a", "text": "#00ff88", "accent": "#ff00ff", "card_bg": "#1a1a2e"},
        "corporate": {"bg": "#f8fafc", "text": "#334155", "accent": "#0369a1", "card_bg": "#ffffff"},
        "warm": {"bg": "#fffbeb", "text": "#451a03", "accent": "#d97706", "card_bg": "#fef3c7"},
    }

    def generate_full_presentation(self, topic: str, pres_type: str = "standard",
                                    theme: str = "dark", slide_count: int = 0) -> dict:
        """Generate complete presentation with content, layout, and theme."""
        colors = self.THEME_PRESETS.get(theme, self.THEME_PRESETS["dark"])

        # Use template slides
        result = self._handle_presentation(f"presentation about {topic}", {})
        slides = result.get("data", {}).get("slides", [])

        # Enhance each slide with layout info
        for slide in slides:
            slide["layout"] = "title_content" if slide["slide"] > 1 else "title_only"
            slide["theme"] = colors
            slide["notes"] = f"Speaker notes for {slide['title']}"

        return {
            "topic": topic,
            "type": pres_type,
            "theme": theme,
            "colors": colors,
            "slide_count": len(slides),
            "slides": slides,
            "export_formats": ["html", "pdf", "pptx_stub"],
        }

    # ========================
    # DESIGN SYSTEM TOKENS (V10 → 90%)
    # ========================

    DESIGN_TOKENS = {
        "spacing": {"xs": "4px", "sm": "8px", "md": "16px", "lg": "24px", "xl": "32px", "2xl": "48px"},
        "radius": {"none": "0", "sm": "4px", "md": "8px", "lg": "12px", "xl": "16px", "full": "9999px"},
        "shadow": {
            "sm": "0 1px 2px rgba(0,0,0,0.05)",
            "md": "0 4px 6px rgba(0,0,0,0.1)",
            "lg": "0 10px 15px rgba(0,0,0,0.1)",
            "xl": "0 20px 25px rgba(0,0,0,0.15)",
        },
        "typography": {
            "h1": {"size": "36px", "weight": "800", "line_height": "1.2"},
            "h2": {"size": "30px", "weight": "700", "line_height": "1.3"},
            "h3": {"size": "24px", "weight": "600", "line_height": "1.4"},
            "body": {"size": "16px", "weight": "400", "line_height": "1.6"},
            "caption": {"size": "12px", "weight": "400", "line_height": "1.5"},
        },
        "colors": {
            "primary": {"50": "#eef2ff", "500": "#6366f1", "900": "#312e81"},
            "gray": {"50": "#f8fafc", "500": "#64748b", "900": "#0f172a"},
            "success": "#22c55e",
            "warning": "#f59e0b",
            "error": "#ef4444",
            "info": "#3b82f6",
        },
    }

    def get_design_tokens(self) -> dict:
        return self.DESIGN_TOKENS

    def get_creative_stats(self) -> dict:
        """Get creative module statistics."""
        log = _load_json(CREATIVE_LOG_FILE, [])
        if not isinstance(log, list):
            log = []
        by_type = {}
        for entry in log:
            t = entry.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

        pipelines = _load_json(self.VIDEO_PIPELINE_FILE, [])
        if not isinstance(pipelines, list):
            pipelines = []

        return {
            "total_creations": len(log),
            "by_type": by_type,
            "video_pipelines": len(pipelines),
            "design_tokens_loaded": True,
            "themes_available": list(self.THEME_PRESETS.keys()),
            "render_queue": render_queue.get_stats(),
            "assets": asset_manager.get_stats(),
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


# ========================
# RENDER QUEUE (V10 → 100%)
# ========================

RENDER_QUEUE_FILE = DATA_DIR / "render_queue.json"

class RenderQueue:
    """Frame-by-frame render queue for video pipeline."""

    def __init__(self):
        self.jobs: list = []
        self._load()

    def _load(self):
        data = _load_json(RENDER_QUEUE_FILE, [])
        self.jobs = data if isinstance(data, list) else []

    def _save(self):
        _save_json(RENDER_QUEUE_FILE, self.jobs[-100:])

    def submit_render(self, pipeline_id: str, scene: int, resolution: str = "1920x1080",
                      format_out: str = "mp4") -> dict:
        job = {
            "id": f"render_{int(time.time())}_{scene}",
            "pipeline_id": pipeline_id,
            "scene": scene,
            "resolution": resolution,
            "format": format_out,
            "status": "queued",
            "progress": 0,
            "submitted": datetime.now().isoformat(),
            "frames_rendered": 0,
            "total_frames": 0,
        }
        self.jobs.append(job)
        self._save()
        return {"success": True, "job": job}

    def update_job(self, job_id: str, status: str = "", progress: float = 0,
                   frames: int = 0) -> dict:
        for job in self.jobs:
            if job["id"] == job_id:
                if status:
                    job["status"] = status
                if progress:
                    job["progress"] = min(100, progress)
                if frames:
                    job["frames_rendered"] = frames
                if status == "completed":
                    job["completed"] = datetime.now().isoformat()
                self._save()
                return {"success": True, "job": job}
        return {"error": "Job not found"}

    def get_queue(self, status: str = "") -> dict:
        jobs = self.jobs
        if status:
            jobs = [j for j in jobs if j.get("status") == status]
        return {"jobs": jobs[-20:], "total": len(jobs)}

    def get_stats(self) -> dict:
        by_status = {}
        for j in self.jobs:
            s = j.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
        return {
            "total_jobs": len(self.jobs),
            "by_status": by_status,
            "queued": by_status.get("queued", 0),
            "rendering": by_status.get("rendering", 0),
            "completed": by_status.get("completed", 0),
        }


# ========================
# ASSET MANAGER (V10 → 100%)
# ========================

ASSETS_FILE = DATA_DIR / "creative_assets.json"

class AssetManager:
    """Manage creative assets — images, videos, audio, fonts, templates."""

    def __init__(self):
        self.assets: dict = {}
        self._load()

    def _load(self):
        self.assets = _load_json(ASSETS_FILE, {})

    def _save(self):
        _save_json(ASSETS_FILE, self.assets)

    def register_asset(self, name: str, asset_type: str, path: str = "",
                       metadata: dict = None) -> dict:
        aid = f"asset_{int(time.time())}_{name[:10].replace(' ', '_')}"
        self.assets[aid] = {
            "id": aid,
            "name": name,
            "type": asset_type,  # image, video, audio, font, template
            "path": path,
            "metadata": metadata or {},
            "created": datetime.now().isoformat(),
            "tags": [],
            "uses": 0,
        }
        self._save()
        return {"success": True, "asset": self.assets[aid]}

    def get_asset(self, asset_id: str) -> dict:
        return self.assets.get(asset_id, {"error": "Asset not found"})

    def search_assets(self, query: str = "", asset_type: str = "") -> dict:
        results = []
        for aid, a in self.assets.items():
            if asset_type and a.get("type") != asset_type:
                continue
            if query and query.lower() not in f"{a['name']} {' '.join(a.get('tags', []))}".lower():
                continue
            results.append(a)
        return {"assets": results, "total": len(results)}

    def tag_asset(self, asset_id: str, tags: list) -> dict:
        if asset_id not in self.assets:
            return {"error": "Not found"}
        self.assets[asset_id]["tags"] = list(set(self.assets[asset_id].get("tags", []) + tags))
        self._save()
        return {"success": True, "tags": self.assets[asset_id]["tags"]}

    def delete_asset(self, asset_id: str) -> dict:
        if asset_id not in self.assets:
            return {"error": "Not found"}
        del self.assets[asset_id]
        self._save()
        return {"success": True}

    def get_stats(self) -> dict:
        by_type = {}
        for a in self.assets.values():
            t = a.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        return {"total_assets": len(self.assets), "by_type": by_type}


# Singletons
render_queue = RenderQueue()
asset_manager = AssetManager()
