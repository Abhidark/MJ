"""
Zeus — Master Brain v2. Orchestrates all MJ modules.
Routes user input to the right module based on confidence scores.
Supports: parallel execution, priority routing, module chaining, execution history.
"""

import json
import asyncio
import time
import logging
from pathlib import Path
from typing import Optional, List, Tuple
from collections import deque

logger = logging.getLogger("mj.zeus")

SETTINGS_FILE = Path(__file__).parent.parent / "module_settings.json"
HISTORY_FILE = Path(__file__).parent.parent / "zeus_history.json"

CATEGORY_PRIORITY = {
    "core": 10, "system": 8, "utility": 6, "creative": 4, "lifestyle": 2,
}


class Zeus:
    def __init__(self):
        self.modules = {}
        self._load_settings()
        self.execution_history = deque(maxlen=100)
        self._load_history()

    def register(self, module):
        self.modules[module.name] = module
        saved = self._saved_settings.get(module.name, {})
        if saved:
            module.update_settings(saved)

    def _load_settings(self):
        if SETTINGS_FILE.exists():
            try:
                self._saved_settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            except Exception:
                self._saved_settings = {}
        else:
            self._saved_settings = {}

    def _save_settings(self):
        settings = {}
        for name, mod in self.modules.items():
            settings[name] = mod.get_settings()
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    def _load_history(self):
        if HISTORY_FILE.exists():
            try:
                data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
                self.execution_history = deque(data, maxlen=100)
            except Exception:
                pass

    def _save_history(self):
        try:
            HISTORY_FILE.write_text(json.dumps(list(self.execution_history), indent=2), encoding="utf-8")
        except Exception:
            pass

    def _record_execution(self, module_name, confidence, duration_ms, success, text):
        self.execution_history.append({
            "module": module_name,
            "confidence": round(confidence, 3),
            "duration_ms": round(duration_ms, 1),
            "success": success,
            "text_preview": text[:80],
            "timestamp": time.time()
        })
        self._save_history()

    def route(self, text, intent, context):
        best_module = None
        best_score = 0.0
        for name, module in self.modules.items():
            if not module.enabled:
                continue
            try:
                score = module.can_handle(text, intent, context)
                if score > best_score:
                    best_score = score
                    best_module = module
            except Exception as e:
                logger.warning(f"Module {name} routing error: {e}")
                continue
        if best_module and best_score > 0.1:
            return (best_module, best_score)
        return None

    def route_all(self, text, intent, context, min_confidence=0.3):
        matches = []
        for name, module in self.modules.items():
            if not module.enabled:
                continue
            try:
                score = module.can_handle(text, intent, context)
                if score >= min_confidence:
                    matches.append((module, score))
            except Exception:
                continue
        matches.sort(key=lambda x: (-x[1], -CATEGORY_PRIORITY.get(x[0].category, 0)))
        return matches

    async def execute_module(self, module, text, context, confidence=0.0):
        start = time.time()
        try:
            result = await module.execute_async(text, context)
            duration = (time.time() - start) * 1000
            self._record_execution(module.name, confidence, duration, True, text)
            result["_meta"] = {"module": module.name, "confidence": confidence, "duration_ms": round(duration, 1)}
            return result
        except Exception as e:
            duration = (time.time() - start) * 1000
            self._record_execution(module.name, confidence, duration, False, text)
            logger.error(f"Module {module.name} execution error: {e}")
            return {"response": f"Module {module.display_name} error: {e}", "data": None, "action": "error", "_meta": {"module": module.name, "error": str(e)}}

    async def execute_parallel(self, modules_with_scores, text, context):
        tasks = [self.execute_module(m, text, context, s) for m, s in modules_with_scores]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r if not isinstance(r, Exception) else {"response": str(r), "action": "error"} for r in results]

    async def chain_execute(self, module_names, text, context):
        chain_ctx = dict(context)
        chain_results = []
        for name in module_names:
            mod = self.modules.get(name)
            if not mod or not mod.enabled:
                continue
            result = await self.execute_module(mod, text, chain_ctx, 1.0)
            chain_results.append(result)
            chain_ctx["previous_module"] = name
            chain_ctx["previous_result"] = result.get("response", "")
            chain_ctx["chain_data"] = result.get("data")
        return {"response": chain_results[-1]["response"] if chain_results else "No modules executed.", "chain": chain_results, "action": "chain_complete"}

    def get_module(self, name):
        return self.modules.get(name)

    def get_all_modules(self):
        return [mod.info() for mod in self.modules.values()]

    def get_active_modules(self):
        return [mod for mod in self.modules.values() if mod.enabled]

    def get_modules_by_category(self, category):
        return [mod for mod in self.modules.values() if mod.category == category]

    def update_module_settings(self, module_name, settings):
        mod = self.modules.get(module_name)
        if not mod:
            return False
        mod.update_settings(settings)
        self._save_settings()
        return True

    def get_module_settings(self, module_name):
        mod = self.modules.get(module_name)
        if not mod:
            return {}
        return {"info": mod.info(), "settings": mod.get_settings_schema()}

    def get_extra_system_prompt(self):
        parts = []
        for mod in self.get_active_modules():
            addition = mod.get_system_prompt_addition()
            if addition:
                parts.append(addition)
        return "\n".join(parts)

    def get_context_for_request(self, text, context):
        parts = []
        for mod in self.get_active_modules():
            ctx = mod.get_context_for_llm(text, context)
            if ctx:
                parts.append(ctx)
        return "\n".join(parts)

    def get_execution_stats(self):
        if not self.execution_history:
            return {"total": 0, "modules": {}}
        stats = {"total": len(self.execution_history), "modules": {}}
        for entry in self.execution_history:
            name = entry["module"]
            if name not in stats["modules"]:
                stats["modules"][name] = {"count": 0, "successes": 0, "failures": 0, "total_conf": 0, "total_dur": 0}
            s = stats["modules"][name]
            s["count"] += 1
            s["successes" if entry.get("success") else "failures"] += 1
            s["total_conf"] += entry.get("confidence", 0)
            s["total_dur"] += entry.get("duration_ms", 0)
        for name, s in stats["modules"].items():
            if s["count"] > 0:
                s["avg_confidence"] = round(s["total_conf"] / s["count"], 3)
                s["avg_duration_ms"] = round(s["total_dur"] / s["count"], 1)
            del s["total_conf"]
            del s["total_dur"]
        return stats

    def get_recent_history(self, limit=20):
        return list(self.execution_history)[-limit:]
