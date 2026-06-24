"""
Hephaestus Module v3 — Code & Dev Tools for MJ Assistant.
Handles: code generation, git read+write, file analysis,
code execution, debugging with stack trace analysis,
testing framework, and deploy commands.
"""

import re
import sys
import os
import subprocess
import logging
import tempfile
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.base_module import BaseModule

logger = logging.getLogger("mj.hephaestus")

DEFAULT_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # MJ-Assistant root
TEST_RESULTS_DIR = Path(__file__).parent.parent.parent / "data"
TEST_RESULTS_DIR.mkdir(exist_ok=True)
TEST_RESULTS_FILE = TEST_RESULTS_DIR / "test_results.json"


def _save_test_results(results: dict):
    try:
        existing = []
        if TEST_RESULTS_FILE.exists():
            existing = json.loads(TEST_RESULTS_FILE.read_text(encoding="utf-8"))
        existing.append(results)
        if len(existing) > 50:
            existing = existing[-50:]
        TEST_RESULTS_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


class HephaestusModule(BaseModule):
    name = "hephaestus"
    display_name = "Hephaestus"
    icon = "⚒️"
    description = "Code & Dev Tools v3 — git read+write, debugging, testing, code gen, deploy"
    version = "3.0"
    category = "creative"
    enabled = True

    _language = "python"
    _include_comments = True
    _project_root = str(DEFAULT_PROJECT_ROOT)
    _allow_execution = True
    _allow_git_write = True  # NEW: enable git write operations

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
        r"\b(git\s+(?:status|log|diff|branch|show|blame|stash|remote|tag|fetch|pull|push|commit|checkout|merge|init|add|reset)|"
        r"show\s+(?:git|commit|branches|recent\s+commits)|"
        r"what\s+changed|recent\s+changes|code\s+changes|"
        r"git\s+history|commit\s+history|"
        r"create\s+branch|new\s+branch|switch\s+branch|"
        r"commit\s+(?:this|all|changes|karo))\b",
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
        r"chalao|run\s+kar(?:o|do)?)\b",
        re.IGNORECASE,
    )

    DEBUG_KEYWORDS = re.compile(
        r"\b(debug|traceback|stacktrace|stack\s+trace|error\s+(?:in|at|on)|"
        r"exception|bug|fix\s+(?:this|my)\s+(?:error|bug|issue)|"
        r"why\s+(?:is|does|am)\s+(?:this|my)|what\s+(?:went|is)\s+wrong|"
        r"analyze\s+(?:this\s+)?error|diagnose)\b",
        re.IGNORECASE,
    )

    TEST_KEYWORDS = re.compile(
        r"\b(test\s+(?:this|my|the)\s+(?:code|function|api|endpoint|module)|"
        r"run\s+tests?|unittest|pytest|test\s+cases?|"
        r"generate\s+tests?|write\s+tests?|"
        r"test\s+results?|test\s+coverage|"
        r"test\s+(?:likh|likho|bana|banao|karo))\b",
        re.IGNORECASE,
    )

    DEPLOY_KEYWORDS = re.compile(
        r"\b(deploy|deployment|build\s+(?:for\s+)?(?:production|prod)|"
        r"package|release|publish|ship|"
        r"docker(?:ize)?|containerize|"
        r"setup\s+(?:project|env|environment)|"
        r"install\s+(?:dependencies|packages|requirements))\b",
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

    # Common error patterns for smart debugging
    ERROR_PATTERNS = {
        r"ModuleNotFoundError: No module named '(\w+)'": {
            "type": "missing_module",
            "fix": "Install with: pip install {0}",
        },
        r"ImportError: cannot import name '(\w+)' from '(\w+)'": {
            "type": "import_error",
            "fix": "Check if '{0}' exists in module '{1}'. May need different version.",
        },
        r"SyntaxError: (?:invalid syntax|unexpected EOF)": {
            "type": "syntax_error",
            "fix": "Check for missing brackets, colons, or quotes near the indicated line.",
        },
        r"IndentationError": {
            "type": "indentation",
            "fix": "Fix indentation — use consistent spaces (4) not tabs.",
        },
        r"TypeError: .+ takes (\d+) .+ but (\d+) .+ given": {
            "type": "argument_mismatch",
            "fix": "Function expects {0} arguments but got {1}. Check function signature.",
        },
        r"KeyError: '(\w+)'": {
            "type": "key_error",
            "fix": "Key '{0}' not found in dict. Use .get('{0}', default) for safe access.",
        },
        r"AttributeError: '(\w+)' object has no attribute '(\w+)'": {
            "type": "attribute_error",
            "fix": "Object of type '{0}' doesn't have '{1}'. Check spelling or object type.",
        },
        r"FileNotFoundError: .+No such file.+'(.+)'": {
            "type": "file_not_found",
            "fix": "File '{0}' not found. Check path and ensure file exists.",
        },
        r"ConnectionRefusedError|Connection refused": {
            "type": "connection_error",
            "fix": "Server not running or wrong port. Check if service is started.",
        },
        r"PermissionError": {
            "type": "permission_error",
            "fix": "Insufficient permissions. Try running with admin/sudo privileges.",
        },
        r"RecursionError": {
            "type": "recursion_error",
            "fix": "Infinite recursion detected. Add/fix base case in recursive function.",
        },
        r"JSONDecodeError": {
            "type": "json_error",
            "fix": "Invalid JSON. Check for trailing commas, missing quotes, or malformed data.",
        },
        r"UnicodeDecodeError": {
            "type": "encoding_error",
            "fix": "Encoding mismatch. Try: open(file, encoding='utf-8', errors='ignore')",
        },
    }

    # ========================
    # ROUTING
    # ========================

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        if self.GIT_KEYWORDS.search(text):
            return 0.95
        if self.DEBUG_KEYWORDS.search(text):
            return 0.94
        if self.TEST_KEYWORDS.search(text):
            return 0.93
        if self.DEPLOY_KEYWORDS.search(text):
            return 0.92
        if self.EXECUTION_KEYWORDS.search(text):
            return 0.91
        if self.CODE_KEYWORDS.search(text):
            return 0.90
        if self.FILE_ANALYSIS_KEYWORDS.search(text):
            return 0.88
        if intent in ("code", "generate_code", "coding", "programming", "debug", "git_operation", "code_help", "testing", "deploy"):
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
    # EXECUTION ROUTER
    # ========================

    def execute(self, text: str, context: dict) -> dict:
        if self.DEBUG_KEYWORDS.search(text):
            return self._handle_debug(text, context)
        if self.TEST_KEYWORDS.search(text):
            return self._handle_testing(text, context)
        if self.DEPLOY_KEYWORDS.search(text):
            return self._handle_deploy(text, context)
        if self.GIT_KEYWORDS.search(text):
            return self._handle_git(text, context)
        if self.EXECUTION_KEYWORDS.search(text):
            return self._handle_execution(text, context)
        if self.FILE_ANALYSIS_KEYWORDS.search(text):
            return self._handle_file_analysis(text, context)
        return self._handle_code_gen(text, context)

    # ========================
    # GIT OPERATIONS (READ + WRITE)
    # ========================

    # Safe read-only commands
    GIT_READ_CMDS = {
        "status": ["git", "status", "--short"],
        "log": ["git", "log", "--oneline", "-20"],
        "diff": ["git", "diff", "--stat"],
        "diff_full": ["git", "diff"],
        "branch": ["git", "branch", "-a"],
        "remote": ["git", "remote", "-v"],
        "tag": ["git", "tag", "-l"],
        "stash_list": ["git", "stash", "list"],
        "show": ["git", "show", "--stat", "HEAD"],
    }

    def _handle_git(self, text: str, context: dict) -> dict:
        text_lower = text.lower()

        # ---- GIT WRITE OPERATIONS ----
        if self._allow_git_write:
            # git add
            if re.search(r"git\s+add", text_lower):
                files = "."
                file_match = re.search(r"git\s+add\s+(.+)", text, re.IGNORECASE)
                if file_match:
                    files = file_match.group(1).strip()
                return self._run_git_cmd(["git", "add", files], "git add")

            # git commit
            if re.search(r"git\s+commit|commit\s+(?:this|all|changes|karo)", text_lower):
                msg_match = re.search(r'(?:message|msg|m)\s*[=:]\s*["\']?(.+?)["\']?\s*$', text, re.IGNORECASE)
                if not msg_match:
                    msg_match = re.search(r'commit\s+(?:with\s+)?(?:message\s+)?["\'](.+?)["\']', text, re.IGNORECASE)
                msg = msg_match.group(1) if msg_match else f"Update from MJ-Assistant ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
                return self._run_git_cmd(["git", "commit", "-m", msg], "git commit")

            # git push
            if re.search(r"git\s+push", text_lower):
                remote = "origin"
                branch_match = re.search(r"git\s+push\s+(\w+)\s+(\w+)", text, re.IGNORECASE)
                if branch_match:
                    return self._run_git_cmd(["git", "push", branch_match.group(1), branch_match.group(2)], "git push")
                return self._run_git_cmd(["git", "push"], "git push")

            # git pull
            if re.search(r"git\s+pull", text_lower):
                return self._run_git_cmd(["git", "pull"], "git pull")

            # git checkout / switch branch
            if re.search(r"git\s+checkout|switch\s+branch", text_lower):
                branch_match = re.search(r"(?:checkout|switch\s+(?:to\s+)?(?:branch\s+)?)(\S+)", text, re.IGNORECASE)
                if branch_match:
                    branch = branch_match.group(1)
                    return self._run_git_cmd(["git", "checkout", branch], "git checkout")
                return {"response": "Specify branch name: git checkout <branch>", "data": None, "action": "git_info"}

            # git create branch
            if re.search(r"(?:create|new)\s+branch", text_lower):
                branch_match = re.search(r"branch\s+(\S+)", text, re.IGNORECASE)
                if branch_match:
                    branch = branch_match.group(1)
                    return self._run_git_cmd(["git", "checkout", "-b", branch], "git checkout -b")
                return {"response": "Specify branch name: create branch <name>", "data": None, "action": "git_info"}

            # git merge
            if re.search(r"git\s+merge", text_lower):
                branch_match = re.search(r"merge\s+(\S+)", text, re.IGNORECASE)
                if branch_match:
                    return self._run_git_cmd(["git", "merge", branch_match.group(1)], "git merge")
                return {"response": "Specify branch to merge: git merge <branch>", "data": None, "action": "git_info"}

            # git stash
            if re.search(r"git\s+stash\s*(save|push|pop|apply|drop)?", text_lower):
                sub = re.search(r"git\s+stash\s+(save|push|pop|apply|drop|list)", text_lower)
                if sub:
                    action = sub.group(1)
                    if action == "list":
                        return self._run_git_cmd(["git", "stash", "list"], "git stash list")
                    return self._run_git_cmd(["git", "stash", action], f"git stash {action}")
                return self._run_git_cmd(["git", "stash"], "git stash")

            # git reset
            if re.search(r"git\s+reset", text_lower):
                if "hard" in text_lower:
                    return self._run_git_cmd(["git", "reset", "--hard", "HEAD"], "git reset --hard")
                return self._run_git_cmd(["git", "reset", "HEAD"], "git reset")

        # ---- GIT READ OPERATIONS ----
        git_cmd = None
        if re.search(r"git\s+status|what\s+changed|code\s+changes", text_lower):
            git_cmd = self.GIT_READ_CMDS["status"]
        elif re.search(r"git\s+log|commit\s+history|recent\s+commits|git\s+history", text_lower):
            git_cmd = self.GIT_READ_CMDS["log"]
        elif re.search(r"git\s+diff\s+full|show\s+full\s+diff", text_lower):
            git_cmd = self.GIT_READ_CMDS["diff_full"]
        elif re.search(r"git\s+diff|show\s+diff", text_lower):
            git_cmd = self.GIT_READ_CMDS["diff"]
        elif re.search(r"git\s+branch|show\s+branches", text_lower):
            git_cmd = self.GIT_READ_CMDS["branch"]
        elif re.search(r"git\s+remote", text_lower):
            git_cmd = self.GIT_READ_CMDS["remote"]
        elif re.search(r"git\s+tag", text_lower):
            git_cmd = self.GIT_READ_CMDS["tag"]
        elif re.search(r"git\s+stash\s*$|stash\s+list", text_lower):
            git_cmd = self.GIT_READ_CMDS["stash_list"]
        elif re.search(r"git\s+show", text_lower):
            git_cmd = self.GIT_READ_CMDS["show"]
        elif re.search(r"git\s+blame", text_lower):
            file_match = re.search(r"blame\s+(\S+)", text, re.IGNORECASE)
            if file_match:
                git_cmd = ["git", "blame", "--date=short", file_match.group(1)]
            else:
                return {"response": "Specify file: git blame <filename>", "data": None, "action": "git_info"}
        elif re.search(r"git\s+init", text_lower):
            return self._run_git_cmd(["git", "init"], "git init")

        # Write commands when git_write is disabled
        if not git_cmd and not self._allow_git_write:
            if re.search(r"git\s+(commit|push|pull|merge|checkout|add|reset)", text_lower):
                return {
                    "response": "Git write operations are disabled in settings. Enable 'Allow Git Write' to use commit, push, pull, etc.",
                    "data": {"type": "git_write_disabled"},
                    "action": "git_info",
                }

        if not git_cmd:
            return {"response": "Unrecognized git command. Try: status, log, diff, branch, commit, push, pull, checkout, merge, stash, reset", "data": None, "action": "git_info"}

        return self._run_git_cmd(git_cmd, " ".join(git_cmd[:3]))

    def _run_git_cmd(self, cmd: list, label: str) -> dict:
        try:
            result = subprocess.run(
                cmd, cwd=self._project_root,
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
            )
            output = result.stdout.strip() or result.stderr.strip() or "(no output)"
            if len(output) > 3000:
                output = output[:3000] + "\n... (truncated)"

            success = result.returncode == 0
            icon = "✅" if success else "❌"
            return {
                "response": f"{icon} **{label}**\n```\n{output}\n```",
                "data": {"type": "git_result", "command": label, "output": output, "return_code": result.returncode, "success": success},
                "action": "git_result",
            }
        except subprocess.TimeoutExpired:
            return {"response": f"⏰ Git command timed out: {label}", "data": None, "action": "error"}
        except FileNotFoundError:
            return {"response": "Git is not installed or not in PATH.", "data": None, "action": "error"}
        except Exception as e:
            return {"response": f"Git error: {e}", "data": None, "action": "error"}

    # ========================
    # DEBUGGING ENGINE
    # ========================

    def _handle_debug(self, text: str, context: dict) -> dict:
        # Extract error/traceback from text or context
        error_text = text
        code_block = re.search(r'```[\s\S]*?```', text)
        if code_block:
            error_text = code_block.group()

        # Analyze the error
        analysis = self._analyze_error(error_text)

        if analysis["patterns_found"]:
            lines = ["🔍 **Debug Analysis:**\n"]
            for finding in analysis["patterns_found"]:
                lines.append(f"  **{finding['type']}**: {finding['fix']}")

            if analysis.get("line_number"):
                lines.append(f"\n  📍 **Error location:** Line {analysis['line_number']}")
            if analysis.get("file"):
                lines.append(f"  📂 **File:** {analysis['file']}")

            lines.append("\n**Suggestions:**")
            for i, suggestion in enumerate(analysis.get("suggestions", []), 1):
                lines.append(f"  {i}. {suggestion}")

            return {
                "response": "\n".join(lines),
                "data": {"type": "debug_analysis", "analysis": analysis},
                "action": "code_debug",
            }

        # If no patterns matched, provide general debug guidance
        return {
            "response": (
                "🔍 **Debug Helper**\n\n"
                "Share the error message or traceback and I'll analyze it.\n\n"
                "**I can detect:**\n"
                "  - Missing modules / imports\n"
                "  - Syntax & indentation errors\n"
                "  - Type errors & argument mismatches\n"
                "  - Key/attribute errors\n"
                "  - File, connection, permission errors\n"
                "  - JSON/encoding issues\n"
                "  - Recursion problems\n\n"
                "Paste your error in a code block (```) for best results."
            ),
            "data": {"type": "debug_help"},
            "action": "code_debug",
        }

    def _analyze_error(self, text: str) -> dict:
        result = {"patterns_found": [], "suggestions": [], "line_number": None, "file": None}

        # Extract line number
        line_match = re.search(r'line\s+(\d+)', text, re.IGNORECASE)
        if line_match:
            result["line_number"] = int(line_match.group(1))

        # Extract file
        file_match = re.search(r'File\s+"([^"]+)"', text)
        if file_match:
            result["file"] = file_match.group(1)

        # Match known patterns
        for pattern, info in self.ERROR_PATTERNS.items():
            match = re.search(pattern, text)
            if match:
                fix = info["fix"]
                try:
                    fix = fix.format(*match.groups())
                except (IndexError, KeyError):
                    pass
                result["patterns_found"].append({
                    "type": info["type"],
                    "fix": fix,
                    "pattern": pattern,
                })

        # Add contextual suggestions
        if any(p["type"] == "missing_module" for p in result["patterns_found"]):
            result["suggestions"].append("Run: pip install <module_name>")
            result["suggestions"].append("Check if you're in the right virtual environment")
        if any(p["type"] == "syntax_error" for p in result["patterns_found"]):
            result["suggestions"].append("Check for unclosed brackets or quotes on lines above the error")
            result["suggestions"].append("Use a linter (flake8/pylint) to catch syntax issues")
        if any(p["type"] == "connection_error" for p in result["patterns_found"]):
            result["suggestions"].append("Verify the service is running on the expected port")
            result["suggestions"].append("Check firewall/network settings")
        if not result["suggestions"]:
            result["suggestions"].append("Add print() statements before the error to trace variable values")
            result["suggestions"].append("Use try/except to catch and log the full traceback")
            result["suggestions"].append("Check Python version compatibility")

        return result

    # ========================
    # TESTING FRAMEWORK
    # ========================

    def _handle_testing(self, text: str, context: dict) -> dict:
        text_lower = text.lower()

        # Run existing tests
        if re.search(r"run\s+tests?|pytest|unittest", text_lower):
            return self._run_tests(text)

        # Show test results
        if re.search(r"test\s+results?|last\s+test|test\s+history", text_lower):
            return self._show_test_results()

        # Generate test for a file
        if re.search(r"generate\s+tests?|write\s+tests?|test\s+(?:likho|banao|bana)", text_lower):
            return self._generate_test_plan(text, context)

        # Test a specific function/module
        return self._run_tests(text)

    def _run_tests(self, text: str) -> dict:
        """Run pytest or unittest and capture results."""
        # Detect test file or default
        file_match = re.search(r'(?:run\s+tests?\s+(?:for|on|in)\s+)(\S+)', text, re.IGNORECASE)
        target = file_match.group(1) if file_match else None

        # Try pytest first
        cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short", "--no-header", "-q"]
        if target:
            target_path = Path(self._project_root) / target
            if target_path.exists():
                cmd.append(str(target_path))
            else:
                cmd.append(target)

        try:
            result = subprocess.run(
                cmd, cwd=self._project_root,
                capture_output=True, text=True, timeout=60,
                encoding="utf-8", errors="replace",
            )
            output = result.stdout.strip() or result.stderr.strip() or "(no output)"

            # Parse results
            passed = len(re.findall(r"PASSED", output))
            failed = len(re.findall(r"FAILED", output))
            errors = len(re.findall(r"ERROR", output))
            total = passed + failed + errors

            if len(output) > 4000:
                output = output[:4000] + "\n... (truncated)"

            test_result = {
                "timestamp": datetime.now().isoformat(),
                "total": total, "passed": passed, "failed": failed, "errors": errors,
                "success": result.returncode == 0,
                "target": target or "all",
            }
            _save_test_results(test_result)

            icon = "✅" if result.returncode == 0 else "❌"
            summary = f"{icon} **Test Results:** {passed} passed, {failed} failed, {errors} errors (total: {total})"

            return {
                "response": f"{summary}\n\n```\n{output}\n```",
                "data": {"type": "test_result", **test_result},
                "action": "test_result",
            }

        except subprocess.TimeoutExpired:
            return {"response": "⏰ Tests timed out (60s limit).", "data": None, "action": "error"}
        except Exception as e:
            # Fallback: try unittest
            try:
                cmd2 = [sys.executable, "-m", "unittest", "discover", "-s", self._project_root, "-v"]
                result2 = subprocess.run(cmd2, cwd=self._project_root, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
                output2 = result2.stdout.strip() or result2.stderr.strip() or "(no output)"
                if len(output2) > 4000:
                    output2 = output2[:4000] + "\n... (truncated)"
                return {
                    "response": f"**Test Results (unittest):**\n```\n{output2}\n```",
                    "data": {"type": "test_result", "framework": "unittest"},
                    "action": "test_result",
                }
            except Exception:
                return {"response": f"Test error: {e}", "data": None, "action": "error"}

    def _show_test_results(self) -> dict:
        try:
            if not TEST_RESULTS_FILE.exists():
                return {"response": "No test results yet. Run tests first.", "data": None, "action": "test_result"}

            results = json.loads(TEST_RESULTS_FILE.read_text(encoding="utf-8"))
            if not results:
                return {"response": "No test results found.", "data": None, "action": "test_result"}

            lines = ["📊 **Test History (last 10):**\n"]
            for r in results[-10:]:
                icon = "✅" if r.get("success") else "❌"
                ts = r.get("timestamp", "?")[:16]
                lines.append(f"  {icon} [{ts}] {r.get('passed', 0)}✓ {r.get('failed', 0)}✗ {r.get('errors', 0)}⚠ — {r.get('target', 'all')}")

            return {
                "response": "\n".join(lines),
                "data": {"type": "test_history", "results": results[-10:]},
                "action": "test_result",
            }
        except Exception as e:
            return {"response": f"Error reading test results: {e}", "data": None, "action": "error"}

    def _generate_test_plan(self, text: str, context: dict) -> dict:
        """Generate a test plan / test cases for code."""
        target = self._extract_path(text)
        language = self._detect_language(text)

        if target and Path(target).exists():
            try:
                code = Path(target).read_text(encoding="utf-8", errors="ignore")[:3000]
                # Extract function/class names
                funcs = re.findall(r"(?:def|function|class)\s+(\w+)", code)
                lines = [f"📝 **Test Plan for {Path(target).name}:**\n"]
                lines.append(f"Found {len(funcs)} functions/classes to test:\n")
                for f in funcs[:20]:
                    lines.append(f"  - test_{f}(): verify normal behavior")
                    lines.append(f"  - test_{f}_edge(): edge cases & boundary values")
                    lines.append(f"  - test_{f}_error(): error handling & exceptions")

                lines.append(f"\n**Framework:** pytest ({language})")
                lines.append("**Coverage target:** 80%+")

                return {
                    "response": "\n".join(lines),
                    "data": {"type": "test_plan", "functions": funcs, "file": target, "instruction": f"Generate pytest tests for these functions in {language}"},
                    "action": "code_generate",
                }
            except Exception as e:
                return {"response": f"Error analyzing file: {e}", "data": None, "action": "error"}

        return {
            "response": (
                "📝 **Test Generation**\n\n"
                "Specify a file to generate tests for:\n"
                "  - `generate tests for backend/main.py`\n"
                "  - `write tests for utils.py`\n\n"
                "Or describe what you want to test and I'll generate test cases."
            ),
            "data": {"type": "test_help", "instruction": "Generate test cases for the user's code"},
            "action": "code_generate",
        }

    # ========================
    # DEPLOY ENGINE
    # ========================

    def _handle_deploy(self, text: str, context: dict) -> dict:
        text_lower = text.lower()

        # Check project type
        project_root = Path(self._project_root)
        has_package_json = (project_root / "package.json").exists()
        has_requirements = (project_root / "requirements.txt").exists()
        has_dockerfile = (project_root / "Dockerfile").exists()
        has_setup_py = (project_root / "setup.py").exists()
        has_pyproject = (project_root / "pyproject.toml").exists()

        # Install dependencies
        if re.search(r"install\s+(?:dependencies|packages|requirements)", text_lower):
            return self._install_deps(project_root, has_package_json, has_requirements)

        # Build for production
        if re.search(r"build\s+(?:for\s+)?(?:production|prod)", text_lower):
            return self._build_production(project_root, has_package_json)

        # Docker
        if re.search(r"docker|container", text_lower):
            return self._docker_info(project_root, has_dockerfile)

        # Setup/init project
        if re.search(r"setup\s+(?:project|env|environment)", text_lower):
            return self._project_setup(project_root)

        # General deploy info
        lines = ["🚀 **Deploy Status:**\n"]
        lines.append(f"  📁 Project: {project_root.name}")
        lines.append(f"  📦 package.json: {'✅' if has_package_json else '❌'}")
        lines.append(f"  📋 requirements.txt: {'✅' if has_requirements else '❌'}")
        lines.append(f"  🐳 Dockerfile: {'✅' if has_dockerfile else '❌'}")
        lines.append(f"  📐 setup.py/pyproject.toml: {'✅' if (has_setup_py or has_pyproject) else '❌'}")

        lines.append("\n**Available commands:**")
        lines.append("  - `install dependencies` — install all project deps")
        lines.append("  - `build for production` — create prod build")
        lines.append("  - `docker info` — Dockerfile status & commands")
        lines.append("  - `setup project` — initialize project environment")

        return {
            "response": "\n".join(lines),
            "data": {"type": "deploy_info", "has_package_json": has_package_json, "has_requirements": has_requirements, "has_dockerfile": has_dockerfile},
            "action": "deploy_info",
        }

    def _install_deps(self, root: Path, has_npm: bool, has_pip: bool) -> dict:
        results = []
        if has_pip:
            try:
                r = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                    cwd=str(root), capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
                results.append(f"**pip install:** {'✅ Success' if r.returncode == 0 else '❌ Failed'}\n```\n{(r.stdout or r.stderr)[:1000]}\n```")
            except Exception as e:
                results.append(f"**pip install:** ❌ Error: {e}")

        if has_npm:
            try:
                npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
                r = subprocess.run([npm_cmd, "install"], cwd=str(root), capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
                results.append(f"**npm install:** {'✅ Success' if r.returncode == 0 else '❌ Failed'}\n```\n{(r.stdout or r.stderr)[:1000]}\n```")
            except Exception as e:
                results.append(f"**npm install:** ❌ Error: {e}")

        if not results:
            return {"response": "No package files found (requirements.txt / package.json).", "data": None, "action": "deploy_info"}

        return {
            "response": "📦 **Dependency Installation:**\n\n" + "\n\n".join(results),
            "data": {"type": "install_result"},
            "action": "deploy_result",
        }

    def _build_production(self, root: Path, has_npm: bool) -> dict:
        if has_npm:
            try:
                npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
                r = subprocess.run([npm_cmd, "run", "build"], cwd=str(root), capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace")
                output = (r.stdout or r.stderr)[:2000]
                icon = "✅" if r.returncode == 0 else "❌"
                return {
                    "response": f"{icon} **Production Build:**\n```\n{output}\n```",
                    "data": {"type": "build_result", "success": r.returncode == 0},
                    "action": "deploy_result",
                }
            except Exception as e:
                return {"response": f"Build error: {e}", "data": None, "action": "error"}
        return {"response": "No build script found. Add `npm run build` or similar.", "data": None, "action": "deploy_info"}

    def _docker_info(self, root: Path, has_dockerfile: bool) -> dict:
        if has_dockerfile:
            try:
                content = (root / "Dockerfile").read_text(encoding="utf-8")[:2000]
                return {
                    "response": f"🐳 **Dockerfile found:**\n```dockerfile\n{content}\n```\n\n**Commands:**\n  `docker build -t {root.name.lower()} .`\n  `docker run -p 8000:8000 {root.name.lower()}`",
                    "data": {"type": "docker_info", "has_dockerfile": True},
                    "action": "deploy_info",
                }
            except Exception:
                pass
        return {
            "response": "🐳 No Dockerfile found. I can generate one if you tell me the project type (Python/Node/etc).",
            "data": {"type": "docker_info", "has_dockerfile": False},
            "action": "deploy_info",
        }

    def _project_setup(self, root: Path) -> dict:
        lines = ["⚙️ **Project Setup Guide:**\n"]
        if (root / "requirements.txt").exists():
            lines.append("**Python:**")
            lines.append("  1. `python -m venv venv`")
            lines.append("  2. `venv\\Scripts\\activate` (Windows) or `source venv/bin/activate`")
            lines.append("  3. `pip install -r requirements.txt`")
        if (root / "package.json").exists():
            lines.append("\n**Node.js:**")
            lines.append("  1. `npm install`")
            lines.append("  2. `npm run dev` (development)")
            lines.append("  3. `npm run build` (production)")
        if (root / ".env.example").exists():
            lines.append("\n**Environment:**")
            lines.append("  `copy .env.example .env` → fill in your API keys")
        elif (root / ".env").exists():
            lines.append("\n**Environment:** .env file exists ✅")
        return {
            "response": "\n".join(lines),
            "data": {"type": "setup_guide"},
            "action": "deploy_info",
        }

    # ========================
    # CODE EXECUTION (sandboxed)
    # ========================

    def _handle_execution(self, text: str, context: dict) -> dict:
        if not self._allow_execution:
            return {"response": "Code execution is disabled in settings.", "data": None, "action": "error"}

        code = context.get("code") or context.get("previous_result") or ""
        code_match = re.search(r'```(?:\w+)?\n([\s\S]+?)```', text)
        if code_match:
            code = code_match.group(1)

        if not code.strip():
            return {"response": "No code found. Provide code in a ``` code block.", "data": None, "action": "code_execution"}

        lang = self._detect_language(text) or "python"
        if lang not in ("python", "bash", "shell", "powershell"):
            return {"response": f"Direct execution supports Python and Bash only. For {lang}, copy and run in your IDE.", "data": {"code": code, "language": lang}, "action": "code_execution"}

        try:
            if lang == "python":
                result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace", cwd=tempfile.gettempdir())
            else:
                result = subprocess.run(
                    ["bash", "-c", code] if os.name != "nt" else ["powershell", "-Command", code],
                    capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace", cwd=tempfile.gettempdir())

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            output = stdout or "(no output)"
            if stderr:
                output += f"\n\nSTDERR:\n{stderr}"
            if len(output) > 3000:
                output = output[:3000] + "\n... (truncated)"

            return {
                "response": f"**Execution result** ({lang}):\n```\n{output}\n```",
                "data": {"type": "execution_result", "language": lang, "stdout": stdout[:2000], "stderr": stderr[:1000], "return_code": result.returncode, "success": result.returncode == 0},
                "action": "code_execution",
            }
        except subprocess.TimeoutExpired:
            return {"response": "⏰ Code timed out (15s). Possible infinite loop.", "data": None, "action": "error"}
        except Exception as e:
            return {"response": f"Execution error: {e}", "data": None, "action": "error"}

    # ========================
    # FILE ANALYSIS
    # ========================

    def _handle_file_analysis(self, text: str, context: dict) -> dict:
        text_lower = text.lower()
        if re.search(r"list\s+(?:files|directory|folder)", text_lower):
            target = self._extract_path(text) or self._project_root
            return self._list_directory(target)
        if re.search(r"count\s+lines", text_lower):
            target = self._extract_path(text)
            if target: return self._count_lines(target)
            return {"response": "Specify a file path.", "data": None, "action": "file_analysis"}
        if re.search(r"file\s+(?:size|info|stats)", text_lower):
            target = self._extract_path(text)
            if target: return self._file_stats(target)
            return {"response": "Specify a file path.", "data": None, "action": "file_analysis"}
        if re.search(r"(?:find|search)\s+(?:in\s+code|files?)", text_lower):
            pat = re.search(r'(?:find|search)\s+(?:for\s+)?["\']?(.+?)["\']?\s+(?:in|from)', text, re.IGNORECASE)
            if pat: return self._search_files(pat.group(1).strip())
            return {"response": "Specify what to search. Example: find 'def main' in code", "data": None, "action": "file_analysis"}
        target = self._extract_path(text)
        if target: return self._read_file(target)
        return {"response": "What to analyze? I can: list files, count lines, file stats, search code, read a file.", "data": None, "action": "file_analysis"}

    def _list_directory(self, path: str) -> dict:
        p = Path(path)
        if not p.exists(): return {"response": f"Not found: {path}", "data": None, "action": "error"}
        if not p.is_dir(): return {"response": f"Not a directory: {path}", "data": None, "action": "error"}
        items = []
        try:
            for item in sorted(p.iterdir()):
                if item.name.startswith("."): continue
                kind = "📁" if item.is_dir() else "📄"
                size = ""
                if item.is_file():
                    sz = item.stat().st_size
                    size = f" ({sz:,} bytes)" if sz < 1024*1024 else f" ({sz/1024/1024:.1f} MB)"
                items.append(f"{kind} {item.name}{size}")
        except PermissionError:
            return {"response": f"Permission denied: {path}", "data": None, "action": "error"}
        if not items: return {"response": f"Empty: {path}", "data": None, "action": "file_analysis"}
        listing = "\n".join(items[:50])
        return {"response": f"**{p.name}/** ({len(items)} items):\n```\n{listing}\n```", "data": {"type": "directory_listing", "path": str(p), "item_count": len(items)}, "action": "file_analysis"}

    def _count_lines(self, path: str) -> dict:
        p = Path(path)
        if not p.exists() or not p.is_file(): return {"response": f"Not found: {path}", "data": None, "action": "error"}
        try:
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            code_lines = [l for l in lines if l.strip() and not l.strip().startswith(("#", "//", "/*", "*"))]
            return {"response": f"**{p.name}**: {len(lines)} total, {len(code_lines)} code lines", "data": {"file": str(p), "total_lines": len(lines), "code_lines": len(code_lines)}, "action": "file_analysis"}
        except Exception as e:
            return {"response": f"Error: {e}", "data": None, "action": "error"}

    def _file_stats(self, path: str) -> dict:
        p = Path(path)
        if not p.exists(): return {"response": f"Not found: {path}", "data": None, "action": "error"}
        stat = p.stat()
        return {"response": f"**{p.name}** | {stat.st_size:,} bytes | Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')} | Ext: {p.suffix or 'none'}", "data": {"file": str(p), "size": stat.st_size}, "action": "file_analysis"}

    def _read_file(self, path: str) -> dict:
        p = Path(path)
        if not p.exists() or not p.is_file(): return {"response": f"Not found: {path}", "data": None, "action": "error"}
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            if len(content) > 5000: content = content[:5000] + "\n... (truncated)"
            return {"response": f"**{p.name}**:\n```{p.suffix.lstrip('.')}\n{content}\n```", "data": {"file": str(p)}, "action": "file_analysis"}
        except Exception as e:
            return {"response": f"Error: {e}", "data": None, "action": "error"}

    def _search_files(self, pattern: str) -> dict:
        root = Path(self._project_root)
        matches = []
        exts = (".py", ".js", ".ts", ".jsx", ".html", ".css", ".json", ".md", ".yaml", ".yml", ".toml")
        try:
            for fpath in root.rglob("*"):
                if fpath.is_file() and fpath.suffix in exts and ".git" not in str(fpath):
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="ignore")
                        for i, line in enumerate(content.splitlines(), 1):
                            if pattern.lower() in line.lower():
                                matches.append(f"{fpath.relative_to(root)}:{i}: {line.strip()[:120]}")
                                if len(matches) >= 30: break
                    except Exception: continue
                if len(matches) >= 30: break
        except Exception as e:
            return {"response": f"Search error: {e}", "data": None, "action": "error"}
        if not matches: return {"response": f"No matches for '{pattern}'.", "data": None, "action": "file_analysis"}
        return {"response": f"Found {len(matches)} matches:\n```\n" + "\n".join(matches) + "\n```", "data": {"type": "search_result", "pattern": pattern, "match_count": len(matches)}, "action": "file_analysis"}

    def _extract_path(self, text: str) -> str:
        match = re.search(r'["\']([^"\']+)["\']', text)
        if match: return match.group(1)
        match = re.search(r'(\S+\.\w{1,6})', text)
        if match and not match.group(1).startswith("http"):
            path = match.group(1)
            full = Path(self._project_root) / path
            if full.exists(): return str(full)
            if Path(path).exists(): return path
        return ""

    # ========================
    # CODE GENERATION
    # ========================

    def _handle_code_gen(self, text: str, context: dict) -> dict:
        language = self._detect_language(text)
        task = self._extract_task(text)
        is_debug = bool(re.search(r"\b(debug|fix|error|bug|issue|problem)\b", text, re.IGNORECASE))
        if is_debug:
            instruction = f"Debug and fix the code. Explain what was wrong. Language: {language}."
            action = "code_debug"
        else:
            comment_note = " Include clear comments." if self._include_comments else ""
            instruction = f"Generate clean {language} code for: {task}. Best practices + error handling.{comment_note}"
            action = "code_generate"
        return {
            "response": f"Let me {'debug' if is_debug else 'write'} that {language} code...",
            "data": {"language": language, "task": task, "is_debug": is_debug, "instruction": instruction},
            "action": action,
        }

    def _detect_language(self, text: str) -> str:
        match = self.LANGUAGE_PATTERNS.search(text)
        if match:
            lang = match.group(1).lower()
            norms = {"golang": "go", "csharp": "c#", "node": "javascript", "react": "javascript (React)", "vue": "javascript (Vue)", "angular": "typescript (Angular)", "flask": "python (Flask)", "django": "python (Django)", "fastapi": "python (FastAPI)"}
            return norms.get(lang, lang)
        return self._language

    def _extract_task(self, text: str) -> str:
        task = self.CODE_KEYWORDS.sub("", text).strip()
        task = re.sub(r"^(in|using|with|for|a|an|the|ek|mujhe)\s+", "", task, flags=re.IGNORECASE).strip()
        task = self.LANGUAGE_PATTERNS.sub("", task).strip()
        return task if len(task) > 2 else text

    # ========================
    # SYSTEM PROMPT & SETTINGS
    # ========================

    def get_system_prompt_addition(self) -> str:
        return (
            f"Dev tools v3 — default language: {self._language}\n"
            f"Git: full read+write (status/log/diff/commit/push/pull/branch/merge/stash/reset)\n"
            f"Debug: stack trace analysis, 13+ error pattern matchers, auto-fix suggestions\n"
            f"Testing: run pytest/unittest, generate test plans, test history tracking\n"
            f"Deploy: install deps, production build, Docker info, project setup\n"
            f"Code: generation, execution (Python/Bash), file analysis, search"
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        language = self._detect_language(text)
        task = self._extract_task(text)
        if task and task != text:
            return f"[Hephaestus v3] Language: {language} | Task: {task}"
        return ""

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "language": self._language,
            "include_comments": self._include_comments,
            "project_root": self._project_root,
            "allow_execution": self._allow_execution,
            "allow_git_write": self._allow_git_write,
        }

    def update_settings(self, settings: dict):
        super().update_settings(settings)
        if "language" in settings: self._language = settings["language"]
        if "include_comments" in settings: self._include_comments = bool(settings["include_comments"])
        if "project_root" in settings: self._project_root = settings["project_root"]
        if "allow_execution" in settings: self._allow_execution = bool(settings["allow_execution"])
        if "allow_git_write" in settings: self._allow_git_write = bool(settings["allow_git_write"])

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {"key": "language", "label": "Default Language", "type": "select", "value": self._language,
             "options": [{"label": "Python", "value": "python"}, {"label": "JavaScript", "value": "javascript"}, {"label": "TypeScript", "value": "typescript"}, {"label": "Java", "value": "java"}, {"label": "Go", "value": "go"}, {"label": "Rust", "value": "rust"}, {"label": "HTML/CSS", "value": "html"}, {"label": "SQL", "value": "sql"}, {"label": "Bash", "value": "bash"}]},
            {"key": "include_comments", "label": "Include Code Comments", "type": "toggle", "value": self._include_comments},
            {"key": "allow_execution", "label": "Allow Code Execution", "type": "toggle", "value": self._allow_execution},
            {"key": "allow_git_write", "label": "Allow Git Write (commit/push/pull)", "type": "toggle", "value": self._allow_git_write},
        ]
