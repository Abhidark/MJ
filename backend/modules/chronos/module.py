"""
Chronos Module v2 -- Scheduler, Todo Manager & Daily Planner (V14 upgrade).
Manages tasks, calendar events, daily plans, and productivity tracking.
NEW: Calendar integration, daily planning engine, time-blocked scheduling.
"""

import re
import json
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.base_module import BaseModule

logger = logging.getLogger("mj.chronos")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
TODOS_FILE = Path(__file__).parent.parent.parent / "todos.json"
CALENDAR_FILE = DATA_DIR / "chronos_calendar.json"
PLANS_FILE = DATA_DIR / "chronos_daily_plans.json"
PRODUCTIVITY_FILE = DATA_DIR / "chronos_productivity.json"


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
# CALENDAR ENGINE
# ========================

class CalendarEngine:
    """Local calendar with events, recurring events, and time blocks."""

    def __init__(self):
        self.events: list = []
        self._load()

    def _load(self):
        data = _load_json(CALENDAR_FILE, [])
        self.events = data if isinstance(data, list) else []

    def _save(self):
        _save_json(CALENDAR_FILE, self.events)

    def add_event(self, title: str, date: str, start_time: str = "", end_time: str = "",
                  category: str = "general", recurring: str = "") -> dict:
        event = {
            "id": f"evt_{int(time.time() * 1000)}",
            "title": title,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "category": category,
            "recurring": recurring,
            "created": datetime.now().isoformat(),
        }
        self.events.append(event)
        self._save()
        return event

    def get_events(self, date: str = "") -> list:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        return [e for e in self.events if e.get("date") == date]

    def get_upcoming(self, days: int = 7) -> list:
        today = datetime.now().date()
        cutoff = (today + timedelta(days=days)).isoformat()
        today_str = today.isoformat()
        upcoming = [e for e in self.events if today_str <= e.get("date", "") <= cutoff]
        return sorted(upcoming, key=lambda e: (e.get("date", ""), e.get("start_time", "")))

    def delete_event(self, event_id: str) -> dict:
        before = len(self.events)
        self.events = [e for e in self.events if e.get("id") != event_id]
        if len(self.events) < before:
            self._save()
            return {"success": True}
        return {"success": False, "error": "Event not found"}

    def get_stats(self) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        today_events = sum(1 for e in self.events if e.get("date") == today)
        recurring = sum(1 for e in self.events if e.get("recurring"))
        return {"total_events": len(self.events), "today_events": today_events, "recurring": recurring}

    def expand_recurring(self, days_ahead: int = 30) -> list:
        """Expand recurring events into individual occurrences."""
        expanded = []
        today = datetime.now().date()
        for event in self.events:
            recur = event.get("recurring", "")
            if not recur:
                continue
            base_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
            for d in range(days_ahead):
                check_date = today + timedelta(days=d)
                if recur == "daily":
                    should_fire = check_date >= base_date
                elif recur == "weekly":
                    should_fire = check_date >= base_date and check_date.weekday() == base_date.weekday()
                elif recur == "monthly":
                    should_fire = check_date >= base_date and check_date.day == base_date.day
                elif recur == "weekdays":
                    should_fire = check_date >= base_date and check_date.weekday() < 5
                else:
                    should_fire = False
                if should_fire:
                    expanded.append({**event, "date": check_date.isoformat(), "is_recurring_instance": True})
        return sorted(expanded, key=lambda e: (e["date"], e.get("start_time", "")))

    def get_events_with_recurring(self, date: str = "") -> list:
        """Get events for a date, including recurring event instances."""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        direct = [e for e in self.events if e.get("date") == date and not e.get("recurring")]
        # Expand recurring for just this date
        recurring = []
        check = datetime.strptime(date, "%Y-%m-%d").date()
        for event in self.events:
            recur = event.get("recurring", "")
            if not recur:
                continue
            base = datetime.strptime(event["date"], "%Y-%m-%d").date()
            if check < base:
                continue
            if recur == "daily" or (recur == "weekly" and check.weekday() == base.weekday()) or \
               (recur == "monthly" and check.day == base.day) or \
               (recur == "weekdays" and check.weekday() < 5):
                recurring.append({**event, "date": date, "is_recurring_instance": True})
        return direct + recurring

    def convert_timezone(self, event_time: str, from_tz: str = "Asia/Kolkata", to_tz: str = "UTC") -> str:
        """Convert event time between timezones (best effort without pytz)."""
        # Common offsets
        TZ_OFFSETS = {
            "Asia/Kolkata": 5.5, "IST": 5.5, "UTC": 0, "GMT": 0,
            "US/Eastern": -5, "EST": -5, "US/Pacific": -8, "PST": -8,
            "Europe/London": 0, "Europe/Berlin": 1, "Asia/Tokyo": 9,
        }
        from_off = TZ_OFFSETS.get(from_tz, 0)
        to_off = TZ_OFFSETS.get(to_tz, 0)
        try:
            parts = event_time.split(":")
            h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
            total_min = h * 60 + m - int(from_off * 60) + int(to_off * 60)
            total_min = total_min % (24 * 60)
            return f"{total_min // 60:02d}:{total_min % 60:02d}"
        except Exception:
            return event_time


# ========================
# GOOGLE CALENDAR STUB (V14 → 90%+)
# ========================

class GoogleCalendarStub:
    """
    Stub for Google Calendar API integration.
    Provides the interface so code can be written against it.
    When real OAuth credentials are configured, swap to the real API.
    """

    def __init__(self):
        self._connected = False
        self._credentials = None

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self, credentials_path: str = "") -> dict:
        """Connect to Google Calendar (stub — returns instructions)."""
        return {
            "connected": False,
            "instructions": [
                "1. Go to Google Cloud Console → Enable Calendar API",
                "2. Create OAuth2 credentials (Desktop app)",
                "3. Download credentials.json to backend/data/",
                "4. Set GOOGLE_CALENDAR_CREDENTIALS env var",
                "5. Restart backend — auto-connects on startup",
            ],
            "status": "stub_mode",
        }

    def list_events(self, days: int = 7) -> dict:
        if not self._connected:
            return {"events": [], "source": "stub", "note": "Google Calendar not connected. Using local calendar."}
        return {"events": [], "source": "google"}

    def create_event(self, title: str, date: str, start: str = "", end: str = "") -> dict:
        if not self._connected:
            return {"created": False, "reason": "Google Calendar not connected", "stub": True}
        return {"created": True, "stub": True}

    def get_status(self) -> dict:
        return {
            "connected": self._connected,
            "provider": "google_calendar",
            "mode": "stub" if not self._connected else "live",
        }

google_calendar = GoogleCalendarStub()


# ========================
# DAILY PLANNER
# ========================

class DailyPlanner:
    """Generates time-blocked daily plans from tasks and calendar events."""

    def __init__(self):
        self.plans: dict = {}
        self._load()

    def _load(self):
        self.plans = _load_json(PLANS_FILE, {})

    def _save(self):
        _save_json(PLANS_FILE, self.plans)

    def generate_plan(self, tasks: list, events: list, date: str = "") -> dict:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        # Time blocks: morning, midday, afternoon, evening
        blocks = {
            "morning": {"time": "08:00-12:00", "tasks": [], "events": []},
            "midday": {"time": "12:00-14:00", "tasks": [], "events": []},
            "afternoon": {"time": "14:00-18:00", "tasks": [], "events": []},
            "evening": {"time": "18:00-22:00", "tasks": [], "events": []},
        }

        # Assign events to blocks by start_time
        for evt in events:
            st = evt.get("start_time", "09:00")
            hour = int(st.split(":")[0]) if ":" in st else 9
            if hour < 12:
                blocks["morning"]["events"].append(evt)
            elif hour < 14:
                blocks["midday"]["events"].append(evt)
            elif hour < 18:
                blocks["afternoon"]["events"].append(evt)
            else:
                blocks["evening"]["events"].append(evt)

        # Distribute tasks by priority
        high = [t for t in tasks if t.get("priority") == "high"]
        medium = [t for t in tasks if t.get("priority") == "medium"]
        low = [t for t in tasks if t.get("priority") == "low"]

        # High priority → morning, medium → afternoon, low → evening
        blocks["morning"]["tasks"] = high[:3]
        blocks["afternoon"]["tasks"] = medium[:4]
        blocks["evening"]["tasks"] = low[:3]
        # Overflow goes to midday
        overflow = high[3:] + medium[4:] + low[3:]
        blocks["midday"]["tasks"] = overflow[:3]

        plan = {
            "date": date,
            "blocks": blocks,
            "total_tasks": len(tasks),
            "total_events": len(events),
            "generated_at": datetime.now().isoformat(),
        }
        self.plans[date] = plan
        self._save()
        return plan

    def get_plan(self, date: str = "") -> dict:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        return self.plans.get(date, {})

    def get_stats(self) -> dict:
        return {"total_plans": len(self.plans), "dates": list(self.plans.keys())[-10:]}


# ========================
# PRODUCTIVITY TRACKER
# ========================

class ProductivityTracker:
    """Track task completion rates, focus time, and streaks."""

    def __init__(self):
        self.data: dict = {"daily": {}, "streaks": {"current": 0, "best": 0}}
        self._load()

    def _load(self):
        self.data = _load_json(PRODUCTIVITY_FILE, {"daily": {}, "streaks": {"current": 0, "best": 0}})

    def _save(self):
        _save_json(PRODUCTIVITY_FILE, self.data)

    def log_completion(self, task_count: int = 1):
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.data["daily"]:
            self.data["daily"][today] = {"completed": 0, "added": 0}
        self.data["daily"][today]["completed"] += task_count

        # Update streak
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if yesterday in self.data["daily"] and self.data["daily"][yesterday].get("completed", 0) > 0:
            self.data["streaks"]["current"] += 1
        else:
            self.data["streaks"]["current"] = 1
        self.data["streaks"]["best"] = max(self.data["streaks"]["best"], self.data["streaks"]["current"])
        self._save()

    def log_add(self, task_count: int = 1):
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.data["daily"]:
            self.data["daily"][today] = {"completed": 0, "added": 0}
        self.data["daily"][today]["added"] += task_count
        self._save()

    def get_stats(self) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        today_data = self.data["daily"].get(today, {"completed": 0, "added": 0})
        week_completed = sum(
            d.get("completed", 0) for date, d in self.data["daily"].items()
            if date >= (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        )
        return {
            "today": today_data,
            "week_completed": week_completed,
            "streaks": self.data["streaks"],
            "total_days_tracked": len(self.data["daily"]),
        }


# ========================
# CONFLICT DETECTION (V14 → 100%)
# ========================

class ScheduleConflictDetector:
    """Detect scheduling conflicts and suggest alternatives."""

    def check_conflicts(self, events: list, new_event: dict) -> dict:
        """Check if a new event conflicts with existing ones."""
        new_start = new_event.get("start_time", "")
        new_end = new_event.get("end_time", "")
        new_date = new_event.get("date", "")
        conflicts = []

        for evt in events:
            if evt.get("date") != new_date:
                continue
            if not evt.get("start_time") or not new_start:
                continue
            # Simple time overlap check
            e_start = evt["start_time"]
            e_end = evt.get("end_time", "23:59")
            if not new_end:
                new_end = str(int(new_start.split(":")[0]) + 1).zfill(2) + ":00"

            if e_start < new_end and new_start < e_end:
                conflicts.append({
                    "event_id": evt.get("id", ""),
                    "title": evt.get("title", ""),
                    "time": f"{e_start}-{e_end}",
                    "overlap": "partial" if e_start != new_start else "exact",
                })

        return {
            "has_conflict": len(conflicts) > 0,
            "conflicts": conflicts,
            "suggestions": self._suggest_alternatives(events, new_date, new_start, new_end) if conflicts else [],
        }

    def _suggest_alternatives(self, events: list, date: str, start: str, end: str, count: int = 3) -> list:
        """Suggest conflict-free time slots."""
        busy = []
        for evt in events:
            if evt.get("date") == date and evt.get("start_time"):
                e_end = evt.get("end_time", str(int(evt["start_time"].split(":")[0]) + 1).zfill(2) + ":00")
                busy.append((evt["start_time"], e_end))
        busy.sort()

        # Find free slots between 08:00-22:00
        duration_min = 60
        try:
            sh, sm = int(start.split(":")[0]), int(start.split(":")[1]) if ":" in start else 0
            eh, em = int(end.split(":")[0]), int(end.split(":")[1]) if ":" in end else 0
            duration_min = (eh * 60 + em) - (sh * 60 + sm)
            if duration_min <= 0:
                duration_min = 60
        except Exception:
            pass

        suggestions = []
        for hour in range(8, 22):
            slot_start = f"{hour:02d}:00"
            slot_end_h = hour + (duration_min // 60)
            slot_end_m = duration_min % 60
            slot_end = f"{slot_end_h:02d}:{slot_end_m:02d}"
            if slot_end_h > 22:
                continue

            # Check if slot is free
            is_free = True
            for bs, be in busy:
                if bs < slot_end and slot_start < be:
                    is_free = False
                    break
            if is_free:
                suggestions.append({"start": slot_start, "end": slot_end, "date": date})
                if len(suggestions) >= count:
                    break

        return suggestions

    def get_day_availability(self, events: list, date: str) -> dict:
        """Get free/busy times for a day."""
        busy = []
        for evt in events:
            if evt.get("date") == date and evt.get("start_time"):
                e_end = evt.get("end_time", str(int(evt["start_time"].split(":")[0]) + 1).zfill(2) + ":00")
                busy.append({"start": evt["start_time"], "end": e_end, "title": evt.get("title", "")})
        busy.sort(key=lambda x: x["start"])

        total_busy_min = 0
        for b in busy:
            try:
                sh = int(b["start"].split(":")[0])
                eh = int(b["end"].split(":")[0])
                total_busy_min += (eh - sh) * 60
            except Exception:
                pass

        return {
            "date": date,
            "busy_slots": busy,
            "busy_hours": round(total_busy_min / 60, 1),
            "free_hours": round(14 - total_busy_min / 60, 1),  # 8AM-10PM = 14h
            "utilization_pct": round(total_busy_min / (14 * 60) * 100, 1),
        }


# ========================
# HABIT TRACKER (V14 → 100%)
# ========================

HABITS_FILE = DATA_DIR / "habits.json"

class HabitTracker:
    """Track daily habits and streaks."""

    def __init__(self):
        self.habits: dict = {}
        self._load()

    def _load(self):
        self.habits = _load_json(HABITS_FILE, {})

    def _save(self):
        _save_json(HABITS_FILE, self.habits)

    def add_habit(self, name: str, frequency: str = "daily", target: int = 1) -> dict:
        hid = name.lower().replace(" ", "_")
        if hid in self.habits:
            return {"success": False, "error": f"Habit '{name}' already exists"}
        self.habits[hid] = {
            "name": name, "frequency": frequency, "target": target,
            "log": {}, "streak": 0, "best_streak": 0,
            "created": datetime.now().isoformat(),
        }
        self._save()
        return {"success": True, "habit": self.habits[hid]}

    def log_habit(self, habit_id: str, date: str = "", count: int = 1) -> dict:
        if habit_id not in self.habits:
            return {"error": f"Habit '{habit_id}' not found"}
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        h = self.habits[habit_id]
        h["log"][date] = h["log"].get(date, 0) + count
        # Update streak
        self._update_streak(habit_id)
        self._save()
        return {"success": True, "date": date, "count": h["log"][date], "streak": h["streak"]}

    def _update_streak(self, habit_id: str):
        h = self.habits[habit_id]
        today = datetime.now().date()
        streak = 0
        day = today
        while True:
            ds = day.strftime("%Y-%m-%d")
            if h["log"].get(ds, 0) >= h.get("target", 1):
                streak += 1
                day -= timedelta(days=1)
            else:
                break
        h["streak"] = streak
        h["best_streak"] = max(h.get("best_streak", 0), streak)

    def get_habits(self) -> dict:
        items = []
        for hid, h in self.habits.items():
            today = datetime.now().strftime("%Y-%m-%d")
            items.append({
                "id": hid, "name": h["name"], "frequency": h["frequency"],
                "target": h.get("target", 1),
                "today_count": h["log"].get(today, 0),
                "streak": h.get("streak", 0),
                "best_streak": h.get("best_streak", 0),
                "completed_today": h["log"].get(today, 0) >= h.get("target", 1),
            })
        return {"habits": items, "total": len(items)}

    def delete_habit(self, habit_id: str) -> dict:
        if habit_id not in self.habits:
            return {"error": "Not found"}
        del self.habits[habit_id]
        self._save()
        return {"success": True}

    def get_stats(self) -> dict:
        total_logged = sum(sum(h["log"].values()) for h in self.habits.values())
        return {
            "total_habits": len(self.habits),
            "total_entries": total_logged,
            "active_streaks": sum(1 for h in self.habits.values() if h.get("streak", 0) > 0),
        }


# Module-level singletons
calendar_engine = CalendarEngine()
daily_planner = DailyPlanner()
productivity_tracker = ProductivityTracker()
conflict_detector = ScheduleConflictDetector()
habit_tracker = HabitTracker()


class ChronosModule(BaseModule):
    name = "chronos"
    display_name = "Chronos"
    icon = "\U0001f4c5"  # calendar
    description = "Scheduler -- tasks, calendar, daily planner, productivity"
    version = "2.0"
    category = "utility"
    enabled = True

    KEYWORDS = [
        r"\bremind\w*\b", r"\btimer\b", r"\balarm\b", r"\bschedul\w*\b",
        r"\btodo\b", r"\bto-?do\b", r"\btask\b", r"\byaad\s+dilana\b",
        r"\badd\s+task\b", r"\blist\s+task\b", r"\bcomplete\b.*\btask\b",
        r"\bdelete\b.*\btask\b", r"\bkaam\b", r"\bkarna\s+hai\b",
        r"\bremember\b", r"\bnote\b.*\b(down|this)\b", r"\bpending\b",
        r"\bdone\b.*\btask\b", r"\bfinish\w*\b.*\btask\b",
    ]

    CALENDAR_KEYWORDS = re.compile(
        r"\b(calendar|event|meeting|appointment|schedule\s+(?:a|an)|"
        r"add\s+event|upcoming|what'?s\s+(?:on|happening)|agenda|"
        r"plan\s+(?:my|the)\s+day|daily\s+plan|time\s+block|today'?s\s+plan)\b",
        re.IGNORECASE,
    )

    PLAN_KEYWORDS = re.compile(
        r"\b(plan\s+(?:my|the|today|tomorrow)|daily\s+plan|day\s+plan|"
        r"organize\s+(?:my|the)\s+day|productivity|how\s+(?:am\s+I|was\s+my)\s+doing|"
        r"streak|focus\s+time)\b",
        re.IGNORECASE,
    )

    def __init__(self):
        self.reminder_sound = True
        self._ensure_file()

    def _ensure_file(self):
        """Ensure the todos JSON file exists."""
        if not TODOS_FILE.exists():
            TODOS_FILE.write_text(json.dumps({"tasks": []}, indent=2), encoding="utf-8")

    def _load_tasks(self) -> list[dict]:
        """Load tasks from the JSON file."""
        self._ensure_file()
        try:
            data = json.loads(TODOS_FILE.read_text(encoding="utf-8"))
            return data.get("tasks", [])
        except (json.JSONDecodeError, IOError):
            return []

    def _save_tasks(self, tasks: list[dict]):
        """Save tasks to the JSON file."""
        TODOS_FILE.write_text(
            json.dumps({"tasks": tasks}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _next_id(self, tasks: list[dict]) -> int:
        """Get the next available task ID."""
        if not tasks:
            return 1
        return max(t.get("id", 0) for t in tasks) + 1

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        if self.CALENDAR_KEYWORDS.search(text):
            return 0.90
        if self.PLAN_KEYWORDS.search(text):
            return 0.88
        text_lower = text.lower()
        for pattern in self.KEYWORDS:
            if re.search(pattern, text_lower):
                return 0.85
        if intent in ("add_task", "list_tasks", "complete_task", "delete_task",
                       "reminder", "schedule", "calendar", "plan", "productivity"):
            return 0.9
        return 0.0

    def _detect_action(self, text: str) -> str:
        text_lower = text.lower()
        if re.search(r"\b(add|create|new|banao|likho|note)\b", text_lower):
            return "add"
        if re.search(r"\b(list|show|dikha|pending|sab|all|kya.*karna)\b", text_lower):
            return "list"
        if re.search(r"\b(complete|done|finish|ho\s*gaya|kar\s*diya|mark)\b", text_lower):
            return "complete"
        if re.search(r"\b(delete|remove|hata|cancel|clear)\b", text_lower):
            return "delete"
        # If text has a task-like content, default to add
        if len(text.split()) >= 2:
            return "add"
        return "list"

    def _extract_task_text(self, text: str) -> str:
        """Extract the task description from user input."""
        # Remove command words
        cleaned = re.sub(
            r"\b(add|create|new|task|todo|to-?do|remind|reminder|me|to|please|"
            r"banao|likho|note|down|karo|kaam|yaad|dilana|set|a)\b",
            "", text, flags=re.IGNORECASE,
        )
        cleaned = cleaned.strip(" :-,.")
        return cleaned if cleaned else text.strip()

    def _extract_task_id(self, text: str) -> int | None:
        """Extract a task ID number from text."""
        match = re.search(r"\b#?(\d+)\b", text)
        if match:
            return int(match.group(1))
        return None

    def _extract_priority(self, text: str) -> str:
        text_lower = text.lower()
        if re.search(r"\b(urgent|important|high|zaruri)\b", text_lower):
            return "high"
        if re.search(r"\b(low|later|baad\s+mein)\b", text_lower):
            return "low"
        return "medium"

    def execute(self, text: str, context: dict) -> dict:
        # Calendar & planning handlers
        if self.PLAN_KEYWORDS.search(text):
            if re.search(r"\b(productivity|streak|how.+doing)\b", text, re.I):
                return self._show_productivity()
            return self._generate_daily_plan(text)
        if self.CALENDAR_KEYWORDS.search(text):
            if re.search(r"\b(add\s+event|schedule\s+(?:a|an)|set\s+(?:a|an))\b", text, re.I):
                return self._add_calendar_event(text)
            if re.search(r"\b(upcoming|next\s+week|this\s+week)\b", text, re.I):
                return self._upcoming_events()
            return self._show_today_events()

        # Task handlers
        action = self._detect_action(text)
        if action == "add":
            return self._add_task(text)
        elif action == "list":
            return self._list_tasks()
        elif action == "complete":
            return self._complete_task(text)
        elif action == "delete":
            return self._delete_task(text)

        return self._list_tasks()

    def _add_task(self, text: str) -> dict:
        task_text = self._extract_task_text(text)
        if not task_text or len(task_text) < 2:
            return {
                "response": "Please specify what task to add. Example: 'Add task: Buy groceries'",
                "data": None,
                "action": "no_task",
            }

        tasks = self._load_tasks()
        priority = self._extract_priority(text)
        new_task = {
            "id": self._next_id(tasks),
            "text": task_text,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
        }
        tasks.append(new_task)
        self._save_tasks(tasks)
        productivity_tracker.log_add()

        priority_icons = {"high": "\U0001f534", "medium": "\U0001f7e1", "low": "\U0001f7e2"}
        p_icon = priority_icons.get(priority, "\U0001f7e1")

        pending_count = sum(1 for t in tasks if t["status"] == "pending")
        return {
            "response": (
                f"✅ **Task Added!**\n\n"
                f"  {p_icon} #{new_task['id']}: {task_text}\n"
                f"  Priority: {priority.title()}\n\n"
                f"You have **{pending_count}** pending task{'s' if pending_count != 1 else ''}."
            ),
            "data": new_task,
            "action": "task_added",
        }

    def _list_tasks(self) -> dict:
        tasks = self._load_tasks()
        pending = [t for t in tasks if t["status"] == "pending"]
        completed = [t for t in tasks if t["status"] == "completed"]

        if not tasks:
            return {
                "response": (
                    "\U0001f4c5 **No tasks yet!**\n\n"
                    "Add a task: 'Add task: Buy groceries'\n"
                    "Or say: 'Remind me to call dentist'"
                ),
                "data": {"tasks": [], "pending": 0, "completed": 0},
                "action": "empty_list",
            }

        priority_icons = {"high": "\U0001f534", "medium": "\U0001f7e1", "low": "\U0001f7e2"}
        lines = [f"\U0001f4c5 **Your Tasks** ({len(pending)} pending, {len(completed)} done):\n"]

        if pending:
            lines.append("**Pending:**")
            for t in pending:
                p_icon = priority_icons.get(t.get("priority", "medium"), "\U0001f7e1")
                lines.append(f"  {p_icon} #{t['id']}: {t['text']}")

        if completed:
            lines.append("\n**Completed:**")
            for t in completed[-5:]:  # Show last 5 completed
                lines.append(f"  ✅ #{t['id']}: ~~{t['text']}~~")
            if len(completed) > 5:
                lines.append(f"  *...and {len(completed) - 5} more*")

        return {
            "response": "\n".join(lines),
            "data": {"pending": len(pending), "completed": len(completed), "tasks": tasks},
            "action": "task_list",
        }

    def _complete_task(self, text: str) -> dict:
        task_id = self._extract_task_id(text)
        tasks = self._load_tasks()

        if task_id is None:
            # Try to match by text
            task_text = self._extract_task_text(text).lower()
            for t in tasks:
                if t["status"] == "pending" and task_text in t["text"].lower():
                    task_id = t["id"]
                    break

        if task_id is None:
            pending = [t for t in tasks if t["status"] == "pending"]
            if len(pending) == 1:
                task_id = pending[0]["id"]
            else:
                return {
                    "response": "Which task to complete? Use the task number, e.g., 'Complete task #1'",
                    "data": None,
                    "action": "need_id",
                }

        for t in tasks:
            if t["id"] == task_id:
                if t["status"] == "completed":
                    return {
                        "response": f"Task #{task_id} is already completed!",
                        "data": t,
                        "action": "already_done",
                    }
                t["status"] = "completed"
                t["completed_at"] = datetime.now().isoformat()
                self._save_tasks(tasks)
                productivity_tracker.log_completion()

                pending_count = sum(1 for tt in tasks if tt["status"] == "pending")
                return {
                    "response": (
                        f"\U0001f389 **Task Completed!**\n\n"
                        f"  ✅ #{t['id']}: ~~{t['text']}~~\n\n"
                        f"**{pending_count}** task{'s' if pending_count != 1 else ''} remaining."
                    ),
                    "data": t,
                    "action": "task_completed",
                }

        return {
            "response": f"Task #{task_id} not found.",
            "data": None,
            "action": "not_found",
        }

    def _delete_task(self, text: str) -> dict:
        task_id = self._extract_task_id(text)
        tasks = self._load_tasks()

        # Check for "delete all" / "clear all"
        if re.search(r"\b(all|sab|sara)\b", text.lower()):
            count = len(tasks)
            self._save_tasks([])
            return {
                "response": f"\U0001f5d1️ Cleared **{count}** task{'s' if count != 1 else ''}. Fresh start!",
                "data": {"deleted": count},
                "action": "all_deleted",
            }

        if task_id is None:
            return {
                "response": "Which task to delete? Use the task number, e.g., 'Delete task #1'",
                "data": None,
                "action": "need_id",
            }

        original_count = len(tasks)
        tasks = [t for t in tasks if t["id"] != task_id]

        if len(tasks) == original_count:
            return {
                "response": f"Task #{task_id} not found.",
                "data": None,
                "action": "not_found",
            }

        self._save_tasks(tasks)
        return {
            "response": f"\U0001f5d1️ Task #{task_id} deleted. {len(tasks)} task{'s' if len(tasks) != 1 else ''} remaining.",
            "data": {"deleted_id": task_id},
            "action": "task_deleted",
        }

    # ---- CALENDAR METHODS ----

    def _add_calendar_event(self, text: str) -> dict:
        cleaned = re.sub(r"\b(add\s+event|schedule|set|calendar|a|an)\b", "", text, flags=re.I).strip(" :,.-")
        # Try to extract date
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if date_match:
            date = date_match.group(1)
        elif re.search(r"\btomorrow\b", text, re.I):
            date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            date = datetime.now().strftime("%Y-%m-%d")

        # Try to extract time
        time_match = re.search(r"(\d{1,2}:\d{2})", text)
        start_time = time_match.group(1) if time_match else ""

        title = re.sub(r"\d{4}-\d{2}-\d{2}|\d{1,2}:\d{2}|tomorrow|today", "", cleaned, flags=re.I).strip(" ,.-")
        if not title or len(title) < 2:
            title = cleaned[:80] if cleaned else "Untitled Event"

        event = calendar_engine.add_event(title=title, date=date, start_time=start_time)
        return {
            "response": f"\U0001f4c5 Event added: **{title}** on {date}" + (f" at {start_time}" if start_time else ""),
            "data": event,
            "action": "event_added",
        }

    def _show_today_events(self) -> dict:
        today = datetime.now().strftime("%Y-%m-%d")
        events = calendar_engine.get_events(today)
        tasks = self._load_tasks()
        pending = [t for t in tasks if t["status"] == "pending"]

        if not events and not pending:
            return {
                "response": "\U0001f4c5 **Today's Agenda**: Nothing scheduled. Add events or tasks!",
                "data": {"events": [], "tasks": []},
                "action": "today_agenda",
            }

        lines = [f"\U0001f4c5 **Today ({today})**\n"]
        if events:
            lines.append("**Events:**")
            for e in events:
                t = f" at {e['start_time']}" if e.get("start_time") else ""
                lines.append(f"  \U0001f4cc {e['title']}{t}")
        if pending:
            lines.append(f"\n**Tasks:** ({len(pending)} pending)")
            for t in pending[:5]:
                lines.append(f"  \U0001f7e1 #{t['id']}: {t['text']}")

        return {
            "response": "\n".join(lines),
            "data": {"events": events, "pending_tasks": len(pending)},
            "action": "today_agenda",
        }

    def _upcoming_events(self) -> dict:
        events = calendar_engine.get_upcoming(days=7)
        if not events:
            return {"response": "No upcoming events in the next 7 days.", "data": {"events": []}, "action": "upcoming"}
        lines = ["\U0001f4c5 **Upcoming Events (7 days):**\n"]
        current_date = ""
        for e in events:
            if e["date"] != current_date:
                current_date = e["date"]
                lines.append(f"\n**{current_date}**")
            t = f" at {e['start_time']}" if e.get("start_time") else ""
            lines.append(f"  \U0001f4cc {e['title']}{t}")
        return {"response": "\n".join(lines), "data": {"events": events, "count": len(events)}, "action": "upcoming"}

    # ---- DAILY PLANNER ----

    def _generate_daily_plan(self, text: str) -> dict:
        date = datetime.now().strftime("%Y-%m-%d")
        if "tomorrow" in text.lower():
            date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        tasks = [t for t in self._load_tasks() if t["status"] == "pending"]
        events = calendar_engine.get_events(date)
        plan = daily_planner.generate_plan(tasks, events, date)

        lines = [f"\U0001f4cb **Daily Plan for {date}**\n"]
        for block_name, block in plan.get("blocks", {}).items():
            icon = {"morning": "🌅", "midday": "☀️", "afternoon": "🌤️", "evening": "🌙"}.get(block_name, "⏰")
            lines.append(f"\n{icon} **{block_name.title()}** ({block['time']})")
            for evt in block.get("events", []):
                lines.append(f"  \U0001f4cc {evt['title']}")
            for task in block.get("tasks", []):
                lines.append(f"  \U0001f7e1 {task['text']}")
            if not block.get("events") and not block.get("tasks"):
                lines.append("  \U0001f7e2 Free time")

        return {
            "response": "\n".join(lines),
            "data": plan,
            "action": "daily_plan",
        }

    # ---- PRODUCTIVITY ----

    def _show_productivity(self) -> dict:
        stats = productivity_tracker.get_stats()
        today = stats.get("today", {})
        streaks = stats.get("streaks", {})
        lines = [
            "\U0001f4ca **Productivity Stats**\n",
            f"**Today:** {today.get('completed', 0)} completed, {today.get('added', 0)} added",
            f"**This Week:** {stats.get('week_completed', 0)} tasks completed",
            f"**Streak:** {streaks.get('current', 0)} days (best: {streaks.get('best', 0)})",
            f"**Days Tracked:** {stats.get('total_days_tracked', 0)}",
        ]
        return {"response": "\n".join(lines), "data": stats, "action": "productivity"}

    def get_system_prompt_addition(self) -> str:
        tasks = self._load_tasks()
        pending = sum(1 for t in tasks if t["status"] == "pending")
        return (
            f"You can manage tasks and reminders. The user has {pending} pending tasks. "
            "Help them add, complete, or organize tasks."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        tasks = self._load_tasks()
        pending = [t for t in tasks if t["status"] == "pending"]
        if pending:
            task_list = "; ".join(f"#{t['id']}: {t['text']}" for t in pending[:5])
            return f"[Chronos] Pending tasks: {task_list}"
        return "[Chronos] No pending tasks."

    def get_settings(self) -> dict:
        cal_stats = calendar_engine.get_stats()
        prod_stats = productivity_tracker.get_stats()
        return {
            "enabled": self.enabled,
            "reminder_sound": self.reminder_sound,
            "calendar_events": cal_stats["total_events"],
            "today_events": cal_stats["today_events"],
            "productivity": prod_stats,
        }

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "reminder_sound" in settings:
            self.reminder_sound = bool(settings["reminder_sound"])

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "reminder_sound", "label": "Reminder Sound",
                "type": "toggle", "value": self.reminder_sound,
            },
        ]
