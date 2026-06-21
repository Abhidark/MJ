"""
MJ Self-Healing: Auto Fixer
Uses Ollama LLM to analyze errors and attempt automatic code fixes.
"""

import httpx
import json
import re
import shutil
from pathlib import Path
from datetime import datetime
from self_healer.error_tracker import update_error

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:1.5b"

# Backup dir for pre-fix code
BACKUP_DIR = Path(__file__).parent.parent / "error_logs" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


async def attempt_fix(error_entry: dict) -> dict:
    """
    Attempt to auto-fix an error using Ollama.

    Steps:
    1. Read the broken file
    2. Send error + code to Ollama for analysis
    3. Get fix suggestion
    4. Backup original file
    5. Apply the fix
    6. Return result
    """
    error_id = error_entry["id"]
    file_path = error_entry.get("file_path", "")

    if not file_path or not Path(file_path).exists():
        update_error(error_id, "failed", "Source file not found in traceback.")
        return {
            "success": False,
            "message": "Error ka source file nahi mila. Manual fix needed.",
            "error_id": error_id,
        }

    update_error(error_id, "attempting", "Ollama se fix puch rahe hain...")

    try:
        # Step 1: Read the broken file
        source_path = Path(file_path)
        original_code = source_path.read_text(encoding="utf-8")

        # Get surrounding lines for context (20 lines around error)
        lines = original_code.split("\n")
        line_num = error_entry.get("line_number", 0)
        start = max(0, line_num - 15)
        end = min(len(lines), line_num + 15)
        context_lines = "\n".join(
            f"{'>>>' if i+1 == line_num else '   '} {i+1}: {line}"
            for i, line in enumerate(lines[start:end], start=start)
        )

        # Step 2: Build prompt for Ollama
        prompt = f"""You are a Python debugging expert. An error occurred in a FastAPI application.

ERROR TYPE: {error_entry['type']}
ERROR MESSAGE: {error_entry['message']}

TRACEBACK:
{error_entry['traceback']}

FILE: {file_path}
ERROR LINE: {line_num}

CODE AROUND ERROR:
{context_lines}

FULL FILE CODE:
```python
{original_code}
```

INSTRUCTIONS:
1. Analyze the error carefully
2. Identify the exact cause
3. Provide the FIXED version of the ENTIRE file
4. Only fix the bug, do NOT change any working functionality
5. Do NOT add new features or remove existing code
6. Keep all imports, all functions, all endpoints exactly as they are
7. Only change what is necessary to fix this specific error

Respond with ONLY the fixed Python code wrapped in ```python ... ``` tags.
No explanation needed, just the fixed code.
"""

        # Step 3: Call Ollama
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(OLLAMA_URL, json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
            })

            if resp.status_code != 200:
                update_error(error_id, "failed", f"Ollama returned status {resp.status_code}")
                return {
                    "success": False,
                    "message": f"Ollama se response nahi aaya (status {resp.status_code}).",
                    "error_id": error_id,
                }

            result = resp.json()
            llm_response = result.get("response", "")

        # Step 4: Extract fixed code from response
        fixed_code = _extract_code(llm_response)

        if not fixed_code:
            update_error(error_id, "failed", "LLM ne valid code nahi diya.")
            return {
                "success": False,
                "message": "Ollama se fix code nahi mil paya. Manual check karo.",
                "error_id": error_id,
                "suggestion": llm_response[:500],
            }

        # Step 5: Validate fix is not destructive
        validation = _validate_fix(original_code, fixed_code, file_path)
        if not validation["safe"]:
            update_error(error_id, "failed", f"Fix risky: {validation['reason']}")
            return {
                "success": False,
                "message": f"Fix apply nahi ki — risky thi: {validation['reason']}",
                "error_id": error_id,
                "suggested_fix": fixed_code[:1000],
            }

        # Step 6: Backup original
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source_path.stem}_{timestamp}_backup{source_path.suffix}"
        backup_path = BACKUP_DIR / backup_name
        shutil.copy2(file_path, backup_path)

        # Step 7: Apply fix
        source_path.write_text(fixed_code, encoding="utf-8")

        update_error(
            error_id, "fixed",
            f"Auto-fixed! Backup: {backup_name}. Changes applied to {source_path.name}."
        )

        return {
            "success": True,
            "message": f"Fix apply kar di {source_path.name} me! Backup bhi le li hai. Server restart karo: stop.bat → start.bat",
            "error_id": error_id,
            "backup": str(backup_path),
            "file_fixed": file_path,
        }

    except httpx.ConnectError:
        update_error(error_id, "failed", "Ollama not running.")
        return {
            "success": False,
            "message": "Ollama chal nahi raha! 'ollama serve' run karo pehle.",
            "error_id": error_id,
        }
    except Exception as e:
        update_error(error_id, "failed", f"Fix attempt error: {str(e)}")
        return {
            "success": False,
            "message": f"Fix attempt me error: {str(e)}",
            "error_id": error_id,
        }


async def analyze_error(error_entry: dict) -> str:
    """
    Just analyze the error (don't fix), return explanation.
    """
    try:
        prompt = f"""You are a Python debugging expert. Explain this error in simple Hindi-English mix (Hinglish).

ERROR: {error_entry['type']}: {error_entry['message']}
FILE: {error_entry.get('file_path', 'unknown')}
LINE: {error_entry.get('line_number', '?')}

TRACEBACK:
{error_entry['traceback']}

Give a short explanation (2-3 lines max) of:
1. Kya error hai
2. Kyun aaya
3. Kaise fix hoga
"""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(OLLAMA_URL, json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
            })
            if resp.status_code == 200:
                return resp.json().get("response", "Analysis failed.")
    except Exception:
        pass

    return f"{error_entry['type']}: {error_entry['message']} — File: {error_entry.get('file_path', '?')} Line: {error_entry.get('line_number', '?')}"


def _extract_code(llm_response: str) -> str:
    """Extract Python code from LLM response."""
    # Try to find ```python ... ``` blocks
    pattern = r"```(?:python)?\s*\n(.*?)```"
    matches = re.findall(pattern, llm_response, re.DOTALL)

    if matches:
        # Return the longest match (likely the full file)
        return max(matches, key=len).strip()

    # If no code blocks, check if the whole response looks like Python code
    lines = llm_response.strip().split("\n")
    if lines and (lines[0].startswith("import ") or lines[0].startswith("from ") or lines[0].startswith("#")):
        return llm_response.strip()

    return ""


def _validate_fix(original: str, fixed: str, file_path: str) -> dict:
    """
    Validate that the fix is safe to apply.
    Checks that it doesn't remove too much code or change structure drastically.
    """
    orig_lines = original.strip().split("\n")
    fixed_lines = fixed.strip().split("\n")

    # Check 1: Fixed code shouldn't be way shorter (>30% shorter = suspicious)
    if len(fixed_lines) < len(orig_lines) * 0.7:
        return {
            "safe": False,
            "reason": f"Fix me bahut code remove ho gaya ({len(orig_lines)} → {len(fixed_lines)} lines)"
        }

    # Check 2: Fixed code shouldn't be empty or too short
    if len(fixed_lines) < 5:
        return {
            "safe": False,
            "reason": "Fix code bahut chhota hai — lagta hai LLM ne partial code diya"
        }

    # Check 3: Key imports should still be present
    orig_imports = set(re.findall(r"^(?:from|import)\s+\S+", original, re.MULTILINE))
    fixed_imports = set(re.findall(r"^(?:from|import)\s+\S+", fixed, re.MULTILINE))
    missing_imports = orig_imports - fixed_imports

    # Allow some missing if they were the problem, but not more than 3
    if len(missing_imports) > 3:
        return {
            "safe": False,
            "reason": f"{len(missing_imports)} imports remove ho gaye — too risky"
        }

    # Check 4: Function/class count shouldn't drop drastically
    orig_defs = len(re.findall(r"^(?:def |class |async def )", original, re.MULTILINE))
    fixed_defs = len(re.findall(r"^(?:def |class |async def )", fixed, re.MULTILINE))

    if fixed_defs < orig_defs * 0.7:
        return {
            "safe": False,
            "reason": f"Functions/classes kam ho gaye ({orig_defs} → {fixed_defs}) — risky"
        }

    # Check 5: Must be valid Python syntax
    try:
        compile(fixed, file_path, "exec")
    except SyntaxError as e:
        return {
            "safe": False,
            "reason": f"Fixed code me syntax error hai: {str(e)}"
        }

    return {"safe": True, "reason": ""}
