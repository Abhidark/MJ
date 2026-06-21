"""
MJ Multi-Model AI Brain — Zeus Smart Router
Routes requests to the best model based on task type.

Architecture (RTX 3060 12GB / 32GB RAM):
  🧠 Qwen3 8B    → Fast everyday chat (default)
  👑 Qwen3 14B   → Complex / advanced tasks
  🧩 DeepSeek-R1 → Deep reasoning, logic, math, algorithms
  👁 Moondream   → Vision / image understanding

Only one model loads into VRAM at a time. Ollama handles swap automatically.
"""

import httpx
import json
import re
from pathlib import Path

OLLAMA_API = "http://localhost:11434"
MODEL_CONFIG_FILE = Path(__file__).parent.parent / "model_config.json"

# ── Model Roster ──────────────────────────────────────────────
MODELS = {
    "fast_chat":  "qwen3:8b",
    "complex":    "qwen3:14b",
    "reasoning":  "deepseek-r1:8b",
    "vision":     "moondream",
}

DEFAULT_CONFIG = {
    "active_model": "qwen3:8b",
    "auto_select": True,
    "model_map": {
        "chat":        "qwen3:8b",
        "coding":      "qwen3:8b",
        "creative":    "qwen3:8b",
        "analysis":    "qwen3:8b",
        "reasoning":   "deepseek-r1:8b",
        "vision":      "moondream",
        "translation": "qwen3:8b",
    },
}

# ── Task Detection Patterns ──────────────────────────────────

TASK_PATTERNS = {
    "reasoning": [
        r"(?:solve|proof|prove|theorem|algorithm|logic|deduce|infer|derive)",
        r"(?:step.by.step|think.through|work.out|figure.out|reason)",
        r"(?:math|calculus|equation|formula|integral|derivative|probability)",
        r"(?:why\s+does|why\s+is|how\s+come|what\s+if\s+we)",
        r"(?:puzzle|brain\s*teaser|riddle\s+solve|logical)",
        r"(?:socho|soch\s+ke\s+batao|dimag\s+lagao|hisab)",
        r"(?:compare.*(?:which|better|pros|cons))",
        r"(?:debug.*(?:why|reason|cause|trace))",
    ],
    "coding": [
        r"(?:code|program|function|class|debug|fix\s+(?:this|my|the)\s+(?:bug|error|code))",
        r"(?:script|api|html|css|python|javascript|java|typescript|react|node)",
        r"(?:compile|syntax|import|module|package|library|framework)",
        r"(?:write\s+(?:a\s+)?(?:code|program|script|function|class|api))",
        r"(?:code\s+likh|program\s+bana|debug\s+kar|error\s+fix|code\s+bana)",
        r"(?:build\s+(?:a\s+)?(?:website|app|tool|system|backend|frontend))",
        r"(?:implement|refactor|optimize\s+(?:this|my|the)\s+code)",
    ],
    "creative": [
        r"(?:write\s+(?:a\s+)?(?:story|poem|song|essay|blog|article|script))",
        r"(?:imagine|fiction|creative\s+writing|narrative|compose)",
        r"(?:kahani|kavita|joke\s+suna|shayari|gaana\s+likh)",
        r"(?:brainstorm|ideate|come\s+up\s+with|suggest\s+names)",
    ],
    "analysis": [
        r"(?:analyze|compare|summarize|evaluate|research|report)",
        r"(?:explain\s+(?:in\s+detail|thoroughly|completely|everything))",
        r"(?:deep\s+dive|comprehensive|detailed\s+(?:analysis|review|breakdown))",
        r"(?:samjha.*detail|pura\s+batao|analysis\s+kar|review\s+kar)",
    ],
    "translation": [
        r"(?:translate|convert\s+(?:to|into)\s+(?:hindi|english|spanish|french))",
        r"(?:hindi\s+(?:me|mein)\s+(?:batao|likho|bol))",
        r"(?:english\s+(?:me|mein)\s+(?:batao|likho))",
        r"(?:meaning|matlab|ka\s+matlab|means?\s+kya)",
    ],
    "chat": [],  # fallback
}

# Complexity signals → upgrade to 14B
COMPLEX_SIGNALS = [
    r"(?:complete|full|entire|comprehensive|production|professional)\s+(?:system|app|project|code|solution)",
    r"(?:design|architect|plan)\s+(?:a\s+)?(?:system|architecture|database|schema)",
    r"(?:build\s+(?:a\s+)?(?:complete|full|entire|production))",
    r"(?:write\s+(?:a\s+)?(?:long|detailed|comprehensive|full))",
    r"(?:multiple|several|all|every)\s+(?:features?|modules?|components?|endpoints?)",
    r"(?:optimize|scale|performance|benchmark|enterprise)",
]


def load_model_config() -> dict:
    try:
        if MODEL_CONFIG_FILE.exists():
            data = json.loads(MODEL_CONFIG_FILE.read_text(encoding="utf-8"))
            # Migrate old config format
            if "model_preferences" in data and "model_map" not in data:
                data["model_map"] = data.pop("model_preferences")
                # Inject new task types if missing
                data["model_map"].setdefault("reasoning", MODELS["reasoning"])
                data["model_map"].setdefault("vision", MODELS["vision"])
                save_model_config(data)
            return data
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()


def save_model_config(config: dict):
    MODEL_CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


async def get_available_models() -> list:
    """Get list of models installed in Ollama."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{OLLAMA_API}/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return [
                    {
                        "name": m["name"],
                        "size": _format_size(m.get("size", 0)),
                        "modified": m.get("modified_at", ""),
                    }
                    for m in models
                ]
    except Exception:
        pass
    return []


def detect_task_type(text: str, has_image: bool = False) -> str:
    """Detect task type from user message. Vision takes priority if image attached."""
    if has_image:
        return "vision"

    lower = text.lower()

    # Check each task type
    for task_type, patterns in TASK_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, lower):
                return task_type

    return "chat"


def _is_complex(text: str) -> bool:
    """Check if request is complex enough to warrant the big model."""
    lower = text.lower()
    for pat in COMPLEX_SIGNALS:
        if re.search(pat, lower):
            return True
    # Long messages (>200 chars) with coding intent → likely complex
    if len(text) > 200:
        return True
    return False


def get_model_for_task(text: str, has_image: bool = False) -> str:
    """
    Zeus Model Router — picks the best model for the task.

    Priority:
      1. Image attached → moondream (always)
      2. Auto-select OFF → use active_model
      3. Detect task type → map to model
      4. Complexity check → upgrade to 14B if needed
    """
    config = load_model_config()

    # Vision override — always use moondream for images
    if has_image:
        return config.get("model_map", {}).get("vision", MODELS["vision"])

    # Manual mode
    if not config.get("auto_select", True):
        return config.get("active_model", MODELS["fast_chat"])

    # Detect task
    task_type = detect_task_type(text)
    model_map = config.get("model_map", DEFAULT_CONFIG["model_map"])
    selected = model_map.get(task_type, MODELS["fast_chat"])

    # Complexity upgrade: if chat/translation but message is complex → use 14B
    if task_type in ("chat", "translation") and _is_complex(text):
        selected = model_map.get("coding", MODELS["complex"])

    return selected


def get_routing_info(text: str, has_image: bool = False) -> dict:
    """Return routing decision with explanation (for UI/debug)."""
    task_type = detect_task_type(text, has_image)
    model = get_model_for_task(text, has_image)
    is_complex = _is_complex(text)

    reasons = {
        "vision": "Image attached → Vision model",
        "reasoning": "Logic/math/algorithm detected → Reasoning model",
        "coding": "Code task detected → Code model",
        "creative": "Creative writing detected → Creative model",
        "analysis": "Analysis/research detected → Analysis model",
        "translation": "Translation request → Fast model",
        "chat": "General conversation → Fast model",
    }

    reason = reasons.get(task_type, "Default routing")
    if is_complex and task_type in ("chat", "translation"):
        reason += " (upgraded: complex request)"

    return {
        "task_type": task_type,
        "model": model,
        "reason": reason,
        "complex": is_complex,
    }


def set_active_model(model_name: str) -> dict:
    config = load_model_config()
    config["active_model"] = model_name
    save_model_config(config)
    return {"success": True, "message": f"Model switched to: {model_name}"}


def set_model_for_task(task_type: str, model_name: str) -> dict:
    config = load_model_config()
    if "model_map" not in config:
        config["model_map"] = {}
    config["model_map"][task_type] = model_name
    save_model_config(config)
    return {"success": True, "message": f"{task_type.title()} tasks ke liye {model_name} set kar diya."}


def toggle_auto_select(enabled: bool) -> dict:
    config = load_model_config()
    config["auto_select"] = enabled
    save_model_config(config)
    state = "ON" if enabled else "OFF"
    return {"success": True, "message": f"Auto model selection: {state}"}


def parse_model_command(text: str) -> dict | None:
    """Parse model-related commands."""
    lower = text.lower().strip()

    # Switch model
    m = re.search(r"(?:switch|change|use|set)\s+(?:model|brain)\s+(?:to\s+)?(.+)", lower)
    if m:
        return {"action": "switch", "model": m.group(1).strip()}

    m = re.search(r"(.+)\s+(?:model|brain)\s+(?:use|set|switch)\s*(?:karo|kar)?", lower)
    if m:
        return {"action": "switch", "model": m.group(1).strip()}

    # List models
    if any(w in lower for w in ["list model", "show model", "available model", "kaun se model", "models dikhao", "which model"]):
        return {"action": "list"}

    # Current model / routing info
    if any(w in lower for w in ["current model", "kaunsa model", "which model active", "model kya hai"]):
        return {"action": "current"}

    # Model routing status
    if any(w in lower for w in ["model map", "model routing", "routing table", "model config", "kaun kya handle"]):
        return {"action": "routing"}

    # Auto select toggle
    if any(w in lower for w in ["auto model on", "auto select on", "smart model on", "zeus routing on"]):
        return {"action": "auto_on"}
    if any(w in lower for w in ["auto model off", "auto select off", "smart model off", "zeus routing off"]):
        return {"action": "auto_off"}

    # Set model for specific task
    m = re.search(r"(?:set|use)\s+(.+?)\s+(?:for|ke\s+liye)\s+(coding|chat|reasoning|vision|creative|analysis|translation)", lower)
    if m:
        return {"action": "set_task", "model": m.group(1).strip(), "task": m.group(2).strip()}

    return None


async def handle_model_command(cmd: dict) -> dict:
    """Handle model management commands."""
    action = cmd["action"]

    if action == "list":
        models = await get_available_models()
        if not models:
            return {"success": False, "message": "Koi model nahi mila. Ollama chal raha hai?"}
        config = load_model_config()
        active = config.get("active_model", "?")
        lines = [f"📦 Installed Models ({len(models)}):"]
        for m in models:
            marker = " ← ACTIVE" if m["name"] == active else ""
            lines.append(f"  • {m['name']} ({m['size']}){marker}")
        lines.append(f"\n🧠 Auto-select: {'ON' if config.get('auto_select') else 'OFF'}")
        return {"success": True, "message": "\n".join(lines)}

    elif action == "current":
        config = load_model_config()
        auto = "ON" if config.get("auto_select") else "OFF"
        return {"success": True, "message": f"Current model: {config.get('active_model', '?')} | Auto-select: {auto}"}

    elif action == "routing":
        config = load_model_config()
        model_map = config.get("model_map", DEFAULT_CONFIG["model_map"])
        lines = ["⚡ Zeus Model Routing Table:"]
        icons = {"chat": "💬", "coding": "💻", "creative": "🎨", "analysis": "📊", "reasoning": "🧩", "vision": "👁", "translation": "🌐"}
        for task, model in model_map.items():
            icon = icons.get(task, "•")
            lines.append(f"  {icon} {task.title():15s} → {model}")
        lines.append(f"\n🧠 Auto-select: {'ON' if config.get('auto_select') else 'OFF'}")
        return {"success": True, "message": "\n".join(lines)}

    elif action == "switch":
        model = cmd["model"]
        models = await get_available_models()
        model_names = [m["name"] for m in models]

        matched = None
        for mn in model_names:
            if model in mn.lower() or mn.lower() in model:
                matched = mn
                break

        if not matched:
            return {"success": False, "message": f"'{model}' nahi mila. Available: {', '.join(model_names)}"}

        result = set_active_model(matched)
        return {"success": True, "message": f"Model switched to: {matched}"}

    elif action == "set_task":
        model = cmd["model"]
        task = cmd["task"]
        models = await get_available_models()
        model_names = [m["name"] for m in models]

        matched = None
        for mn in model_names:
            if model in mn.lower() or mn.lower() in model:
                matched = mn
                break

        if not matched:
            return {"success": False, "message": f"'{model}' nahi mila. Available: {', '.join(model_names)}"}

        return set_model_for_task(task, matched)

    elif action == "auto_on":
        return toggle_auto_select(True)
    elif action == "auto_off":
        return toggle_auto_select(False)

    return {"success": False, "message": "Unknown model command."}


def _format_size(bytes_size: int) -> str:
    if bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.0f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024*1024):.0f} MB"
    else:
        return f"{bytes_size / (1024*1024*1024):.1f} GB"
