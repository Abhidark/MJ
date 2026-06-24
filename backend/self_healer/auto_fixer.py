"""
MJ Self-Healing: Auto Fixer
Uses Groq or Ollama LLM to analyze errors and attempt automatic code fixes.
Auto-detects provider (Groq on laptop, Ollama on PC).
"""

import httpx
import json
import re
import os
import shutil
import importlib
from pathlib import Path
from datetime import datetime
from self_healer.error_tracker import update_error, learn_fix

# Backup dir for pre-fix code
BACKUP_DIR = Path(__file__).parent.parent / "error_logs" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Provider config
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3:1.7b"

# Recovery log
RECOVERY_LOG = Path(__file__).parent.parent / "error_logs" / "recovery_history.json"


def _get_groq_key():
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GROQ_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


async def _call_llm(messages, max_tokens=2000):
    """Call Groq or Ollama, auto-detecting which is available."""
    # Try Groq first (faster, works on laptop)
    groq_key = _get_groq_key()
    if groq_key:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    GROQ_API_URL,
                    headers={"Authorization": "Bearer " + groq_key, "Content-Type": "application/json"},
                    json={"model": GROQ_MODEL, "messages": messages, "temperature": 0.1, "max_tokens": max_tokens},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"]
                    # Strip think tags
                    text = re.sub(r'<think>[\s\S]*?</think>', '', text).strip()
                    return text
        except Exception:
            pass

    # Fallback to Ollama
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                OLLAMA_URL,
                json={"model": OLLAMA_MODEL, "messages": messages, "stream": False,
                      "options": {"temperature": 0.1, "num_predict": max_tokens}},
            )
            if resp.status_code == 200:
                text = resp.json().get("message", {}).get("content", "")
                text = re.sub(r'<think>[\s\S]*?</think>', '', text).strip()
                return text
    except Exception:
        pass

    return None


async def attempt_fix(error_entry):
    """
    Attempt to auto-fix an error using LLM.
    Steps: Read broken file -> LLM analysis -> Validate fix -> Backup -> Apply
    """
    error_id = error_entry["id"]
    file_path = error_entry.get("file_path", "")

    if not file_path or not Path(file_path).exists():
        update_error(error_id, "failed", "Source file not found in traceback.")
        return {"success": False, "message": "Source file nahi mila. Manual fix needed.", "error_id": error_id}

    update_error(error_id, "attempting", "LLM se fix puch rahe hain...")

    try:
        # Step 1: Read the broken file
        source_path = Path(file_path)
        original_code = source_path.read_text(encoding="utf-8")

        # Context lines around error
        lines = original_code.split("\n")
        line_num = error_entry.get("line_number", 0)
        start = max(0, line_num - 15)
        end = min(len(lines), line_num + 15)
        context_lines = "\n".join(
            (">>> " if i + 1 == line_num else "    ") + str(i + 1) + ": " + line
            for i, line in enumerate(lines[start:end], start=start)
        )

        # Step 2: Build prompt
        messages = [
            {"role": "system", "content": "You are a Python debugging expert. Fix bugs in FastAPI applications. Return ONLY the fixed Python code in ```python``` blocks. No explanation."},
            {"role": "user", "content": "ERROR TYPE: " + error_entry["type"] + "\nERROR: " + error_entry["message"] + "\n\nFILE: " + file_path + "\nLINE: " + str(line_num) + "\n\nCODE AROUND ERROR:\n" + context_lines + "\n\nFULL FILE:\n```python\n" + original_code + "\n```\n\nFix ONLY the bug. Keep all imports, functions, endpoints exactly as they are."},
        ]

        # Step 3: Call LLM
        llm_response = await _call_llm(messages, max_tokens=3000)

        if not llm_response:
            update_error(error_id, "failed", "LLM not available (neither Groq nor Ollama).")
            return {"success": False, "message": "LLM available nahi hai. Groq key ya Ollama check karo.", "error_id": error_id}

        # Step 4: Extract fixed code
        fixed_code = _extract_code(llm_response)
        if not fixed_code:
            update_error(error_id, "failed", "LLM ne valid code nahi diya.")
            return {"success": False, "message": "LLM se fix code nahi mila.", "error_id": error_id, "suggestion": llm_response[:500]}

        # Step 5: Validate
        validation = _validate_fix(original_code, fixed_code, file_path)
        if not validation["safe"]:
            update_error(error_id, "failed", "Fix risky: " + validation["reason"])
            return {"success": False, "message": "Fix apply nahi ki -- risky: " + validation["reason"], "error_id": error_id, "suggested_fix": fixed_code[:1000]}

        # Step 6: Backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = source_path.stem + "_" + timestamp + "_backup" + source_path.suffix
        backup_path = BACKUP_DIR / backup_name
        shutil.copy2(file_path, backup_path)

        # Step 7: Apply fix
        source_path.write_text(fixed_code, encoding="utf-8")

        # Step 8: Try hot-reload the module
        reload_result = _try_hot_reload(file_path)

        update_error(error_id, "fixed", "Auto-fixed! Backup: " + backup_name)

        # Log recovery
        _log_recovery(error_entry, backup_name, reload_result)

        # Learn the fix pattern
        learn_fix(error_entry["type"], "Auto-fixed in " + source_path.name)

        msg = "Fix applied to " + source_path.name + "!"
        if reload_result:
            msg += " Module hot-reloaded successfully."
        else:
            msg += " Server restart needed: stop.bat -> start.bat"

        return {"success": True, "message": msg, "error_id": error_id, "backup": str(backup_path), "hot_reloaded": reload_result}

    except Exception as e:
        update_error(error_id, "failed", "Fix attempt error: " + str(e))
        return {"success": False, "message": "Fix attempt me error: " + str(e), "error_id": error_id}


async def analyze_error(error_entry):
    """Analyze error without fixing -- return explanation."""
    messages = [
        {"role": "system", "content": "You are a Python debugging expert. Explain errors in simple Hinglish (Hindi + English mix). Keep it short -- 2-3 lines max."},
        {"role": "user", "content": "ERROR: " + error_entry["type"] + ": " + error_entry["message"] + "\nFILE: " + error_entry.get("file_path", "unknown") + "\nLINE: " + str(error_entry.get("line_number", "?")) + "\n\nTRACEBACK:\n" + error_entry.get("traceback", "") + "\n\nExplain: 1) Kya error hai 2) Kyun aaya 3) Kaise fix hoga"},
    ]

    result = await _call_llm(messages, max_tokens=300)
    if result:
        return result
    return error_entry["type"] + ": " + error_entry["message"] + " -- File: " + error_entry.get("file_path", "?")


def _extract_code(llm_response):
    """Extract Python code from LLM response."""
    pattern = r"```(?:python)?\s*\n(.*?)```"
    matches = re.findall(pattern, llm_response, re.DOTALL)
    if matches:
        return max(matches, key=len).strip()
    lines = llm_response.strip().split("\n")
    if lines and (lines[0].startswith("import ") or lines[0].startswith("from ") or lines[0].startswith("#")):
        return llm_response.strip()
    return ""


def _validate_fix(original, fixed, file_path):
    """Validate fix is safe to apply."""
    orig_lines = original.strip().split("\n")
    fixed_lines = fixed.strip().split("\n")

    if len(fixed_lines) < len(orig_lines) * 0.7:
        return {"safe": False, "reason": "Too much code removed (" + str(len(orig_lines)) + " -> " + str(len(fixed_lines)) + " lines)"}

    if len(fixed_lines) < 5:
        return {"safe": False, "reason": "Fixed code too short -- likely partial"}

    orig_imports = set(re.findall(r"^(?:from|import)\s+\S+", original, re.MULTILINE))
    fixed_imports = set(re.findall(r"^(?:from|import)\s+\S+", fixed, re.MULTILINE))
    missing = orig_imports - fixed_imports
    if len(missing) > 3:
        return {"safe": False, "reason": str(len(missing)) + " imports removed -- too risky"}

    orig_defs = len(re.findall(r"^(?:def |class |async def )", original, re.MULTILINE))
    fixed_defs = len(re.findall(r"^(?:def |class |async def )", fixed, re.MULTILINE))
    if fixed_defs < orig_defs * 0.7:
        return {"safe": False, "reason": "Functions reduced (" + str(orig_defs) + " -> " + str(fixed_defs) + ")"}

    try:
        compile(fixed, file_path, "exec")
    except SyntaxError as e:
        return {"safe": False, "reason": "Syntax error in fix: " + str(e)}

    return {"safe": True, "reason": ""}


def _try_hot_reload(file_path):
    """Try to hot-reload the fixed module without server restart."""
    try:
        # Convert file path to module path
        fp = Path(file_path)
        backend_dir = Path(__file__).parent.parent

        # Only reload if file is inside backend
        try:
            rel = fp.relative_to(backend_dir)
        except ValueError:
            return False

        # Build module name from path
        parts = list(rel.with_suffix("").parts)
        module_name = ".".join(parts)

        import sys
        if module_name in sys.modules:
            mod = sys.modules[module_name]
            importlib.reload(mod)
            return True
    except Exception:
        pass
    return False


def _log_recovery(error_entry, backup_name, hot_reloaded):
    """Log recovery to history file."""
    try:
        history = []
        if RECOVERY_LOG.exists():
            history = json.loads(RECOVERY_LOG.read_text(encoding="utf-8"))

        history.append({
            "timestamp": datetime.now().isoformat(),
            "error_type": error_entry["type"],
            "error_message": error_entry["message"][:100],
            "file": error_entry.get("file_path", ""),
            "backup": backup_name,
            "hot_reloaded": hot_reloaded,
        })

        # Keep last 100
        history = history[-100:]
        RECOVERY_LOG.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def get_recovery_history(limit=20):
    """Get recent recovery history."""
    try:
        if RECOVERY_LOG.exists():
            history = json.loads(RECOVERY_LOG.read_text(encoding="utf-8"))
            return history[-limit:]
    except Exception:
        pass
    return []
