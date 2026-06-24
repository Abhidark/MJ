"""
MJ Intelligence: Learning Engine (V17)
- Habit Detection: learn user's daily patterns and routines
- Preference Learning: track and adapt to user preferences (language, detail, style)
- Prompt Optimization: improve system prompts based on interaction feedback
- Workflow Learning: detect repeated task sequences and suggest automations
"""

import json
import time
import re
import logging
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("mj.learning")

DATA_DIR = Path(__file__).parent.parent / "learning_data"
DATA_DIR.mkdir(exist_ok=True)

HABITS_FILE = DATA_DIR / "habits.json"
PREFERENCES_FILE = DATA_DIR / "preferences.json"
PROMPTS_FILE = DATA_DIR / "prompt_optimizations.json"
WORKFLOWS_FILE = DATA_DIR / "learned_workflows.json"


class LearningEngine:
    """
    Learns from user interactions to improve over time.
    Tracks habits, preferences, optimizes prompts, and discovers workflow patterns.
    """

    def __init__(self):
        self.habits: Dict = self._load(HABITS_FILE, {
            "time_patterns": {},     # hour -> {action_counts}
            "day_patterns": {},      # weekday -> {action_counts}
            "sequences": [],         # recent action sequences
            "detected_habits": [],   # confirmed habits
        })
        self.preferences: Dict = self._load(PREFERENCES_FILE, {
            "language": {"english": 0, "hindi": 0, "hinglish": 0},
            "detail_level": {"brief": 0, "normal": 0, "detailed": 0},
            "response_style": {"formal": 0, "casual": 0, "technical": 0},
            "topics": {},            # topic -> frequency
            "corrections": [],       # user corrections for learning
            "inferred": {},          # inferred preferences
        })
        self.prompt_opts: Dict = self._load(PROMPTS_FILE, {
            "optimizations": [],     # applied optimizations
            "feedback_log": [],      # positive/negative feedback
            "effective_patterns": {},  # patterns that work well
        })
        self.workflows: Dict = self._load(WORKFLOWS_FILE, {
            "action_history": [],    # recent actions
            "detected_patterns": [], # detected repeated sequences
            "suggested": [],         # suggested automations
        })

    # ========================
    # HABIT DETECTION
    # ========================

    def record_action(self, action: str, module: str = "", metadata: dict = None):
        """Record a user action for habit detection."""
        now = datetime.now()
        hour = str(now.hour)
        day = now.strftime("%A")

        # Time patterns
        if hour not in self.habits["time_patterns"]:
            self.habits["time_patterns"][hour] = {}
        time_data = self.habits["time_patterns"][hour]
        time_data[action] = time_data.get(action, 0) + 1

        # Day patterns
        if day not in self.habits["day_patterns"]:
            self.habits["day_patterns"][day] = {}
        day_data = self.habits["day_patterns"][day]
        day_data[action] = day_data.get(action, 0) + 1

        # Action sequence (keep last 200)
        self.habits["sequences"].append({
            "action": action,
            "module": module,
            "hour": int(hour),
            "day": day,
            "timestamp": time.time(),
        })
        self.habits["sequences"] = self.habits["sequences"][-200:]

        # Also record for workflow detection
        self.workflows["action_history"].append({
            "action": action,
            "module": module,
            "timestamp": time.time(),
        })
        self.workflows["action_history"] = self.workflows["action_history"][-300:]

        self._save(HABITS_FILE, self.habits)

    def detect_habits(self) -> List[dict]:
        """Analyze patterns to detect habits."""
        detected = []

        # Time-based habits: actions that happen 3+ times at same hour
        for hour, actions in self.habits["time_patterns"].items():
            for action, count in actions.items():
                if count >= 3:
                    period = "morning" if int(hour) < 12 else "afternoon" if int(hour) < 17 else "evening"
                    detected.append({
                        "type": "time_habit",
                        "pattern": f"You often {action} in the {period} (around {hour}:00)",
                        "action": action,
                        "hour": int(hour),
                        "frequency": count,
                        "confidence": min(1.0, count / 10),
                    })

        # Day-based habits: actions repeated on same weekday
        for day, actions in self.habits["day_patterns"].items():
            for action, count in actions.items():
                if count >= 3:
                    detected.append({
                        "type": "day_habit",
                        "pattern": f"You tend to {action} on {day}s",
                        "action": action,
                        "day": day,
                        "frequency": count,
                        "confidence": min(1.0, count / 8),
                    })

        # Sequence habits: actions that often follow each other
        seq = self.habits["sequences"]
        if len(seq) >= 10:
            pairs = []
            for i in range(len(seq) - 1):
                if seq[i + 1]["timestamp"] - seq[i]["timestamp"] < 300:  # Within 5 min
                    pairs.append((seq[i]["action"], seq[i + 1]["action"]))
            pair_counts = Counter(pairs)
            for (a1, a2), count in pair_counts.most_common(5):
                if count >= 3 and a1 != a2:
                    detected.append({
                        "type": "sequence_habit",
                        "pattern": f"You often do '{a2}' right after '{a1}'",
                        "sequence": [a1, a2],
                        "frequency": count,
                        "confidence": min(1.0, count / 6),
                    })

        detected.sort(key=lambda x: -x["confidence"])
        self.habits["detected_habits"] = detected
        self._save(HABITS_FILE, self.habits)
        return detected

    def get_habits(self) -> List[dict]:
        return self.habits.get("detected_habits", [])

    # ========================
    # PREFERENCE LEARNING
    # ========================

    def learn_preference(self, message: str, response: str = "",
                         feedback: str = "neutral"):
        """Learn user preferences from interaction."""
        # Detect language preference
        hindi_chars = len(re.findall(r'[ऀ-ॿ]', message))
        english_words = len(re.findall(r'\b[a-zA-Z]{2,}\b', message))
        hindi_transliterated = len(re.findall(
            r'\b(kya|hai|karo|kaise|mujhe|batao|bhai|yaar|nahi|haan|acha|theek)\b',
            message, re.I
        ))

        if hindi_chars > 5:
            self.preferences["language"]["hindi"] += 1
        elif hindi_transliterated > 2:
            self.preferences["language"]["hinglish"] += 1
        elif english_words > 3:
            self.preferences["language"]["english"] += 1

        # Detect detail preference
        if re.search(r'\b(brief|short|quickly|jaldi|chhota)\b', message, re.I):
            self.preferences["detail_level"]["brief"] += 1
        elif re.search(r'\b(detail|explain|elaborate|vistaar|poora)\b', message, re.I):
            self.preferences["detail_level"]["detailed"] += 1
        else:
            self.preferences["detail_level"]["normal"] += 1

        # Detect style
        if re.search(r'\b(sir|please|kindly|formally|professional)\b', message, re.I):
            self.preferences["response_style"]["formal"] += 1
        elif re.search(r'\b(bro|dude|yaar|bhai|chill)\b', message, re.I):
            self.preferences["response_style"]["casual"] += 1
        elif re.search(r'\b(code|function|API|debug|deploy|git)\b', message, re.I):
            self.preferences["response_style"]["technical"] += 1

        # Track topics
        topic_keywords = re.findall(r'\b[a-zA-Z]{4,}\b', message.lower())
        for word in topic_keywords[:5]:
            if word not in ("what", "that", "this", "with", "have", "from", "been", "your"):
                self.preferences["topics"][word] = self.preferences["topics"].get(word, 0) + 1

        # Log feedback
        if feedback != "neutral":
            self.preferences["corrections"].append({
                "message": message[:200],
                "feedback": feedback,
                "timestamp": time.time(),
            })
            self.preferences["corrections"] = self.preferences["corrections"][-100:]

        # Infer dominant preferences
        self.preferences["inferred"] = {
            "language": max(self.preferences["language"], key=self.preferences["language"].get),
            "detail": max(self.preferences["detail_level"], key=self.preferences["detail_level"].get),
            "style": max(self.preferences["response_style"], key=self.preferences["response_style"].get),
            "top_topics": sorted(self.preferences["topics"].items(), key=lambda x: -x[1])[:10],
        }

        self._save(PREFERENCES_FILE, self.preferences)

    def get_preferences(self) -> dict:
        return {
            "language": self.preferences["language"],
            "detail_level": self.preferences["detail_level"],
            "response_style": self.preferences["response_style"],
            "inferred": self.preferences.get("inferred", {}),
            "top_topics": sorted(
                self.preferences["topics"].items(), key=lambda x: -x[1]
            )[:15],
        }

    def get_preference_prompt(self) -> str:
        """Generate a prompt addition based on learned preferences."""
        inferred = self.preferences.get("inferred", {})
        if not inferred:
            return ""

        parts = []
        lang = inferred.get("language", "english")
        if lang == "hinglish":
            parts.append("User prefers Hinglish (Hindi-English mix).")
        elif lang == "hindi":
            parts.append("User prefers Hindi responses.")

        detail = inferred.get("detail", "normal")
        if detail == "brief":
            parts.append("Keep responses concise and brief.")
        elif detail == "detailed":
            parts.append("User prefers detailed explanations.")

        style = inferred.get("style", "casual")
        if style == "formal":
            parts.append("Use professional and formal tone.")
        elif style == "casual":
            parts.append("Use casual, friendly tone.")
        elif style == "technical":
            parts.append("User is technical — use precise terminology.")

        return " ".join(parts)

    # ========================
    # PROMPT OPTIMIZATION
    # ========================

    def log_prompt_feedback(self, prompt_type: str, query: str,
                            positive: bool, notes: str = ""):
        """Log feedback on prompt effectiveness."""
        entry = {
            "prompt_type": prompt_type,
            "query": query[:200],
            "positive": positive,
            "notes": notes,
            "timestamp": time.time(),
        }
        self.prompt_opts["feedback_log"].append(entry)
        self.prompt_opts["feedback_log"] = self.prompt_opts["feedback_log"][-200:]

        # Track effective patterns
        if positive:
            self.prompt_opts["effective_patterns"][prompt_type] = \
                self.prompt_opts["effective_patterns"].get(prompt_type, 0) + 1

        self._save(PROMPTS_FILE, self.prompt_opts)

    def get_prompt_suggestions(self) -> List[dict]:
        """Analyze feedback to suggest prompt improvements."""
        suggestions = []
        feedback = self.prompt_opts["feedback_log"]

        if len(feedback) < 5:
            return [{"suggestion": "Not enough data yet. Need at least 5 feedback entries.", "priority": "low"}]

        # Count positive/negative by prompt type
        by_type = defaultdict(lambda: {"positive": 0, "negative": 0})
        for f in feedback[-100:]:
            key = "positive" if f["positive"] else "negative"
            by_type[f["prompt_type"]][key] += 1

        for ptype, counts in by_type.items():
            total = counts["positive"] + counts["negative"]
            if total >= 3:
                rate = counts["positive"] / total
                if rate < 0.5:
                    suggestions.append({
                        "prompt_type": ptype,
                        "success_rate": round(rate * 100, 1),
                        "suggestion": f"'{ptype}' prompts have low success ({round(rate * 100)}%) — needs rework",
                        "priority": "high" if rate < 0.3 else "medium",
                    })

        return suggestions if suggestions else [{"suggestion": "All prompt types performing well.", "priority": "low"}]

    def get_prompt_stats(self) -> dict:
        """Get prompt optimization statistics."""
        feedback = self.prompt_opts["feedback_log"]
        total = len(feedback)
        positive = sum(1 for f in feedback if f["positive"])
        return {
            "total_feedback": total,
            "positive": positive,
            "negative": total - positive,
            "success_rate": round(positive / total * 100, 1) if total > 0 else 0,
            "effective_patterns": self.prompt_opts["effective_patterns"],
        }

    # ========================
    # WORKFLOW LEARNING
    # ========================

    def detect_workflows(self) -> List[dict]:
        """Detect repeated action sequences that could be automated."""
        actions = self.workflows["action_history"]
        if len(actions) < 10:
            return []

        detected = []

        # Look for 2-action and 3-action sequences
        for seq_len in (2, 3):
            sequences = []
            for i in range(len(actions) - seq_len):
                # Check time proximity (all within 5 min)
                if actions[i + seq_len - 1]["timestamp"] - actions[i]["timestamp"] < 300:
                    seq = tuple(a["action"] for a in actions[i:i + seq_len])
                    sequences.append(seq)

            seq_counts = Counter(sequences)
            for seq, count in seq_counts.most_common(5):
                if count >= 3 and len(set(seq)) > 1:  # At least 3 occurrences, not all same action
                    detected.append({
                        "sequence": list(seq),
                        "length": seq_len,
                        "occurrences": count,
                        "confidence": min(1.0, count / 5),
                        "suggestion": f"You often do: {' → '.join(seq)}. Want to automate this?",
                        "automatable": True,
                    })

        detected.sort(key=lambda x: -x["occurrences"])
        self.workflows["detected_patterns"] = detected
        self._save(WORKFLOWS_FILE, self.workflows)
        return detected

    def get_workflows(self) -> List[dict]:
        return self.workflows.get("detected_patterns", [])

    def get_stats(self) -> dict:
        """Get learning engine statistics."""
        return {
            "habits_detected": len(self.habits.get("detected_habits", [])),
            "actions_recorded": len(self.habits.get("sequences", [])),
            "preference_language": self.preferences.get("inferred", {}).get("language", "unknown"),
            "preference_style": self.preferences.get("inferred", {}).get("style", "unknown"),
            "topics_tracked": len(self.preferences.get("topics", {})),
            "prompt_feedback": len(self.prompt_opts.get("feedback_log", [])),
            "workflows_detected": len(self.workflows.get("detected_patterns", [])),
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
learning_engine = LearningEngine()
