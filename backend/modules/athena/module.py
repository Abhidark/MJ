"""
Athena Module v2 — Knowledge & Learning for MJ Assistant.
Handles explanations, definitions, teaching, knowledge queries.
Integrates with RAG knowledge base for document-backed answers with citations.
"""

import re
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.base_module import BaseModule

logger = logging.getLogger("mj.athena")


class AthenaModule(BaseModule):
    name = "athena"
    display_name = "Athena"
    icon = "📚"
    description = "Knowledge & Learning — explains concepts, teaches, answers knowledge queries, searches your documents"
    version = "2.0"
    category = "utility"
    enabled = True

    _detail_level = "normal"  # brief, normal, detailed
    _use_kb = True  # Auto-search knowledge base when relevant

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

    KB_PATTERNS = re.compile(
        r"(?:from|in|according to)\s+(?:my|the)\s+(?:docs?|documents?|files?|notes?|knowledge|uploads?|kb)|"
        r"(?:my|the)\s+(?:docs?|documents?|files?|notes?|knowledge|uploads?)\s+(?:say|mention|contain|have)|"
        r"(?:check|search|look|find|dhundho|dekho)\s+(?:in\s+)?(?:my|the)\s+(?:docs?|documents?|files?|notes?|knowledge|kb)|"
        r"(?:what|kya).*(?:my|the)\s+(?:docs?|documents?|files?|notes?|knowledge)",
        re.IGNORECASE,
    )

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        # KB search requests get highest priority
        if self.KB_PATTERNS.search(text):
            return 0.95

        if self.KNOWLEDGE_KEYWORDS.search(text):
            return 0.85

        if self.LEARNING_PATTERNS.search(text):
            return 0.82

        if intent in ("explain", "define", "teach", "knowledge", "learn", "knowledge_query"):
            return 0.80

        # Questions starting with interrogative words
        if re.match(r"^(what|why|how|when|where|who|which)\b", text, re.IGNORECASE):
            return 0.4

        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        """Athena execution — searches KB if relevant, provides context for LLM."""
        topic = self._extract_topic(text)
        is_kb_query = bool(self.KB_PATTERNS.search(text))

        kb_results = []
        kb_context_str = ""

        # Search knowledge base if it's a KB query or if auto-KB is enabled and topic is specific
        if is_kb_query or (self._use_kb and topic and len(topic) > 3):
            try:
                from intelligence.knowledge_base import search_knowledge, format_kb_context
                kb_results = search_knowledge(topic if topic != text else text, top_k=5)
                if kb_results:
                    kb_context_str = format_kb_context(kb_results)
            except Exception as e:
                logger.warning(f"KB search failed: {e}")

        detail_instruction = {
            "brief": "Give a concise 2-3 sentence answer.",
            "normal": "Explain clearly with an example. Keep it under a paragraph.",
            "detailed": "Give a thorough explanation with multiple examples, analogies, and related concepts.",
        }

        # Build citation info for frontend
        citations = []
        for r in kb_results:
            cite = {"source": r["source"], "relevance": r["score"]}
            if r.get("page"):
                cite["page"] = r["page"]
            citations.append(cite)

        response_text = f"Let me explain about {topic}..." if topic else "Let me help you understand that..."
        if is_kb_query and kb_results:
            response_text = f"Found {len(kb_results)} relevant passages in your documents about {topic}."
        elif is_kb_query and not kb_results:
            response_text = f"No relevant information found in your documents about '{topic}'. I'll answer from my general knowledge."

        return {
            "response": response_text,
            "data": {
                "topic": topic,
                "detail_level": self._detail_level,
                "instruction": detail_instruction.get(self._detail_level, ""),
                "type": "knowledge_query",
                "kb_context": kb_context_str,
                "citations": citations,
                "kb_hit": len(kb_results) > 0,
            },
            "action": "knowledge_response",
        }

    def _extract_topic(self, text: str) -> str:
        """Extract the topic being asked about."""
        topic = re.sub(
            r"^(explain|what\s+(?:is|are)|how\s+(?:does|do)|teach\s+me\s+about|"
            r"tell\s+me\s+about|define|kya\s+hai|samjhao|batao\s+(?:ki)?)\s+",
            "", text, flags=re.IGNORECASE,
        ).strip()
        # Remove KB trigger phrases from topic
        topic = re.sub(
            r"(?:from|in|according to)\s+(?:my|the)\s+(?:docs?|documents?|files?|notes?|knowledge|uploads?|kb)",
            "", topic, flags=re.IGNORECASE,
        ).strip()
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
        base = detail_prompts.get(self._detail_level, detail_prompts["normal"])
        base += (
            "\n\nWhen citing information from the knowledge base, include the source filename "
            "and page number (if available) in your response. Example: 'According to report.pdf (Page 5), ...'"
        )
        return base

    def get_context_for_llm(self, text: str, context: dict) -> str:
        topic = self._extract_topic(text)
        parts = []
        if topic and topic != text:
            parts.append(f"[Knowledge Query] Topic: {topic} | Detail level: {self._detail_level}")
        return "\n".join(parts)

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "detail_level": self._detail_level,
            "use_kb": self._use_kb,
        }

    def update_settings(self, settings: dict):
        super().update_settings(settings)
        if "detail_level" in settings and settings["detail_level"] in ("brief", "normal", "detailed"):
            self._detail_level = settings["detail_level"]
        if "use_kb" in settings:
            self._use_kb = bool(settings["use_kb"])

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
            {"key": "use_kb", "label": "Auto-search Knowledge Base", "type": "toggle", "value": self._use_kb},
        ]
