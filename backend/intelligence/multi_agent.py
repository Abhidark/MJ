"""
Multi-Agent Collaboration Engine v1 for MJ-Assistant (V20).
Pipeline orchestrator, parallel execution, peer-to-peer messaging,
agent groups, and dependency-based task graphs.
"""

import os
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
# REAL LLM STAGE EXECUTOR
# ========================
# Used when a pipeline stage has no matching registered agent module
# (e.g. the "zeus" summarize stage, or an agent that failed to load).
# Instead of returning a "[Simulated]" placeholder, we run real inference
# via Groq (cloud — works on laptop) and fall back to local Ollama.

import httpx as _httpx

OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"


def _llm_complete_sync(prompt: str, system: str = "", max_tokens: int = 700,
                       timeout: float = 30.0) -> Optional[str]:
    """
    Synchronous LLM completion. Tries Groq first (cloud, fast, no GPU),
    then local Ollama. Returns generated text, or None if no provider works.
    Safe to call from worker threads and (via asyncio.to_thread) from async code.
    """
    # ---- 1. Groq (cloud) ----
    try:
        from intelligence.groq_provider import _load_api_key, GROQ_API_URL, GROQ_MODELS
        key = _load_api_key()
        if key:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            payload = {
                "model": GROQ_MODELS[0],
                "messages": messages,
                "temperature": 0.6,
                "max_tokens": max_tokens,
                "stream": False,
            }
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            with _httpx.Client(timeout=timeout) as client:
                resp = client.post(GROQ_API_URL, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if text and text.strip():
                        return text.strip()
    except Exception as e:
        logger.debug(f"Groq stage completion failed: {e}")

    # ---- 2. Ollama (local GPU) ----
    try:
        full_prompt = (f"{system}\n\n{prompt}" if system else prompt)
        model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
        with _httpx.Client(timeout=timeout) as client:
            resp = client.post(OLLAMA_GENERATE_URL, json={
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": {"num_predict": max_tokens},
            })
            if resp.status_code == 200:
                text = resp.json().get("response", "")
                if text and text.strip():
                    return text.strip()
    except Exception as e:
        logger.debug(f"Ollama stage completion failed: {e}")

    return None


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

    def _build_stage_input(self, stage: dict, context: dict) -> str:
        """Build the natural-language input for a stage from its action,
        description, and any upstream stage outputs in the shared context."""
        action = stage.get("action", "")
        description = stage.get("description", "") or stage.get("id", "")
        text = description
        if action:
            text = f"{description} (action: {action})"

        # Append upstream results so the stage has the data it depends on
        upstream = []
        for dep in stage.get("depends_on", []):
            prior = context.get(f"stage_{dep}")
            if prior:
                upstream.append(f"- {dep}: {str(prior)[:800]}")
        if upstream:
            text += "\n\nInput from previous stages:\n" + "\n".join(upstream)
        return text

    def _execute_via_llm(self, stage: dict, agent_name: str, stage_input: str) -> dict:
        """Run a stage with a real LLM, role-played as the target agent.
        Returns a result dict (status 'completed' with source 'llm', or 'simulated')."""
        result = {
            "stage_id": stage["id"],
            "agent": agent_name or "llm",
            "description": stage.get("description", ""),
            "status": "pending",
        }
        system = (
            f"You are '{agent_name or 'an AI agent'}', a specialized agent inside the MJ "
            f"multi-agent assistant. Perform the requested step concisely and concretely. "
            f"Action requested: {stage.get('action', 'process')}. "
            f"Return only the useful result of this step — no preamble."
        )
        text = _llm_complete_sync(stage_input, system=system, max_tokens=700)
        if text:
            result["status"] = "completed"
            result["source"] = "llm"
            result["response"] = text[:1500]
        else:
            # Last resort only when no LLM provider is reachable at all
            result["status"] = "simulated"
            result["source"] = "placeholder"
            result["response"] = f"[Simulated] {stage.get('description', stage['id'])}"
            result["reason"] = "No agent module and no LLM provider (Groq/Ollama) available"
        return result

    def _execute_stage(self, stage: dict, modules: dict, context: dict) -> dict:
        """Execute a single pipeline stage.

        Resolution order:
          1. Real registered agent module (if enabled)
          2. Capability-based remap to another registered module that can do it
          3. Real LLM inference (role-played as the agent)  ← no more fake [Simulated]
          4. Placeholder simulation (only if no LLM provider is reachable)
        """
        result = {
            "stage_id": stage["id"],
            "agent": stage.get("agent", "unknown"),
            "description": stage.get("description", ""),
            "status": "pending",
        }

        agent_name = stage.get("agent")
        stage_input = self._build_stage_input(stage, context)

        # ---- 1. Direct registered module ----
        if agent_name and modules and agent_name in modules:
            mod = modules[agent_name]
            if hasattr(mod, "enabled") and mod.enabled:
                try:
                    resp = mod.execute(stage_input, context)
                    result["status"] = "completed"
                    result["source"] = "module"
                    result["response"] = (resp.get("response", "") or "")[:1500]
                    result["data"] = resp.get("data")
                    return result
                except Exception as e:
                    result["status"] = "error"
                    result["error"] = str(e)[:200]
                    return result
            # Module exists but disabled → fall through to capability remap / LLM

        # ---- 2. Capability-based remap to a capable registered module ----
        if modules:
            wanted_caps = self.AGENT_CAPABILITIES.get((agent_name or "").lower(), [])
            action = (stage.get("action") or "").lower()
            for cap in ([action] + wanted_caps):
                if not cap:
                    continue
                hit = self.find_capable_agent(cap).get("agents", [])
                for cand in hit:
                    cname = cand["agent"]
                    if cname in modules and cname != agent_name:
                        cmod = modules[cname]
                        if getattr(cmod, "enabled", False):
                            try:
                                resp = cmod.execute(stage_input, context)
                                result["status"] = "completed"
                                result["source"] = "module_remap"
                                result["agent"] = cname
                                result["original_agent"] = agent_name
                                result["response"] = (resp.get("response", "") or "")[:1500]
                                result["data"] = resp.get("data")
                                return result
                            except Exception:
                                pass  # try next candidate / fall through to LLM

        # ---- 3 & 4. Real LLM, else placeholder ----
        return self._execute_via_llm(stage, agent_name, stage_input)

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

            # Run sequential stages in order. Offload to a worker thread so the
            # synchronous LLM/module calls don't block the asyncio event loop.
            for stage in sequential_stages:
                result = await asyncio.to_thread(
                    self._execute_stage, stage, modules, dict(shared_context)
                )
                all_results.append(result)
                if result.get("response"):
                    shared_context[f"stage_{result['stage_id']}"] = result["response"]

        duration = time.time() - start_time
        pipeline["run_count"] = pipeline.get("run_count", 0) + 1
        pipeline["last_run"] = datetime.now().isoformat()
        self._save_pipelines()

        # Real completions = executed by a module or a real LLM.
        completed = sum(1 for r in all_results if r["status"] == "completed")
        simulated = sum(1 for r in all_results if r["status"] == "simulated")
        errored = sum(1 for r in all_results if r["status"] == "error")
        overall = "completed" if errored == 0 else "partial"
        self._log(pipeline_id, overall, all_results, duration)

        return {
            "success": True,
            "pipeline": pipeline["name"],
            "waves": len(waves),
            "stages_total": len(all_results),
            "stages_completed": completed,
            "stages_simulated": simulated,
            "stages_errored": errored,
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

    # ========================
    # REAL-TIME AGENT STATUS (V20 → 80%+)
    # ========================

    _agent_status: dict = {}

    def update_agent_status(self, agent_name: str, status: str, detail: str = "") -> dict:
        """Update real-time status for an agent."""
        self._agent_status[agent_name] = {
            "status": status,  # idle, running, waiting, error
            "detail": detail,
            "updated": datetime.now().isoformat(),
        }
        return {"updated": True, "agent": agent_name, "status": status}

    def get_agent_statuses(self) -> dict:
        return {"agents": self._agent_status, "total": len(self._agent_status)}

    # ========================
    # CONFLICT RESOLUTION (V20 → 80%+)
    # ========================

    _resource_locks: dict = {}

    def acquire_resource(self, agent_name: str, resource: str, timeout: float = 30.0) -> dict:
        """Agent requests exclusive access to a resource."""
        now = time.time()
        lock = self._resource_locks.get(resource)
        if lock and lock.get("agent") != agent_name:
            # Check if lock expired
            if now - lock.get("acquired_at", 0) < timeout:
                return {
                    "acquired": False, "resource": resource,
                    "held_by": lock["agent"],
                    "since": lock.get("acquired_at", 0),
                }
        self._resource_locks[resource] = {
            "agent": agent_name, "acquired_at": now,
        }
        return {"acquired": True, "resource": resource, "agent": agent_name}

    def release_resource(self, agent_name: str, resource: str) -> dict:
        lock = self._resource_locks.get(resource)
        if lock and lock.get("agent") == agent_name:
            del self._resource_locks[resource]
            return {"released": True, "resource": resource}
        return {"released": False, "reason": "Not held by this agent"}

    def get_resource_locks(self) -> dict:
        return {"locks": self._resource_locks, "total": len(self._resource_locks)}

    def resolve_conflict(self, agents: list, resource: str, strategy: str = "priority") -> dict:
        """Resolve conflict between agents for a resource."""
        if not agents:
            return {"error": "No agents provided"}

        # Priority order based on agent category
        PRIORITY = {"zeus": 0, "sentinel": 1, "athena": 2, "hermes": 3, "hephaestus": 4,
                     "chronos": 5, "mnemosyne": 6, "apollo": 7, "ares": 8, "argus": 9}

        if strategy == "priority":
            winner = min(agents, key=lambda a: PRIORITY.get(a.lower(), 50))
        elif strategy == "round_robin":
            # Pick the agent that hasn't had access recently
            locks_count = {}
            for lock in self._resource_locks.values():
                a = lock.get("agent", "")
                locks_count[a] = locks_count.get(a, 0) + 1
            winner = min(agents, key=lambda a: locks_count.get(a, 0))
        else:
            winner = agents[0]

        self.acquire_resource(winner, resource)
        return {"winner": winner, "strategy": strategy, "resource": resource, "contestants": agents}

    # ========================
    # COORDINATION PROTOCOL (V20 → 80%+)
    # ========================

    _coordination_tasks: list = []

    def request_coordination(self, requesting_agent: str, target_agents: list, task: str, data: dict = None) -> dict:
        """Agent requests coordination with other agents for a task."""
        coord = {
            "id": f"coord_{int(time.time())}",
            "requester": requesting_agent,
            "targets": target_agents,
            "task": task,
            "data": data or {},
            "status": "pending",
            "responses": {},
            "created": datetime.now().isoformat(),
        }
        self._coordination_tasks.append(coord)
        # Auto-send mail to targets
        for target in target_agents:
            self.mailbox.send(requesting_agent, target, f"[COORD] {task}")
        return {"success": True, "coordination": coord}

    def respond_coordination(self, coord_id: str, agent: str, response: str, accept: bool = True) -> dict:
        for coord in self._coordination_tasks:
            if coord["id"] == coord_id:
                coord["responses"][agent] = {"response": response, "accept": accept, "at": datetime.now().isoformat()}
                # Check if all responded
                if len(coord["responses"]) >= len(coord["targets"]):
                    all_accept = all(r.get("accept") for r in coord["responses"].values())
                    coord["status"] = "accepted" if all_accept else "partial"
                return {"success": True, "coordination": coord}
        return {"error": "Coordination request not found"}

    def get_coordination_tasks(self, limit: int = 20) -> dict:
        return {"tasks": self._coordination_tasks[-limit:], "total": len(self._coordination_tasks)}

    # ========================
    # LOAD BALANCING & HEALTH (V20 → 95%)
    # ========================

    _agent_load: dict = {}
    _agent_health: dict = {}
    HEALTH_FILE = DATA_DIR / "agent_health.json"

    def update_agent_load(self, agent: str, active_tasks: int = 0, capacity: int = 10) -> dict:
        """Update load info for an agent."""
        self._agent_load[agent] = {
            "active_tasks": active_tasks,
            "capacity": capacity,
            "utilization_pct": round(active_tasks / max(capacity, 1) * 100, 1),
            "updated": datetime.now().isoformat(),
        }
        return {"success": True, "agent": agent, "load": self._agent_load[agent]}

    def get_least_loaded(self, agents: list = None) -> dict:
        """Return the agent with lowest utilization."""
        candidates = agents or list(self._agent_load.keys())
        if not candidates:
            return {"agent": None, "reason": "No agents registered"}

        best = None
        best_util = 999
        for a in candidates:
            load = self._agent_load.get(a, {"utilization_pct": 0})
            if load.get("utilization_pct", 0) < best_util:
                best_util = load["utilization_pct"]
                best = a

        return {"agent": best, "utilization_pct": best_util}

    def get_load_report(self) -> dict:
        """Get full load balancing report."""
        return {
            "agents": self._agent_load,
            "total_active": sum(l.get("active_tasks", 0) for l in self._agent_load.values()),
            "avg_utilization": round(
                sum(l.get("utilization_pct", 0) for l in self._agent_load.values())
                / max(len(self._agent_load), 1), 1
            ),
            "overloaded": [a for a, l in self._agent_load.items() if l.get("utilization_pct", 0) > 80],
        }

    def report_health(self, agent: str, status: str = "healthy", error: str = "") -> dict:
        """Agent health check-in."""
        self._agent_health[agent] = {
            "status": status,  # healthy, degraded, down
            "error": error,
            "last_heartbeat": datetime.now().isoformat(),
            "consecutive_failures": 0 if status == "healthy" else
                self._agent_health.get(agent, {}).get("consecutive_failures", 0) + 1,
        }
        self._save_health()
        return {"success": True, "agent": agent, "health": self._agent_health[agent]}

    def get_health_report(self) -> dict:
        """Get health status of all agents."""
        healthy = sum(1 for h in self._agent_health.values() if h.get("status") == "healthy")
        degraded = sum(1 for h in self._agent_health.values() if h.get("status") == "degraded")
        down = sum(1 for h in self._agent_health.values() if h.get("status") == "down")
        return {
            "agents": self._agent_health,
            "summary": {"healthy": healthy, "degraded": degraded, "down": down},
            "overall": "healthy" if down == 0 and degraded == 0 else ("degraded" if down == 0 else "unhealthy"),
        }

    def redistribute_tasks(self, failed_agent: str) -> dict:
        """Redistribute tasks from a failed agent to healthy ones."""
        healthy = [a for a, h in self._agent_health.items()
                   if h.get("status") == "healthy" and a != failed_agent]
        if not healthy:
            return {"success": False, "error": "No healthy agents available"}

        failed_tasks = self._agent_load.get(failed_agent, {}).get("active_tasks", 0)
        per_agent = max(1, failed_tasks // len(healthy))
        redistribution = {}

        for i, agent in enumerate(healthy):
            assigned = min(per_agent, failed_tasks)
            redistribution[agent] = assigned
            failed_tasks -= assigned
            if failed_tasks <= 0:
                break

        # Clear failed agent load
        if failed_agent in self._agent_load:
            self._agent_load[failed_agent]["active_tasks"] = 0

        return {
            "success": True,
            "failed_agent": failed_agent,
            "redistributed_to": redistribution,
            "total_redistributed": sum(redistribution.values()),
        }

    def _save_health(self):
        try:
            _save_json(self.HEALTH_FILE, self._agent_health)
        except Exception:
            pass

    # ========================
    # LIVE ORCHESTRATION ENGINE (V20 → 100%)
    # ========================

    _orchestration_state: dict = {}
    ORCHESTRATION_FILE = DATA_DIR / "orchestration_state.json"

    def start_orchestration(self, name: str, agents: list, strategy: str = "sequential") -> dict:
        """Start a live orchestration session."""
        oid = f"orch_{int(time.time())}"
        self._orchestration_state[oid] = {
            "id": oid,
            "name": name,
            "agents": agents,
            "strategy": strategy,  # sequential, parallel, round_robin, priority
            "status": "running",
            "started": datetime.now().isoformat(),
            "current_agent": agents[0] if agents else None,
            "completed_agents": [],
            "results": {},
            "errors": [],
        }
        self._save_orchestration()
        return {"success": True, "orchestration_id": oid, "status": "running"}

    def advance_orchestration(self, orch_id: str, agent: str, result: dict = None,
                               error: str = "") -> dict:
        """Advance orchestration to next agent."""
        orch = self._orchestration_state.get(orch_id)
        if not orch:
            return {"error": "Orchestration not found"}

        orch["completed_agents"].append(agent)
        if result:
            orch["results"][agent] = result
        if error:
            orch["errors"].append({"agent": agent, "error": error})

        remaining = [a for a in orch["agents"] if a not in orch["completed_agents"]]
        if remaining:
            orch["current_agent"] = remaining[0]
            orch["status"] = "running"
        else:
            orch["current_agent"] = None
            orch["status"] = "completed"
            orch["completed_at"] = datetime.now().isoformat()

        self._save_orchestration()
        return {"success": True, "status": orch["status"], "next_agent": orch["current_agent"]}

    def get_orchestration(self, orch_id: str = "") -> dict:
        if orch_id:
            return self._orchestration_state.get(orch_id, {"error": "Not found"})
        return {"orchestrations": list(self._orchestration_state.values())[-10:]}

    def stop_orchestration(self, orch_id: str) -> dict:
        orch = self._orchestration_state.get(orch_id)
        if not orch:
            return {"error": "Not found"}
        orch["status"] = "stopped"
        orch["completed_at"] = datetime.now().isoformat()
        self._save_orchestration()
        return {"success": True}

    def _save_orchestration(self):
        try:
            _save_json(self.ORCHESTRATION_FILE, self._orchestration_state)
        except Exception:
            pass

    # ========================
    # AGENT CAPABILITY REGISTRY (V20 → 100%)
    # ========================

    _capabilities: dict = {}

    AGENT_CAPABILITIES = {
        "zeus": ["planning", "routing", "intent_detection", "task_breakdown"],
        "hermes": ["email", "messaging", "notifications", "webhooks"],
        "athena": ["search", "rag", "research", "pdf", "knowledge_graph"],
        "hephaestus": ["coding", "git", "debugging", "testing", "cicd"],
        "apollo": ["image_gen", "writing", "video", "ui_mockup", "presentation"],
        "ares": ["desktop_control", "keyboard", "mouse", "browser"],
        "argus": ["ocr", "camera", "object_detection", "screen_ai"],
        "mnemosyne": ["memory", "episodic", "preferences", "knowledge_base"],
        "chronos": ["calendar", "reminders", "planning", "habits"],
        "sentinel": ["security", "encryption", "audit", "permissions"],
    }

    def register_capability(self, agent: str, capabilities: list) -> dict:
        self._capabilities[agent] = {
            "capabilities": capabilities,
            "registered": datetime.now().isoformat(),
        }
        return {"success": True, "agent": agent, "capabilities": capabilities}

    def find_capable_agent(self, capability: str) -> dict:
        """Find agents that can handle a capability."""
        matches = []
        # Check registered first
        for agent, info in self._capabilities.items():
            if capability in info.get("capabilities", []):
                matches.append({"agent": agent, "source": "registered"})

        # Check defaults
        for agent, caps in self.AGENT_CAPABILITIES.items():
            if capability in caps and agent not in [m["agent"] for m in matches]:
                matches.append({"agent": agent, "source": "default"})

        return {"capability": capability, "agents": matches, "count": len(matches)}

    def get_all_capabilities(self) -> dict:
        merged = dict(self.AGENT_CAPABILITIES)
        for agent, info in self._capabilities.items():
            merged[agent] = info.get("capabilities", [])
        return {"capabilities": merged, "total_agents": len(merged)}

    def assign_task_to_best(self, task_type: str, required_caps: list) -> dict:
        """Find the best agent for a task based on required capabilities + load."""
        scores = {}
        all_caps = self.get_all_capabilities()["capabilities"]

        for agent, caps in all_caps.items():
            cap_match = sum(1 for c in required_caps if c in caps)
            if cap_match == 0:
                continue
            load = self._agent_load.get(agent, {}).get("utilization_pct", 0)
            health = self._agent_health.get(agent, {}).get("status", "healthy")
            health_penalty = 0 if health == "healthy" else (0.3 if health == "degraded" else 1.0)
            score = (cap_match / max(len(required_caps), 1)) - (load / 200) - health_penalty
            scores[agent] = round(score, 3)

        if not scores:
            return {"error": "No capable agent found", "required": required_caps}

        best = max(scores, key=scores.get)
        return {
            "assigned_to": best,
            "score": scores[best],
            "task_type": task_type,
            "all_scores": scores,
        }


# Singleton
multi_agent = PipelineOrchestrator()
