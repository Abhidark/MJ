"""
Chronos Module -- Scheduler & Todo Manager
Manages a todo/task list stored in a JSON file. Supports add, list, complete, and delete.
"""

import re
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.base_module import BaseModule

TODOS_FILE = Path(__file__).parent.parent.parent / "todos.json"


class ChronosModule(BaseModule):
    name = "chronos"
    display_name = "Chronos"
    icon = "\U0001f4c5"  # calendar
    description = "Scheduler -- manage tasks, reminders, and to-do lists"
    version = "1.0"
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
        text_lower = text.lower()
        for pattern in self.KEYWORDS:
            if re.search(pattern, text_lower):
                return 0.85
        if intent in ("add_task", "list_tasks", "complete_task", "delete_task", "reminder", "schedule"):
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
        return {
            "enabled": self.enabled,
            "reminder_sound": self.reminder_sound,
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
