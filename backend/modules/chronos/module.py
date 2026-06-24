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
        return {"total_events": len(self.events), "today_events": today_events}


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


# Module-level singletons
calendar_engine = CalendarEngine()
daily_planner = DailyPlanner()
productivity_tracker = ProductivityTracker()


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
