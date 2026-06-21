"""
Daedalus Module -- Code Sandbox
Safely executes Python code snippets using subprocess with timeout.
"""

import re
import subprocess
import sys
import tempfile
import os
from pathlib import Path

# Adjust import path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.base_module import BaseModule


class DaedalusModule(BaseModule):
    name = "daedalus"
    display_name = "Daedalus"
    icon = "\U0001f9ea"  # beaker
    description = "Code Sandbox -- execute Python code safely with timeout and output capture"
    version = "1.0"
    category = "utility"
    enabled = True

    KEYWORDS = [
        r"\brun\s+code\b", r"\bexecute\b", r"\btest\s+this\b", r"\bchala\b",
        r"\boutput\s+kya\s+hoga\b", r"\brun\s+this\b", r"\bcode\s+run\b",
        r"\bpython\s+run\b", r"\bexec\b", r"\bcompile\b", r"\bscript\b",
        r"\bprogram\b.*\brun\b", r"\btry\s+this\s+code\b",
    ]

    BLOCKED_IMPORTS = [
        "os", "sys", "subprocess", "shutil", "socket", "http",
        "urllib", "requests", "pathlib", "glob", "signal", "ctypes",
        "importlib", "pickle", "shelve", "webbrowser",
    ]

    def __init__(self):
        self.timeout_seconds = 10
        self.allow_imports = False

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        text_lower = text.lower()
        # Check for code blocks
        if "```" in text:
            return 0.9
        for pattern in self.KEYWORDS:
            if re.search(pattern, text_lower):
                return 0.85
        if intent in ("run_code", "execute_code", "code_sandbox"):
            return 0.9
        return 0.0

    def _extract_code(self, text: str) -> str:
        """Extract Python code from text, handling markdown code blocks."""
        # Try markdown code block first
        match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Try inline code
        match = re.search(r"`([^`]+)`", text)
        if match:
            return match.group(1).strip()
        # Look for lines that look like code
        lines = text.split("\n")
        code_lines = []
        for line in lines:
            stripped = line.strip()
            if any(stripped.startswith(kw) for kw in (
                "print", "for ", "while ", "if ", "def ", "class ",
                "import ", "from ", "x ", "y ", "a ", "b ", "result",
                "    ", "\t",
            )) or "=" in stripped:
                code_lines.append(line)
        if code_lines:
            return "\n".join(code_lines)
        return ""

    def _check_safety(self, code: str) -> tuple[bool, str]:
        """Check if the code is safe to run. Returns (safe, reason)."""
        dangerous_patterns = [
            (r"\bos\.(system|popen|exec|remove|unlink|rmdir|makedirs)\b", "OS command execution"),
            (r"\bsubprocess\b", "Subprocess calls"),
            (r"\b(open|write)\s*\(.*['\"]w['\"]", "File write operations"),
            (r"\b__import__\b", "Dynamic imports"),
            (r"\beval\s*\(", "Eval usage"),
            (r"\bexec\s*\(", "Exec usage"),
            (r"\bsocket\b", "Network socket access"),
            (r"\bshutil\b", "File system operations"),
        ]
        for pattern, reason in dangerous_patterns:
            if re.search(pattern, code):
                return False, f"Blocked: {reason} is not allowed for safety."

        if not self.allow_imports:
            import_matches = re.findall(r"(?:^|\n)\s*(?:import|from)\s+(\w+)", code)
            for mod in import_matches:
                if mod in self.BLOCKED_IMPORTS:
                    return False, f"Blocked: Import of '{mod}' is not allowed. Enable imports in settings."

        return True, ""

    def execute(self, text: str, context: dict) -> dict:
        code = self._extract_code(text)
        if not code:
            return {
                "response": "No code found to execute. Please wrap your code in ``` backticks or say 'run this code: ...'",
                "data": None,
                "action": "no_code",
            }

        safe, reason = self._check_safety(code)
        if not safe:
            return {
                "response": f"⚠️ {reason}",
                "data": {"code": code, "blocked": True},
                "action": "blocked",
            }

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                tmp_path = f.name

            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if result.returncode == 0:
                output = stdout if stdout else "(No output)"
                return {
                    "response": f"✅ Code executed successfully!\n\n**Output:**\n```\n{output}\n```",
                    "data": {"stdout": stdout, "stderr": stderr, "returncode": 0},
                    "action": "executed",
                }
            else:
                error_msg = stderr if stderr else "Unknown error"
                return {
                    "response": f"❌ Execution error:\n```\n{error_msg}\n```",
                    "data": {"stdout": stdout, "stderr": stderr, "returncode": result.returncode},
                    "action": "error",
                }

        except subprocess.TimeoutExpired:
            return {
                "response": f"⏰ Code execution timed out after {self.timeout_seconds} seconds.",
                "data": {"timeout": True},
                "action": "timeout",
            }
        except Exception as e:
            return {
                "response": f"❌ Failed to execute code: {str(e)}",
                "data": {"error": str(e)},
                "action": "error",
            }
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def get_system_prompt_addition(self) -> str:
        return (
            "You can execute Python code. When the user asks to run code, "
            "extract the code and pass it for execution. Show the output clearly."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        return f"[Daedalus] Code sandbox ready. Timeout: {self.timeout_seconds}s. Imports allowed: {self.allow_imports}."

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "timeout_seconds": self.timeout_seconds,
            "allow_imports": self.allow_imports,
        }

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "timeout_seconds" in settings:
            self.timeout_seconds = max(5, min(30, int(settings["timeout_seconds"])))
        if "allow_imports" in settings:
            self.allow_imports = bool(settings["allow_imports"])

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "timeout_seconds", "label": "Execution Timeout (seconds)",
                "type": "range", "value": self.timeout_seconds, "min": 5, "max": 30, "step": 1,
            },
            {
                "key": "allow_imports", "label": "Allow Imports",
                "type": "toggle", "value": self.allow_imports,
            },
        ]
