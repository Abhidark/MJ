"""
MJ Scheduled Tasks / Cron System
Supports: recurring tasks (every X min/hour/day), daily at time, one-time delayed.
Persists tasks to JSON so they survive restarts.
"""

import re
import json
import asyncio
import threading
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

TASKS_FILE = Path(__file__).parent.parent / "scheduled_tasks.json"

# In-memory task list
scheduled_tasks = []
_scheduler_thread = None
_running = False


def _load_tasks():
    global scheduled_tasks
    try:
        if TASKS_FILE.exists():
            scheduled_tasks = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
            # Reset running state on load
            for t in scheduled_tasks:
                t["_timer"] = None
    except Exception:
        scheduled_tasks = []


def _save_tasks():
    try:
        # Don't save timer objects
        save_data = []
        for t in scheduled_tasks:
            d = {k: v for k, v in t.items() if k != "_timer"}
            save_data.append(d)
        TASKS_FILE.write_text(json.dumps(save_data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def parse_schedule(text: str) -> Optional[dict]:
    """Parse scheduling commands from user text."""
    lower = text.lower().strip()

    # ---- EVERY X MINUTES/HOURS ----
    m = re.search(
        r"(?:every|har|repeat)\s+(\d+)\s*(min(?:ute)?s?|hour?s?|ghante?|mint?)\s+(.+)",
        lower
    )
    if m:
        interval = int(m.group(1))
        unit = m.group(2)
        action = m.group(3).strip()
        seconds = _to_seconds(interval, unit)
        return {
            "type": "interval",
            "interval_seconds": seconds,
            "interval_desc": f"{interval} {unit}",
            "action": _clean_action(action),
            "action_raw": action,
        }

    # ---- DAILY AT TIME: "har subah 8 baje X", "daily at 9am X" ----
    m = re.search(
        r"(?:daily|har\s*(?:din|roz|subah|sham))\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm|baje)?\s+(.+)",
        lower
    )
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        period = m.group(3) or ""
        action = m.group(4).strip()

        if period == "pm" and hour < 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
        elif period == "baje" and hour <= 6:
            hour += 12

        return {
            "type": "daily",
            "hour": hour,
            "minute": minute,
            "time_desc": f"{hour:02d}:{minute:02d}",
            "action": _clean_action(action),
            "action_raw": action,
        }

    # ---- EVERY DAY (no specific time, default morning 8am) ----
    m = re.search(r"(?:every\s*day|har\s*din|roz|rozana)\s+(.+)", lower)
    if m:
        action = m.group(1).strip()
        return {
            "type": "daily",
            "hour": 8,
            "minute": 0,
            "time_desc": "08:00",
            "action": _clean_action(action),
            "action_raw": action,
        }

    # ---- SCHEDULE / SET: "schedule X every Y" ----
    m = re.search(r"(?:schedule|set)\s+(.+?)\s+(?:every|har)\s+(\d+)\s*(min|hour|day)", lower)
    if m:
        action = m.group(1).strip()
        interval = int(m.group(2))
        unit = m.group(3)
        if unit == "day":
            return {
                "type": "daily",
                "hour": 8,
                "minute": 0,
                "time_desc": "08:00",
                "action": _clean_action(action),
                "action_raw": action,
            }
        seconds = _to_seconds(interval, unit)
        return {
            "type": "interval",
            "interval_seconds": seconds,
            "interval_desc": f"{interval} {unit}",
            "action": _clean_action(action),
            "action_raw": action,
        }

    # ---- LIST TASKS ----
    if any(w in lower for w in ["list schedule", "scheduled tasks", "show schedule", "meri tasks", "kya schedule hai"]):
        return {"type": "list"}

    # ---- CANCEL/STOP TASK ----
    m = re.search(r"(?:cancel|stop|delete|remove|hatao|band)\s+(?:schedule|task|scheduled task)\s*#?(\d+)?", lower)
    if m:
        task_num = int(m.group(1)) if m.group(1) else None
        return {"type": "cancel", "task_number": task_num}

    return None


def add_scheduled_task(schedule_info: dict) -> dict:
    """Add a new scheduled task."""
    task_id = f"task_{datetime.now().strftime('%H%M%S')}_{len(scheduled_tasks)}"

    task = {
        "id": task_id,
        "type": schedule_info["type"],
        "action": schedule_info["action"],
        "action_raw": schedule_info.get("action_raw", schedule_info["action"]),
        "created": datetime.now().isoformat(),
        "last_run": None,
        "run_count": 0,
        "active": True,
        "_timer": None,
    }

    if schedule_info["type"] == "interval":
        task["interval_seconds"] = schedule_info["interval_seconds"]
        task["interval_desc"] = schedule_info["interval_desc"]
        desc = f"Every {schedule_info['interval_desc']}: {schedule_info['action']}"
    elif schedule_info["type"] == "daily":
        task["hour"] = schedule_info["hour"]
        task["minute"] = schedule_info["minute"]
        task["time_desc"] = schedule_info["time_desc"]
        desc = f"Daily at {schedule_info['time_desc']}: {schedule_info['action']}"
    else:
        desc = schedule_info["action"]

    task["description"] = desc
    scheduled_tasks.append(task)
    _save_tasks()

    # Start the task
    _start_task(task)

    return {
        "success": True,
        "message": f"Scheduled! {desc}",
        "task_id": task_id,
    }


def list_scheduled_tasks() -> dict:
    """List all scheduled tasks."""
    if not scheduled_tasks:
        return {"success": True, "message": "Koi scheduled task nahi hai abhi.", "tasks": []}

    lines = [f"{len(scheduled_tasks)} scheduled task(s):"]
    for i, t in enumerate(scheduled_tasks):
        status = "Active" if t.get("active") else "Paused"
        runs = t.get("run_count", 0)
        lines.append(f"  #{i+1} [{status}] {t['description']} (ran {runs}x)")

    return {
        "success": True,
        "message": "\n".join(lines),
        "tasks": [{k: v for k, v in t.items() if k != "_timer"} for t in scheduled_tasks],
    }


def cancel_task(task_number: Optional[int]) -> dict:
    """Cancel a scheduled task."""
    if task_number is None:
        # Cancel last task
        if scheduled_tasks:
            task = scheduled_tasks.pop()
            if task.get("_timer"):
                task["_timer"].cancel()
            _save_tasks()
            return {"success": True, "message": f"Task cancelled: {task['description']}"}
        return {"success": False, "message": "Koi task nahi hai cancel karne ko."}

    idx = task_number - 1
    if 0 <= idx < len(scheduled_tasks):
        task = scheduled_tasks.pop(idx)
        if task.get("_timer"):
            task["_timer"].cancel()
        _save_tasks()
        return {"success": True, "message": f"Task #{task_number} cancelled: {task['description']}"}

    return {"success": False, "message": f"Task #{task_number} nahi mila."}


def _start_task(task: dict):
    """Start a scheduled task timer."""
    if task["type"] == "interval":
        _run_interval_task(task)
    elif task["type"] == "daily":
        _run_daily_task(task)


def _run_interval_task(task: dict):
    """Run a recurring interval task."""
    def callback():
        if not task.get("active"):
            return
        _execute_task_action(task)
        task["run_count"] = task.get("run_count", 0) + 1
        task["last_run"] = datetime.now().isoformat()
        _save_tasks()
        # Reschedule
        if task.get("active"):
            timer = threading.Timer(task["interval_seconds"], callback)
            timer.daemon = True
            timer.start()
            task["_timer"] = timer

    timer = threading.Timer(task["interval_seconds"], callback)
    timer.daemon = True
    timer.start()
    task["_timer"] = timer


def _run_daily_task(task: dict):
    """Run a daily task at specific time."""
    def callback():
        if not task.get("active"):
            return
        _execute_task_action(task)
        task["run_count"] = task.get("run_count", 0) + 1
        task["last_run"] = datetime.now().isoformat()
        _save_tasks()
        # Reschedule for next day
        if task.get("active"):
            _schedule_next_daily(task)

    _schedule_next_daily_with_callback(task, callback)


def _schedule_next_daily(task: dict):
    """Schedule next daily execution."""
    _schedule_next_daily_with_callback(task, lambda: _run_daily_task(task))


def _schedule_next_daily_with_callback(task: dict, callback):
    now = datetime.now()
    target = now.replace(hour=task["hour"], minute=task["minute"], second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    delay = (target - now).total_seconds()
    timer = threading.Timer(delay, callback)
    timer.daemon = True
    timer.start()
    task["_timer"] = timer


def _execute_task_action(task: dict):
    """Execute the task's action — send notification with the action text."""
    action = task.get("action", "")
    desc = task.get("description", action)

    # Send Windows notification
    ps = f'''
Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.Visible = $true
$n.ShowBalloonTip(10000, "MJ Scheduled Task", "{_escape(desc)}", [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Seconds 11
$n.Dispose()
'''
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps],
            creationflags=0x08000000
        )
    except Exception:
        pass


def start_all_tasks():
    """Start all active tasks (call on server boot)."""
    _load_tasks()
    for task in scheduled_tasks:
        if task.get("active"):
            _start_task(task)


def _clean_action(text: str) -> str:
    """Clean action text."""
    for filler in ["karo", "kar", "do", "please", "karna", "bolna", "batana", "batao"]:
        text = text.replace(filler, "").strip()
    return text.strip()


def _to_seconds(amount: int, unit: str) -> int:
    unit = unit.lower()
    if unit.startswith("sec"):
        return amount
    elif unit.startswith("min") or unit.startswith("mint"):
        return amount * 60
    elif unit.startswith("hour") or unit.startswith("ghant"):
        return amount * 3600
    elif unit.startswith("day"):
        return amount * 86400
    return amount * 60


def _escape(text: str) -> str:
    return text.replace('"', '`"').replace("'", "`'").replace("\n", " ")
