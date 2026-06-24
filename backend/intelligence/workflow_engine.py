"""
Workflow Engine v2 for MJ-Assistant (V19).
Adds: morning routine, news digest, email automation,
scheduled triggers, event-driven workflows, workflow templates.
Works with existing Zeus workflows + scheduler.
"""

import json
import time
import asyncio
import logging
import re
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

logger = logging.getLogger("mj.workflow_engine")

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
WORKFLOWS_FILE = DATA_DIR / "workflow_engine.json"
WORKFLOW_LOGS_FILE = DATA_DIR / "workflow_logs.json"
TRIGGERS_FILE = DATA_DIR / "workflow_triggers.json"


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
# WORKFLOW TEMPLATES
# ========================

BUILT_IN_WORKFLOWS = {
    "morning_routine": {
        "name": "Morning Routine",
        "icon": "\U0001f305",
        "description": "Complete morning briefing: weather, news, tasks, emails, motivation",
        "trigger": {"type": "daily", "hour": 7, "minute": 0},
        "steps": [
            {"id": "weather", "module": "atlas", "action": "weather", "description": "Get today's weather forecast", "params": {}},
            {"id": "news", "module": "sherlock", "action": "news", "description": "Top headlines & trending", "params": {"count": 5}},
            {"id": "tasks", "module": "chronos", "action": "pending_tasks", "description": "Show pending reminders & tasks", "params": {}},
            {"id": "emails", "module": "hermes", "action": "unread_count", "description": "Check unread emails", "params": {}},
            {"id": "greeting", "module": None, "action": "llm_generate", "description": "Generate personalized morning greeting with summary", "params": {"prompt": "Generate a brief, motivating morning greeting. Include weather, news summary, and task count from context."}},
        ],
        "enabled": True,
        "run_count": 0,
        "last_run": None,
    },
    "news_digest": {
        "name": "News Digest",
        "icon": "\U0001f4f0",
        "description": "Fetch, categorize, and summarize top news",
        "trigger": {"type": "interval", "hours": 4},
        "steps": [
            {"id": "tech_news", "module": "sherlock", "action": "search", "description": "Search tech news", "params": {"query": "latest technology news today"}},
            {"id": "world_news", "module": "sherlock", "action": "search", "description": "Search world news", "params": {"query": "top world news today"}},
            {"id": "summarize", "module": None, "action": "llm_generate", "description": "Summarize and categorize news", "params": {"prompt": "Summarize the news results into categories: Tech, World, Business. Keep it brief — 2-3 lines per story."}},
        ],
        "enabled": False,
        "run_count": 0,
        "last_run": None,
    },
    "email_auto_sort": {
        "name": "Email Auto-Sort",
        "icon": "\U0001f4e7",
        "description": "Check emails, categorize by priority, draft quick replies",
        "trigger": {"type": "interval", "minutes": 30},
        "steps": [
            {"id": "fetch", "module": "hermes", "action": "check_inbox", "description": "Fetch recent unread emails", "params": {"count": 10}},
            {"id": "categorize", "module": None, "action": "llm_generate", "description": "Categorize emails by priority", "params": {"prompt": "Categorize these emails into: Urgent, Important, FYI, Spam. For urgent ones, suggest a 1-line reply."}},
        ],
        "enabled": False,
        "run_count": 0,
        "last_run": None,
    },
    "code_health_check": {
        "name": "Code Health Check",
        "icon": "\U0001f4bb",
        "description": "Git status, test run, error log review",
        "trigger": {"type": "daily", "hour": 10, "minute": 0},
        "steps": [
            {"id": "git_status", "module": "hephaestus", "action": "git_status", "description": "Check git status", "params": {}},
            {"id": "run_tests", "module": "hephaestus", "action": "run_tests", "description": "Run project tests", "params": {}},
            {"id": "error_review", "module": None, "action": "llm_generate", "description": "Summarize code health", "params": {"prompt": "Based on git status and test results, give a brief code health summary."}},
        ],
        "enabled": False,
        "run_count": 0,
        "last_run": None,
    },
    "daily_planner": {
        "name": "Daily Planner",
        "icon": "\U0001f4c5",
        "description": "Plan your day: tasks, calendar, priorities",
        "trigger": {"type": "daily", "hour": 8, "minute": 30},
        "steps": [
            {"id": "tasks", "module": "chronos", "action": "pending_tasks", "description": "Get all pending tasks", "params": {}},
            {"id": "calendar", "module": "chronos", "action": "today_events", "description": "Today's calendar events", "params": {}},
            {"id": "plan", "module": None, "action": "llm_generate", "description": "Create prioritized day plan", "params": {"prompt": "Create a prioritized daily plan based on tasks and calendar. Suggest time blocks and breaks."}},
        ],
        "enabled": False,
        "run_count": 0,
        "last_run": None,
    },
    "security_patrol": {
        "name": "Security Patrol",
        "icon": "\U0001f6e1️",
        "description": "System health + security scan",
        "trigger": {"type": "daily", "hour": 22, "minute": 0},
        "steps": [
            {"id": "health", "module": "sentinel", "action": "system_health", "description": "Check system health", "params": {}},
            {"id": "audit", "module": "sentinel", "action": "audit_recent", "description": "Review recent audit logs", "params": {}},
            {"id": "summary", "module": None, "action": "llm_generate", "description": "Security summary", "params": {"prompt": "Summarize system health and any security concerns from audit logs."}},
        ],
        "enabled": False,
        "run_count": 0,
        "last_run": None,
    },
}

# ========================
# EVENT TRIGGERS
# ========================

EVENT_TRIGGER_TYPES = {
    "time": "Run at a specific time daily",
    "interval": "Run every N minutes/hours",
    "event": "Run when a specific event occurs",
    "keyword": "Run when user says a keyword",
    "startup": "Run when MJ starts",
    "idle": "Run after N minutes of inactivity",
}


# ========================
# WORKFLOW ENGINE CLASS
# ========================

class WorkflowEngine:
    """Manages workflow creation, execution, scheduling, and templates."""

    def __init__(self):
        self.workflows: Dict[str, dict] = {}
        self.triggers: List[dict] = []
        self.execution_log: List[dict] = []
        self._timers: List[threading.Timer] = []
        self._load()

    def _load(self):
        saved = _load_json(WORKFLOWS_FILE, {})
        if saved:
            self.workflows = saved
        else:
            self.workflows = dict(BUILT_IN_WORKFLOWS)
            _save_json(WORKFLOWS_FILE, self.workflows)

        self.triggers = _load_json(TRIGGERS_FILE, [])
        logs = _load_json(WORKFLOW_LOGS_FILE, [])
        self.execution_log = logs if isinstance(logs, list) else []

    def _save_workflows(self):
        _save_json(WORKFLOWS_FILE, self.workflows)

    def _save_triggers(self):
        _save_json(TRIGGERS_FILE, self.triggers)

    def _log_execution(self, workflow_id: str, status: str, results: list, duration: float):
        entry = {
            "workflow_id": workflow_id,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "steps_completed": len(results),
            "duration_seconds": round(duration, 2),
        }
        self.execution_log.append(entry)
        if len(self.execution_log) > 200:
            self.execution_log = self.execution_log[-200:]
        _save_json(WORKFLOW_LOGS_FILE, self.execution_log)

    # ========================
    # WORKFLOW CRUD
    # ========================

    def list_workflows(self) -> dict:
        items = []
        for wid, w in self.workflows.items():
            items.append({
                "id": wid,
                "name": w.get("name", wid),
                "icon": w.get("icon", "\U0001f504"),
                "description": w.get("description", ""),
                "steps": len(w.get("steps", [])),
                "enabled": w.get("enabled", False),
                "trigger": w.get("trigger", {}),
                "run_count": w.get("run_count", 0),
                "last_run": w.get("last_run"),
            })
        return {"workflows": items, "total": len(items)}

    def get_workflow(self, workflow_id: str) -> Optional[dict]:
        return self.workflows.get(workflow_id)

    def create_workflow(self, workflow_id: str, data: dict) -> dict:
        if workflow_id in self.workflows:
            return {"success": False, "error": f"Workflow '{workflow_id}' already exists"}
        workflow = {
            "name": data.get("name", workflow_id),
            "icon": data.get("icon", "\U0001f504"),
            "description": data.get("description", ""),
            "trigger": data.get("trigger", {}),
            "steps": data.get("steps", []),
            "enabled": data.get("enabled", True),
            "run_count": 0,
            "last_run": None,
            "created": datetime.now().isoformat(),
        }
        self.workflows[workflow_id] = workflow
        self._save_workflows()
        return {"success": True, "workflow": workflow}

    def update_workflow(self, workflow_id: str, data: dict) -> dict:
        if workflow_id not in self.workflows:
            return {"success": False, "error": f"Workflow '{workflow_id}' not found"}
        w = self.workflows[workflow_id]
        for key in ("name", "icon", "description", "trigger", "steps", "enabled"):
            if key in data:
                w[key] = data[key]
        self._save_workflows()
        return {"success": True, "workflow": w}

    def delete_workflow(self, workflow_id: str) -> dict:
        if workflow_id not in self.workflows:
            return {"success": False, "error": f"Workflow '{workflow_id}' not found"}
        del self.workflows[workflow_id]
        self._save_workflows()
        return {"success": True}

    def toggle_workflow(self, workflow_id: str, enabled: bool) -> dict:
        if workflow_id not in self.workflows:
            return {"success": False, "error": f"Not found: {workflow_id}"}
        self.workflows[workflow_id]["enabled"] = enabled
        self._save_workflows()
        return {"success": True, "enabled": enabled}

    # ========================
    # WORKFLOW EXECUTION
    # ========================

    async def execute_workflow(self, workflow_id: str, modules: dict = None, context: dict = None) -> dict:
        """Execute a workflow by running its steps sequentially."""
        w = self.workflows.get(workflow_id)
        if not w:
            return {"success": False, "error": f"Workflow '{workflow_id}' not found"}
        if not w.get("enabled", True):
            return {"success": False, "error": f"Workflow '{w['name']}' is disabled"}

        start_time = time.time()
        results = []
        step_context = dict(context or {})

        for step in w.get("steps", []):
            step_result = {"step_id": step.get("id", "?"), "description": step.get("description", ""), "status": "pending"}

            module_name = step.get("module")
            if module_name and modules and module_name in modules:
                mod = modules[module_name]
                if hasattr(mod, "enabled") and mod.enabled:
                    try:
                        result = mod.execute(step.get("description", ""), step_context)
                        step_result["status"] = "completed"
                        step_result["response"] = result.get("response", "")[:500]
                        step_context["previous_step"] = result.get("response", "")
                        step_context["step_data"] = result.get("data")
                    except Exception as e:
                        step_result["status"] = "error"
                        step_result["error"] = str(e)[:200]
                else:
                    step_result["status"] = "skipped"
                    step_result["reason"] = f"Module '{module_name}' not available"
            elif step.get("action") == "llm_generate":
                # LLM step — will be handled by caller with context
                step_result["status"] = "llm_pending"
                step_result["prompt"] = step.get("params", {}).get("prompt", "")
                step_result["context"] = step_context.get("previous_step", "")[:500]
            else:
                step_result["status"] = "skipped"
                step_result["reason"] = "No module specified"

            results.append(step_result)

        duration = time.time() - start_time
        w["run_count"] = w.get("run_count", 0) + 1
        w["last_run"] = datetime.now().isoformat()
        self._save_workflows()

        completed = sum(1 for r in results if r["status"] == "completed")
        self._log_execution(workflow_id, "completed", results, duration)

        return {
            "success": True,
            "workflow": w["name"],
            "steps_total": len(results),
            "steps_completed": completed,
            "duration": round(duration, 2),
            "results": results,
        }

    # ========================
    # TRIGGER MANAGEMENT
    # ========================

    def add_trigger(self, workflow_id: str, trigger: dict) -> dict:
        if workflow_id not in self.workflows:
            return {"success": False, "error": f"Workflow '{workflow_id}' not found"}
        trigger_entry = {
            "id": f"trig_{int(time.time())}",
            "workflow_id": workflow_id,
            "type": trigger.get("type", "time"),
            "config": trigger,
            "enabled": True,
            "created": datetime.now().isoformat(),
        }
        self.triggers.append(trigger_entry)
        self._save_triggers()
        return {"success": True, "trigger": trigger_entry}

    def list_triggers(self) -> dict:
        return {"triggers": self.triggers, "total": len(self.triggers)}

    def remove_trigger(self, trigger_id: str) -> dict:
        before = len(self.triggers)
        self.triggers = [t for t in self.triggers if t.get("id") != trigger_id]
        if len(self.triggers) < before:
            self._save_triggers()
            return {"success": True}
        return {"success": False, "error": "Trigger not found"}

    # ========================
    # EXECUTION LOG
    # ========================

    def get_execution_log(self, limit: int = 20) -> dict:
        return {"logs": self.execution_log[-limit:], "total": len(self.execution_log)}

    # ========================
    # STATS
    # ========================

    def get_stats(self) -> dict:
        total = len(self.workflows)
        enabled = sum(1 for w in self.workflows.values() if w.get("enabled"))
        total_runs = sum(w.get("run_count", 0) for w in self.workflows.values())
        return {
            "total_workflows": total,
            "enabled_workflows": enabled,
            "total_triggers": len(self.triggers),
            "total_executions": total_runs,
            "log_entries": len(self.execution_log),
        }

    # ========================
    # TEMPLATE HELPERS
    # ========================

    def get_templates(self) -> dict:
        """Return built-in workflow templates."""
        templates = {}
        for wid, w in BUILT_IN_WORKFLOWS.items():
            templates[wid] = {
                "name": w["name"],
                "icon": w["icon"],
                "description": w["description"],
                "steps": len(w["steps"]),
                "trigger": w.get("trigger", {}),
            }
        return {"templates": templates}

    def install_template(self, template_id: str) -> dict:
        """Install a built-in template as an active workflow."""
        if template_id not in BUILT_IN_WORKFLOWS:
            return {"success": False, "error": f"Template '{template_id}' not found"}
        if template_id in self.workflows:
            return {"success": False, "error": f"Workflow '{template_id}' already exists"}

        template = dict(BUILT_IN_WORKFLOWS[template_id])
        template["enabled"] = True
        template["created"] = datetime.now().isoformat()
        self.workflows[template_id] = template
        self._save_workflows()
        return {"success": True, "workflow": template}

    def reset_to_defaults(self) -> dict:
        """Reset all workflows to built-in defaults."""
        self.workflows = dict(BUILT_IN_WORKFLOWS)
        self._save_workflows()
        return {"success": True, "count": len(self.workflows)}


# Singleton
workflow_engine = WorkflowEngine()
