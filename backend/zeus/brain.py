"""
Zeus — Master Brain v3. Orchestrates all MJ modules.
Routes user input to the right module based on confidence scores.
Supports: intent classification, task planning, error recovery,
parallel execution, priority routing, module chaining, execution history.
"""

import json
import asyncio
import time
import logging
import re
import httpx
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from collections import deque

logger = logging.getLogger("mj.zeus")

SETTINGS_FILE = Path(__file__).parent.parent / "module_settings.json"
HISTORY_FILE = Path(__file__).parent.parent / "zeus_history.json"
WORKFLOWS_FILE = Path(__file__).parent.parent / "zeus_workflows.json"
OLLAMA_URL = "http://localhost:11434/api/chat"

CATEGORY_PRIORITY = {
    "core": 10, "system": 8, "utility": 6, "creative": 4, "lifestyle": 2,
}

# Intent categories that Zeus can classify
INTENT_CATEGORIES = [
    "greeting", "farewell", "question", "command", "creative_writing",
    "code_help", "web_search", "file_operation", "system_control",
    "reminder", "email", "image_generation", "knowledge_query",
    "git_operation", "math_calculation", "translation", "summarization",
    "conversation", "unknown"
]

# Fast regex patterns for instant intent detection (no LLM needed)
FAST_INTENT_PATTERNS = {
    "greeting": re.compile(
        r"^(hi|hello|hey|namaste|kya hal|good morning|good evening|howdy|sup|yo)\b",
        re.IGNORECASE
    ),
    "farewell": re.compile(
        r"^(bye|goodbye|good night|alvida|see you|take care|cya)\b",
        re.IGNORECASE
    ),
    "reminder": re.compile(
        r"(remind|yaad|timer|alarm|baad|minutes? me|hours? me|baje)",
        re.IGNORECASE
    ),
    "email": re.compile(
        r"(send\s+email|email\s+bhej|mail\s+kar|compose\s+email|write\s+email|inbox)",
        re.IGNORECASE
    ),
    "image_generation": re.compile(
        r"(generate\s+image|create\s+image|draw|make\s+a?\s*(picture|image|art|photo)|image\s+bana)",
        re.IGNORECASE
    ),
    "git_operation": re.compile(
        r"(git\s+(status|log|diff|commit|push|pull|branch|checkout|merge|stash|clone))",
        re.IGNORECASE
    ),
    "system_control": re.compile(
        r"(open\s+\w+|close\s+\w+|launch|shutdown|restart|volume|brightness|screenshot|screen\s+record)",
        re.IGNORECASE
    ),
    "file_operation": re.compile(
        r"(create\s+file|delete\s+file|move\s+file|copy\s+file|rename|list\s+files|folder|directory)",
        re.IGNORECASE
    ),
    "web_search": re.compile(
        r"(search\s+(for|about)|google|look\s+up|find\s+info|what\s+is\s+the\s+latest|news\s+about|current)",
        re.IGNORECASE
    ),
    "math_calculation": re.compile(
        r"(calculate|compute|solve|what\s+is\s+\d|how\s+much\s+is|\d+\s*[\+\-\*\/\^]\s*\d+)",
        re.IGNORECASE
    ),
    "code_help": re.compile(
        r"(write\s+(a\s+)?(code|function|script|program|class)|debug|fix\s+(this|my)\s+code|code\s+likh|implement)",
        re.IGNORECASE
    ),
    "knowledge_query": re.compile(
        r"(search\s+(my\s+)?(docs|documents|knowledge|notes|files)|in\s+my\s+(knowledge|docs)|kb\s+search)",
        re.IGNORECASE
    ),
}


class Zeus:
    def __init__(self):
        self.modules = {}
        self._load_settings()
        self.execution_history = deque(maxlen=100)
        self._load_history()
        self.workflows = {}
        self._load_workflows()
        self._intent_cache = {}  # LRU-style cache for recent intents
        self._cache_max = 50

    # ========================
    # MODULE REGISTRATION
    # ========================

    def register(self, module):
        self.modules[module.name] = module
        saved = self._saved_settings.get(module.name, {})
        if saved:
            module.update_settings(saved)

    # ========================
    # INTENT CLASSIFICATION
    # ========================

    def classify_intent_fast(self, text: str) -> Optional[str]:
        """Fast regex-based intent classification. Returns intent or None if ambiguous."""
        text_lower = text.strip().lower()

        # Check cache first
        cache_key = text_lower[:100]
        if cache_key in self._intent_cache:
            return self._intent_cache[cache_key]

        for intent, pattern in FAST_INTENT_PATTERNS.items():
            if pattern.search(text_lower):
                self._cache_intent(cache_key, intent)
                return intent

        # Simple heuristics for common patterns
        if text_lower.endswith("?") or text_lower.startswith(("what", "who", "where", "when", "why", "how", "kya", "kaun", "kab", "kaise", "kahan")):
            self._cache_intent(cache_key, "question")
            return "question"

        return None

    async def classify_intent_llm(self, text: str, model: str = None) -> Dict[str, Any]:
        """LLM-based intent classification for ambiguous messages.
        Only called when fast classification fails. Uses smallest available model."""
        if not model:
            model = await self._get_fastest_model()
            if not model:
                return {"intent": "conversation", "confidence": 0.5, "sub_intents": [], "needs_planning": False}

        prompt = f"""Classify this user message into exactly ONE intent category.

Categories: {', '.join(INTENT_CATEGORIES)}

Also determine:
1. Is this a multi-step task that needs planning? (true/false)
2. What sub-intents are involved? (list)
3. Confidence level (0.0-1.0)

User message: "{text}"

Respond in JSON only:
{{"intent": "category", "confidence": 0.9, "sub_intents": ["sub1"], "needs_planning": false}}"""

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(OLLAMA_URL, json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"num_ctx": 1024, "num_predict": 150, "temperature": 0.1}
                })
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                # Extract JSON from response
                match = re.search(r'\{[^}]+\}', content)
                if match:
                    result = json.loads(match.group())
                    result.setdefault("intent", "conversation")
                    result.setdefault("confidence", 0.5)
                    result.setdefault("sub_intents", [])
                    result.setdefault("needs_planning", False)
                    return result
        except Exception as e:
            logger.warning(f"LLM intent classification failed: {e}")

        return {"intent": "conversation", "confidence": 0.5, "sub_intents": [], "needs_planning": False}

    async def classify_intent(self, text: str, model: str = None) -> Dict[str, Any]:
        """Hybrid intent classification: fast regex first, LLM fallback for ambiguous."""
        fast_result = self.classify_intent_fast(text)
        if fast_result:
            return {"intent": fast_result, "confidence": 0.9, "sub_intents": [], "needs_planning": False, "method": "fast"}

        llm_result = await self.classify_intent_llm(text, model)
        llm_result["method"] = "llm"
        return llm_result

    def _cache_intent(self, key, intent):
        if len(self._intent_cache) >= self._cache_max:
            # Remove oldest entry
            oldest = next(iter(self._intent_cache))
            del self._intent_cache[oldest]
        self._intent_cache[key] = intent

    # ========================
    # TASK PLANNING
    # ========================

    async def plan_task(self, text: str, intent_info: Dict, model: str = None) -> List[Dict]:
        """Break complex requests into executable steps.
        Only called when intent_info['needs_planning'] is True."""
        if not model:
            model = await self._get_fastest_model()
            if not model:
                return [{"step": 1, "action": "direct", "module": None, "description": text}]

        # Get available module names for the planner
        available = [f"{m.name} ({m.display_name}: {m.description})" for m in self.modules.values() if m.enabled]

        prompt = f"""Break this user request into sequential steps. Each step should use one of the available modules.

Available modules:
{chr(10).join(available)}

User request: "{text}"
Detected intent: {intent_info.get('intent', 'unknown')}
Sub-intents: {intent_info.get('sub_intents', [])}

Return a JSON array of steps:
[{{"step": 1, "module": "module_name_or_null", "action": "description", "depends_on": null}}]

Keep it minimal — 2-4 steps max. Use null for module if the main LLM should handle it directly."""

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(OLLAMA_URL, json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"num_ctx": 2048, "num_predict": 300, "temperature": 0.2}
                })
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                match = re.search(r'\[[\s\S]*\]', content)
                if match:
                    steps = json.loads(match.group())
                    if isinstance(steps, list) and len(steps) > 0:
                        return steps
        except Exception as e:
            logger.warning(f"Task planning failed: {e}")

        return [{"step": 1, "action": "direct", "module": None, "description": text}]

    async def execute_plan(self, steps: List[Dict], text: str, context: Dict) -> Dict:
        """Execute a multi-step plan sequentially."""
        results = []
        plan_context = dict(context)

        for step in steps:
            module_name = step.get("module")
            if module_name and module_name in self.modules:
                mod = self.modules[module_name]
                if mod.enabled:
                    result = await self.execute_with_recovery(mod, text, plan_context)
                    results.append({"step": step.get("step", len(results) + 1), "module": module_name, "result": result})
                    plan_context["previous_step"] = result.get("response", "")
                    plan_context["step_data"] = result.get("data")
            else:
                results.append({"step": step.get("step", len(results) + 1), "module": None, "action": step.get("action", "direct"), "result": {"response": "Handled by main LLM"}})

        return {
            "response": results[-1]["result"].get("response", "") if results else "No steps executed.",
            "plan_results": results,
            "action": "plan_complete",
            "steps_executed": len(results)
        }

    # ========================
    # SMART ROUTING
    # ========================

    def route(self, text: str, intent: str = "", context: Dict = None) -> Optional[Tuple]:
        """Route to best matching module based on confidence scores."""
        context = context or {}
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

    def route_all(self, text: str, intent: str = "", context: Dict = None, min_confidence: float = 0.3) -> List[Tuple]:
        """Get all modules that can handle this request, sorted by confidence."""
        context = context or {}
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

    async def smart_route(self, text: str, context: Dict = None) -> Dict:
        """Full intelligent routing pipeline:
        1. Classify intent (fast → LLM fallback)
        2. Route to modules
        3. Check if planning needed
        4. Execute with recovery
        Returns routing decision with intent info."""
        context = context or {}

        # Step 1: Classify intent
        intent_info = await self.classify_intent(text)
        intent = intent_info["intent"]

        # Step 2: Find matching modules
        matches = self.route_all(text, intent, context)

        # Step 3: Check if multi-step planning needed
        plan = None
        if intent_info.get("needs_planning") and len(intent_info.get("sub_intents", [])) > 1:
            plan = await self.plan_task(text, intent_info)

        return {
            "intent": intent_info,
            "matches": [(m.name, s) for m, s in matches],
            "plan": plan,
            "primary_module": matches[0][0].name if matches else None,
            "primary_confidence": matches[0][1] if matches else 0.0,
        }

    # ========================
    # EXECUTION WITH RECOVERY
    # ========================

    async def execute_module(self, module, text: str, context: Dict = None, confidence: float = 0.0) -> Dict:
        """Execute a single module with timing and history tracking."""
        context = context or {}
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
            return {
                "response": f"Module {module.display_name} error: {e}",
                "data": None, "action": "error",
                "_meta": {"module": module.name, "error": str(e)}
            }

    async def execute_with_recovery(self, primary_module, text: str, context: Dict = None, confidence: float = 0.0) -> Dict:
        """Execute with automatic fallback to next best module on failure."""
        context = context or {}
        result = await self.execute_module(primary_module, text, context, confidence)

        # Check if execution failed
        if result.get("action") == "error" or result.get("_meta", {}).get("error"):
            logger.info(f"Primary module {primary_module.name} failed, attempting recovery...")

            # Find fallback modules
            fallbacks = self.route_all(text, "", context, min_confidence=0.2)
            for fallback_mod, fb_score in fallbacks:
                if fallback_mod.name == primary_module.name:
                    continue  # Skip the one that failed
                logger.info(f"Trying fallback: {fallback_mod.name} (confidence: {fb_score})")
                fb_result = await self.execute_module(fallback_mod, text, context, fb_score)
                if fb_result.get("action") != "error":
                    fb_result["_meta"]["recovery"] = True
                    fb_result["_meta"]["original_module"] = primary_module.name
                    return fb_result

            # All fallbacks failed — return original error with recovery info
            result["_meta"]["recovery_attempted"] = True
            result["_meta"]["recovery_failed"] = True

        return result

    async def execute_parallel(self, modules_with_scores: List[Tuple], text: str, context: Dict = None) -> List[Dict]:
        """Execute multiple modules in parallel."""
        context = context or {}
        tasks = [self.execute_module(m, text, context, s) for m, s in modules_with_scores]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r if not isinstance(r, Exception) else {"response": str(r), "action": "error"} for r in results]

    async def chain_execute(self, module_names: List[str], text: str, context: Dict = None) -> Dict:
        """Execute modules sequentially, passing context between them."""
        context = context or {}
        chain_ctx = dict(context)
        chain_results = []
        for name in module_names:
            mod = self.modules.get(name)
            if not mod or not mod.enabled:
                continue
            result = await self.execute_with_recovery(mod, text, chain_ctx, 1.0)
            chain_results.append(result)
            chain_ctx["previous_module"] = name
            chain_ctx["previous_result"] = result.get("response", "")
            chain_ctx["chain_data"] = result.get("data")
        return {
            "response": chain_results[-1]["response"] if chain_results else "No modules executed.",
            "chain": chain_results,
            "action": "chain_complete"
        }

    # ========================
    # WORKFLOW ENGINE
    # ========================

    def register_workflow(self, name: str, steps: List[Dict], description: str = ""):
        """Register a reusable workflow (sequence of module calls)."""
        self.workflows[name] = {
            "name": name,
            "description": description,
            "steps": steps,
            "created": time.time()
        }
        self._save_workflows()

    def get_workflow(self, name: str) -> Optional[Dict]:
        return self.workflows.get(name)

    def list_workflows(self) -> List[Dict]:
        return [{"name": w["name"], "description": w["description"], "steps": len(w["steps"])} for w in self.workflows.values()]

    async def run_workflow(self, name: str, text: str, context: Dict = None) -> Dict:
        """Execute a named workflow."""
        context = context or {}
        workflow = self.workflows.get(name)
        if not workflow:
            return {"response": f"Workflow '{name}' not found.", "action": "error"}

        results = []
        wf_ctx = dict(context)
        for step in workflow["steps"]:
            mod_name = step.get("module")
            mod = self.modules.get(mod_name)
            if not mod:
                results.append({"step": step, "error": f"Module {mod_name} not found"})
                continue
            result = await self.execute_with_recovery(mod, text, wf_ctx)
            results.append({"step": step, "result": result})
            wf_ctx["previous_result"] = result.get("response", "")

        return {
            "response": results[-1]["result"].get("response", "") if results else "Workflow empty.",
            "workflow": name,
            "steps_completed": len(results),
            "results": results,
            "action": "workflow_complete"
        }

    # ========================
    # MODULE ACCESS
    # ========================

    def get_module(self, name: str):
        return self.modules.get(name)

    def get_all_modules(self) -> List[Dict]:
        return [mod.info() for mod in self.modules.values()]

    def get_active_modules(self) -> List:
        return [mod for mod in self.modules.values() if mod.enabled]

    def get_modules_by_category(self, category: str) -> List:
        return [mod for mod in self.modules.values() if mod.category == category]

    def update_module_settings(self, module_name: str, settings: Dict) -> bool:
        mod = self.modules.get(module_name)
        if not mod:
            return False
        mod.update_settings(settings)
        self._save_settings()
        return True

    def get_module_settings(self, module_name: str) -> Dict:
        mod = self.modules.get(module_name)
        if not mod:
            return {}
        return {"info": mod.info(), "settings": mod.get_settings_schema()}

    def get_extra_system_prompt(self) -> str:
        parts = []
        for mod in self.get_active_modules():
            addition = mod.get_system_prompt_addition()
            if addition:
                parts.append(addition)
        return "\n".join(parts)

    def get_context_for_request(self, text: str, context: Dict = None) -> str:
        context = context or {}
        parts = []
        for mod in self.get_active_modules():
            ctx = mod.get_context_for_llm(text, context)
            if ctx:
                parts.append(ctx)
        return "\n".join(parts)

    # ========================
    # STATS & HISTORY
    # ========================

    def get_execution_stats(self) -> Dict:
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

    def get_recent_history(self, limit: int = 20) -> List[Dict]:
        return list(self.execution_history)[-limit:]

    # ========================
    # PERSISTENCE
    # ========================

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

    def _load_workflows(self):
        if WORKFLOWS_FILE.exists():
            try:
                self.workflows = json.loads(WORKFLOWS_FILE.read_text(encoding="utf-8"))
            except Exception:
                self.workflows = {}

    def _save_workflows(self):
        try:
            WORKFLOWS_FILE.write_text(json.dumps(self.workflows, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _record_execution(self, module_name: str, confidence: float, duration_ms: float, success: bool, text: str):
        self.execution_history.append({
            "module": module_name,
            "confidence": round(confidence, 3),
            "duration_ms": round(duration_ms, 1),
            "success": success,
            "text_preview": text[:80],
            "timestamp": time.time()
        })
        self._save_history()

    # ========================
    # HELPERS
    # ========================

    async def _get_fastest_model(self) -> Optional[str]:
        """Get the smallest/fastest available Ollama model for classification tasks."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("http://localhost:11434/api/tags")
                models = resp.json().get("models", [])
                if not models:
                    return None
                # Prefer small models for classification
                preferred = ["qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b", "phi3:mini", "gemma2:2b", "llama3.2:1b", "llama3.2:3b"]
                for pref in preferred:
                    for m in models:
                        if pref in m.get("name", "").lower():
                            return m["name"]
                # Fallback: pick smallest by size
                models.sort(key=lambda x: x.get("size", float("inf")))
                return models[0]["name"]
        except Exception:
            return None
