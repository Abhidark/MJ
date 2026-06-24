"""
Multi-Agent Collaboration Engine v1 for MJ-Assistant (V20).
Pipeline orchestrator, parallel execution, peer-to-peer messaging,
agent groups, and dependency-based task graphs.
"""

import json
import time
import asyncio
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("mj.multi_agent")

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
PIPELINES_FILE = DATA_DIR / "agent_pipelines.json"
COLLAB_LOG_FILE = DATA_DIR / "agent_collab_log.json"
GROUPS_FILE = DATA_DIR / "agent_groups.json"


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
# BUILT-IN PIPELINE TEMPLATES
# ========================

BUILT_IN_PIPELINES = {
    "research_and_report": {
        "name": "Research & Report",
        "icon": "\U0001f4dd",
        "description": "Search the web, analyze results, generate a structured report",
        "stages": [
            {"id": "search", "agent": "sherlock", "action": "deep_search", "parallel": False,
             "description": "Search multiple sources for the topic"},
            {"id": "analyze", "agent": "athena", "action": "analyze", "parallel": False,
             "depends_on": ["search"], "description": "Analyze and cross-reference findings"},
            {"id": "write", "agent": "apollo", "action": "write_report", "parallel": False,
             "depends_on": ["analyze"], "description": "Write a structured report"},
        ],
    },
    "morning_intel": {
        "name": "Morning Intelligence",
        "icon": "☀️",
        "description": "Parallel fetch of weather, news, emails, tasks — then summarize",
        "stages": [
            {"id": "weather", "agent": "atlas", "action": "weather", "parallel": True,
             "description": "Get weather forecast"},
            {"id": "news", "agent": "sherlock", "action": "news", "parallel": True,
             "description": "Fetch top headlines"},
            {"id": "emails", "agent": "hermes", "action": "unread_count", "parallel": True,
             "description": "Check unread emails"},
            {"id": "tasks", "agent": "chronos", "action": "pending_tasks", "parallel": True,
             "description": "Get pending tasks"},
            {"id": "summarize", "agent": "zeus", "action": "summarize", "parallel": False,
             "depends_on": ["weather", "news", "emails", "tasks"],
             "description": "Summarize all intel into a morning briefing"},
        ],
    },
    "code_review_pipeline": {
        "name": "Code Review Pipeline",
        "icon": "\U0001f50d",
        "description": "Git diff → analyze → test → security check → report",
        "stages": [
            {"id": "diff", "agent": "hephaestus", "action": "git_diff", "parallel": False,
             "description": "Get recent git changes"},
            {"id": "analyze", "agent": "hephaestus", "action": "analyze_code", "parallel": True,
             "depends_on": ["diff"], "description": "Analyze code quality"},
            {"id": "test", "agent": "hephaestus", "action": "run_tests", "parallel": True,
             "depends_on": ["diff"], "description": "Run test suite"},
            {"id": "security", "agent": "sentinel", "action": "scan", "parallel": True,
             "depends_on": ["diff"], "description": "Security vulnerability scan"},
            {"id": "report", "agent": "apollo", "action": "write_report", "parallel": False,
             "depends_on": ["analyze", "test", "security"],
             "description": "Generate code review report"},
        ],
    },
    "content_creation": {
        "name": "Content Creation",
        "icon": "\U0001f3a8",
        "description": "Research topic → write → generate image → format",
        "stages": [
            {"id": "research", "agent": "sherlock", "action": "search", "parallel": False,
             "description": "Research the topic"},
            {"id": "write", "agent": "apollo", "action": "creative_write", "parallel": False,
             "depends_on": ["research"], "description": "Write the content"},
            {"id": "image", "agent": "apollo", "action": "generate_image", "parallel": True,
             "depends_on": ["write"], "description": "Generate supporting image"},
            {"id": "format", "agent": "apollo", "action": "format_output", "parallel": True,
             "depends_on": ["write"], "description": "Format and polish output"},
        ],
    },
}


# ========================
# PEER-TO-PEER MESSAGE BUS
# ========================

class AgentMailbox:
    """Simple peer-to-peer messaging between agents."""

    def __init__(self):
        self._mailboxes: Dict[str, List[dict]] = {}
        self._subscribers: Dict[str, List[callable]] = {}
        self._lock = threading.Lock()

    def send(self, from_agent: str, to_agent: str, message: str, data: Any = None) -> dict:
        with self._lock:
            if to_agent not in self._mailboxes:
                self._mailboxes[to_agent] = []
            msg = {
                "id": f"msg_{int(time.time() * 1000)}",
                "from": from_agent,
                "to": to_agent,
                "message": message,
                "data": data,
                "timestamp": datetime.now().isoformat(),
                "read": False,
            }
            self._mailboxes[to_agent].append(msg)
            if len(self._mailboxes[to_agent]) > 100:
                self._mailboxes[to_agent] = self._mailboxes[to_agent][-100:]
            return {"success": True, "message_id": msg["id"]}

    def receive(self, agent_name: str, unread_only: bool = True) -> List[dict]:
        with self._lock:
            msgs = self._mailboxes.get(agent_name, [])
            if unread_only:
                result = [m for m in msgs if not m.get("read")]
            else:
                result = list(msgs)
            for m in result:
                m["read"] = True
            return result

    def broadcast(self, from_agent: str, message: str, data: Any = None) -> dict:
        with self._lock:
            count = 0
            msg_base = {
                "from": from_agent,
                "message": message,
                "data": data,
                "timestamp": datetime.now().isoformat(),
                "read": False,
            }
            for agent in self._mailboxes:
                if agent != from_agent:
                    msg = {**msg_base, "id": f"msg_{int(time.time() * 1000)}_{count}", "to": agent}
                    self._mailboxes[agent].append(msg)
                    count += 1
            return {"success": True, "sent_to": count}

    def get_stats(self) -> dict:
        with self._lock:
            stats = {}
            for agent, msgs in self._mailboxes.items():
                unread = sum(1 for m in msgs if not m.get("read"))
                stats[agent] = {"total": len(msgs), "unread": unread}
            return stats


# ========================
# AGENT GROUPS
# ========================

class AgentGroupManager:
    """Organize agents into collaborative groups for specific tasks."""

    def __init__(self):
        self.groups: Dict[str, dict] = {}
        self._load()

    def _load(self):
        self.groups = _load_json(GROUPS_FILE, {})

    def _save(self):
        _save_json(GROUPS_FILE, self.groups)

    def create_group(self, group_id: str, name: str, agents: List[str], purpose: str = "") -> dict:
        if group_id in self.groups:
            return {"success": False, "error": f"Group '{group_id}' already exists"}
        self.groups[group_id] = {
            "name": name,
            "agents": agents,
            "purpose": purpose,
            "created": datetime.now().isoformat(),
            "active": True,
        }
        self._save()
        return {"success": True, "group": self.groups[group_id]}

    def list_groups(self) -> dict:
        return {"groups": [{"id": gid, **g} for gid, g in self.groups.items()], "total": len(self.groups)}

    def get_group(self, group_id: str) -> Optional[dict]:
        return self.groups.get(group_id)

    def delete_group(self, group_id: str) -> dict:
        if group_id not in self.groups:
            return {"success": False, "error": "Group not found"}
        del self.groups[group_id]
        self._save()
        return {"success": True}

    def add_agent(self, group_id: str, agent: str) -> dict:
        g = self.groups.get(group_id)
        if not g:
            return {"success": False, "error": "Group not found"}
        if agent not in g["agents"]:
            g["agents"].append(agent)
            self._save()
        return {"success": True, "agents": g["agents"]}

    def remove_agent(self, group_id: str, agent: str) -> dict:
        g = self.groups.get(group_id)
        if not g:
            return {"success": False, "error": "Group not found"}
        g["agents"] = [a for a in g["agents"] if a != agent]
        self._save()
        return {"success": True, "agents": g["agents"]}


# ========================
# PIPELINE ORCHESTRATOR
# ========================

class PipelineOrchestrator:
    """
    Runs multi-agent pipelines with dependency resolution,
    parallel stage execution, and context passing.
    """

    def __init__(self):
        self.pipelines: Dict[str, dict] = {}
        self.execution_log: List[dict] = []
        self.mailbox = AgentMailbox()
        self.groups = AgentGroupManager()
        self._executor = ThreadPoolExecutor(max_workers=6)
        self._load()

    def _load(self):
        saved = _load_json(PIPELINES_FILE, {})
        if saved:
            self.pipelines = saved
        else:
            self.pipelines = {k: {**v, "run_count": 0, "last_run": None} for k, v in BUILT_IN_PIPELINES.items()}
            _save_json(PIPELINES_FILE, self.pipelines)

        logs = _load_json(COLLAB_LOG_FILE, [])
        self.execution_log = logs if isinstance(logs, list) else []

    def _save_pipelines(self):
        _save_json(PIPELINES_FILE, self.pipelines)

    def _log(self, pipeline_id: str, status: str, results: list, duration: float):
        entry = {
            "pipeline_id": pipeline_id,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "stages_completed": len([r for r in results if r.get("status") == "completed"]),
            "stages_total": len(results),
            "duration_seconds": round(duration, 2),
        }
        self.execution_log.append(entry)
        if len(self.execution_log) > 200:
            self.execution_log = self.execution_log[-200:]
        _save_json(COLLAB_LOG_FILE, self.execution_log)

    # ---- PIPELINE CRUD ----

    def list_pipelines(self) -> dict:
        items = []
        for pid, p in self.pipelines.items():
            items.append({
                "id": pid,
                "name": p.get("name", pid),
                "icon": p.get("icon", "\U0001f504"),
                "description": p.get("description", ""),
                "stages": len(p.get("stages", [])),
                "run_count": p.get("run_count", 0),
                "last_run": p.get("last_run"),
            })
        return {"pipelines": items, "total": len(items)}

    def get_pipeline(self, pipeline_id: str) -> Optional[dict]:
        return self.pipelines.get(pipeline_id)

    def create_pipeline(self, pipeline_id: str, data: dict) -> dict:
        if pipeline_id in self.pipelines:
            return {"success": False, "error": f"Pipeline '{pipeline_id}' already exists"}
        pipeline = {
            "name": data.get("name", pipeline_id),
            "icon": data.get("icon", "\U0001f504"),
            "description": data.get("description", ""),
            "stages": data.get("stages", []),
            "run_count": 0,
            "last_run": None,
            "created": datetime.now().isoformat(),
        }
        self.pipelines[pipeline_id] = pipeline
        self._save_pipelines()
        return {"success": True, "pipeline": pipeline}

    def delete_pipeline(self, pipeline_id: str) -> dict:
        if pipeline_id not in self.pipelines:
            return {"success": False, "error": "Pipeline not found"}
        del self.pipelines[pipeline_id]
        self._save_pipelines()
        return {"success": True}

    # ---- DEPENDENCY RESOLUTION ----

    def _resolve_execution_order(self, stages: List[dict]) -> List[List[dict]]:
        """
        Topological sort of stages into execution waves.
        Stages in the same wave can run in parallel.
        """
        stage_map = {s["id"]: s for s in stages}
        completed = set()
        waves = []

        remaining = list(stages)
        max_iterations = len(stages) + 1

        for _ in range(max_iterations):
            if not remaining:
                break
            wave = []
            still_remaining = []
            for stage in remaining:
                deps = stage.get("depends_on", [])
                if all(d in completed for d in deps):
                    wave.append(stage)
                else:
                    still_remaining.append(stage)
            if not wave:
                # Circular dependency — force remaining into one wave
                wave = still_remaining
                still_remaining = []
            waves.append(wave)
            for s in wave:
                completed.add(s["id"])
            remaining = still_remaining

        return waves

    # ---- EXECUTION ----

    def _execute_stage(self, stage: dict, modules: dict, context: dict) -> dict:
        """Execute a single pipeline stage."""
        result = {
            "stage_id": stage["id"],
            "agent": stage.get("agent", "unknown"),
            "description": stage.get("description", ""),
            "status": "pending",
        }

        agent_name = stage.get("agent")
        if agent_name and modules and agent_name in modules:
            mod = modules[agent_name]
            if hasattr(mod, "enabled") and mod.enabled:
                try:
                    resp = mod.execute(stage.get("description", ""), context)
                    result["status"] = "completed"
                    result["response"] = resp.get("response", "")[:500]
                    result["data"] = resp.get("data")
                except Exception as e:
                    result["status"] = "error"
                    result["error"] = str(e)[:200]
            else:
                result["status"] = "skipped"
                result["reason"] = f"Agent '{agent_name}' not available"
        else:
            result["status"] = "simulated"
            result["response"] = f"[Simulated] {stage.get('description', stage['id'])}"

        return result

    async def run_pipeline(self, pipeline_id: str, modules: dict = None, context: dict = None) -> dict:
        """Run a pipeline with dependency resolution and parallel execution."""
        pipeline = self.pipelines.get(pipeline_id)
        if not pipeline:
            return {"success": False, "error": f"Pipeline '{pipeline_id}' not found"}

        start_time = time.time()
        stages = pipeline.get("stages", [])
        waves = self._resolve_execution_order(stages)
        all_results = []
        shared_context = dict(context or {})

        for wave_idx, wave in enumerate(waves):
            parallel_stages = [s for s in wave if s.get("parallel", False)]
            sequential_stages = [s for s in wave if not s.get("parallel", False)]

            # Run parallel stages concurrently
            if parallel_stages:
                futures = {}
                for stage in parallel_stages:
                    future = self._executor.submit(self._execute_stage, stage, modules, dict(shared_context))
                    futures[future] = stage["id"]

                for future in as_completed(futures):
                    result = future.result()
                    all_results.append(result)
                    if result.get("response"):
                        shared_context[f"stage_{result['stage_id']}"] = result["response"]

            # Run sequential stages in order
            for stage in sequential_stages:
                result = self._execute_stage(stage, modules, shared_context)
                all_results.append(result)
                if result.get("response"):
                    shared_context[f"stage_{result['stage_id']}"] = result["response"]

        duration = time.time() - start_time
        pipeline["run_count"] = pipeline.get("run_count", 0) + 1
        pipeline["last_run"] = datetime.now().isoformat()
        self._save_pipelines()

        completed = sum(1 for r in all_results if r["status"] in ("completed", "simulated"))
        self._log(pipeline_id, "completed", all_results, duration)

        return {
            "success": True,
            "pipeline": pipeline["name"],
            "waves": len(waves),
            "stages_total": len(all_results),
            "stages_completed": completed,
            "duration": round(duration, 2),
            "results": all_results,
        }

    # ---- STATS ----

    def get_stats(self) -> dict:
        total_runs = sum(p.get("run_count", 0) for p in self.pipelines.values())
        return {
            "total_pipelines": len(self.pipelines),
            "total_runs": total_runs,
            "total_groups": len(self.groups.groups),
            "mailbox_stats": self.mailbox.get_stats(),
            "log_entries": len(self.execution_log),
        }

    def get_logs(self, limit: int = 20) -> dict:
        return {"logs": self.execution_log[-limit:], "total": len(self.execution_log)}

    def get_templates(self) -> dict:
        templates = {}
        for pid, p in BUILT_IN_PIPELINES.items():
            templates[pid] = {
                "name": p["name"],
                "icon": p["icon"],
                "description": p["description"],
                "stages": len(p["stages"]),
            }
        return {"templates": templates}

    def install_template(self, template_id: str) -> dict:
        if template_id not in BUILT_IN_PIPELINES:
            return {"success": False, "error": f"Template '{template_id}' not found"}
        if template_id in self.pipelines:
            return {"success": False, "error": f"Pipeline '{template_id}' already exists"}
        tpl = {**BUILT_IN_PIPELINES[template_id], "run_count": 0, "last_run": None,
               "created": datetime.now().isoformat()}
        self.pipelines[template_id] = tpl
        self._save_pipelines()
        return {"success": True, "pipeline": tpl}

    def reset_to_defaults(self) -> dict:
        self.pipelines = {k: {**v, "run_count": 0, "last_run": None} for k, v in BUILT_IN_PIPELINES.items()}
        self._save_pipelines()
        return {"success": True, "count": len(self.pipelines)}


# Singleton
multi_agent = PipelineOrchestrator()
