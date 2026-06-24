"""
MJ Self-Healing: Unified Error Tracker
Captures, logs, stores errors with full context.
Now includes pattern detection and fix suggestions (merged from error_learner).
"""

import json
import time
import traceback
from datetime import datetime
from pathlib import Path
from collections import Counter
from typing import Optional

ERROR_LOG_DIR = Path(__file__).parent.parent / "error_logs"
ERROR_LOG_DIR.mkdir(exist_ok=True)
ERROR_LOG_FILE = ERROR_LOG_DIR / "errors.json"
PERF_FILE = Path(__file__).parent.parent / "performance_log.json"

# In-memory recent errors (last 50)
recent_errors = []
MAX_ERRORS = 50

# Known fix patterns -- MJ learns new ones over time
KNOWN_FIXES = {
    "timeout": "Model swap takes time. Use qwen3:8b for faster response or increase timeout.",
    "connect_error": "Ollama not running. Run 'ollama serve' in terminal.",
    "model_not_found": "Model not installed. Run 'ollama pull <model>' to download.",
    "out_of_memory": "VRAM full. Close other GPU apps or use smaller model.",
    "empty_response": "Model returned empty. Try rephrasing or use different model.",
    "slow_response": "Response too slow. Reduce num_ctx or use faster model.",
    "web_search_fail": "Web search failed. Check internet connection.",
    "stuck_thinking": "Model stuck in thinking loop. Add /no_think to skip reasoning.",
    "port_conflict": "Port already in use. Kill existing process first.",
    "module_crash": "Module crashed. Will be auto-disabled by circuit breaker.",
}

# Error pattern counters (in-memory, for pattern detection)
_pattern_counts = {}


def log_error(
    error=None,
    source="unknown",
    endpoint="",
    user_input="",
    extra_context="",
    error_type="",
    message="",
):
    """
    Log an error with full context. Accepts either Exception object or type+message strings.
    Returns the error entry dict.
    """
    if error and isinstance(error, Exception):
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        tb_str = "".join(tb)
        err_type = type(error).__name__
        err_msg = str(error)

        # Extract file and line from traceback
        file_path = ""
        line_number = 0
        code_snippet = ""
        for frame in traceback.extract_tb(error.__traceback__):
            if "MJ-Assistant" in str(frame.filename):
                file_path = frame.filename
                line_number = frame.lineno
                code_snippet = frame.line or ""
    else:
        tb_str = ""
        err_type = error_type or "unknown"
        err_msg = message or str(error) if error else "unknown error"
        file_path = ""
        line_number = 0
        code_snippet = ""

    # Get fix suggestion
    fix_suggestion = _get_fix(err_type, err_msg)

    error_entry = {
        "id": "err_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
        "timestamp": datetime.now().isoformat(),
        "time_display": datetime.now().strftime("%I:%M:%S %p"),
        "type": err_type,
        "message": err_msg,
        "source": source,
        "endpoint": endpoint,
        "user_input": user_input[:200] if user_input else "",
        "traceback": tb_str,
        "file_path": file_path,
        "line_number": line_number,
        "code_snippet": code_snippet,
        "extra_context": extra_context,
        "fix_status": "pending",
        "fix_details": "",
        "fix_suggestion": fix_suggestion,
    }

    # Track pattern
    _pattern_counts[err_type] = _pattern_counts.get(err_type, 0) + 1

    # Add to in-memory list
    recent_errors.insert(0, error_entry)
    if len(recent_errors) > MAX_ERRORS:
        recent_errors.pop()

    _save_errors()
    return error_entry


def log_performance(user_msg, model, task_type, response_time, token_count, success, error_msg=None):
    """Log request performance for analysis."""
    data = _load_perf()

    entry = {
        "timestamp": datetime.now().isoformat(),
        "user_msg_preview": user_msg[:80],
        "model": model,
        "task_type": task_type,
        "response_time_sec": round(response_time, 2),
        "tokens": token_count,
        "success": success,
        "error": error_msg,
    }

    data["requests"].append(entry)
    _save_perf(data)

    issues = _detect_issues(data)
    return issues


def learn_fix(error_type, fix_description):
    """Learn a new fix from successful resolution."""
    KNOWN_FIXES[error_type] = fix_description


def get_recent_errors(limit=20):
    return recent_errors[:limit]


def get_error_by_id(error_id):
    for e in recent_errors:
        if e["id"] == error_id:
            return e
    return None


def update_error(error_id, fix_status, fix_details=""):
    for e in recent_errors:
        if e["id"] == error_id:
            e["fix_status"] = fix_status
            e["fix_details"] = fix_details
            break
    _save_errors()


def get_error_stats():
    if not recent_errors:
        return {"total": 0, "pending": 0, "fixed": 0, "failed": 0, "last_error": None, "patterns": {}}

    return {
        "total": len(recent_errors),
        "pending": sum(1 for e in recent_errors if e["fix_status"] == "pending"),
        "fixed": sum(1 for e in recent_errors if e["fix_status"] == "fixed"),
        "failed": sum(1 for e in recent_errors if e["fix_status"] == "failed"),
        "last_error": recent_errors[0]["time_display"] if recent_errors else None,
        "patterns": dict(_pattern_counts),
    }


def clear_errors():
    global recent_errors
    recent_errors = []
    _pattern_counts.clear()
    _save_errors()


def get_diagnostics():
    """Full diagnostic report."""
    perf = _load_perf()
    recent = perf["requests"][-50:]

    total_requests = len(recent)
    successful = len([r for r in recent if r["success"]])
    avg_time = sum(r["response_time_sec"] for r in recent) / max(total_requests, 1)
    total_tokens = sum(r["tokens"] for r in recent)

    model_stats = {}
    for r in recent:
        m = r["model"]
        if m not in model_stats:
            model_stats[m] = {"count": 0, "avg_time": 0, "failures": 0, "total_time": 0}
        model_stats[m]["count"] += 1
        model_stats[m]["total_time"] += r["response_time_sec"]
        if not r["success"]:
            model_stats[m]["failures"] += 1
    for m in model_stats:
        model_stats[m]["avg_time"] = round(model_stats[m]["total_time"] / model_stats[m]["count"], 1)

    error_types = Counter(e["type"] for e in recent_errors[-50:])
    issues = _detect_issues(perf)

    return {
        "summary": {
            "total_requests": total_requests,
            "success_rate": str(round((successful / max(total_requests, 1)) * 100)) + "%",
            "avg_response_time": str(round(avg_time, 1)) + "s",
            "total_tokens": total_tokens,
            "total_errors_logged": len(recent_errors),
            "patterns": dict(_pattern_counts),
        },
        "model_breakdown": model_stats,
        "top_errors": dict(error_types.most_common(5)),
        "active_issues": issues,
        "recent_errors": [e for e in recent_errors[:5]],
        "health": "CRITICAL" if any(i["severity"] == "critical" for i in issues) else
                  "WARNING" if issues else "HEALTHY",
    }


def get_live_issues():
    """Get current active issues for dashboard."""
    perf = _load_perf()
    return _detect_issues(perf)


# --- Internal helpers ---

def _get_fix(error_type, message):
    msg_lower = message.lower()
    for key, fix in KNOWN_FIXES.items():
        if key in error_type.lower() or key in msg_lower:
            return fix
    return "No known fix. Error logged for analysis."


def _detect_issues(perf_data):
    issues = []
    recent = perf_data["requests"][-20:]
    if not recent:
        return issues

    failures = [r for r in recent if not r["success"]]
    if len(failures) >= 3:
        issues.append({
            "type": "high_failure_rate",
            "severity": "critical",
            "message": "Last 20 requests me " + str(len(failures)) + " fail hue",
            "suggestion": "Check Ollama status, VRAM usage, model availability",
        })

    slow = [r for r in recent if r["response_time_sec"] > 30]
    if len(slow) >= 3:
        avg_time = sum(r["response_time_sec"] for r in slow) / len(slow)
        issues.append({
            "type": "slow_responses",
            "severity": "warning",
            "message": str(len(slow)) + " slow responses (avg " + str(round(avg_time)) + "s)",
            "suggestion": "Use smaller model or reduce context window",
        })

    models_used = [r["model"] for r in recent[-10:]]
    if len(set(models_used)) >= 3:
        issues.append({
            "type": "model_thrashing",
            "severity": "warning",
            "message": "Frequent model swaps -- causes VRAM reload delays",
            "suggestion": "Stick to one model or disable auto-select",
        })

    model_failures = Counter()
    for r in recent:
        if not r["success"]:
            model_failures[r["model"]] += 1
    for model, count in model_failures.items():
        if count >= 2:
            issues.append({
                "type": "model_unreliable",
                "severity": "warning",
                "message": "Model '" + model + "' failed " + str(count) + " times",
                "suggestion": "Check: ollama pull " + model,
            })

    empty = [r for r in recent if r["tokens"] == 0 and r["success"]]
    if len(empty) >= 3:
        issues.append({
            "type": "empty_responses",
            "severity": "warning",
            "message": str(len(empty)) + " empty responses",
            "suggestion": "Try 'use groq' or pull bigger model",
        })

    # Recurring error pattern alert
    for err_type, count in _pattern_counts.items():
        if count >= 5:
            issues.append({
                "type": "recurring_error",
                "severity": "warning",
                "message": "Error '" + err_type + "' occurred " + str(count) + " times",
                "suggestion": KNOWN_FIXES.get(err_type, "Investigate manually"),
            })

    return issues


def _save_errors():
    try:
        data = recent_errors[:100]
        ERROR_LOG_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def _load_errors():
    global recent_errors
    try:
        if ERROR_LOG_FILE.exists():
            recent_errors = json.loads(ERROR_LOG_FILE.read_text(encoding="utf-8"))
    except Exception:
        recent_errors = []


def _load_perf():
    if PERF_FILE.exists():
        try:
            return json.loads(PERF_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"requests": []}


def _save_perf(data):
    data["requests"] = data["requests"][-500:]
    PERF_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# Load on import
_load_errors()
