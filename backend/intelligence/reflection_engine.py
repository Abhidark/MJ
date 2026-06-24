"""
MJ Intelligence: Reflection Engine (V16)
- Mistake Tracking: detect and log response failures, wrong answers, user corrections
- Learning Reports: periodic analysis of error patterns and improvements
- Improvement Suggestions: actionable recommendations based on mistake history
- Daily Reflection: automated end-of-day summary of performance
- Agent Score: per-module performance scoring based on success/failure rates
"""

import json
import time
import re
import logging
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("mj.reflection")

DATA_DIR = Path(__file__).parent.parent / "reflection_data"
DATA_DIR.mkdir(exist_ok=True)

MISTAKES_FILE = DATA_DIR / "mistakes.json"
REPORTS_FILE = DATA_DIR / "reports.json"
SCORES_FILE = DATA_DIR / "agent_scores.json"


class ReflectionEngine:
    """
    Tracks mistakes, generates learning reports, scores agents,
    and produces daily reflections.
    """

    def __init__(self):
        self.mistakes: List[dict] = self._load(MISTAKES_FILE, [])
        self.reports: List[dict] = self._load(REPORTS_FILE, [])
        self.agent_scores: Dict[str, dict] = self._load(SCORES_FILE, {})

    # ========================
    # MISTAKE TRACKING
    # ========================

    # Patterns indicating user correction / dissatisfaction
    CORRECTION_PATTERNS = [
        re.compile(r"\b(no|nahi|nhi|wrong|galat|incorrect|that'?s\s+not|not\s+what\s+i)\b", re.I),
        re.compile(r"\b(i\s+(?:said|meant|asked)|maine\s+(?:bola|kaha|pucha))\b", re.I),
        re.compile(r"\b(try\s+again|phir\s+se|dobara|again\s+kar|fix\s+(?:it|this))\b", re.I),
        re.compile(r"\b(useless|bakwas|bekar|stupid|idiot|pagal)\b", re.I),
    ]

    def detect_correction(self, user_message: str) -> bool:
        """Check if user message indicates a correction / dissatisfaction."""
        for pattern in self.CORRECTION_PATTERNS:
            if pattern.search(user_message):
                return True
        return False

    def log_mistake(self, query: str, response: str, module: str = "unknown",
                    mistake_type: str = "wrong_answer", user_feedback: str = "") -> dict:
        """Log a mistake for learning."""
        entry = {
            "id": f"mis_{int(time.time())}_{len(self.mistakes) % 1000}",
            "timestamp": time.time(),
            "time_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "query": query[:300],
            "response_preview": response[:300],
            "module": module,
            "type": mistake_type,  # wrong_answer, irrelevant, incomplete, slow, error, hallucination
            "user_feedback": user_feedback[:200],
            "learned": False,
        }
        self.mistakes.append(entry)
        self._update_agent_score(module, "failure")
        self._save(MISTAKES_FILE, self.mistakes[-500:])
        return entry

    def log_success(self, module: str = "unknown"):
        """Log a successful response for score tracking."""
        self._update_agent_score(module, "success")

    def get_mistakes(self, limit: int = 50, module: str = None,
                     mistake_type: str = None) -> List[dict]:
        """Get mistake history with optional filters."""
        results = self.mistakes
        if module:
            results = [m for m in results if m["module"] == module]
        if mistake_type:
            results = [m for m in results if m["type"] == mistake_type]
        return results[-limit:]

    # ========================
    # LEARNING REPORTS
    # ========================

    def generate_report(self, days: int = 7) -> dict:
        """Generate a learning report for the last N days."""
        cutoff = time.time() - (days * 86400)
        recent = [m for m in self.mistakes if m["timestamp"] > cutoff]

        if not recent:
            report = {
                "period_days": days,
                "generated_at": datetime.now().isoformat(),
                "total_mistakes": 0,
                "summary": "No mistakes recorded in this period. Great performance!",
                "by_type": {},
                "by_module": {},
                "patterns": [],
                "suggestions": ["Keep up the good work!"],
            }
            self.reports.append(report)
            self._save(REPORTS_FILE, self.reports[-50:])
            return report

        # Analyze by type
        by_type = Counter(m["type"] for m in recent)

        # Analyze by module
        by_module = Counter(m["module"] for m in recent)

        # Detect patterns — repeated mistake types from same module
        patterns = []
        module_type_combos = Counter((m["module"], m["type"]) for m in recent)
        for (mod, mtype), count in module_type_combos.most_common(5):
            if count >= 2:
                patterns.append({
                    "module": mod,
                    "type": mtype,
                    "count": count,
                    "pattern": f"{mod} has {count} '{mtype}' mistakes in {days} days",
                })

        # Generate suggestions
        suggestions = self._generate_suggestions(by_type, by_module, patterns)

        # Summary
        top_type = by_type.most_common(1)[0] if by_type else ("none", 0)
        top_module = by_module.most_common(1)[0] if by_module else ("none", 0)
        summary = (
            f"{len(recent)} mistakes in the last {days} days. "
            f"Most common issue: {top_type[0]} ({top_type[1]}x). "
            f"Module with most issues: {top_module[0]} ({top_module[1]}x)."
        )

        report = {
            "period_days": days,
            "generated_at": datetime.now().isoformat(),
            "total_mistakes": len(recent),
            "summary": summary,
            "by_type": dict(by_type),
            "by_module": dict(by_module),
            "patterns": patterns,
            "suggestions": suggestions,
            "trend": self._calculate_trend(days),
        }
        self.reports.append(report)
        self._save(REPORTS_FILE, self.reports[-50:])
        return report

    def _generate_suggestions(self, by_type: Counter, by_module: Counter,
                              patterns: list) -> List[str]:
        """Generate improvement suggestions based on mistake analysis."""
        suggestions = []

        if by_type.get("wrong_answer", 0) >= 3:
            suggestions.append("Frequent wrong answers — consider improving KB search or adding web verification")
        if by_type.get("hallucination", 0) >= 2:
            suggestions.append("Hallucination detected — enable stricter Constitutional AI checks")
        if by_type.get("incomplete", 0) >= 2:
            suggestions.append("Incomplete responses — increase LLM context window or response length")
        if by_type.get("slow", 0) >= 3:
            suggestions.append("Slow responses — consider using Groq cloud for complex queries")
        if by_type.get("irrelevant", 0) >= 2:
            suggestions.append("Irrelevant responses — improve intent detection in Zeus")
        if by_type.get("error", 0) >= 3:
            suggestions.append("Multiple errors — check self-healer logs for recurring exceptions")

        for p in patterns:
            if p["count"] >= 3:
                suggestions.append(f"Recurring issue in {p['module']}: {p['type']} — needs targeted fix")

        if not suggestions:
            suggestions.append("No major issues detected. System performing well.")

        return suggestions

    def _calculate_trend(self, days: int) -> str:
        """Compare recent mistakes with previous period."""
        now = time.time()
        current = len([m for m in self.mistakes if m["timestamp"] > now - (days * 86400)])
        previous = len([m for m in self.mistakes
                        if now - (days * 2 * 86400) < m["timestamp"] <= now - (days * 86400)])
        if previous == 0:
            return "new" if current > 0 else "stable"
        change = ((current - previous) / previous) * 100
        if change > 20:
            return "worsening"
        elif change < -20:
            return "improving"
        return "stable"

    def get_reports(self, limit: int = 10) -> List[dict]:
        return self.reports[-limit:]

    # ========================
    # DAILY REFLECTION
    # ========================

    def daily_reflection(self) -> dict:
        """Generate today's reflection summary."""
        today = datetime.now().strftime("%Y-%m-%d")
        today_mistakes = [m for m in self.mistakes if m.get("date") == today]

        # Get agent scores
        scores = {}
        for module, data in self.agent_scores.items():
            total = data.get("success", 0) + data.get("failure", 0)
            if total > 0:
                scores[module] = round(data["success"] / total * 100, 1)

        top_agents = sorted(scores.items(), key=lambda x: -x[1])[:5]
        bottom_agents = sorted(scores.items(), key=lambda x: x[1])[:3]

        reflection = {
            "date": today,
            "generated_at": datetime.now().isoformat(),
            "total_mistakes_today": len(today_mistakes),
            "mistake_types_today": dict(Counter(m["type"] for m in today_mistakes)),
            "agent_scores": scores,
            "top_performing": [{"module": m, "score": s} for m, s in top_agents],
            "needs_improvement": [{"module": m, "score": s} for m, s in bottom_agents if s < 80],
            "overall_health": "good" if len(today_mistakes) < 5 else "fair" if len(today_mistakes) < 15 else "poor",
        }

        # Add narrative
        if len(today_mistakes) == 0:
            reflection["narrative"] = "Perfect day! No mistakes recorded."
        else:
            types = reflection["mistake_types_today"]
            top_issue = max(types.items(), key=lambda x: x[1]) if types else ("none", 0)
            reflection["narrative"] = (
                f"Today had {len(today_mistakes)} mistake(s). "
                f"Main issue: {top_issue[0]} ({top_issue[1]}x). "
                + (f"Modules needing attention: {', '.join(m['module'] for m in reflection['needs_improvement'])}."
                   if reflection["needs_improvement"] else "All modules performing well.")
            )

        return reflection

    # ========================
    # AGENT SCORING
    # ========================

    def _update_agent_score(self, module: str, outcome: str):
        """Update agent performance score."""
        if module not in self.agent_scores:
            self.agent_scores[module] = {
                "success": 0, "failure": 0,
                "streak": 0, "best_streak": 0,
                "last_updated": "",
            }

        data = self.agent_scores[module]
        if outcome == "success":
            data["success"] += 1
            data["streak"] = max(0, data["streak"]) + 1
            data["best_streak"] = max(data["best_streak"], data["streak"])
        else:
            data["failure"] += 1
            data["streak"] = min(0, data["streak"]) - 1

        data["last_updated"] = datetime.now().isoformat()
        self._save(SCORES_FILE, self.agent_scores)

    def get_agent_scores(self) -> dict:
        """Get all agent performance scores."""
        result = {}
        for module, data in self.agent_scores.items():
            total = data["success"] + data["failure"]
            result[module] = {
                **data,
                "total": total,
                "score": round(data["success"] / total * 100, 1) if total > 0 else 0,
            }
        return result

    def get_agent_score(self, module: str) -> Optional[dict]:
        """Get score for a specific agent."""
        if module not in self.agent_scores:
            return None
        data = self.agent_scores[module]
        total = data["success"] + data["failure"]
        return {
            **data,
            "total": total,
            "score": round(data["success"] / total * 100, 1) if total > 0 else 0,
        }

    # ========================
    # IMPROVEMENT SUGGESTIONS
    # ========================

    def get_suggestions(self) -> List[dict]:
        """Get actionable improvement suggestions based on all data."""
        suggestions = []
        scores = self.get_agent_scores()

        # Low-scoring agents
        for module, data in scores.items():
            if data["total"] >= 5 and data["score"] < 70:
                suggestions.append({
                    "priority": "high",
                    "module": module,
                    "suggestion": f"{module} has only {data['score']}% success rate — review and improve",
                    "data": {"score": data["score"], "total": data["total"]},
                })

        # Recent error spikes
        last_24h = time.time() - 86400
        recent = [m for m in self.mistakes if m["timestamp"] > last_24h]
        if len(recent) > 10:
            suggestions.append({
                "priority": "high",
                "module": "system",
                "suggestion": f"{len(recent)} mistakes in last 24h — investigate error spike",
                "data": {"count": len(recent)},
            })

        # Recurring mistake types
        type_counts = Counter(m["type"] for m in self.mistakes[-100:])
        for mtype, count in type_counts.most_common(3):
            if count >= 5:
                suggestions.append({
                    "priority": "medium",
                    "module": "system",
                    "suggestion": f"Recurring '{mtype}' mistakes ({count}x) — add targeted handling",
                    "data": {"type": mtype, "count": count},
                })

        if not suggestions:
            suggestions.append({
                "priority": "low",
                "module": "system",
                "suggestion": "System performing well — no critical improvements needed",
                "data": {},
            })

        return suggestions

    def get_stats(self) -> dict:
        """Get reflection engine statistics."""
        return {
            "total_mistakes": len(self.mistakes),
            "total_reports": len(self.reports),
            "agents_tracked": len(self.agent_scores),
            "mistake_types": dict(Counter(m["type"] for m in self.mistakes)),
            "mistakes_last_24h": len([m for m in self.mistakes if m["timestamp"] > time.time() - 86400]),
            "mistakes_last_7d": len([m for m in self.mistakes if m["timestamp"] > time.time() - 604800]),
        }

    # ========================
    # PERSISTENCE
    # ========================

    @staticmethod
    def _load(filepath: Path, default):
        if filepath.exists():
            try:
                return json.loads(filepath.read_text(encoding="utf-8"))
            except Exception:
                pass
        return default if not callable(default) else default()

    @staticmethod
    def _save(filepath: Path, data):
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save {filepath.name}: {e}")


# Singleton
reflection_engine = ReflectionEngine()
