"""
MJ Self-Learning Error System
Logs every error/issue, detects patterns, suggests fixes, learns from mistakes.

Features:
  - Auto-log all errors with context (model, task, input, timing)
  - Pattern detection (recurring errors get flagged)
  - Auto-fix suggestions based on learned patterns
  - Performance tracking (slow responses, timeouts, failures)
  - Diagnostic report generation
"""

import json
import time
from datetime import datetime
from pathlib import Path
from collections import Counter

LOG_FILE = Path(__file__).parent.parent / "error_learning.json"
PERF_FILE = Path(__file__).parent.parent / "performance_log.json"

# Known fix patterns — MJ learns new ones over time
DEFAULT_FIXES = {
    "timeout": "Model swap takes time. Consider using qwen3:8b for faster response or increase timeout.",
    "connect_error": "Ollama is not running. Run 'ollama serve' in terminal.",
    "model_not_found": "Model not installed. Run 'ollama pull <model>' to download.",
    "out_of_memory": "VRAM full. Close other GPU apps or use smaller model (8B instead of 14B).",
    "empty_response": "Model returned empty response. Try rephrasing or use different model.",
    "slow_response": "Response took too long. Reduce num_ctx or use faster model.",
    "web_search_fail": "Web search failed. Check internet connection.",
    "stuck_thinking": "Model stuck in thinking loop. Add /no_think to skip internal reasoning.",
    "port_conflict": "Port 11434 already in use. Kill existing Ollama process first.",
}


def _load_log():
    if LOG_FILE.exists():
        try:
            return json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return {"errors": [], "patterns": {}, "fixes_applied": [], "stats": {"total": 0, "auto_fixed": 0}}


def _save_log(data):
    LOG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_perf():
    if PERF_FILE.exists():
        try:
            return json.loads(PERF_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return {"requests": []}


def _save_perf(data):
    # Keep only last 500 entries
    data["requests"] = data["requests"][-500:]
    PERF_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def log_error(error_type: str, message: str, context: dict = None):
    """Log an error with full context for learning."""
    data = _load_log()

    entry = {
        "id": f"err_{int(time.time()*1000)}",
        "type": error_type,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "context": context or {},
        "fix_suggestion": _get_fix(error_type, message),
        "resolved": False,
    }

    data["errors"].append(entry)
    data["stats"]["total"] += 1

    # Update pattern count
    key = error_type
    data["patterns"][key] = data["patterns"].get(key, 0) + 1

    # Keep only last 200 errors
    data["errors"] = data["errors"][-200:]
    _save_log(data)

    return entry


def log_performance(user_msg: str, model: str, task_type: str,
                    response_time: float, token_count: int, success: bool,
                    error_msg: str = None):
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

    # Auto-detect issues
    issues = _detect_issues(data)
    return issues


def _get_fix(error_type: str, message: str):
    """Get fix suggestion from learned patterns."""
    msg_lower = message.lower()

    # Check known fixes
    for key, fix in DEFAULT_FIXES.items():
        if key in error_type.lower() or key in msg_lower:
            return fix

    # Check learned fixes
    data = _load_log()
    for fix_entry in data.get("fixes_applied", []):
        if fix_entry.get("error_type") == error_type:
            return fix_entry.get("fix_description", "No known fix yet.")

    return "No known fix. Error logged for analysis."


def learn_fix(error_type: str, fix_description: str):
    """Learn a new fix from successful resolution."""
    data = _load_log()
    data["fixes_applied"].append({
        "error_type": error_type,
        "fix_description": fix_description,
        "learned_at": datetime.now().isoformat(),
    })
    data["stats"]["auto_fixed"] = data["stats"].get("auto_fixed", 0) + 1
    _save_log(data)


def _detect_issues(perf_data):
    """Auto-detect performance issues from recent data."""
    issues = []
    recent = perf_data["requests"][-20:]  # Last 20 requests

    if not recent:
        return issues

    # Issue 1: High failure rate
    failures = [r for r in recent if not r["success"]]
    if len(failures) >= 3:
        issues.append({
            "type": "high_failure_rate",
            "severity": "critical",
            "message": f"Last 20 requests me {len(failures)} fail hue",
            "suggestion": "Check Ollama status, VRAM usage, model availability",
        })

    # Issue 2: Slow responses
    slow = [r for r in recent if r["response_time_sec"] > 30]
    if len(slow) >= 3:
        avg_time = sum(r["response_time_sec"] for r in slow) / len(slow)
        issues.append({
            "type": "slow_responses",
            "severity": "warning",
            "message": f"{len(slow)} slow responses (avg {avg_time:.0f}s)",
            "suggestion": "Use qwen3:8b instead of 14B, or reduce context window",
        })

    # Issue 3: Model swap thrashing
    models_used = [r["model"] for r in recent[-10:]]
    if len(set(models_used)) >= 3:
        issues.append({
            "type": "model_thrashing",
            "severity": "warning",
            "message": "Frequent model swaps detected — causes VRAM reload delays",
            "suggestion": "Stick to one model or disable auto-select for speed",
        })

    # Issue 4: Specific model always failing
    model_failures = Counter()
    for r in recent:
        if not r["success"]:
            model_failures[r["model"]] += 1
    for model, count in model_failures.items():
        if count >= 2:
            issues.append({
                "type": "model_unreliable",
                "severity": "warning",
                "message": f"Model '{model}' failed {count} times recently",
                "suggestion": f"Check if '{model}' is properly installed: ollama pull {model}",
            })

    # Issue 5: Empty responses (only alert if 3+ consecutive empty)
    empty = [r for r in recent if r["tokens"] == 0 and r["success"]]
    if len(empty) >= 3:
        issues.append({
            "type": "empty_responses",
            "severity": "warning",
            "message": f"{len(empty)} empty responses — model may be too weak",
            "suggestion": "Try 'use groq' for cloud AI, or pull a bigger model: ollama pull qwen2.5:7b",
        })

    return issues


def get_diagnostics():
    """Full diagnostic report — called by /diagnostics endpoint."""
    log = _load_log()
    perf = _load_perf()
    recent = perf["requests"][-50:]

    # Calculate stats
    total_requests = len(recent)
    successful = len([r for r in recent if r["success"]])
    avg_time = sum(r["response_time_sec"] for r in recent) / max(total_requests, 1)
    total_tokens = sum(r["tokens"] for r in recent)

    # Model usage breakdown
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

    # Top error types
    error_types = Counter(e["type"] for e in log.get("errors", [])[-50:])

    # Current issues
    issues = _detect_issues(perf)

    return {
        "summary": {
            "total_requests": total_requests,
            "success_rate": f"{(successful/max(total_requests,1))*100:.0f}%",
            "avg_response_time": f"{avg_time:.1f}s",
            "total_tokens": total_tokens,
            "total_errors_logged": log["stats"]["total"],
            "auto_fixes_applied": log["stats"].get("auto_fixed", 0),
        },
        "model_breakdown": model_stats,
        "top_errors": dict(error_types.most_common(5)),
        "active_issues": issues,
        "recent_errors": log.get("errors", [])[-5:],
        "health": "CRITICAL" if any(i["severity"] == "critical" for i in issues) else
                  "WARNING" if issues else "HEALTHY",
    }


def get_live_issues():
    """Get current active issues for orb alert display."""
    perf = _load_perf()
    issues = _detect_issues(perf)
    return issues
