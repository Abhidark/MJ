"""
MJ Self-Healing: Error Tracker
Captures, logs, and stores all errors with full context.
"""

import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

ERROR_LOG_DIR = Path(__file__).parent.parent / "error_logs"
ERROR_LOG_DIR.mkdir(exist_ok=True)
ERROR_LOG_FILE = ERROR_LOG_DIR / "errors.json"

# In-memory recent errors (last 50)
recent_errors = []
MAX_ERRORS = 50


def log_error(
    error: Exception,
    source: str = "unknown",
    endpoint: str = "",
    user_input: str = "",
    extra_context: str = "",
) -> dict:
    """
    Log an error with full context.
    Returns the error entry dict.
    """
    tb = traceback.format_exception(type(error), error, error.__traceback__)
    tb_str = "".join(tb)

    # Extract the file and line from traceback
    file_path = ""
    line_number = 0
    code_snippet = ""
    for frame in traceback.extract_tb(error.__traceback__):
        if "MJ-Assistant" in str(frame.filename):
            file_path = frame.filename
            line_number = frame.lineno
            code_snippet = frame.line or ""

    error_entry = {
        "id": f"err_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
        "timestamp": datetime.now().isoformat(),
        "time_display": datetime.now().strftime("%I:%M:%S %p"),
        "type": type(error).__name__,
        "message": str(error),
        "source": source,
        "endpoint": endpoint,
        "user_input": user_input[:200] if user_input else "",
        "traceback": tb_str,
        "file_path": file_path,
        "line_number": line_number,
        "code_snippet": code_snippet,
        "extra_context": extra_context,
        "fix_status": "pending",  # pending, attempting, fixed, failed
        "fix_details": "",
    }

    # Add to in-memory list
    recent_errors.insert(0, error_entry)
    if len(recent_errors) > MAX_ERRORS:
        recent_errors.pop()

    # Save to file
    _save_errors()

    return error_entry


def get_recent_errors(limit: int = 20) -> list:
    """Get recent errors."""
    return recent_errors[:limit]


def get_error_by_id(error_id: str) -> Optional[dict]:
    """Get a specific error by ID."""
    for e in recent_errors:
        if e["id"] == error_id:
            return e
    return None


def update_error(error_id: str, fix_status: str, fix_details: str = ""):
    """Update error fix status."""
    for e in recent_errors:
        if e["id"] == error_id:
            e["fix_status"] = fix_status
            e["fix_details"] = fix_details
            break
    _save_errors()


def get_error_stats() -> dict:
    """Get error statistics."""
    if not recent_errors:
        return {"total": 0, "pending": 0, "fixed": 0, "failed": 0, "last_error": None}

    return {
        "total": len(recent_errors),
        "pending": sum(1 for e in recent_errors if e["fix_status"] == "pending"),
        "fixed": sum(1 for e in recent_errors if e["fix_status"] == "fixed"),
        "failed": sum(1 for e in recent_errors if e["fix_status"] == "failed"),
        "last_error": recent_errors[0]["time_display"] if recent_errors else None,
    }


def clear_errors():
    """Clear all errors."""
    global recent_errors
    recent_errors = []
    _save_errors()


def _save_errors():
    """Save errors to file."""
    try:
        # Only save last 100 to file
        data = recent_errors[:100]
        ERROR_LOG_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception:
        pass


def _load_errors():
    """Load errors from file on startup."""
    global recent_errors
    try:
        if ERROR_LOG_FILE.exists():
            recent_errors = json.loads(ERROR_LOG_FILE.read_text(encoding="utf-8"))
    except Exception:
        recent_errors = []


# Load on import
_load_errors()
