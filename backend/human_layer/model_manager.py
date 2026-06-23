"""
MJ Multi-Model AI Brain — Zeus Smart Router
Routes requests to the best model based on task type.
Auto-detects installed models — works on any machine (laptop or PC).
Supports: Ollama (local) + Groq (cloud) with auto-fallback.

Laptop (no GPU):   Groq cloud (fast) or small Ollama models
PC (RTX 3060 12GB): Ollama local with 14B, 8B, vision, reasoning
"""

import httpx
import json
import re
import time
from pathlib import Path
from typing import Optional

OLLAMA_API = "http://localhost:11434"
MODEL_CONFIG_FILE = Path(__file__).parent.parent / "model_config.json"

# Provider: "ollama" (local) or "groq" (cloud)
_active_provider: str = "ollama"

# ── Preferred models by role (ordered by preference — first available wins) ──
# The system picks the FIRST model from each list that's actually installed.
ROLE_PREFERENCES = {
    "fast_chat": ["qwen3:8b", "qwen2.5:7b", "qwen2.5:3b", "llama3.1:8b", "gemma2:9b", "mistral:7b"],
    "complex":   ["qwen3:14b", "qwen2.5:14b", "deepseek-v2:16b", "qwen3:8b", "qwen2.5:7b"],
    "reasoning": ["deepseek-r1:8b", "deepseek-r1:14b", "qwen3:8b"],
    "vision":    ["moondream", "llava:7b", "llava:13b", "bakllava"],
    "coding":    ["qwen3:8b", "qwen2.5-coder:7b", "codellama:7b", "deepseek-coder:6.7b"],
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

# Complexity signals — only used if a bigger model is actually installed
COMPLEX_SIGNALS = [
    r"(?:complete|full|entire|comprehensive|production|professional)\s+(?:system|app|project|code|solution)",
    r"(?:design|architect|plan)\s+(?:a\s+)?(?:system|architecture|database|schema)",
    r"(?:build\s+(?:a\s+)?(?:complete|full|entire|production))",
    r"(?:write\s+(?:a\s+)?(?:long|detailed|comprehensive|full))",
    r"(?:multiple|several|all|every)\s+(?:features?|modules?|components?|endpoints?)",
    r"(?:optimize|scale|performance|benchmark|enterprise)",
]

# ── Installed Model Cache ────────────────────────────────────
_installed_cache: list = []
_installed_cache_time: float = 0
_CACHE_TTL = 60  # refresh every 60 seconds

# ── Dynamic Roster (built from what's actually installed) ────
_dynamic_roster: dict = {}
_roster_built: bool = False


def _refresh_installed_models() -> list:
    """Fetch installed model list from Ollama. Cached for 60s."""
    global _installed_cache, _installed_cache_time
    now = time.time()
    if _installed_cache and (now - _installed_cache_time) < _CACHE_TTL:
        return _installed_cache
    try:
        resp = httpx.get(f"{OLLAMA_API}/api/tags", timeout=5)
        if resp.status_code == 200:
            _installed_cache = [m["name"] for m in resp.json().get("models", [])]
            _installed_cache_time = now
            return _installed_cache
    except Exception:
        pass
    return _installed_cache  # return stale cache if refresh fails


def _find_best_installed(role: str) -> Optional[str]:
    """Find the first preferred model for a role that's actually installed."""
    installed = _refresh_installed_models()
    if not installed:
        return None

    preferences = ROLE_PREFERENCES.get(role, [])
    for preferred in preferences:
        # Exact match
        if preferred in installed:
            return preferred
        # Partial match (e.g. "qwen3:8b" matches "qwen3:8b-q4_K_M")
        base = preferred.split(":")[0]
        for inst in installed:
            if base == inst.split(":")[0]:
                return inst
    return None


def _build_dynamic_roster():
    """Build the model roster from what's ACTUALLY installed. Called once on first use."""
    global _dynamic_roster, _roster_built

    installed = _refresh_installed_models()
    if not installed:
        _roster_built = False
        return

    _dynamic_roster = {}
    for role in ROLE_PREFERENCES:
        best = _find_best_installed(role)
        if best:
            _dynamic_roster[role] = best

    # Ensure at least a fallback exists
    if "fast_chat" not in _dynamic_roster and installed:
        _dynamic_roster["fast_chat"] = installed[0]

    _roster_built = True


def _get_roster() -> dict:
    """Get the dynamic roster, building it if needed."""
    if not _roster_built:
        _build_dynamic_roster()
    return _dynamic_roster


def _get_safe_fallback() -> str:
    """Always returns a valid model name — the safest possible fallback."""
    roster = _get_roster()
    if roster:
        return roster.get("fast_chat", list(roster.values())[0])
    # Last resort: check installed directly
    installed = _refresh_installed_models()
    if installed:
        return installed[0]
    return "qwen3:8b"  # absolute last resort string


# ── Config Management ────────────────────────────────────────

def _default_config() -> dict:
    """Build default config from currently installed models."""
    roster = _get_roster()
    fast = roster.get("fast_chat", "qwen3:8b")
    return {
        "active_model": fast,
        "auto_select": True,
        "model_map": {
            "chat":        roster.get("fast_chat", fast),
            "coding":      roster.get("coding", fast),
            "creative":    roster.get("fast_chat", fast),
            "analysis":    roster.get("fast_chat", fast),
            "reasoning":   roster.get("reasoning", fast),
            "vision":      roster.get("vision", fast),
            "translation": roster.get("fast_chat", fast),
        },
    }


def load_model_config() -> dict:
    try:
        if MODEL_CONFIG_FILE.exists():
            data = json.loads(MODEL_CONFIG_FILE.read_text(encoding="utf-8"))
            # Migrate old config
            if "model_preferences" in data and "model_map" not in data:
                data["model_map"] = data.pop("model_preferences")
                save_model_config(data)
            return data
    except Exception:
        pass
    return _default_config()


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


# ── Task Detection ───────────────────────────────────────────

def detect_task_type(text: str, has_image: bool = False) -> str:
    if has_image:
        return "vision"
    lower = text.lower()
    for task_type, patterns in TASK_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, lower):
                return task_type
    return "chat"


def _is_complex(text: str) -> bool:
    """Check if request is complex enough to warrant a bigger model."""
    lower = text.lower()
    for pat in COMPLEX_SIGNALS:
        if re.search(pat, lower):
            return True
    # Only long messages with actual content signals, not just greetings
    if len(text) > 300 and any(w in lower for w in ["build", "create", "write", "design", "implement", "complete"]):
        return True
    return False


def _validate_model(selected: str) -> str:
    """
    Validate that the selected model is actually installed.
    ALWAYS returns an installed model — never returns a non-existent model.
    """
    installed = _refresh_installed_models()

    # If we can't reach Ollama, return safe fallback — NOT the unvalidated selection
    if not installed:
        return _get_safe_fallback()

    # Exact match
    if selected in installed:
        return selected

    # Partial match (same model family)
    selected_base = selected.split(":")[0]
    for m in installed:
        if selected_base == m.split(":")[0]:
            return m

    # Selected model not installed at all — fallback to safe default
    return _get_safe_fallback()


# ── Main Router ──────────────────────────────────────────────

def get_model_for_task(text: str, has_image: bool = False) -> str:
    """
    Zeus Model Router — picks the best INSTALLED model for the task.

    Key principle: NEVER return a model that isn't installed.

    Priority:
      1. Image attached → vision model (if installed)
      2. Auto-select OFF → use active_model (validated)
      3. Detect task type → map to installed model
      4. Complexity check → upgrade ONLY if bigger model is installed
      5. Final validation → always returns an installed model
    """
    config = load_model_config()
    roster = _get_roster()

    # Vision override
    if has_image:
        vision_model = roster.get("vision") or config.get("model_map", {}).get("vision")
        if vision_model:
            return _validate_model(vision_model)
        return _get_safe_fallback()

    # Manual mode
    if not config.get("auto_select", True):
        selected = config.get("active_model", _get_safe_fallback())
        return _validate_model(selected)

    # Detect task
    task_type = detect_task_type(text)
    model_map = config.get("model_map", {})
    selected = model_map.get(task_type, _get_safe_fallback())

    # Complexity upgrade — ONLY if a bigger model is actually installed
    if task_type in ("chat", "translation") and _is_complex(text):
        complex_model = roster.get("complex")
        if complex_model:
            # complex_model is already validated as installed by _build_dynamic_roster
            selected = complex_model
        else:
            # No bigger model installed — stay with current selection
            selected = model_map.get("coding", selected)

    return _validate_model(selected)


def get_routing_info(text: str, has_image: bool = False) -> dict:
    """Return routing decision with explanation (for UI/debug)."""
    task_type = detect_task_type(text, has_image)
    model = get_model_for_task(text, has_image)
    is_complex = _is_complex(text)
    roster = _get_roster()

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
        if roster.get("complex"):
            reason += " (upgraded: complex request)"
        else:
            reason += " (complex, but no bigger model installed — using default)"

    return {
        "task_type": task_type,
        "model": model,
        "reason": reason,
        "complex": is_complex,
        "installed_models": len(_refresh_installed_models()),
        "device_has_big_model": "complex" in roster,
    }


def sync_config_with_installed():
    """
    Re-sync model_config.json with actually installed models.
    Call this on backend startup to auto-fix stale configs.
    """
    _build_dynamic_roster()
    roster = _get_roster()
    if not roster:
        return

    config = load_model_config()
    model_map = config.get("model_map", {})
    changed = False

    for task_type, model_name in model_map.items():
        validated = _validate_model(model_name)
        if validated != model_name:
            model_map[task_type] = validated
            changed = True

    # Also validate active_model
    active = config.get("active_model", "")
    validated_active = _validate_model(active)
    if validated_active != active:
        config["active_model"] = validated_active
        changed = True

    if changed:
        config["model_map"] = model_map
        save_model_config(config)


# ── Provider Management ──────────────────────────────────────

def get_active_provider() -> str:
    """Return current provider: 'ollama' or 'groq'."""
    global _active_provider
    config = load_model_config()
    return config.get("provider", _active_provider)


def set_provider(provider: str) -> dict:
    """Switch between 'ollama' and 'groq'."""
    global _active_provider
    provider = provider.lower().strip()
    if provider not in ("ollama", "groq"):
        return {"success": False, "message": f"Unknown provider: {provider}. Use 'ollama' or 'groq'."}

    if provider == "groq":
        try:
            from intelligence.groq_provider import is_groq_available
            if not is_groq_available():
                return {"success": False, "message": "Groq API key not set. Create backend/.env with GROQ_API_KEY=gsk_..."}
        except ImportError:
            return {"success": False, "message": "Groq provider module not found."}

    _active_provider = provider
    config = load_model_config()
    config["provider"] = provider
    save_model_config(config)
    return {"success": True, "message": f"Provider switched to: {provider.upper()}"}


def auto_detect_provider() -> str:
    """
    Auto-detect best provider:
    - If Groq API key exists → ALWAYS use Groq (user set it up for a reason)
    - Only fall back to Ollama if no Groq key
    - On PC: user won't have .env with Groq key → auto-picks Ollama
    - On Laptop: user has .env with Groq key → auto-picks Groq
    """
    global _active_provider

    groq_available = False
    try:
        from intelligence.groq_provider import is_groq_available
        groq_available = is_groq_available()
    except ImportError:
        pass

    if groq_available:
        _active_provider = "groq"
    else:
        _active_provider = "ollama"

    # Save to config
    config = load_model_config()
    config["provider"] = _active_provider
    save_model_config(config)

    return _active_provider


# ── Command Handlers ─────────────────────────────────────────

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

    m = re.search(r"(?:switch|change|use|set)\s+(?:model|brain)\s+(?:to\s+)?(.+)", lower)
    if m:
        return {"action": "switch", "model": m.group(1).strip()}

    m = re.search(r"(.+)\s+(?:model|brain)\s+(?:use|set|switch)\s*(?:karo|kar)?", lower)
    if m:
        return {"action": "switch", "model": m.group(1).strip()}

    if any(w in lower for w in ["list model", "show model", "available model", "kaun se model", "models dikhao", "which model"]):
        return {"action": "list"}

    if any(w in lower for w in ["current model", "kaunsa model", "which model active", "model kya hai"]):
        return {"action": "current"}

    if any(w in lower for w in ["model map", "model routing", "routing table", "model config", "kaun kya handle"]):
        return {"action": "routing"}

    if any(w in lower for w in ["auto model on", "auto select on", "smart model on", "zeus routing on"]):
        return {"action": "auto_on"}
    if any(w in lower for w in ["auto model off", "auto select off", "smart model off", "zeus routing off"]):
        return {"action": "auto_off"}

    m = re.search(r"(?:set|use)\s+(.+?)\s+(?:for|ke\s+liye)\s+(coding|chat|reasoning|vision|creative|analysis|translation)", lower)
    if m:
        return {"action": "set_task", "model": m.group(1).strip(), "task": m.group(2).strip()}

    # Provider switching
    if any(w in lower for w in ["use groq", "switch to groq", "groq use karo", "groq chalao", "cloud mode"]):
        return {"action": "set_provider", "provider": "groq"}
    if any(w in lower for w in ["use ollama", "switch to ollama", "ollama use karo", "local mode", "offline mode"]):
        return {"action": "set_provider", "provider": "ollama"}
    if any(w in lower for w in ["which provider", "provider kya", "groq ya ollama", "cloud or local"]):
        return {"action": "provider_status"}

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
        roster = _get_roster()

        lines = [f"📦 Installed Models ({len(models)}):"]
        for m in models:
            marker = " ← ACTIVE" if m["name"] == active else ""
            lines.append(f"  • {m['name']} ({m['size']}){marker}")

        lines.append(f"\n⚡ Auto-assigned Roles:")
        role_icons = {"fast_chat": "💬", "complex": "👑", "reasoning": "🧩", "vision": "👁", "coding": "💻"}
        for role, model in roster.items():
            icon = role_icons.get(role, "•")
            lines.append(f"  {icon} {role:12s} → {model}")

        lines.append(f"\n🧠 Auto-select: {'ON' if config.get('auto_select') else 'OFF'}")
        has_big = "complex" in roster
        device = "PC (big models available)" if has_big else "Laptop (small models only)"
        lines.append(f"💻 Device: {device}")

        return {"success": True, "message": "\n".join(lines)}

    elif action == "current":
        config = load_model_config()
        auto = "ON" if config.get("auto_select") else "OFF"
        roster = _get_roster()
        has_big = "complex" in roster
        device = "PC" if has_big else "Laptop"
        return {"success": True, "message": f"Current model: {config.get('active_model', '?')} | Auto-select: {auto} | Device: {device}"}

    elif action == "routing":
        config = load_model_config()
        model_map = config.get("model_map", {})
        lines = ["⚡ Zeus Model Routing Table:"]
        icons = {"chat": "💬", "coding": "💻", "creative": "🎨", "analysis": "📊", "reasoning": "🧩", "vision": "👁", "translation": "🌐"}
        for task, model in model_map.items():
            icon = icons.get(task, "•")
            installed = _refresh_installed_models()
            status = "✓" if model in installed else "✗ NOT INSTALLED"
            lines.append(f"  {icon} {task.title():15s} → {model} {status}")
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

    elif action == "set_provider":
        return set_provider(cmd["provider"])
    elif action == "provider_status":
        provider = get_active_provider()
        groq_avail = False
        try:
            from intelligence.groq_provider import is_groq_available
            groq_avail = is_groq_available()
        except ImportError:
            pass
        return {
            "success": True,
            "message": (
                f"🔌 Active Provider: {provider.upper()}\n"
                f"  Ollama: {'Connected' if _refresh_installed_models() else 'Not running'}\n"
                f"  Groq:   {'API key set ✓' if groq_avail else 'Not configured ✗'}\n"
                f"\nSwitch: say 'use groq' or 'use ollama'"
            ),
        }

    return {"success": False, "message": "Unknown model command."}


def _format_size(bytes_size: int) -> str:
    if bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.0f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024*1024):.0f} MB"
    else:
        return f"{bytes_size / (1024*1024*1024):.1f} GB"
