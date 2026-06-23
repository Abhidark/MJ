"""
Hephaestus Module v2 — Code & Dev Tools for MJ Assistant.
Handles code writing, generation, debugging, file analysis,
git operations (status/log/diff), and safe code execution.
"""

import re
import sys
import os
import subprocess
import logging
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.base_module import BaseModule

logger = logging.getLogger("mj.hephaestus")

# Safe project root for git operations (configurable)
DEFAULT_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # MJ-Assistant root


class HephaestusModule(BaseModule):
    name = "hephaestus"
    display_name = "Hephaestus"
    icon = "⚒️"
    description = "Code & Dev Tools — writes code, runs git commands, analyzes files, executes scripts"
    version = "2.0"
    category = "creative"
    enabled = True

    _language = "python"
    _include_comments = True
    _project_root = str(DEFAULT_PROJECT_ROOT)
    _allow_execution = True  # Allow safe code execution (sandboxed)

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

    GIT_KEYWORDS = re.compile(
        r"\b(git\s+(?:status|log|diff|branch|show|blame|stash|remote|tag|fetch|pull|push|commit|checkout|merge)|"
        r"show\s+(?:git|commit|branches|recent\s+commits)|"
        r"what\s+changed|recent\s+changes|code\s+changes|"
        r"git\s+history|commit\s+history)\b",
        re.IGNORECASE,
    )

    FILE_ANALYSIS_KEYWORDS = re.compile(
        r"\b(analyze\s+(?:this|my)\s+(?:code|file|script)|"
        r"read\s+(?:file|code)|show\s+(?:file|code)|"
        r"count\s+lines|file\s+(?:size|info|stats)|"
        r"list\s+(?:files|directory|folder)|"
        r"find\s+(?:files?|in\s+code)|search\s+(?:code|files?))\b",
        re.IGNORECASE,
    )

    EXECUTION_KEYWORDS = re.compile(
        r"\b(run\s+(?:this|my|the)\s+(?:code|script|program)|"
        r"execute\s+(?:this|my|the)|"
        r"test\s+(?:this|my)\s+code|"
        r"chalao|run\s+kar(?:o|do)?)\b",
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

    # ========================
    # ROUTING
    # ========================

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        if self.GIT_KEYWORDS.search(text):
            return 0.95

        if self.EXECUTION_KEYWORDS.search(text):
            return 0.93

        if self.CODE_KEYWORDS.search(text):
            return 0.92

        if self.FILE_ANALYSIS_KEYWORDS.search(text):
            return 0.88

        if intent in ("code", "generate_code", "coding", "programming", "debug", "git_operation", "code_help"):
            return 0.88

        if self.LANGUAGE_PATTERNS.search(text):
            action_words = re.compile(r"\b(write|create|build|make|generate|implement|banao|likho)\b", re.IGNORECASE)
            if action_words.search(text):
                return 0.90
            return 0.5

        if self.PROGRAMMING_CONTEXT.search(text):
            return 0.4

        return 0.0

    # ========================
    # EXECUTION
    # ========================

    def execute(self, text: str, context: dict) -> dict:
        """Route to appropriate handler based on request type."""
        # Git commands
        if self.GIT_KEYWORDS.search(text):
            return self._handle_git(text, context)

        # Code execution
        if self.EXECUTION_KEYWORDS.search(text):
            return self._handle_execution(text, context)

        # File analysis
        if self.FILE_ANALYSIS_KEYWORDS.search(text):
            return self._handle_file_analysis(text, context)

        # Default: code generation (LLM-powered via prompt context)
        return self._handle_code_gen(text, context)

    # ========================
    # GIT OPERATIONS
    # ========================

    def _handle_git(self, text: str, context: dict) -> dict:
        """Execute read-only git commands and return results."""
        text_lower = text.lower()

        # Map natural language to git commands
        git_cmd = None
        if re.search(r"git\s+status|what\s+changed|code\s+changes", text_lower):
            git_cmd = ["git", "status", "--short"]
        elif re.search(r"git\s+log|commit\s+history|recent\s+commits|git\s+history", text_lower):
            git_cmd = ["git", "log", "--oneline", "-20"]
        elif re.search(r"git\s+diff|show\s+diff", text_lower):
            git_cmd = ["git", "diff", "--stat"]
        elif re.search(r"git\s+branch|show\s+branches", text_lower):
            git_cmd = ["git", "branch", "-a"]
        elif re.search(r"git\s+remote", text_lower):
            git_cmd = ["git", "remote", "-v"]
        elif re.search(r"git\s+tag", text_lower):
            git_cmd = ["git", "tag", "-l"]
        elif re.search(r"git\s+stash", text_lower):
            git_cmd = ["git", "stash", "list"]
        elif re.search(r"git\s+show", text_lower):
            git_cmd = ["git", "show", "--stat", "HEAD"]
        elif re.search(r"git\s+blame", text_lower):
            # Extract filename if mentioned
            file_match = re.search(r"blame\s+(\S+)", text, re.IGNORECASE)
            if file_match:
                git_cmd = ["git", "blame", "--date=short", file_match.group(1)]
            else:
                return {"response": "Please specify a file for git blame. Example: git blame main.py", "data": None, "action": "git_info"}

        # WRITE operations — return info but don't execute
        elif re.search(r"git\s+(commit|push|pull|merge|checkout|fetch)", text_lower):
            cmd_match = re.search(r"git\s+(commit|push|pull|merge|checkout|fetch)", text_lower)
            cmd = cmd_match.group(1) if cmd_match else "unknown"
            return {
                "response": f"Git write operations like '{cmd}' should be done manually in your terminal for safety. Here's the command you can copy:",
                "data": {"type": "git_write_blocked", "suggested_command": f"git {cmd}", "reason": "Write operations require manual confirmation"},
                "action": "git_info",
            }

        if not git_cmd:
            return {"response": "I didn't recognize that git command. Try: git status, git log, git diff, git branch, git remote, git tag, git stash, git show, git blame <file>", "data": None, "action": "git_info"}

        # Execute read-only git command
        try:
            result = subprocess.run(
                git_cmd,
                cwd=self._project_root,
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="replace",
            )
            output = result.stdout.strip() or result.stderr.strip() or "(no output)"
            # Truncate if too long
            if len(output) > 3000:
                output = output[:3000] + "\n... (truncated)"

            return {
                "response": f"```\n$ {' '.join(git_cmd)}\n{output}\n```",
                "data": {
                    "type": "git_result",
                    "command": " ".join(git_cmd),
                    "output": output,
                    "return_code": result.returncode,
                },
                "action": "git_result",
            }
        except subprocess.TimeoutExpired:
            return {"response": "Git command timed out (10s limit).", "data": None, "action": "error"}
        except FileNotFoundError:
            return {"response": "Git is not installed or not in PATH.", "data": None, "action": "error"}
        except Exception as e:
            return {"response": f"Git error: {e}", "data": None, "action": "error"}

    # ========================
    # CODE EXECUTION (sandboxed)
    # ========================

    def _handle_execution(self, text: str, context: dict) -> dict:
        """Execute code snippets safely with timeout and output capture."""
        if not self._allow_execution:
            return {"response": "Code execution is disabled in settings.", "data": None, "action": "error"}

        # Extract code from context (e.g., previous message or code block)
        code = context.get("code") or context.get("previous_result") or ""

        # Try to extract code block from text itself
        code_match = re.search(r'```(?:\w+)?\n([\s\S]+?)```', text)
        if code_match:
            code = code_match.group(1)

        if not code.strip():
            return {
                "response": "No code found to execute. Please provide code in a code block (```python ... ```) or paste it in the previous message.",
                "data": None,
                "action": "code_execution",
            }

        # Detect language from code or text
        lang = self._detect_language(text) or "python"

        # Only execute Python and Bash safely
        if lang not in ("python", "bash", "shell", "powershell"):
            return {
                "response": f"Direct execution only supports Python and Bash. For {lang}, copy the code and run it in your IDE.",
                "data": {"code": code, "language": lang},
                "action": "code_execution",
            }

        try:
            if lang == "python":
                result = subprocess.run(
                    [sys.executable, "-c", code],
                    capture_output=True, text=True, timeout=15,
                    encoding="utf-8", errors="replace",
                    cwd=tempfile.gettempdir(),
                )
            else:
                result = subprocess.run(
                    ["bash", "-c", code] if os.name != "nt" else ["powershell", "-Command", code],
                    capture_output=True, text=True, timeout=15,
                    encoding="utf-8", errors="replace",
                    cwd=tempfile.gettempdir(),
                )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            output = stdout or "(no output)"
            if stderr:
                output += f"\n\nSTDERR:\n{stderr}"
            if len(output) > 3000:
                output = output[:3000] + "\n... (truncated)"

            return {
                "response": f"**Execution result** ({lang}):\n```\n{output}\n```",
                "data": {
                    "type": "execution_result",
                    "language": lang,
                    "stdout": stdout[:2000],
                    "stderr": stderr[:1000],
                    "return_code": result.returncode,
                    "success": result.returncode == 0,
                },
                "action": "code_execution",
            }
        except subprocess.TimeoutExpired:
            return {"response": "Code execution timed out (15s limit). The code may have an infinite loop.", "data": None, "action": "error"}
        except Exception as e:
            return {"response": f"Execution error: {e}", "data": None, "action": "error"}

    # ========================
    # FILE ANALYSIS
    # ========================

    def _handle_file_analysis(self, text: str, context: dict) -> dict:
        """Analyze files: read, count lines, show stats, list directory."""
        text_lower = text.lower()

        # List directory
        if re.search(r"list\s+(?:files|directory|folder)", text_lower):
            target = self._extract_path(text) or self._project_root
            return self._list_directory(target)

        # Count lines
        if re.search(r"count\s+lines", text_lower):
            target = self._extract_path(text)
            if target:
                return self._count_lines(target)
            return {"response": "Please specify a file path to count lines.", "data": None, "action": "file_analysis"}

        # File stats
        if re.search(r"file\s+(?:size|info|stats)", text_lower):
            target = self._extract_path(text)
            if target:
                return self._file_stats(target)
            return {"response": "Please specify a file path for stats.", "data": None, "action": "file_analysis"}

        # Search in files
        if re.search(r"(?:find|search)\s+(?:in\s+code|files?)", text_lower):
            pattern_match = re.search(r'(?:find|search)\s+(?:for\s+)?["\']?(.+?)["\']?\s+(?:in|from)', text, re.IGNORECASE)
            if pattern_match:
                return self._search_files(pattern_match.group(1).strip())
            return {"response": "Please specify what to search for. Example: find 'def main' in code", "data": None, "action": "file_analysis"}

        # Read file
        target = self._extract_path(text)
        if target:
            return self._read_file(target)

        return {
            "response": "What would you like me to analyze? I can: list files, count lines, show file stats, search code, or read a file.",
            "data": None,
            "action": "file_analysis",
        }

    def _list_directory(self, path: str) -> dict:
        p = Path(path)
        if not p.exists():
            return {"response": f"Path not found: {path}", "data": None, "action": "error"}
        if not p.is_dir():
            return {"response": f"Not a directory: {path}", "data": None, "action": "error"}

        items = []
        try:
            for item in sorted(p.iterdir()):
                if item.name.startswith("."):
                    continue
                kind = "📁" if item.is_dir() else "📄"
                size = ""
                if item.is_file():
                    sz = item.stat().st_size
                    size = f" ({sz:,} bytes)" if sz < 1024*1024 else f" ({sz/1024/1024:.1f} MB)"
                items.append(f"{kind} {item.name}{size}")
        except PermissionError:
            return {"response": f"Permission denied: {path}", "data": None, "action": "error"}

        if not items:
            return {"response": f"Directory is empty: {path}", "data": None, "action": "file_analysis"}

        listing = "\n".join(items[:50])
        if len(items) > 50:
            listing += f"\n... and {len(items) - 50} more items"

        return {
            "response": f"**{p.name}/** ({len(items)} items):\n```\n{listing}\n```",
            "data": {"type": "directory_listing", "path": str(p), "item_count": len(items)},
            "action": "file_analysis",
        }

    def _count_lines(self, path: str) -> dict:
        p = Path(path)
        if not p.exists() or not p.is_file():
            return {"response": f"File not found: {path}", "data": None, "action": "error"}
        try:
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            code_lines = [l for l in lines if l.strip() and not l.strip().startswith(("#", "//", "/*", "*"))]
            return {
                "response": f"**{p.name}**: {len(lines)} total lines, {len(code_lines)} code lines (excluding comments/blank)",
                "data": {"file": str(p), "total_lines": len(lines), "code_lines": len(code_lines)},
                "action": "file_analysis",
            }
        except Exception as e:
            return {"response": f"Error reading file: {e}", "data": None, "action": "error"}

    def _file_stats(self, path: str) -> dict:
        p = Path(path)
        if not p.exists():
            return {"response": f"File not found: {path}", "data": None, "action": "error"}
        stat = p.stat()
        from datetime import datetime
        return {
            "response": (
                f"**{p.name}**\n"
                f"Size: {stat.st_size:,} bytes\n"
                f"Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')}\n"
                f"Extension: {p.suffix or 'none'}"
            ),
            "data": {"file": str(p), "size": stat.st_size, "extension": p.suffix},
            "action": "file_analysis",
        }

    def _read_file(self, path: str) -> dict:
        p = Path(path)
        if not p.exists() or not p.is_file():
            return {"response": f"File not found: {path}", "data": None, "action": "error"}
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            if len(content) > 5000:
                content = content[:5000] + "\n... (truncated, showing first 5000 chars)"
            ext = p.suffix.lstrip(".")
            return {
                "response": f"**{p.name}**:\n```{ext}\n{content}\n```",
                "data": {"file": str(p), "content_length": len(content)},
                "action": "file_analysis",
            }
        except Exception as e:
            return {"response": f"Error reading file: {e}", "data": None, "action": "error"}

    def _search_files(self, pattern: str) -> dict:
        """Search for a pattern in project files using grep-like search."""
        root = Path(self._project_root)
        matches = []
        extensions = (".py", ".js", ".ts", ".html", ".css", ".json", ".md", ".txt", ".yaml", ".yml", ".toml")

        try:
            for fpath in root.rglob("*"):
                if fpath.is_file() and fpath.suffix in extensions and ".git" not in str(fpath):
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="ignore")
                        for i, line in enumerate(content.splitlines(), 1):
                            if pattern.lower() in line.lower():
                                matches.append(f"{fpath.relative_to(root)}:{i}: {line.strip()[:120]}")
                                if len(matches) >= 30:
                                    break
                    except Exception:
                        continue
                if len(matches) >= 30:
                    break
        except Exception as e:
            return {"response": f"Search error: {e}", "data": None, "action": "error"}

        if not matches:
            return {"response": f"No matches found for '{pattern}' in project files.", "data": None, "action": "file_analysis"}

        result = "\n".join(matches)
        return {
            "response": f"Found {len(matches)} matches for '{pattern}':\n```\n{result}\n```",
            "data": {"type": "search_result", "pattern": pattern, "match_count": len(matches)},
            "action": "file_analysis",
        }

    def _extract_path(self, text: str) -> str:
        """Extract a file path from text."""
        # Match quoted paths
        match = re.search(r'["\']([^"\']+)["\']', text)
        if match:
            return match.group(1)
        # Match paths with extensions
        match = re.search(r'(\S+\.\w{1,6})', text)
        if match and not match.group(1).startswith("http"):
            path = match.group(1)
            # Check if relative to project root
            full = Path(self._project_root) / path
            if full.exists():
                return str(full)
            if Path(path).exists():
                return path
        return ""

    # ========================
    # CODE GENERATION (LLM-powered)
    # ========================

    def _handle_code_gen(self, text: str, context: dict) -> dict:
        """Prepare context for LLM to generate code."""
        language = self._detect_language(text)
        task = self._extract_task(text)
        is_debug = bool(re.search(r"\b(debug|fix|error|bug|issue|problem)\b", text, re.IGNORECASE))

        if is_debug:
            action = "code_debug"
            instruction = f"Debug and fix the code. Explain what was wrong and show the corrected version. Language: {language}."
        else:
            action = "code_generate"
            comment_note = " Include clear comments explaining each section." if self._include_comments else ""
            instruction = f"Generate clean, production-quality {language} code for: {task}. Follow best practices and include error handling.{comment_note}"

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
        match = self.LANGUAGE_PATTERNS.search(text)
        if match:
            lang = match.group(1).lower()
            normalizations = {
                "golang": "go", "csharp": "c#", "node": "javascript",
                "react": "javascript (React)", "vue": "javascript (Vue)",
                "angular": "typescript (Angular)", "flask": "python (Flask)",
                "django": "python (Django)", "fastapi": "python (FastAPI)",
            }
            return normalizations.get(lang, lang)
        return self._language

    def _extract_task(self, text: str) -> str:
        task = self.CODE_KEYWORDS.sub("", text).strip()
        task = re.sub(r"^(in|using|with|for|a|an|the|ek|mujhe)\s+", "", task, flags=re.IGNORECASE).strip()
        task = self.LANGUAGE_PATTERNS.sub("", task).strip()
        task = re.sub(r"^(in|using|with|for|a|an|the)\s+", "", task, flags=re.IGNORECASE).strip()
        return task if len(task) > 2 else text

    # ========================
    # SYSTEM PROMPT & SETTINGS
    # ========================

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
            f"- Use type hints (for Python/TypeScript)\n"
            f"\nYou also have real dev tool capabilities:\n"
            f"- Git operations (read-only): status, log, diff, branch, remote, tag, stash, show, blame\n"
            f"- File analysis: list directory, count lines, file stats, search in code, read files\n"
            f"- Code execution: run Python and Bash scripts with timeout and output capture"
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
            "project_root": self._project_root,
            "allow_execution": self._allow_execution,
        }

    def update_settings(self, settings: dict):
        super().update_settings(settings)
        if "language" in settings:
            self._language = settings["language"]
        if "include_comments" in settings:
            self._include_comments = bool(settings["include_comments"])
        if "project_root" in settings:
            self._project_root = settings["project_root"]
        if "allow_execution" in settings:
            self._allow_execution = bool(settings["allow_execution"])

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
            {"key": "include_comments", "label": "Include Code Comments", "type": "toggle", "value": self._include_comments},
            {"key": "allow_execution", "label": "Allow Code Execution", "type": "toggle", "value": self._allow_execution},
        ]
