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
# RESPONSE QUALITY SCORER (V24 → 90%)
# ========================

class QualityScorer:
    """Auto-score response quality based on heuristics."""

    def __init__(self):
        self.scores: list = []
        self._load()

    def _load(self):
        data = _load_json(QUALITY_LOG_FILE, [])
        self.scores = data if isinstance(data, list) else []

    def _save(self):
        _save_json(QUALITY_LOG_FILE, self.scores[-300:])

    def score_response(self, query: str, response: str, latency_ms: float = 0,
                       user_feedback: float = 0.0) -> dict:
        """Auto-score a response based on heuristics + optional user feedback."""
        score = 0.5  # baseline

        # Length appropriateness
        resp_words = len(response.split())
        query_words = len(query.split())
        if resp_words > 5 and resp_words < 2000:
            score += 0.1
        if resp_words < 2:
            score -= 0.2

        # Relevance heuristic: word overlap
        q_words = set(query.lower().split())
        r_words = set(response.lower().split())
        overlap = len(q_words & r_words) / max(len(q_words), 1)
        score += overlap * 0.15

        # Error indicators
        error_phrases = ["sorry", "i can't", "error", "failed", "unable to"]
        if any(p in response.lower() for p in error_phrases):
            score -= 0.15

        # Latency penalty
        if latency_ms > 5000:
            score -= 0.1
        elif latency_ms < 1000 and latency_ms > 0:
            score += 0.05

        # User feedback override (strongest signal)
        if user_feedback > 0:
            score = score * 0.3 + user_feedback * 0.7

        score = max(0.0, min(1.0, score))

        entry = {
            "query_hash": hashlib.md5(query.encode()).hexdigest()[:8],
            "auto_score": round(score, 3),
            "user_feedback": user_feedback,
            "latency_ms": latency_ms,
            "response_length": resp_words,
            "ts": time.time(),
        }
        self.scores.append(entry)
        self._save()
        return entry

    def get_quality_trend(self, window: int = 50) -> dict:
        """Get quality trend over recent responses."""
        recent = self.scores[-window:]
        if not recent:
            return {"message": "No data yet"}
        scores = [s["auto_score"] for s in recent]
        first_half = scores[:len(scores)//2]
        second_half = scores[len(scores)//2:]
        return {
            "avg_score": round(sum(scores) / len(scores), 3),
            "trend": "improving" if sum(second_half)/max(len(second_half),1) >
                     sum(first_half)/max(len(first_half),1) else "stable",
            "total_scored": len(self.scores),
            "recent_avg": round(sum(scores[-10:]) / max(len(scores[-10:]), 1), 3),
        }

    def get_low_quality(self, threshold: float = 0.4, limit: int = 10) -> list:
        """Get lowest quality responses for review."""
        low = [s for s in self.scores if s["auto_score"] < threshold]
        return sorted(low, key=lambda x: x["auto_score"])[:limit]


# ========================
# AUTO-RETRY ENGINE (V24 → 90%)
# ========================

class AutoRetryEngine:
    """Automatically retry failed or low-quality responses with improved prompts."""

    RETRY_LOG_FILE = DATA_DIR / "auto_retries.json"

    def __init__(self):
        self.retries: list = []
        self._load()

    def _load(self):
        data = _load_json(self.RETRY_LOG_FILE, [])
        self.retries = data if isinstance(data, list) else []

    def _save(self):
        _save_json(self.RETRY_LOG_FILE, self.retries[-200:])

    def should_retry(self, quality_score: float, error: bool = False,
                     attempt: int = 0, max_attempts: int = 2) -> dict:
        """Decide if a response should be retried."""
        retry = False
        reason = ""

        if error and attempt < max_attempts:
            retry = True
            reason = "error_response"
        elif quality_score < 0.3 and attempt < max_attempts:
            retry = True
            reason = "low_quality"
        elif quality_score < 0.5 and attempt == 0:
            retry = True
            reason = "below_threshold"

        return {"should_retry": retry, "reason": reason, "attempt": attempt + 1}

    def improve_prompt(self, original: str, reason: str) -> str:
        """Improve a prompt for retry based on failure reason."""
        if reason == "low_quality":
            return f"Please provide a detailed and helpful answer: {original}"
        elif reason == "error_response":
            return f"Try a different approach to answer: {original}"
        elif reason == "below_threshold":
            return f"Be specific and thorough: {original}"
        return original

    def log_retry(self, query_hash: str, original_score: float,
                  retry_score: float, reason: str) -> dict:
        entry = {
            "query_hash": query_hash,
            "original_score": original_score,
            "retry_score": retry_score,
            "improvement": round(retry_score - original_score, 3),
            "reason": reason,
            "ts": time.time(),
        }
        self.retries.append(entry)
        self._save()
        return entry

    def get_retry_stats(self) -> dict:
        if not self.retries:
            return {"total_retries": 0}
        improvements = [r["improvement"] for r in self.retries]
        successful = sum(1 for i in improvements if i > 0)
        return {
            "total_retries": len(self.retries),
            "successful_improvements": successful,
            "avg_improvement": round(sum(improvements) / len(improvements), 3),
            "success_rate": round(successful / len(self.retries) * 100, 1),
        }


# ========================
# LEARNING FEEDBACK LOOP (V24 → 90%)
# ========================

LEARNING_LOG_FILE = DATA_DIR / "learning_feedback.json"

class LearningLoop:
    """Track what works and feed it back into the system."""

    def __init__(self):
        self.feedback: list = []
        self.patterns: dict = {}
        self._load()

    def _load(self):
        data = _load_json(LEARNING_LOG_FILE, {})
        self.feedback = data.get("feedback", [])
        self.patterns = data.get("patterns", {})

    def _save(self):
        _save_json(LEARNING_LOG_FILE, {
            "feedback": self.feedback[-300:],
            "patterns": self.patterns,
        })

    def record_outcome(self, module: str, action: str, success: bool, context: str = "") -> dict:
        """Record whether an action succeeded or failed."""
        key = f"{module}:{action}"
        if key not in self.patterns:
            self.patterns[key] = {"successes": 0, "failures": 0, "last_context": ""}

        if success:
            self.patterns[key]["successes"] += 1
        else:
            self.patterns[key]["failures"] += 1
        self.patterns[key]["last_context"] = context

        self.feedback.append({
            "module": module, "action": action, "success": success,
            "ts": time.time(),
        })
        self._save()
        return {"recorded": True, "pattern": self.patterns[key]}

    def get_success_rates(self) -> dict:
        """Get success rates for all tracked patterns."""
        rates = {}
        for key, data in self.patterns.items():
            total = data["successes"] + data["failures"]
            if total > 0:
                rates[key] = {
                    "rate": round(data["successes"] / total * 100, 1),
                    "total": total,
                }
        return {"patterns": rates, "total_tracked": len(rates)}

    def get_weak_areas(self, threshold: float = 70.0) -> list:
        """Find areas with low success rates."""
        weak = []
        for key, data in self.patterns.items():
            total = data["successes"] + data["failures"]
            if total >= 3:  # minimum sample
                rate = data["successes"] / total * 100
                if rate < threshold:
                    weak.append({"pattern": key, "success_rate": round(rate, 1), "total": total})
        return sorted(weak, key=lambda x: x["success_rate"])


# ========================
# SINGLETONS
# ========================

performance_tracker = PerformanceTracker()
prompt_improver = PromptImprover()
memory_optimizer = MemoryOptimizer()
auto_tuner = AutoTuner()
quality_scorer = QualityScorer()
auto_retry = AutoRetryEngine()
learning_loop = LearningLoop()


def get_self_improve_status() -> dict:
    """Get overall self-improvement system status."""
    return {
        "performance": performance_tracker.get_stats(24),
        "memory": memory_optimizer.get_memory_summary(),
        "prompt_effectiveness": prompt_improver.get_effectiveness_report(),
        "optimizations": auto_tuner.get_stats(),
        "quality": quality_scorer.get_quality_trend(),
        "retries": auto_retry.get_retry_stats(),
        "learning": learning_loop.get_success_rates(),
    }
