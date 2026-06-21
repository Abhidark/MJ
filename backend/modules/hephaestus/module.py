"""
Hephaestus Module — Code Generation for MJ Assistant.
Handles code writing, generation, debugging, and programming tasks.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.base_module import BaseModule


class HephaestusModule(BaseModule):
    name = "hephaestus"
    display_name = "Hephaestus"
    icon = "⚒️"
    description = "Code Generation — writes, debugs, and explains code"
    version = "1.0"
    category = "creative"
    enabled = True

    _language = "python"
    _include_comments = True

    CODE_KEYWORDS = re.compile(
        r"\b(write\s+(?:a\s+)?(?:code|script|program|function|class|api)|"
        r"generate\s+(?:code|script|function)|"
        r"create\s+(?:a\s+)?(?:function|class|script|program|api|endpoint|component)|"
        r"build\s+(?:a\s+)?(?:function|class|app|script|api|tool|bot|server|page)|"
        r"code\s+(?:likho|likh\s+do|bana|banao)|"
        r"banao\s+(?:ek|mujhe)?|"
        r"make\s+(?:a\s+)?(?:function|script|program|api)|"
        r"implement\s+(?:a\s+)?|"
        r"debug\s+(?:this|my)|fix\s+(?:this|my)\s+code|"
        r"code\s+review|refactor|optimize\s+(?:this|my)\s+code)\b",
        re.IGNORECASE,
    )

    LANGUAGE_PATTERNS = re.compile(
        r"\b(python|javascript|typescript|java|c\+\+|c#|csharp|"
        r"rust|go|golang|ruby|php|swift|kotlin|dart|html|css|"
        r"sql|bash|shell|powershell|react|vue|angular|node|flask|django|fastapi)\b",
        re.IGNORECASE,
    )

    PROGRAMMING_CONTEXT = re.compile(
        r"\b(algorithm|data\s+structure|recursion|loop|array|"
        r"dictionary|list|sort|binary|tree|graph|stack|queue|"
        r"linked\s+list|hash|regex|api\s+call|http|rest|"
        r"database|crud|frontend|backend|fullstack)\b",
        re.IGNORECASE,
    )

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        if self.CODE_KEYWORDS.search(text):
            return 0.92

        if intent in ("code", "generate_code", "coding", "programming", "debug"):
            return 0.88

        # Detect language mentions combined with action words
        if self.LANGUAGE_PATTERNS.search(text):
            action_words = re.compile(r"\b(write|create|build|make|generate|implement|banao|likho)\b", re.IGNORECASE)
            if action_words.search(text):
                return 0.90
            # Just mentioning a language with a question
            return 0.5

        if self.PROGRAMMING_CONTEXT.search(text):
            return 0.4

        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        """
        Hephaestus prepares context for the LLM to generate code.
        Detects the language and task, provides structured instructions.
        """
        language = self._detect_language(text)
        task = self._extract_task(text)
        is_debug = bool(re.search(r"\b(debug|fix|error|bug|issue|problem)\b", text, re.IGNORECASE))

        if is_debug:
            action = "code_debug"
            instruction = (
                f"Debug and fix the code. Explain what was wrong and show the corrected version. "
                f"Language: {language}."
            )
        else:
            action = "code_generate"
            comment_note = " Include clear comments explaining each section." if self._include_comments else ""
            instruction = (
                f"Generate clean, production-quality {language} code for: {task}. "
                f"Follow best practices and include error handling.{comment_note}"
            )

        return {
            "response": f"Let me {'debug' if is_debug else 'write'} that {language} code for you...",
            "data": {
                "language": language,
                "task": task,
                "is_debug": is_debug,
                "include_comments": self._include_comments,
                "instruction": instruction,
            },
            "action": action,
        }

    def _detect_language(self, text: str) -> str:
        """Detect programming language from text."""
        match = self.LANGUAGE_PATTERNS.search(text)
        if match:
            lang = match.group(1).lower()
            # Normalize language names
            normalizations = {
                "golang": "go",
                "csharp": "c#",
                "node": "javascript",
                "react": "javascript (React)",
                "vue": "javascript (Vue)",
                "angular": "typescript (Angular)",
                "flask": "python (Flask)",
                "django": "python (Django)",
                "fastapi": "python (FastAPI)",
            }
            return normalizations.get(lang, lang)
        return self._language  # Default language preference

    def _extract_task(self, text: str) -> str:
        """Extract the coding task description."""
        task = self.CODE_KEYWORDS.sub("", text).strip()
        task = re.sub(r"^(in|using|with|for|a|an|the|ek|mujhe)\s+", "", task, flags=re.IGNORECASE).strip()
        # Remove language name from beginning
        task = self.LANGUAGE_PATTERNS.sub("", task).strip()
        task = re.sub(r"^(in|using|with|for|a|an|the)\s+", "", task, flags=re.IGNORECASE).strip()
        return task if len(task) > 2 else text

    def get_system_prompt_addition(self) -> str:
        comment_instruction = (
            "Include clear, helpful comments explaining the logic."
            if self._include_comments
            else "Write clean code without excessive comments. Only add comments for complex logic."
        )
        return (
            f"When generating code, follow these best practices:\n"
            f"- Default language: {self._language}\n"
            f"- Use meaningful variable/function names\n"
            f"- Include proper error handling and input validation\n"
            f"- {comment_instruction}\n"
            f"- Show usage examples after the code\n"
            f"- If the task is complex, break it into functions/classes\n"
            f"- Use type hints (for Python/TypeScript)"
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        language = self._detect_language(text)
        task = self._extract_task(text)
        if task and task != text:
            return f"[Code Task] Language: {language} | Task: {task} | Comments: {self._include_comments}"
        return ""

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "language": self._language,
            "include_comments": self._include_comments,
        }

    def update_settings(self, settings: dict):
        super().update_settings(settings)
        if "language" in settings:
            self._language = settings["language"]
        if "include_comments" in settings:
            self._include_comments = bool(settings["include_comments"])

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "language",
                "label": "Default Language",
                "type": "select",
                "value": self._language,
                "options": [
                    {"label": "Python", "value": "python"},
                    {"label": "JavaScript", "value": "javascript"},
                    {"label": "TypeScript", "value": "typescript"},
                    {"label": "Java", "value": "java"},
                    {"label": "C++", "value": "c++"},
                    {"label": "C#", "value": "c#"},
                    {"label": "Go", "value": "go"},
                    {"label": "Rust", "value": "rust"},
                    {"label": "HTML/CSS", "value": "html"},
                    {"label": "SQL", "value": "sql"},
                    {"label": "Bash", "value": "bash"},
                ],
            },
            {
                "key": "include_comments",
                "label": "Include Code Comments",
                "type": "toggle",
                "value": self._include_comments,
            },
        ]
