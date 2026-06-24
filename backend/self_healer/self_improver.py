"""
MJ Self-Improving Engine (V24)
Adds: memory optimization, prompt auto-improvement, performance tuning,
response quality tracking, auto-retry with better prompts.
"""

import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
PERF_LOG_FILE = DATA_DIR / "self_improve_perf.json"
PROMPT_HISTORY_FILE = DATA_DIR / "prompt_improvements.json"
QUALITY_LOG_FILE = DATA_DIR / "response_quality.json"
OPTIMIZATION_FILE = DATA_DIR / "self_optimizations.json"


def _load_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def _save_json(path, data):
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# ========================
# PERFORMANCE TRACKER
# ========================

class PerformanceTracker:
    """Track and analyze response performance metrics."""

    def __init__(self):
        self.metrics: list = []
        self._load()

    def _load(self):
        data = _load_json(PERF_LOG_FILE, [])
        self.metrics = data if isinstance(data, list) else []

    def _save(self):
        _save_json(PERF_LOG_FILE, self.metrics[-500:])

    def log_request(self, query: str, module: str, latency_ms: float,
                    tokens_used: int = 0, success: bool = True, quality: float = 0.0):
        entry = {
            "query_hash": hashlib.md5(query.encode()).hexdigest()[:8],
            "module": module,
            "latency_ms": round(latency_ms, 1),
            "tokens": tokens_used,
            "success": success,
            "quality": quality,
            "ts": time.time(),
        }
        self.metrics.append(entry)
        self._save()

    def get_stats(self, window_hours: int = 24) -> dict:
        cutoff = time.time() - (window_hours * 3600)
        recent = [m for m in self.metrics if m.get("ts", 0) > cutoff]
        if not recent:
            return {"total": 0, "window_hours": window_hours}

        latencies = [m["latency_ms"] for m in recent]
        successes = sum(1 for m in recent if m.get("success"))
        qualities = [m["quality"] for m in recent if m.get("quality", 0) > 0]

        # Per-module breakdown
        by_module = {}
        for m in recent:
            mod = m.get("module", "unknown")
            if mod not in by_module:
                by_module[mod] = {"count": 0, "total_latency": 0, "errors": 0}
            by_module[mod]["count"] += 1
            by_module[mod]["total_latency"] += m["latency_ms"]
            if not m.get("success"):
                by_module[mod]["errors"] += 1

        for mod, data in by_module.items():
            data["avg_latency_ms"] = round(data["total_latency"] / max(data["count"], 1), 1)

        return {
            "total_requests": len(recent),
            "success_rate": round(successes / len(recent) * 100, 1),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1),
            "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0, 1),
            "avg_quality": round(sum(qualities) / max(len(qualities), 1), 2) if qualities else 0,
            "by_module": by_module,
            "window_hours": window_hours,
        }

    def get_slow_queries(self, threshold_ms: float = 5000, limit: int = 10) -> list:
        slow = [m for m in self.metrics if m["latency_ms"] > threshold_ms]
        return sorted(slow, key=lambda x: x["latency_ms"], reverse=True)[:limit]

    def get_error_patterns(self) -> dict:
        errors = [m for m in self.metrics if not m.get("success")]
        by_module = {}
        for e in errors:
            mod = e.get("module", "unknown")
            by_module[mod] = by_module.get(mod, 0) + 1
        return {"total_errors": len(errors), "by_module": by_module}


# ========================
# PROMPT AUTO-IMPROVER
# ========================

class PromptImprover:
    """Track prompt effectiveness and suggest improvements."""

    def __init__(self):
        self.history: list = []
        self.improvements: dict = {}
        self._load()

    def _load(self):
        data = _load_json(PROMPT_HISTORY_FILE, {})
        self.history = data.get("history", [])
        self.improvements = data.get("improvements", {})

    def _save(self):
        _save_json(PROMPT_HISTORY_FILE, {
            "history": self.history[-200:],
            "improvements": self.improvements,
        })

    def log_prompt(self, prompt_id: str, original: str, quality: float, latency_ms: float):
        entry = {
            "id": prompt_id,
            "original_hash": hashlib.md5(original.encode()).hexdigest()[:12],
            "quality": quality,
            "latency_ms": latency_ms,
            "ts": time.time(),
        }
        self.history.append(entry)
        self._save()

    def suggest_improvement(self, prompt_id: str, original: str) -> dict:
        """Analyze prompt and suggest improvements."""
        suggestions = []
        length = len(original.split())

        if length < 3:
            suggestions.append("Add more context — short prompts get vague answers")
        if length > 200:
            suggestions.append("Shorten prompt — long prompts dilute intent")
        if "?" not in original and not any(w in original.lower() for w in ("please", "give", "show", "tell", "create", "make")):
            suggestions.append("Clarify intent — is this a question or a command?")
        if original == original.upper() and len(original) > 10:
            suggestions.append("Don't use ALL CAPS — it doesn't improve results")
        if original.count("\n") > 10:
            suggestions.append("Consider breaking into multiple requests")

        return {
            "prompt_id": prompt_id,
            "word_count": length,
            "suggestions": suggestions,
            "score": max(0, 1.0 - len(suggestions) * 0.15),
        }

    def get_effectiveness_report(self) -> dict:
        if not self.history:
            return {"message": "No prompt history yet"}

        qualities = [h["quality"] for h in self.history if h.get("quality", 0) > 0]
        return {
            "total_prompts": len(self.history),
            "avg_quality": round(sum(qualities) / max(len(qualities), 1), 2),
            "improvements_applied": len(self.improvements),
        }


# ========================
# MEMORY OPTIMIZER
# ========================

class MemoryOptimizer:
    """Optimize memory usage across the system."""

    def analyze(self) -> dict:
        """Analyze data directory for optimization opportunities."""
        results = {"files": [], "total_size_kb": 0, "optimizable": []}

        for fp in DATA_DIR.glob("*.json"):
            try:
                size_kb = round(fp.stat().st_size / 1024, 1)
                results["files"].append({"name": fp.name, "size_kb": size_kb})
                results["total_size_kb"] += size_kb

                # Check for large files that could be compacted
                if size_kb > 100:
                    data = json.loads(fp.read_text(encoding="utf-8"))
                    if isinstance(data, list) and len(data) > 500:
                        results["optimizable"].append({
                            "file": fp.name, "size_kb": size_kb,
                            "records": len(data),
                            "suggestion": f"Trim to last 200 records (save ~{round(size_kb * 0.6, 1)}KB)",
                        })
                    elif isinstance(data, dict):
                        # Check for empty/null values
                        empty_keys = sum(1 for v in data.values() if not v)
                        if empty_keys > 10:
                            results["optimizable"].append({
                                "file": fp.name, "size_kb": size_kb,
                                "empty_keys": empty_keys,
                                "suggestion": f"Remove {empty_keys} empty entries",
                            })
            except Exception:
                pass

        results["total_size_kb"] = round(results["total_size_kb"], 1)
        return results

    def compact_file(self, filename: str, max_records: int = 200) -> dict:
        """Compact a JSON data file by trimming old entries."""
        fp = DATA_DIR / filename
        if not fp.exists():
            return {"error": f"File '{filename}' not found"}

        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            original_size = fp.stat().st_size

            if isinstance(data, list) and len(data) > max_records:
                trimmed = data[-max_records:]
                fp.write_text(json.dumps(trimmed, ensure_ascii=False, indent=2), encoding="utf-8")
                new_size = fp.stat().st_size
                return {
                    "success": True, "file": filename,
                    "before_records": len(data), "after_records": len(trimmed),
                    "saved_kb": round((original_size - new_size) / 1024, 1),
                }
            return {"success": False, "reason": "File doesn't need compaction"}
        except Exception as e:
            return {"error": str(e)}

    def get_memory_summary(self) -> dict:
        analysis = self.analyze()
        return {
            "total_data_files": len(analysis["files"]),
            "total_size_kb": analysis["total_size_kb"],
            "optimizable_files": len(analysis["optimizable"]),
            "potential_savings_kb": sum(
                o.get("size_kb", 0) * 0.6 for o in analysis["optimizable"]
            ),
        }


# ========================
# AUTO-TUNER
# ========================

class AutoTuner:
    """Automatically tune system parameters based on usage patterns."""

    def __init__(self):
        self.optimizations: list = []
        self._load()

    def _load(self):
        data = _load_json(OPTIMIZATION_FILE, [])
        self.optimizations = data if isinstance(data, list) else []

    def _save(self):
        _save_json(OPTIMIZATION_FILE, self.optimizations[-100:])

    def suggest_optimizations(self, perf_stats: dict) -> list:
        """Analyze performance and suggest optimizations."""
        suggestions = []

        avg_latency = perf_stats.get("avg_latency_ms", 0)
        success_rate = perf_stats.get("success_rate", 100)
        by_module = perf_stats.get("by_module", {})

        if avg_latency > 3000:
            suggestions.append({
                "type": "latency",
                "severity": "high",
                "message": f"Average latency {avg_latency}ms is high. Consider switching to faster models or Groq cloud.",
                "action": "switch_provider",
            })

        if success_rate < 90:
            suggestions.append({
                "type": "reliability",
                "severity": "high",
                "message": f"Success rate {success_rate}% is below target. Check error patterns.",
                "action": "check_errors",
            })

        # Check per-module performance
        for mod, data in by_module.items():
            if data.get("avg_latency_ms", 0) > 5000:
                suggestions.append({
                    "type": "module_slow",
                    "severity": "medium",
                    "message": f"Module '{mod}' avg {data['avg_latency_ms']}ms — consider caching.",
                    "action": "optimize_module",
                    "module": mod,
                })
            if data.get("errors", 0) > 5:
                suggestions.append({
                    "type": "module_errors",
                    "severity": "high",
                    "message": f"Module '{mod}' has {data['errors']} errors — needs investigation.",
                    "action": "fix_module",
                    "module": mod,
                })

        return suggestions

    def apply_optimization(self, optimization: dict) -> dict:
        """Log an applied optimization."""
        entry = {
            **optimization,
            "applied_at": datetime.now().isoformat(),
            "status": "applied",
        }
        self.optimizations.append(entry)
        self._save()
        return {"success": True, "optimization": entry}

    def get_optimization_history(self, limit: int = 20) -> list:
        return self.optimizations[-limit:]

    def get_stats(self) -> dict:
        return {
            "total_optimizations": len(self.optimizations),
            "by_type": {},
        }


# ========================
# SINGLETONS
# ========================

performance_tracker = PerformanceTracker()
prompt_improver = PromptImprover()
memory_optimizer = MemoryOptimizer()
auto_tuner = AutoTuner()


def get_self_improve_status() -> dict:
    """Get overall self-improvement system status."""
    return {
        "performance": performance_tracker.get_stats(24),
        "memory": memory_optimizer.get_memory_summary(),
        "prompt_effectiveness": prompt_improver.get_effectiveness_report(),
        "optimizations": auto_tuner.get_stats(),
    }
