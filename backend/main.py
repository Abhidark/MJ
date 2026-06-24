from fastapi import FastAPI, UploadFile, File, Form, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from pathlib import Path
import httpx
import json
import uuid
import sys
import base64
import os
import time
import re
import asyncio

# Add backend dir to path for human_layer import
sys.path.insert(0, str(Path(__file__).parent))
from auth import (
    setup_default_password, verify_password, change_password,
    create_session, validate_session, invalidate_session,
    is_auth_enabled, get_session_count, toggle_auth,
)
from human_layer.human_brain import MJHumanBrain
from voice_layer.tts_engine import generate_speech, test_voice, cleanup_old_audio
from voice_layer.voice_config import AVAILABLE_VOICES, load_voice_settings, save_voice_settings
from voice_layer.stt_engine import save_and_transcribe, get_stt_status
from pc_control.command_parser import parse_command
from pc_control.executor import execute_command
from pc_control.system_stats import get_system_stats
# pc_control.web_search is deprecated — use intelligence.web_browser instead
# from pc_control.web_search import web_search, needs_web_search
from pc_control.reminder import parse_reminder, set_reminder, get_active_reminders
from pc_control.daily_briefing import is_greeting, generate_briefing
from pc_control.file_manager import parse_file_command, execute_file_command
from pc_control.screen_recorder import parse_recording_command, start_recording, stop_recording
from pc_control.scheduler import parse_schedule, add_scheduled_task, list_scheduled_tasks, cancel_task, start_all_tasks
from pc_control.email_manager import parse_email_command, handle_email_command
from pc_control.clipboard_manager import parse_clipboard_command, handle_clipboard_command, start_clipboard_monitor
from pc_control.app_tracker import parse_tracker_command, handle_tracker_command, start_app_tracker, get_usage_report
from pc_control.image_gen import parse_image_command, handle_image_command
from human_layer.auto_memory import auto_remember
from intelligence.memory_store import memory_store
from intelligence.fact_extractor import extract_and_store
from intelligence.memory_embeddings import hybrid_search, embed_fact, is_ollama_embed_available
from intelligence.short_term_memory import short_term
from intelligence.user_profile import build_user_profile, get_profile_summary

# Intelligence Layer
from intelligence.web_browser import deep_search, deep_research, format_search_for_llm, format_research_for_llm, needs_web_search_v2
from intelligence.knowledge_graph import knowledge_graph
from intelligence.citations import citation_manager
from intelligence.constitutional_ai import constitutional_ai
from intelligence.reflection_engine import reflection_engine
from intelligence.learning_engine import learning_engine
from intelligence.vision_engine import vision_engine
from intelligence.sentinel_engine import sentinel_engine
from intelligence.knowledge_base import (
    ingest_document, search_knowledge, format_kb_context,
    get_kb_stats, delete_document, needs_kb_search
)
from intelligence.context_memory import (
    record_interaction, get_context_prompt, get_memory_stats
)
from intelligence.multi_model import needs_deep_reasoning, chain_of_thought, multi_perspective
from intelligence.live_data import (
    detect_live_data_request, get_live_cricket_scores, get_live_weather,
    get_weather_data, extract_city_from_text, extract_forecast_type,
    get_live_stock_price, get_live_news,
    extract_stock_from_text, extract_news_topic
)
# error_learner merged into self_healer.error_tracker (unified)
from intelligence.ocr_engine import ocr_from_file, ocr_screenshot, detect_ocr_request
from intelligence.smart_suggestions import get_all_suggestions, detect_suggestion_request

# Zeus Module System
from zeus.brain import Zeus
from modules.echo.module import EchoModule
from modules.empathy.module import EmpathyModule
from modules.vulcan.module import VulcanModule
from modules.mnemosyne.module import MnemosyneModule
from modules.sherlock.module import SherlockModule
from modules.athena.module import AthenaModule
from modules.hephaestus.module import HephaestusModule
from modules.apollo.module import ApolloModule
from modules.argus.module import ArgusModule
from modules.hermes.module import HermesModule
from modules.hermes.messaging_hub import messaging_hub
from modules.prometheus.module import PrometheusModule
from modules.sentinel.module import SentinelModule
from modules.atlas.module import AtlasModule
from modules.archivist.module import ArchivistModule
from modules.daedalus.module import DaedalusModule
from modules.mercury.module import MercuryModule
from modules.oracle.module import OracleModule
from modules.hestia.module import HestiaModule
from modules.loki.module import LokiModule
from modules.chronos.module import ChronosModule
from modules.phantom.module import PhantomModule
from human_layer.model_manager import (
    parse_model_command, handle_model_command, get_model_for_task,
    get_available_models, load_model_config, save_model_config,
    get_routing_info, set_active_model, toggle_auto_select,
    set_model_for_task, sync_config_with_installed,
    get_active_provider, auto_detect_provider,
    get_all_providers_status, smart_route_provider
)
from intelligence.groq_provider import is_groq_available, stream_groq_chat, get_groq_model, check_groq_connection
from intelligence.openai_provider import is_openai_available, stream_openai_chat, check_openai_connection
from intelligence.anthropic_provider import is_anthropic_available, stream_anthropic_chat, check_anthropic_connection
from intelligence.gemini_provider import is_gemini_available, stream_gemini_chat, check_gemini_connection
from plugins.plugin_manager import load_plugins, match_plugin, run_plugin, notify_plugins, parse_plugin_command, handle_plugin_management, get_plugin_list
from self_healer.error_tracker import (
    log_error, get_recent_errors, get_error_stats, clear_errors,
    log_performance, get_diagnostics, get_live_issues, learn_fix
)
from self_healer.auto_fixer import attempt_fix, analyze_error

# Agent Framework Core
from core.message_bus import message_bus
from core.event_system import event_system
from core.shared_memory import shared_memory
from core.task_queue import task_queue
from self_healer.health_monitor import check_health
from self_healer.middleware import SelfHealingMiddleware
from self_healer.alert_system import (
    create_alert, resolve_alert, get_active_alerts, get_all_alerts,
    get_alert_stats, clear_all_alerts, clear_resolved, subscribe, unsubscribe,
    check_system_warnings, SEVERITY_WARNING, SEVERITY_ERROR, CAT_HEALTH
)

app = FastAPI()

# Initialize auth (creates default password "jarvis" if no config exists)
setup_default_password()

# Auto-detect installed models and best provider on startup
try:
    sync_config_with_installed()
    auto_detect_provider()
except Exception:
    pass  # Ollama might not be running yet — will retry on first request

# Initialize Human Brain
mj_brain = MJHumanBrain()

# Initialize Zeus & register all modules
zeus = Zeus()
_module_classes = [
    EchoModule, EmpathyModule, VulcanModule, MnemosyneModule, SherlockModule,
    AthenaModule, HephaestusModule, ApolloModule, ArgusModule, HermesModule,
    PrometheusModule, SentinelModule, AtlasModule, ArchivistModule, DaedalusModule,
    MercuryModule, OracleModule, HestiaModule, LokiModule, ChronosModule, PhantomModule,
]
for _cls in _module_classes:
    try:
        zeus.register(_cls())
    except Exception:
        pass  # Module failed to init — skip silently

# Emit startup event
event_system.emit("system.startup", "zeus", {"modules_loaded": len(zeus.modules)})

# Load MJ system prompt from file
MJ_PROMPT_FILE = Path(__file__).parent / "human_layer" / "prompts" / "mj_system_prompt.txt"
MJ_BASE_PROMPT = MJ_PROMPT_FILE.read_text(encoding="utf-8") if MJ_PROMPT_FILE.exists() else ""

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
REACT_DIST_DIR = Path(__file__).parent.parent / "frontend-react" / "dist"

# Load plugins and start background services on boot
load_plugins()
start_all_tasks()
start_clipboard_monitor()
start_app_tracker()

# Self-Healing Middleware — catches all unhandled errors
app.add_middleware(SelfHealingMiddleware)


# --- Background health polling (every 30s) ---
async def _health_polling_loop():
    """Polls system stats every 30s and fires alerts on thresholds."""
    import asyncio as _aio
    await _aio.sleep(10)  # wait for startup
    while True:
        try:
            stats = await _aio.to_thread(get_system_stats)
            check_system_warnings(stats)
        except Exception:
            pass
        await _aio.sleep(30)


@app.on_event("startup")
async def _start_health_polling():
    import asyncio as _aio
    _aio.create_task(_health_polling_loop())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== AUTH MIDDLEWARE =====
# Protects all API routes except /auth/*, /static/*, and /
# Frontend sends token via "Authorization: Bearer <token>" header or "mj_token" cookie

# Routes that don't need auth
_PUBLIC_ROUTES = {"/auth/login", "/auth/status", "/", "/static", "/docs", "/openapi.json"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Allow public routes and static files
    if path in _PUBLIC_ROUTES or path.startswith("/static") or path.startswith("/auth"):
        return await call_next(request)

    # Check if auth is enabled
    if not is_auth_enabled():
        return await call_next(request)

    # Extract token from header or cookie
    auth_header = request.headers.get("authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("mj_token", "")

    if not token or not validate_session(token):
        return JSONResponse(status_code=401, content={"detail": "Not authenticated. Please login."})

    return await call_next(request)


# ===== AUTH ENDPOINTS =====

class LoginRequest(BaseModel):
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class ToggleAuthRequest(BaseModel):
    enabled: bool
    password: str


@app.get("/auth/status")
async def auth_status():
    """Check if auth is enabled and if user is logged in."""
    return {"auth_enabled": is_auth_enabled(), "sessions": get_session_count()}


@app.post("/auth/login")
async def login(req: LoginRequest):
    """Login with password, returns session token."""
    if verify_password(req.password):
        token = create_session()
        resp = JSONResponse(content={"success": True, "token": token, "message": "Welcome back, Boss!"})
        resp.set_cookie("mj_token", token, max_age=86400, httponly=False, samesite="lax")
        return resp
    return JSONResponse(status_code=401, content={"success": False, "message": "Wrong password"})


@app.post("/auth/logout")
async def logout(request: Request):
    """Logout — invalidate session."""
    auth_header = request.headers.get("authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else request.cookies.get("mj_token", "")
    if token:
        invalidate_session(token)
    resp = JSONResponse(content={"success": True, "message": "Logged out"})
    resp.delete_cookie("mj_token")
    return resp


@app.post("/auth/change-password")
async def auth_change_password(req: ChangePasswordRequest):
    """Change password (requires current password)."""
    result = change_password(req.old_password, req.new_password)
    if result["success"]:
        resp = JSONResponse(content=result)
        resp.delete_cookie("mj_token")
        return resp
    return JSONResponse(status_code=400, content=result)


@app.post("/auth/toggle")
async def auth_toggle(req: ToggleAuthRequest):
    """Enable or disable auth."""
    return toggle_auth(req.enabled, req.password)


OLLAMA_URL = "http://localhost:11434/api/chat"
# MODEL is now dynamic — selected by Zeus router from installed Ollama models
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Supported file types for upload
TEXT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss", ".java", ".c",
    ".cpp", ".h", ".hpp", ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt",
    ".sql", ".sh", ".bat", ".ps1", ".r", ".lua", ".pl", ".dart", ".vue",
    ".svelte", ".log", ".env", ".gitignore", ".dockerfile",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

UPLOADS_DIR = Path(__file__).parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

CHATS_DIR = Path(__file__).parent / "chats"
CORE_MEMORY_FILE = Path(__file__).parent / "core_memory.json"
ACTIVE_CHAT_FILE = Path(__file__).parent / "active_chat.txt"

# Ensure chats directory exists
CHATS_DIR.mkdir(exist_ok=True)


def get_active_chat_id():
    if ACTIVE_CHAT_FILE.exists():
        return ACTIVE_CHAT_FILE.read_text(encoding="utf-8").strip()
    return None


def set_active_chat_id(chat_id):
    ACTIVE_CHAT_FILE.write_text(chat_id, encoding="utf-8")


def load_chat(chat_id):
    chat_file = CHATS_DIR / f"{chat_id}.json"
    if chat_file.exists():
        return json.loads(chat_file.read_text(encoding="utf-8"))
    return {"id": chat_id, "title": "New Chat", "messages": []}


def save_chat(chat_id, chat_data):
    chat_file = CHATS_DIR / f"{chat_id}.json"
    # Keep last 50 messages
    chat_data["messages"] = chat_data["messages"][-50:]
    chat_file.write_text(json.dumps(chat_data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_core_memory():
    if CORE_MEMORY_FILE.exists():
        return json.loads(CORE_MEMORY_FILE.read_text(encoding="utf-8"))
    return []


def save_core_memory(facts):
    CORE_MEMORY_FILE.write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8")


class ChatRequest(BaseModel):
    message: str


class RememberRequest(BaseModel):
    fact: str


@app.get("/chats")
async def list_chats():
    """List all chats for sidebar"""
    chats = []
    for f in sorted(CHATS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        data = json.loads(f.read_text(encoding="utf-8"))
        chats.append({"id": data["id"], "title": data["title"]})
    active = get_active_chat_id()
    return {"chats": chats, "active": active}


@app.get("/history")
async def get_history():
    chat_id = get_active_chat_id()
    if not chat_id:
        return {"history": []}
    chat = load_chat(chat_id)
    return {"history": chat["messages"]}


@app.post("/select-chat/{chat_id}")
async def select_chat(chat_id: str):
    set_active_chat_id(chat_id)
    chat = load_chat(chat_id)
    return {"history": chat["messages"]}


@app.get("/core-memory")
async def get_core_memory():
    facts = memory_store.get_all()
    return {
        "facts": [f.content for f in facts],
        "structured": [f.to_dict() for f in facts],
        "stats": memory_store.get_stats(),
    }


@app.post("/remember")
async def remember(req: RememberRequest):
    fact = memory_store.add(req.fact, source="user")
    return {"status": "ok", "facts": memory_store.get_flat_list()}


@app.delete("/delete-chat/{chat_id}")
async def delete_chat(chat_id: str):
    """Delete a specific chat."""
    chat_file = CHATS_DIR / f"{chat_id}.json"
    if chat_file.exists():
        chat_file.unlink()
    # If deleted chat was active, switch to another or create new
    if get_active_chat_id() == chat_id:
        remaining = sorted(CHATS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        if remaining:
            new_active = json.loads(remaining[0].read_text(encoding="utf-8"))["id"]
            set_active_chat_id(new_active)
        else:
            new_id = str(uuid.uuid4())[:8]
            save_chat(new_id, {"id": new_id, "title": "New Chat", "messages": []})
            set_active_chat_id(new_id)
    return {"status": "ok"}


@app.post("/new-chat")
async def new_chat():
    chat_id = str(uuid.uuid4())[:8]
    chat_data = {"id": chat_id, "title": "New Chat", "messages": []}
    save_chat(chat_id, chat_data)
    set_active_chat_id(chat_id)
    return {"status": "ok", "chat_id": chat_id}


class CommandRequest(BaseModel):
    command: str


@app.post("/execute")
async def execute_pc_command(req: CommandRequest):
    """Direct PC command execution endpoint."""
    cmd = parse_command(req.command)
    if cmd:
        action = cmd.get("action", "")
        if action == "mouse":
            from pc_control.mouse_control import execute_mouse_command
            return execute_mouse_command(cmd)
        elif action == "browser":
            from pc_control.browser_control import execute_browser_command
            return execute_browser_command(cmd)
        result = execute_command(cmd)
        return result
    return {"success": False, "message": "Command samajh nahi aaya."}


@app.post("/mouse")
async def mouse_control_endpoint(req: dict):
    """Direct mouse control API."""
    from pc_control.mouse_control import execute_mouse_command
    return execute_mouse_command(req)


@app.post("/browser")
async def browser_control_endpoint(req: dict):
    """Direct browser control API."""
    from pc_control.browser_control import execute_browser_command
    return execute_browser_command(req)


@app.get("/system-stats")
async def system_stats():
    """Get real CPU, RAM, Disk stats."""
    import asyncio
    stats = await asyncio.to_thread(get_system_stats)
    # Check for system warnings and create alerts
    check_system_warnings(stats)
    return stats


@app.get("/top-processes")
async def top_processes_stats():
    """Get top processes sorted by CPU/RAM usage."""
    import asyncio
    from pc_control.system_stats import get_top_processes
    return {"processes": await asyncio.to_thread(get_top_processes)}


@app.get("/reminders")
async def list_reminders():
    """Get active reminders."""
    return {"reminders": get_active_reminders()}


# ===== HERMES MESSAGING API =====

@app.get("/hermes/messaging/config")
async def hermes_msg_config():
    """Get messaging config (sensitive fields masked)."""
    return messaging_hub.get_config()

@app.post("/hermes/messaging/config/{platform}")
async def hermes_msg_update_config(platform: str, settings: dict):
    """Update messaging config for a platform."""
    return messaging_hub.update_config(platform, settings)

@app.post("/hermes/messaging/send")
async def hermes_msg_send(req: ChatRequest):
    """Send message. Body: {message: "platform: your message"} or detect from text."""
    text = req.message
    platform = messaging_hub.detect_platform(text)
    if not platform:
        return {"success": False, "error": "No platform detected. Include discord/slack/telegram/whatsapp/sms in your message."}
    message = messaging_hub.extract_message(text)
    return await messaging_hub.send(platform, message)

@app.post("/hermes/messaging/send/{platform}")
async def hermes_msg_send_platform(platform: str, req: ChatRequest):
    """Send message to specific platform."""
    return await messaging_hub.send(platform, req.message)

@app.post("/hermes/messaging/broadcast")
async def hermes_msg_broadcast(req: ChatRequest):
    """Broadcast message to all enabled platforms."""
    return await messaging_hub.broadcast(req.message)

@app.get("/hermes/messaging/history")
async def hermes_msg_history(limit: int = 50, platform: str = None):
    """Get messaging history."""
    return {"history": messaging_hub.get_history(limit, platform)}

@app.get("/hermes/messaging/stats")
async def hermes_msg_stats():
    """Get messaging statistics."""
    return messaging_hub.get_stats()

@app.get("/hermes/messaging/platforms")
async def hermes_msg_platforms():
    """Get enabled messaging platforms."""
    return {"platforms": messaging_hub.get_enabled_platforms()}

@app.post("/hermes/messaging/test/{platform}")
async def hermes_msg_test(platform: str):
    """Send a test message to a platform."""
    return await messaging_hub.send(platform, "Test message from MJ Assistant!")


@app.get("/health")
async def health_check():
    """Full system health check."""
    result = await check_health()
    # Create alerts for health issues
    if result.get("issues"):
        for issue in result["issues"]:
            create_alert(
                title="Health Issue",
                message=issue,
                severity=SEVERITY_WARNING if result["status"] != "critical" else SEVERITY_ERROR,
                category=CAT_HEALTH,
                source="health_monitor",
                auto_resolve_seconds=300,
            )
    return result


@app.get("/errors")
async def get_errors():
    """Get recent errors and stats."""
    return {
        "errors": get_recent_errors(20),
        "stats": get_error_stats(),
    }


@app.post("/errors/{error_id}/fix")
async def fix_error(error_id: str):
    """Manually trigger auto-fix for a specific error."""
    from self_healer.error_tracker import get_error_by_id
    entry = get_error_by_id(error_id)
    if not entry:
        return {"success": False, "message": "Error not found."}
    result = await attempt_fix(entry)
    return result


@app.post("/errors/{error_id}/analyze")
async def analyze_error_endpoint(error_id: str):
    """Get AI analysis of an error."""
    from self_healer.error_tracker import get_error_by_id
    entry = get_error_by_id(error_id)
    if not entry:
        return {"success": False, "message": "Error not found."}
    analysis = await analyze_error(entry)
    return {"analysis": analysis}


@app.post("/errors/clear")
async def clear_all_errors():
    """Clear all error logs."""
    clear_errors()
    return {"success": True, "message": "Error logs cleared."}


@app.get("/self-heal/status")
async def self_heal_status():
    """Unified self-healing dashboard — error rate, fixes, circuit breakers, health, recovery log."""
    from self_healer.auto_fixer import get_recovery_history
    from self_healer.alert_system import get_alert_stats, get_active_alerts

    error_stats = get_error_stats()
    diagnostics = get_diagnostics()
    alert_stats = get_alert_stats()
    active_alerts = get_active_alerts()
    recovery = get_recovery_history(10)
    circuit_states = zeus.get_circuit_states() if hasattr(zeus, 'get_circuit_states') else {}

    return {
        "errors": error_stats,
        "diagnostics_health": diagnostics.get("health", "UNKNOWN"),
        "success_rate": diagnostics.get("summary", {}).get("success_rate", "N/A"),
        "avg_response_time": diagnostics.get("summary", {}).get("avg_response_time", "N/A"),
        "alerts": {"stats": alert_stats, "active": active_alerts[:10]},
        "circuit_breakers": circuit_states,
        "recovery_history": recovery,
        "live_issues": diagnostics.get("active_issues", []),
    }


@app.get("/models")
async def list_models():
    """List available models (Ollama + Groq)."""
    models = await get_available_models()
    config = load_model_config()
    provider = get_active_provider()
    groq_status = await check_groq_connection() if is_groq_available() else {"available": False}
    return {
        "models": models,
        "active": config.get("active_model"),
        "auto_select": config.get("auto_select"),
        "model_map": config.get("model_map", {}),
        "provider": provider,
        "groq": groq_status,
    }


@app.get("/provider")
async def get_provider_status():
    """Get all AI providers status."""
    return {
        "active": get_active_provider(),
        "providers": get_all_providers_status(),
    }


@app.post("/provider/set")
async def set_provider_endpoint(req: dict):
    """Switch AI provider: ollama, groq, openai, anthropic, gemini."""
    from human_layer.model_manager import set_provider as _set_provider
    provider = req.get("provider", "").lower()
    result = _set_provider(provider)
    return result


@app.get("/provider/check/{provider_name}")
async def check_provider(provider_name: str):
    """Check a specific provider's connection."""
    p = provider_name.lower()
    checkers = {
        "groq": check_groq_connection,
        "openai": check_openai_connection,
        "anthropic": check_anthropic_connection,
        "gemini": check_gemini_connection,
    }
    if p in checkers:
        return await checkers[p]()
    elif p == "ollama":
        models = await get_available_models()
        return {"available": bool(models), "models": [m["name"] for m in models]}
    return {"error": f"Unknown provider: {provider_name}"}


@app.get("/provider/smart-route/{task_type}")
async def smart_route_endpoint(task_type: str):
    """Get smart routing recommendation for a task type."""
    return smart_route_provider(task_type)


@app.get("/provider/smart-route")
async def smart_route_all():
    """Get smart routing for all task types."""
    tasks = ["chat", "coding", "creative", "reasoning", "analysis", "vision", "translation"]
    return {t: smart_route_provider(t) for t in tasks}


@app.post("/models/route")
async def route_preview(req: ChatRequest):
    """Preview which model Zeus would pick for a message."""
    info = get_routing_info(req.message)
    return info


@app.post("/models/set-active")
async def set_active_model_endpoint(req: dict):
    """Set the active model for manual mode."""
    model = req.get("model", "")
    if not model:
        return {"success": False, "message": "No model specified"}
    # Validate model exists in Ollama
    available = await get_available_models()
    names = [m["name"] for m in available]
    if model not in names:
        return {"success": False, "message": f"Model '{model}' not installed. Available: {', '.join(names)}"}
    return set_active_model(model)


@app.post("/models/auto-select")
async def toggle_auto_endpoint(req: dict):
    """Toggle auto model selection on/off."""
    enabled = req.get("enabled", True)
    return toggle_auto_select(enabled)


@app.post("/models/set-task-model")
async def set_task_model_endpoint(req: dict):
    """Set which model handles a specific task type."""
    task = req.get("task", "")
    model = req.get("model", "")
    if not task or not model:
        return {"success": False, "message": "Task and model required"}
    return set_model_for_task(task, model)


@app.get("/plugins")
async def list_plugins_endpoint():
    """List loaded plugins."""
    return {"plugins": get_plugin_list()}


@app.post("/plugins/reload")
async def reload_plugins_endpoint():
    """Hot-reload all plugins."""
    from plugins.plugin_manager import reload_plugins
    loaded = reload_plugins()
    return {"success": True, "count": len(loaded)}


@app.get("/scheduled-tasks")
async def list_tasks_endpoint():
    """List scheduled tasks."""
    return list_scheduled_tasks()


@app.get("/processes")
async def list_processes():
    """Get top processes by CPU usage."""
    import asyncio
    from pc_control.process_manager import get_top_processes
    return {"processes": await asyncio.to_thread(get_top_processes)}


@app.post("/processes/{pid}/kill")
async def kill_proc(pid: int):
    """Kill a process by PID."""
    import asyncio
    from pc_control.process_manager import kill_process
    return await asyncio.to_thread(kill_process, pid)


@app.get("/network-stats")
async def network_stats():
    """Get network usage."""
    import asyncio
    from pc_control.process_manager import get_network_stats
    return await asyncio.to_thread(get_network_stats)


class NotifyRequest(BaseModel):
    title: str
    message: str


@app.post("/notify")
async def send_notification(req: NotifyRequest):
    """Send a Windows desktop notification."""
    import subprocess
    ps = f'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$text = $template.GetElementsByTagName("text")
$text.Item(0).AppendChild($template.CreateTextNode("{req.title}")) > $null
$text.Item(1).AppendChild($template.CreateTextNode("{req.message}")) > $null
$toast = [Windows.UI.Notifications.ToastNotification]::new($template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("MJ Assistant").Show($toast)
'''
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=10)
        return {"success": True}
    except Exception:
        # Fallback: simple BurntToast or msg box
        try:
            ps_fallback = f'''
Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.Visible = $true
$n.ShowBalloonTip(5000, "{req.title}", "{req.message}", [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Seconds 6
$n.Dispose()
'''
            subprocess.Popen(["powershell", "-NoProfile", "-Command", ps_fallback])
            return {"success": True}
        except Exception:
            return {"success": False}


# --- Email, Clipboard, Tracker, Image endpoints ---

@app.get("/email/config")
async def get_email_config():
    from pc_control.email_manager import load_email_config
    config = load_email_config()
    safe = {k: v for k, v in config.items() if k != "password"}
    return safe

@app.get("/clipboard/history")
async def get_clipboard_history():
    from pc_control.clipboard_manager import get_history
    return {"history": get_history(20)}

@app.get("/app-usage")
async def get_app_usage():
    return get_usage_report()

@app.get("/generated-images")
async def list_gen_images():
    from pc_control.image_gen import list_generated_images
    return list_generated_images()


# ===== ALERT SYSTEM API =====

@app.get("/alerts")
async def alerts_endpoint():
    """Get all alerts with stats."""
    return {
        "alerts": get_all_alerts(50),
        "active": get_active_alerts(),
        "stats": get_alert_stats(),
    }

@app.get("/alerts/active")
async def active_alerts():
    """Get only unresolved alerts."""
    return {"alerts": get_active_alerts(), "stats": get_alert_stats()}

@app.post("/alerts/{alert_id}/resolve")
async def resolve_alert_endpoint(alert_id: str):
    """Manually resolve an alert."""
    resolve_alert(alert_id, "Manually resolved by user")
    return {"success": True, "message": "Alert resolved."}

@app.post("/alerts/clear")
async def clear_alerts_endpoint():
    """Clear all alerts."""
    clear_all_alerts()
    return {"success": True, "message": "All alerts cleared."}

@app.post("/alerts/clear-resolved")
async def clear_resolved_endpoint():
    """Clear only resolved alerts."""
    clear_resolved()
    return {"success": True, "message": "Resolved alerts cleared."}

@app.get("/alerts/stream")
async def alert_stream():
    """SSE stream for real-time alerts. Dashboard connects here."""
    queue = subscribe()

    async def event_generator():
        try:
            # Send initial stats
            yield f"data: {json.dumps({'type': 'init', 'stats': get_alert_stats(), 'active': get_active_alerts()})}\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat', 'stats': get_alert_stats()})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            unsubscribe(queue)

    import asyncio
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ===== ZEUS MODULE API =====

@app.get("/zeus/modules")
async def zeus_list_modules():
    """List all registered modules with status."""
    return {"modules": zeus.get_all_modules()}


@app.get("/zeus/modules/{module_name}")
async def zeus_module_detail(module_name: str):
    """Get module settings and info."""
    data = zeus.get_module_settings(module_name)
    if not data:
        return {"error": "Module not found"}
    return data


@app.post("/zeus/modules/{module_name}/settings")
async def zeus_update_module(module_name: str, settings: dict):
    """Update module settings."""
    ok = zeus.update_module_settings(module_name, settings)
    return {"success": ok}


@app.post("/zeus/modules/{module_name}/execute")
async def zeus_execute_module(module_name: str, req: ChatRequest):
    """Execute a specific module directly."""
    mod = zeus.get_module(module_name)
    if not mod:
        return {"error": "Module not found"}
    if not mod.enabled:
        return {"error": "Module is disabled"}
    try:
        result = await mod.execute_async(req.message, {})
    except Exception:
        result = mod.execute(req.message, {})
    return result


@app.get("/zeus/stats")
async def zeus_execution_stats():
    """Get Zeus module execution analytics."""
    return zeus.get_execution_stats()


@app.get("/zeus/history")
async def zeus_history(limit: int = 20):
    """Get recent Zeus execution history."""
    return {"history": zeus.get_recent_history(limit)}


@app.post("/zeus/route")
async def zeus_route_test(req: ChatRequest):
    """Test route a message to see which modules match."""
    matches = zeus.route_all(req.message, "", {})
    return {
        "matches": [
            {"module": m.name, "display_name": m.display_name, "confidence": round(s, 3)}
            for m, s in matches
        ]
    }


@app.post("/zeus/parallel")
async def zeus_parallel_execute(req: ChatRequest):
    """Execute all matching modules in parallel."""
    matches = zeus.route_all(req.message, "", {}, min_confidence=0.3)
    if not matches:
        return {"results": [], "message": "No modules matched."}
    results = await zeus.execute_parallel(matches, req.message, {})
    return {"results": results}


# ===== ZEUS ADVANCED API =====

@app.get("/zeus/workflows")
async def zeus_list_workflows():
    """List all registered workflows."""
    return {"workflows": zeus.list_workflows()}

@app.get("/zeus/workflows/{name}")
async def zeus_get_workflow(name: str):
    """Get workflow details."""
    wf = zeus.get_workflow(name)
    if not wf:
        return {"error": "Workflow not found"}
    return wf

@app.post("/zeus/workflows")
async def zeus_create_workflow(name: str = Form(...), description: str = Form(""),
                                steps: str = Form("[]")):
    """Create a new workflow."""
    step_list = json.loads(steps)
    zeus.register_workflow(name, step_list, description)
    return {"success": True, "name": name}

@app.put("/zeus/workflows/{name}")
async def zeus_update_workflow(name: str, description: str = Form(None), steps: str = Form(None)):
    """Update an existing workflow."""
    step_list = json.loads(steps) if steps else None
    ok = zeus.update_workflow(name, step_list, description)
    return {"success": ok}

@app.delete("/zeus/workflows/{name}")
async def zeus_delete_workflow(name: str):
    """Delete a workflow."""
    ok = zeus.delete_workflow(name)
    return {"success": ok}

@app.post("/zeus/workflows/{name}/run")
async def zeus_run_workflow(name: str, req: ChatRequest):
    """Execute a named workflow."""
    result = await zeus.run_workflow(name, req.message, {})
    return result

@app.post("/zeus/plan")
async def zeus_plan(req: ChatRequest):
    """Plan and execute a complex task (local rules + LLM fallback)."""
    result = await zeus.plan_and_execute(req.message, {})
    return result

@app.post("/zeus/breakdown")
async def zeus_breakdown(req: ChatRequest):
    """Break a task into steps without executing (dry run)."""
    breakdown = zeus.breakdown_task(req.message)
    return breakdown

@app.post("/zeus/smart-route")
async def zeus_smart_route(req: ChatRequest):
    """Full intelligent routing: intent → modules → plan check."""
    result = await zeus.smart_route(req.message, {})
    return result

@app.get("/zeus/recovery")
async def zeus_recovery_stats():
    """Get error recovery and circuit breaker stats."""
    return zeus.get_recovery_stats()


# ===== AGENT FRAMEWORK API =====

# --- Message Bus ---
@app.post("/framework/bus/publish")
async def bus_publish(topic: str = Form(...), sender: str = Form("api"), data: str = Form(None)):
    """Publish a message to the bus."""
    payload = json.loads(data) if data else None
    msg = message_bus.publish(topic, sender, payload)
    return msg.to_dict()

@app.get("/framework/bus/history")
async def bus_history(topic: str = None, limit: int = 50):
    """Get message bus history."""
    return {"messages": message_bus.get_history(topic, limit)}

@app.get("/framework/bus/stats")
async def bus_stats():
    """Get message bus statistics."""
    return message_bus.get_stats()

# --- Event System ---
@app.post("/framework/events/emit")
async def events_emit(name: str = Form(...), source: str = Form("api"), data: str = Form(None)):
    """Emit a system event."""
    payload = json.loads(data) if data else None
    evt = event_system.emit(name, source, payload)
    return evt.to_dict()

@app.get("/framework/events/history")
async def events_history(name: str = None, limit: int = 50):
    """Get event history."""
    return {"events": event_system.get_history(name, limit)}

@app.get("/framework/events/stats")
async def events_stats():
    """Get event system statistics."""
    return event_system.get_stats()

@app.get("/framework/events/types")
async def events_types():
    """List all known event types."""
    return {"events": event_system.list_events()}

# --- Shared Memory ---
@app.post("/framework/memory/set")
async def memory_set(key: str = Form(...), value: str = Form(...),
                     namespace: str = Form("global"), ttl: int = Form(None)):
    """Set a shared memory value."""
    try:
        val = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        val = value
    shared_memory.set(key, val, ttl=ttl if ttl and ttl > 0 else None, namespace=namespace)
    return {"success": True, "key": key, "namespace": namespace}

@app.get("/framework/memory/get/{key}")
async def memory_get(key: str, namespace: str = "global"):
    """Get a shared memory value."""
    val = shared_memory.get(key, namespace=namespace)
    return {"key": key, "value": val, "found": val is not None}

@app.get("/framework/memory/all")
async def memory_all():
    """Get all shared memory entries."""
    return {"memory": shared_memory.get_all()}

@app.get("/framework/memory/namespace/{namespace}")
async def memory_namespace(namespace: str):
    """Get all keys in a namespace."""
    return {"namespace": namespace, "data": shared_memory.get_namespace(namespace)}

@app.get("/framework/memory/stats")
async def memory_stats():
    """Get shared memory statistics."""
    return shared_memory.stats()

@app.delete("/framework/memory/{key}")
async def memory_delete(key: str, namespace: str = "global"):
    """Delete a shared memory key."""
    deleted = shared_memory.delete(key, namespace=namespace)
    return {"success": deleted}

# --- Task Queue ---
@app.post("/framework/queue/submit")
async def queue_submit(name: str = Form(...), handler: str = Form(...),
                       params: str = Form("{}"), priority: int = Form(5),
                       submitted_by: str = Form("api")):
    """Submit a task to the queue."""
    p = json.loads(params)
    task = task_queue.submit(name, handler, p, priority, submitted_by=submitted_by)
    return task.to_dict()

@app.post("/framework/queue/process")
async def queue_process():
    """Process the next task in the queue."""
    result = await task_queue.process_next()
    if not result:
        return {"message": "Queue is empty."}
    return result

@app.post("/framework/queue/process-all")
async def queue_process_all():
    """Process all tasks in the queue."""
    results = await task_queue.process_all()
    return {"processed": len(results), "results": results}

@app.get("/framework/queue")
async def queue_list():
    """Get pending tasks in the queue."""
    return {"queue": task_queue.get_queue()}

@app.get("/framework/queue/stats")
async def queue_stats():
    """Get task queue statistics."""
    return task_queue.get_stats()

@app.get("/framework/queue/history")
async def queue_history(limit: int = 50):
    """Get completed task history."""
    return {"history": task_queue.get_history(limit)}

@app.get("/framework/queue/{task_id}")
async def queue_task(task_id: str):
    """Get task details by ID."""
    task = task_queue.get_task(task_id)
    if not task:
        return {"error": "Task not found"}
    return task

@app.delete("/framework/queue/{task_id}")
async def queue_cancel(task_id: str):
    """Cancel a pending task."""
    cancelled = task_queue.cancel(task_id)
    return {"success": cancelled}

# --- Framework Overview ---
@app.get("/framework/status")
async def framework_status():
    """Get full agent framework status."""
    return {
        "message_bus": message_bus.get_stats(),
        "event_system": event_system.get_stats(),
        "shared_memory": shared_memory.stats(),
        "task_queue": task_queue.get_stats(),
    }


# ===== KNOWLEDGE GRAPH & CITATIONS API =====

@app.get("/knowledge/graph/stats")
async def kg_stats():
    """Get knowledge graph statistics."""
    return knowledge_graph.get_stats()

@app.get("/knowledge/graph")
async def kg_get_all(limit: int = 200):
    """Get full graph data for visualization."""
    return knowledge_graph.get_all(limit)

@app.get("/knowledge/graph/node/{label}")
async def kg_get_node(label: str):
    """Get a node and its connections."""
    node = knowledge_graph.get_node(label)
    if not node:
        return {"error": "Node not found"}
    return node

@app.get("/knowledge/graph/search")
async def kg_search(q: str, limit: int = 10):
    """Search nodes in the knowledge graph."""
    return {"results": knowledge_graph.search_nodes(q, limit)}

@app.get("/knowledge/graph/path")
async def kg_find_path(from_node: str, to_node: str):
    """Find shortest path between two nodes."""
    path = knowledge_graph.find_path(from_node, to_node)
    if not path:
        return {"path": None, "message": "No path found"}
    return {"path": path, "length": len(path)}

@app.post("/knowledge/graph/build")
async def kg_build():
    """Build/rebuild knowledge graph from all KB documents."""
    result = knowledge_graph.build_from_kb()
    return result

@app.post("/knowledge/graph/add")
async def kg_add_node(label: str = Form(...), entity_type: str = Form("concept"),
                      source: str = Form("")):
    """Manually add a node."""
    node_id = knowledge_graph.add_node(label, entity_type, source)
    return {"success": True, "node_id": node_id}

@app.post("/knowledge/graph/connect")
async def kg_add_edge(from_label: str = Form(...), to_label: str = Form(...),
                      relation: str = Form("relates_to")):
    """Add an edge between two nodes."""
    knowledge_graph.add_edge(from_label, to_label, relation)
    return {"success": True}

@app.post("/research")
async def research_endpoint(req: ChatRequest):
    """Deep multi-source research with citations."""
    result = await deep_research(req.message, max_sources=5, scrape_top=3)
    return result

# --- Citations ---
@app.get("/citations")
async def citations_list():
    """Get current session citations."""
    return {"citations": citation_manager.get_session_citations()}

@app.get("/citations/bibliography")
async def citations_bibliography(format: str = "apa"):
    """Get formatted bibliography."""
    return {"bibliography": citation_manager.get_bibliography(format)}

@app.get("/citations/stats")
async def citations_stats():
    """Get citation statistics."""
    return citation_manager.get_stats()

@app.get("/citations/history")
async def citations_history(limit: int = 20):
    """Get citation history."""
    return {"history": citation_manager.get_history(limit)}

@app.post("/citations/clear")
async def citations_clear():
    """Archive and clear current session citations."""
    citation_manager.clear_session()
    return {"success": True}


# ===== CONSTITUTIONAL AI / SAFETY API =====

@app.post("/safety/check-input")
async def safety_check_input(req: ChatRequest):
    """Validate user input for safety."""
    return constitutional_ai.validate_input(req.message)

@app.post("/safety/check-output")
async def safety_check_output(req: ChatRequest):
    """Validate LLM output for safety. Send query in 'message' field."""
    # Expects {message: "query|||response"} separated by |||
    parts = req.message.split("|||", 1)
    query = parts[0].strip()
    response = parts[1].strip() if len(parts) > 1 else query
    return constitutional_ai.validate_output(response, query)

@app.post("/safety/critique")
async def safety_critique(req: ChatRequest):
    """Self-critique a response. Send as 'query|||response'."""
    parts = req.message.split("|||", 1)
    query = parts[0].strip()
    response = parts[1].strip() if len(parts) > 1 else query
    return constitutional_ai.critique_response(query, response)

@app.post("/safety/hallucination")
async def safety_hallucination(req: ChatRequest):
    """Detect hallucinations in text."""
    return constitutional_ai.detect_hallucination(req.message)

@app.post("/safety/confidence")
async def safety_confidence(req: ChatRequest):
    """Score response confidence. Send as 'query|||response'."""
    parts = req.message.split("|||", 1)
    query = parts[0].strip()
    response = parts[1].strip() if len(parts) > 1 else query
    return constitutional_ai.score_confidence(query, response)

@app.post("/safety/full-check")
async def safety_full_check(req: ChatRequest):
    """Full safety pipeline check. Send as 'query|||response'."""
    parts = req.message.split("|||", 1)
    query = parts[0].strip()
    response = parts[1].strip() if len(parts) > 1 else query
    return constitutional_ai.check(query, response)

@app.post("/safety/policy")
async def safety_policy_check(req: ChatRequest):
    """Check text against content policies."""
    return constitutional_ai.check_policy(req.message)

@app.get("/safety/config")
async def safety_get_config():
    """Get safety configuration."""
    return constitutional_ai.get_config()

@app.post("/safety/config")
async def safety_update_config(settings: dict):
    """Update safety configuration."""
    return constitutional_ai.update_config(settings)

@app.get("/safety/stats")
async def safety_stats():
    """Get safety check statistics."""
    return constitutional_ai.get_stats()

@app.get("/safety/audit")
async def safety_audit(limit: int = 50):
    """Get safety audit log."""
    return {"audit": constitutional_ai.get_audit_log(limit)}

@app.post("/safety/audit/clear")
async def safety_audit_clear():
    """Clear safety audit log."""
    constitutional_ai.clear_audit()
    return {"success": True}


# ===== REFLECTION ENGINE (V16) API =====

@app.post("/reflection/log-mistake")
async def reflection_log_mistake(req: ChatRequest):
    """Log a mistake. message format: module|type|query|response"""
    parts = req.message.split("|", 3)
    module = parts[0].strip() if len(parts) > 0 else "unknown"
    mtype = parts[1].strip() if len(parts) > 1 else "wrong_answer"
    query = parts[2].strip() if len(parts) > 2 else req.message
    response = parts[3].strip() if len(parts) > 3 else ""
    return reflection_engine.log_mistake(query, response, module, mtype)

@app.post("/reflection/log-success")
async def reflection_log_success(req: ChatRequest):
    """Log a success for a module."""
    reflection_engine.log_success(req.message.strip())
    return {"success": True}

@app.get("/reflection/mistakes")
async def reflection_mistakes(limit: int = 50, module: str = None):
    """Get mistake history."""
    return {"mistakes": reflection_engine.get_mistakes(limit, module)}

@app.post("/reflection/report")
async def reflection_generate_report(days: int = 7):
    """Generate a learning report."""
    return reflection_engine.generate_report(days)

@app.get("/reflection/reports")
async def reflection_get_reports(limit: int = 10):
    """Get past reports."""
    return {"reports": reflection_engine.get_reports(limit)}

@app.get("/reflection/daily")
async def reflection_daily():
    """Get today's daily reflection."""
    return reflection_engine.daily_reflection()

@app.get("/reflection/scores")
async def reflection_agent_scores():
    """Get all agent performance scores."""
    return reflection_engine.get_agent_scores()

@app.get("/reflection/scores/{module}")
async def reflection_agent_score(module: str):
    """Get score for a specific agent."""
    score = reflection_engine.get_agent_score(module)
    if not score:
        return {"error": "Module not found"}
    return score

@app.get("/reflection/suggestions")
async def reflection_suggestions():
    """Get improvement suggestions."""
    return {"suggestions": reflection_engine.get_suggestions()}

@app.get("/reflection/stats")
async def reflection_stats():
    """Get reflection engine stats."""
    return reflection_engine.get_stats()


# ===== LEARNING ENGINE (V17) API =====

@app.post("/learning/record")
async def learning_record_action(req: ChatRequest):
    """Record a user action. message format: action|module"""
    parts = req.message.split("|", 1)
    action = parts[0].strip()
    module = parts[1].strip() if len(parts) > 1 else ""
    learning_engine.record_action(action, module)
    return {"success": True}

@app.post("/learning/learn")
async def learning_learn_preference(req: ChatRequest):
    """Learn from a user message."""
    learning_engine.learn_preference(req.message)
    return {"success": True}

@app.get("/learning/habits")
async def learning_get_habits():
    """Get detected habits."""
    return {"habits": learning_engine.get_habits()}

@app.post("/learning/habits/detect")
async def learning_detect_habits():
    """Run habit detection analysis."""
    return {"habits": learning_engine.detect_habits()}

@app.get("/learning/preferences")
async def learning_get_preferences():
    """Get learned preferences."""
    return learning_engine.get_preferences()

@app.get("/learning/preference-prompt")
async def learning_preference_prompt():
    """Get preference-based prompt addition."""
    return {"prompt": learning_engine.get_preference_prompt()}

@app.post("/learning/prompt-feedback")
async def learning_prompt_feedback(req: ChatRequest):
    """Log prompt feedback. message format: type|positive|notes"""
    parts = req.message.split("|", 2)
    ptype = parts[0].strip() if len(parts) > 0 else "general"
    positive = parts[1].strip().lower() in ("true", "1", "yes") if len(parts) > 1 else True
    notes = parts[2].strip() if len(parts) > 2 else ""
    learning_engine.log_prompt_feedback(ptype, req.message, positive, notes)
    return {"success": True}

@app.get("/learning/prompt-suggestions")
async def learning_prompt_suggestions():
    """Get prompt improvement suggestions."""
    return {"suggestions": learning_engine.get_prompt_suggestions()}

@app.get("/learning/prompt-stats")
async def learning_prompt_stats():
    """Get prompt optimization statistics."""
    return learning_engine.get_prompt_stats()

@app.get("/learning/workflows")
async def learning_get_workflows():
    """Get detected workflow patterns."""
    return {"workflows": learning_engine.get_workflows()}

@app.post("/learning/workflows/detect")
async def learning_detect_workflows():
    """Run workflow pattern detection."""
    return {"workflows": learning_engine.detect_workflows()}

@app.get("/learning/stats")
async def learning_stats():
    """Get learning engine stats."""
    return learning_engine.get_stats()


# ===== VISION ENGINE (V12) API =====

@app.post("/vision/screenshot")
async def vision_screenshot(req: ChatRequest):
    """Take a screenshot. Optional message: monitor=N or region=x,y,w,h"""
    region = None
    monitor = 0
    msg = req.message or ""
    import re as _re
    mon_match = _re.search(r'monitor\s*=?\s*(\d+)', msg)
    if mon_match:
        monitor = int(mon_match.group(1))
    reg_match = _re.search(r'region\s*=?\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', msg)
    if reg_match:
        region = {"x": int(reg_match.group(1)), "y": int(reg_match.group(2)),
                  "width": int(reg_match.group(3)), "height": int(reg_match.group(4))}
    return vision_engine.take_screenshot(region=region, monitor=monitor)

@app.get("/vision/monitors")
async def vision_monitors():
    """List connected monitors."""
    return vision_engine.get_monitors()

@app.post("/vision/camera")
async def vision_camera(req: ChatRequest):
    """Capture from webcam. Optional message: camera index."""
    idx = 0
    if req.message and req.message.strip().isdigit():
        idx = int(req.message.strip())
    return vision_engine.capture_camera(camera_index=idx)

@app.get("/vision/cameras")
async def vision_cameras():
    """List available cameras."""
    return vision_engine.list_cameras()

@app.post("/vision/detect")
async def vision_detect(req: ChatRequest):
    """Detect objects in an image. message = image path (or empty for screenshot)."""
    image_path = req.message.strip() if req.message else None
    if not image_path:
        ss = vision_engine.take_screenshot()
        if not ss.get("success"):
            return {"success": False, "message": "Screenshot failed"}
        image_path = ss["filepath"]
    return vision_engine.detect_objects(image_path)

@app.post("/vision/analyze")
async def vision_analyze(req: ChatRequest):
    """AI screen analysis. message = image path (or empty for live screen)."""
    image_path = req.message.strip() if req.message else None
    return vision_engine.analyze_screen(image_path or None)

@app.post("/vision/compare")
async def vision_compare(req: ChatRequest):
    """Compare two screenshots. message format: path1|path2"""
    parts = (req.message or "").split("|", 1)
    if len(parts) < 2:
        return {"success": False, "message": "Provide two paths separated by |"}
    return vision_engine.compare_screenshots(parts[0].strip(), parts[1].strip())

@app.get("/vision/history")
async def vision_history(limit: int = 50, type: str = ""):
    """Get vision operation history."""
    return {"history": vision_engine.get_history(limit=limit, type_filter=type)}

@app.get("/vision/detections")
async def vision_detections(limit: int = 20):
    """Get recent object detections."""
    return {"detections": vision_engine.get_recent_detections(limit=limit)}

@app.get("/vision/analyses")
async def vision_analyses(limit: int = 10):
    """Get recent screen analyses."""
    return {"analyses": vision_engine.get_recent_analyses(limit=limit)}

@app.get("/vision/stats")
async def vision_stats():
    """Get vision engine statistics."""
    return vision_engine.get_stats()


# ===== SENTINEL SECURITY (V15) API =====

@app.post("/sentinel/check-permission")
async def sentinel_check_permission(req: ChatRequest):
    """Check permission. message format: user|action|module(optional)"""
    parts = (req.message or "").split("|", 2)
    user = parts[0].strip() if parts else "default"
    action = parts[1].strip() if len(parts) > 1 else "chat"
    module = parts[2].strip() if len(parts) > 2 else ""
    return sentinel_engine.check_permission(user, action, module)

@app.get("/sentinel/roles")
async def sentinel_roles():
    """List all roles."""
    return {"roles": sentinel_engine.get_roles()}

@app.post("/sentinel/roles")
async def sentinel_create_role(req: ChatRequest):
    """Create a role. message format: name|description|perm1,perm2,..."""
    parts = (req.message or "").split("|", 2)
    name = parts[0].strip() if parts else ""
    desc = parts[1].strip() if len(parts) > 1 else ""
    perms = [p.strip() for p in parts[2].split(",")] if len(parts) > 2 else ["chat"]
    if not name:
        return {"success": False, "message": "Role name required"}
    return sentinel_engine.create_role(name, desc, perms)

@app.post("/sentinel/assign-role")
async def sentinel_assign_role(req: ChatRequest):
    """Assign role to user. message format: user|role"""
    parts = (req.message or "").split("|", 1)
    user = parts[0].strip() if parts else ""
    role = parts[1].strip() if len(parts) > 1 else ""
    if not user or not role:
        return {"success": False, "message": "Format: user|role"}
    return sentinel_engine.assign_role(user, role)

@app.post("/sentinel/vault/store")
async def sentinel_store_secret(req: ChatRequest):
    """Store a secret. message format: key|value|category(optional)"""
    parts = (req.message or "").split("|", 2)
    key = parts[0].strip() if parts else ""
    value = parts[1].strip() if len(parts) > 1 else ""
    category = parts[2].strip() if len(parts) > 2 else "general"
    if not key or not value:
        return {"success": False, "message": "Format: key|value"}
    return sentinel_engine.store_secret(key, value, category)

@app.get("/sentinel/vault/{key}")
async def sentinel_get_secret(key: str):
    """Retrieve a secret by key."""
    return sentinel_engine.get_secret(key)

@app.delete("/sentinel/vault/{key}")
async def sentinel_delete_secret(key: str):
    """Delete a secret."""
    return sentinel_engine.delete_secret(key)

@app.get("/sentinel/vault")
async def sentinel_list_secrets():
    """List all secrets (keys only, no values)."""
    return sentinel_engine.list_secrets()

@app.get("/sentinel/audit")
async def sentinel_audit(limit: int = 100, event: str = "", user: str = "", status: str = ""):
    """Query audit logs."""
    return {"logs": sentinel_engine.get_audit_log(limit=limit, event_type=event, user=user, status=status)}

@app.get("/sentinel/audit/stats")
async def sentinel_audit_stats():
    """Get audit log statistics."""
    return sentinel_engine.get_audit_stats()

@app.post("/sentinel/audit/clean")
async def sentinel_audit_clean(req: ChatRequest):
    """Clean old audit logs. message = days (default 30)."""
    days = 30
    if req.message and req.message.strip().isdigit():
        days = int(req.message.strip())
    return sentinel_engine.clear_old_audit_logs(days)

@app.post("/sentinel/scan")
async def sentinel_scan(req: ChatRequest):
    """Scan text for security threats."""
    return sentinel_engine.scan_input(req.message or "", source="api")

@app.get("/sentinel/threats")
async def sentinel_threats(limit: int = 50, severity: str = ""):
    """Get detected threats."""
    return {"threats": sentinel_engine.get_threats(limit=limit, severity=severity)}

@app.get("/sentinel/threats/stats")
async def sentinel_threat_stats():
    """Get threat detection statistics."""
    return sentinel_engine.get_threat_stats()

@app.post("/sentinel/block")
async def sentinel_block_action(req: ChatRequest):
    """Block an action globally."""
    return sentinel_engine.block_action(req.message or "")

@app.post("/sentinel/unblock")
async def sentinel_unblock_action(req: ChatRequest):
    """Unblock an action."""
    return sentinel_engine.unblock_action(req.message or "")

@app.get("/sentinel/health")
async def sentinel_health():
    """Run security health check."""
    return sentinel_engine.health_check()

@app.get("/sentinel/config")
async def sentinel_get_config():
    """Get sentinel configuration."""
    return sentinel_engine.get_config()

@app.post("/sentinel/config")
async def sentinel_update_config(req: ChatRequest):
    """Update sentinel config. message = JSON string."""
    try:
        updates = json.loads(req.message)
    except Exception:
        return {"success": False, "message": "Invalid JSON"}
    return sentinel_engine.update_config(updates)

@app.get("/sentinel/stats")
async def sentinel_all_stats():
    """Get overall sentinel statistics."""
    return sentinel_engine.get_stats()


def get_file_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext in TEXT_EXTENSIONS:
        return "text"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext == ".pdf":
        return "pdf"
    return "unknown"


async def process_uploaded_file(file: UploadFile) -> dict:
    """Process uploaded file and return context info."""
    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE:
        return {"error": "File too large. Maximum size is 10 MB."}

    file_type = get_file_type(file.filename)
    result = {"filename": file.filename, "type": file_type, "context": "", "images": []}

    if file_type == "text":
        try:
            text_content = contents.decode("utf-8")
        except UnicodeDecodeError:
            text_content = contents.decode("latin-1")
        result["context"] = f"\n\n--- Attached File: {file.filename} ---\n{text_content[:8000]}\n--- End of File ---"

    elif file_type == "image":
        img_b64 = base64.b64encode(contents).decode("utf-8")
        result["images"].append(img_b64)
        result["context"] = f"\n\n[User attached an image: {file.filename}. Analyze what you see in the image.]"

    elif file_type == "pdf":
        result["context"] = f"\n\n--- Attached PDF: {file.filename} ---\n"
        try:
            raw_text = contents.decode("latin-1")
            text_parts = []
            for segment in raw_text.split("BT"):
                if "ET" in segment:
                    text_parts.append(segment.split("ET")[0])
            extracted = " ".join(text_parts)
            cleaned = "".join(c for c in extracted if c.isprintable() or c in "\n\t")
            if cleaned.strip():
                result["context"] += cleaned[:5000]
            else:
                result["context"] += "(Could not extract readable text. May be scanned/image-based.)"
        except Exception:
            result["context"] += "(Failed to read PDF content.)"
        result["context"] += "\n--- End of PDF ---"

    else:
        result["context"] = f"\n\n[User attached a file: {file.filename} (unsupported type)]"

    # Save file to uploads dir
    save_path = UPLOADS_DIR / file.filename
    save_path.write_bytes(contents)

    return result


@app.post("/chat")
async def chat(
    message: str = Form(...),
    file: Optional[UploadFile] = File(None),
):
    # Helper to save command result to chat
    def _save_cmd_to_chat(user_msg, reply_msg):
        cid = get_active_chat_id()
        if not cid:
            cid = str(uuid.uuid4())[:8]
            set_active_chat_id(cid)
        cd = load_chat(cid)
        cd["messages"].append({"role": "user", "content": user_msg})
        cd["messages"].append({"role": "assistant", "content": reply_msg})
        if cd["title"] == "New Chat":
            cd["title"] = user_msg[:40]
        save_chat(cid, cd)

    # Check for reminder/timer
    reminder = parse_reminder(message)
    if reminder:
        rid = set_reminder(reminder["delay_seconds"], reminder["message"])
        msg = f"Done! {reminder['time_desc']} baad remind karunga: {reminder['message']}"
        async def rem_stream():
            yield f"data: {json.dumps({'token': msg})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, msg)
        return StreamingResponse(rem_stream(), media_type="text/event-stream")

    # Check for screen recording commands
    rec_cmd = parse_recording_command(message)
    if rec_cmd:
        if rec_cmd["action"] == "start":
            result = start_recording()
        else:
            result = stop_recording()
        async def rec_stream():
            yield f"data: {json.dumps({'token': result['message']})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy' if result['success'] else 'confused'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, result["message"])
        return StreamingResponse(rec_stream(), media_type="text/event-stream")

    # Check for scheduled task commands
    sched = parse_schedule(message)
    if sched:
        if sched["type"] == "list":
            result = list_scheduled_tasks()
        elif sched["type"] == "cancel":
            result = cancel_task(sched.get("task_number"))
        else:
            result = add_scheduled_task(sched)
        async def sched_stream():
            yield f"data: {json.dumps({'token': result['message']})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy' if result.get('success') else 'confused'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, result["message"])
        return StreamingResponse(sched_stream(), media_type="text/event-stream")

    # Check for model management commands
    model_cmd = parse_model_command(message)
    if model_cmd:
        result = await handle_model_command(model_cmd)
        async def model_stream():
            yield f"data: {json.dumps({'token': result['message']})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy' if result.get('success') else 'confused'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, result["message"])
        return StreamingResponse(model_stream(), media_type="text/event-stream")

    # Check for plugin management commands
    plugin_mgmt = parse_plugin_command(message)
    if plugin_mgmt:
        result = handle_plugin_management(plugin_mgmt)
        async def plugin_mgmt_stream():
            yield f"data: {json.dumps({'token': result['message']})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, result["message"])
        return StreamingResponse(plugin_mgmt_stream(), media_type="text/event-stream")

    # Check if any plugin handles this
    matched_plugin = match_plugin(message)
    if matched_plugin:
        result = run_plugin(matched_plugin, message)
        async def plugin_stream():
            yield f"data: {json.dumps({'token': result['message']})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy' if result.get('success') else 'confused'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, result["message"])
        return StreamingResponse(plugin_stream(), media_type="text/event-stream")

    # Check for email commands
    email_cmd = parse_email_command(message)
    if email_cmd:
        result = handle_email_command(email_cmd)
        async def email_stream():
            yield f"data: {json.dumps({'token': result['message']})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy' if result.get('success') else 'confused'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, result["message"])
        return StreamingResponse(email_stream(), media_type="text/event-stream")

    # Check for clipboard commands
    clip_cmd = parse_clipboard_command(message)
    if clip_cmd:
        result = handle_clipboard_command(clip_cmd)
        async def clip_stream():
            yield f"data: {json.dumps({'token': result['message']})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy' if result.get('success') else 'confused'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, result["message"])
        return StreamingResponse(clip_stream(), media_type="text/event-stream")

    # Check for app tracker commands
    tracker_cmd = parse_tracker_command(message)
    if tracker_cmd:
        result = handle_tracker_command(tracker_cmd)
        async def tracker_stream():
            yield f"data: {json.dumps({'token': result['message']})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy' if result.get('success') else 'confused'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, result["message"])
        return StreamingResponse(tracker_stream(), media_type="text/event-stream")

    # Check for image generation commands
    img_cmd = parse_image_command(message)
    if img_cmd:
        result = await handle_image_command(img_cmd)
        async def img_stream():
            msg = result["message"]
            yield f"data: {json.dumps({'token': msg})}\n\n"
            if result.get("url"):
                yield f"data: {json.dumps({'image_url': result['url']})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy' if result.get('success') else 'confused'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, result["message"])
        return StreamingResponse(img_stream(), media_type="text/event-stream")

    # Check for file manager commands
    file_cmd = parse_file_command(message)
    if file_cmd:
        result = execute_file_command(file_cmd)
        async def file_mgr_stream():
            yield f"data: {json.dumps({'token': result['message']})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy' if result['success'] else 'confused'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, result["message"])
        return StreamingResponse(file_mgr_stream(), media_type="text/event-stream")

    # Check for live data requests (cricket, weather) — direct fetch, no LLM needed
    live_type = detect_live_data_request(message)
    if live_type:
        if live_type == "cricket":
            live_result = await get_live_cricket_scores()
        elif live_type == "weather":
            city = extract_city_from_text(message)
            forecast_type = extract_forecast_type(message)
            weather_data = await get_weather_data(city, days=7 if forecast_type == "week" else 3)
            if weather_data.get("error"):
                live_result = f"⚠️ {weather_data['error']}"
            else:
                # Send as weather_widget SSE event (frontend renders rich widget)
                c = weather_data["current"]
                summary = f"🌤️ {weather_data['city']}: {c['temp_c']}°C, {c['condition']}, Humidity {c['humidity']}%"
                async def weather_widget_stream():
                    yield f"data: {json.dumps({'weather_widget': weather_data})}\n\n"
                    yield f"data: {json.dumps({'token': summary})}\n\n"
                    yield f"data: {json.dumps({'emotion': 'happy'})}\n\n"
                    yield "data: [DONE]\n\n"
                _save_cmd_to_chat(message, summary)
                return StreamingResponse(weather_widget_stream(), media_type="text/event-stream")
        elif live_type == "stock":
            stock_query = extract_stock_from_text(message)
            live_result = await get_live_stock_price(stock_query) if stock_query else None
        elif live_type == "news":
            topic = extract_news_topic(message)
            live_result = await get_live_news(topic)
        else:
            live_result = None

        if live_result:
            async def live_stream():
                yield f"data: {json.dumps({'token': live_result})}\n\n"
                yield f"data: {json.dumps({'emotion': 'happy'})}\n\n"
                yield "data: [DONE]\n\n"
            _save_cmd_to_chat(message, live_result)
            return StreamingResponse(live_stream(), media_type="text/event-stream")

    # Check for OCR request (screen read / image text extract)
    ocr_type = detect_ocr_request(message)
    if ocr_type:
        if ocr_type == "screen_ocr":
            ocr_result = ocr_screenshot()
        else:
            ocr_result = {"success": False, "text": "", "message": "Image file path required for OCR"}

        if ocr_result.get("success") and ocr_result.get("text"):
            ocr_reply = f"Screen pe ye text mila:\n\n{ocr_result['text']}"
        else:
            ocr_reply = ocr_result.get("message", "OCR failed — text extract nahi ho paya")

        async def ocr_stream():
            yield f"data: {json.dumps({'token': ocr_reply})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy' if ocr_result.get('success') else 'confused'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, ocr_reply)
        return StreamingResponse(ocr_stream(), media_type="text/event-stream")

    # Check for git commands via chat
    git_patterns = re.compile(
        r"(?:git\s+(?:status|log|add|commit|push|pull|branch|diff|stash))"
        r"|(?:code\s+(?:push|commit)\s+(?:kar|karo|kro|do))"
        r"|(?:(?:push|commit)\s+(?:kar|karo|kro|do)\s+(?:code|changes))"
        r"|(?:git\s+(?:ka|ki|ke)\s+(?:status|haal))"
        r"|(?:kitne\s+(?:changes|files)\s+(?:hai|hain|pending))",
        re.IGNORECASE
    )
    if git_patterns.search(message):
        import subprocess as _sp
        repo = str(Path(__file__).parent.parent)
        lower_msg = message.lower()

        if any(w in lower_msg for w in ["push kar", "push karo", "push kro", "push do", "git push"]):
            # Auto: git add . + commit + push
            _sp.run(["git", "-C", repo, "add", "."], capture_output=True, timeout=10)
            commit_r = _sp.run(["git", "-C", repo, "commit", "-m", "MJ auto-commit"], capture_output=True, text=True, timeout=10)
            push_r = _sp.run(["git", "-C", repo, "push"], capture_output=True, text=True, timeout=30)
            git_reply = f"Git Push Result:\n{commit_r.stdout or commit_r.stderr}\n{push_r.stdout or push_r.stderr}"
        elif any(w in lower_msg for w in ["commit kar", "commit karo", "commit kro", "git commit"]):
            _sp.run(["git", "-C", repo, "add", "."], capture_output=True, timeout=10)
            commit_r = _sp.run(["git", "-C", repo, "commit", "-m", "MJ auto-commit"], capture_output=True, text=True, timeout=10)
            git_reply = f"Git Commit:\n{commit_r.stdout or commit_r.stderr}"
        elif any(w in lower_msg for w in ["git pull"]):
            pull_r = _sp.run(["git", "-C", repo, "pull"], capture_output=True, text=True, timeout=30)
            git_reply = f"Git Pull:\n{pull_r.stdout or pull_r.stderr}"
        elif any(w in lower_msg for w in ["git log"]):
            log_r = _sp.run(["git", "-C", repo, "log", "--oneline", "-10"], capture_output=True, text=True, timeout=10)
            git_reply = f"Last 10 Commits:\n{log_r.stdout or 'No commits found'}"
        elif any(w in lower_msg for w in ["git diff"]):
            diff_r = _sp.run(["git", "-C", repo, "diff", "--stat"], capture_output=True, text=True, timeout=10)
            git_reply = f"Git Changes:\n{diff_r.stdout or 'No changes'}"
        elif any(w in lower_msg for w in ["git branch"]):
            branch_r = _sp.run(["git", "-C", repo, "branch", "-a"], capture_output=True, text=True, timeout=10)
            git_reply = f"Branches:\n{branch_r.stdout or 'No branches'}"
        else:
            # Default: git status
            status_r = _sp.run(["git", "-C", repo, "status", "--short"], capture_output=True, text=True, timeout=10)
            branch_r = _sp.run(["git", "-C", repo, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=5)
            last_r = _sp.run(["git", "-C", repo, "log", "-1", "--oneline"], capture_output=True, text=True, timeout=5)
            changes = status_r.stdout.strip() or "No changes"
            branch = branch_r.stdout.strip()
            last = last_r.stdout.strip()
            git_reply = f"📂 Git Status:\nBranch: {branch}\nLast Commit: {last}\nChanges:\n{changes}"

        async def git_stream():
            yield f"data: {json.dumps({'token': git_reply})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, git_reply)
        return StreamingResponse(git_stream(), media_type="text/event-stream")

    # Check for smart suggestion request
    if detect_suggestion_request(message):
        try:
            s_stats = get_system_stats()
        except Exception:
            s_stats = {}
        try:
            from pc_control.app_tracker import app_usage as _au
            s_usage = dict(_au) if _au else {}
        except Exception:
            s_usage = {}
        suggestions = await get_all_suggestions(stats=s_stats, app_usage=s_usage)
        if suggestions:
            lines = ["🧠 Smart Suggestions for you:\n"]
            for i, s in enumerate(suggestions, 1):
                lines.append(f"{s['icon']} **{s['title']}** — {s['text']}")
                lines.append(f"   Try: {' | '.join(s['commands'])}\n")
            suggest_reply = "\n".join(lines)
        else:
            suggest_reply = "Sab badhiya hai! Koi specific suggestion nahi abhi. Keep going! 💪"

        async def suggest_stream():
            yield f"data: {json.dumps({'token': suggest_reply})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, suggest_reply)
        return StreamingResponse(suggest_stream(), media_type="text/event-stream")

    # Check for greeting -> daily briefing
    if is_greeting(message):
        briefing = await generate_briefing()
        async def brief_stream():
            yield f"data: {json.dumps({'token': briefing})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, briefing)
        return StreamingResponse(brief_stream(), media_type="text/event-stream")

    # Check if this is a PC command first
    cmd = parse_command(message)
    if cmd:
        result = execute_command(cmd)
        async def cmd_stream():
            yield f"data: {json.dumps({'token': result['message']})}\n\n"
            yield f"data: {json.dumps({'emotion': 'happy' if result['success'] else 'confused'})}\n\n"
            yield "data: [DONE]\n\n"
        _save_cmd_to_chat(message, result["message"])
        return StreamingResponse(cmd_stream(), media_type="text/event-stream")

    # Process file if attached
    file_context = ""
    images = []
    file_label = ""

    if file and file.filename:
        file_result = await process_uploaded_file(file)
        if "error" in file_result:
            async def error_stream():
                yield f"data: {json.dumps({'token': file_result['error']})}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(error_stream(), media_type="text/event-stream")
        file_context = file_result["context"]
        images = file_result["images"]
        file_label = f" [{file_result['filename']}]"

    # =====================================================
    # ZEUS MODULE ROUTING — for messages that didn't match
    # any fast-path command above. Zeus finds the best
    # module (git, image gen, notifications, code, KB, etc.)
    # and executes it with recovery/fallback.
    # Only triggers when confidence > 0.7 to avoid false matches.
    # =====================================================
    if not file_context:  # Don't intercept file uploads — let LLM handle those
        zeus_match = zeus.route(message, intent="", context={})
        if zeus_match:
            zeus_mod, zeus_conf = zeus_match
            if zeus_conf >= 0.7:
                try:
                    # Use execute_with_recovery for auto-fallback
                    zeus_result = await zeus.execute_with_recovery(zeus_mod, message, {}, zeus_conf)
                    zeus_response = zeus_result.get("response", "")
                    zeus_action = zeus_result.get("action", "")
                    zeus_data = zeus_result.get("data") or {}

                    # Actions that should return directly (module handled it completely)
                    direct_actions = {
                        "git_result", "file_analysis", "code_execution",
                        "notification_sent", "reminder_set", "reminder_list",
                        "reminder_cancelled", "reminder_snoozed", "history",
                        "image_generated", "image_list",
                    }

                    if zeus_action in direct_actions and zeus_response:
                        async def zeus_stream():
                            yield f"data: {json.dumps({'token': zeus_response})}\n\n"
                            if zeus_data.get("type") == "image_generated" and zeus_data.get("url"):
                                yield f"data: {json.dumps({'image_url': zeus_data['url']})}\n\n"
                            meta = zeus_result.get("_meta", {})
                            yield f"data: {json.dumps({'emotion': 'happy', 'zeus_module': meta.get('module', ''), 'zeus_confidence': meta.get('confidence', 0), 'zeus_duration_ms': meta.get('duration_ms', 0)})}\n\n"
                            yield "data: [DONE]\n\n"
                        _save_cmd_to_chat(message, zeus_response)
                        return StreamingResponse(zeus_stream(), media_type="text/event-stream")

                    # Actions that provide CONTEXT for the LLM (module prepared data, LLM generates response)
                    # e.g. knowledge_response, code_generate, creative_generate
                    if zeus_data.get("kb_context"):
                        file_context += "\n" + zeus_data["kb_context"]
                    if zeus_data.get("instruction"):
                        file_context += "\n\n[Module Instruction] " + zeus_data["instruction"]

                except Exception as _zeus_err:
                    import logging as _log
                    _log.getLogger("mj.chat").warning(f"Zeus routing error: {_zeus_err}")
                    # Fall through to normal LLM flow

    # ============================================================
    # PERFORMANCE-OPTIMIZED PIPELINE
    # Sync functions run directly (they're fast: 1-15ms each)
    # Async search + KB run in parallel via asyncio.gather
    # Pipeline timing sent to frontend via SSE for accurate status
    # ============================================================
    _pipeline_start = time.time()
    _timings = {}

    chat_id = get_active_chat_id()
    if not chat_id:
        chat_id = str(uuid.uuid4())[:8]
        set_active_chat_id(chat_id)

    # Sync pre-LLM work — fast file I/O (~10-20ms total)
    chat_data = load_chat(chat_id)
    new_facts = auto_remember(message)  # legacy regex (fast, sync)
    short_term.add_turn("user", message)  # V2: log to short-term memory
    notify_plugins(message)
    core_facts = memory_store.get_flat_list()
    context_memory_prompt = get_context_prompt()

    # Quick regex checks — instant, no I/O (<1ms total)
    search_query = needs_web_search_v2(message)
    kb_needed = needs_kb_search(message)
    reasoning_type = needs_deep_reasoning(message)

    # Run web search + KB search in parallel (these are the slow ones)
    search_context = ""
    kb_context = ""

    async def _do_search():
        if search_query:
            try:
                data = await asyncio.wait_for(deep_search(search_query, max_results=3), timeout=5.0)
                return format_search_for_llm(data)
            except (asyncio.TimeoutError, Exception):
                return ""
        return ""

    async def _do_kb():
        if kb_needed:
            results = search_knowledge(message, top_k=2)
            return format_kb_context(results)
        elif not search_query:
            results = search_knowledge(message, top_k=1)
            if results and results[0]["score"] > 0.15:
                return format_kb_context(results)
        return ""

    _gather_start = time.time()
    search_context, kb_context = await asyncio.gather(_do_search(), _do_kb())
    _timings["gather"] = round(time.time() - _gather_start, 3)

    memory_context = memory_store.get_context_string(max_facts=30)

    # Process through Human Brain (<1ms — pure regex)
    brain_result = mj_brain.process(user_text=message, memory_context=memory_context)

    # Build system prompt
    system_content = MJ_BASE_PROMPT
    system_content += f"\n\nCurrent date: {datetime.now().strftime('%A, %d %B %Y')}"
    system_content += f"\nCurrent time: {datetime.now().strftime('%I:%M %p')}"

    if memory_context:
        system_content += "\n\nIMPORTANT - Things you must always remember about the user:\n"
        system_content += memory_context

    if file_context:
        system_content += "\n\nWhen a user shares a file, analyze its content thoroughly and provide helpful insights."

    if search_context:
        system_content += f"\n\n{search_context}"

    if kb_context:
        system_content += f"\n\n{kb_context}"

    if context_memory_prompt:
        system_content += context_memory_prompt

    if reasoning_type:
        system_content += f"\n\nDEEP REASONING MODE: Use step-by-step {reasoning_type} reasoning. Think carefully before answering."

    # Append file context to user message for LLM
    user_prompt = brain_result["response_prompt"] + file_context

    # Zeus Smart Router — pick best model (vision if image attached)
    has_image = len(images) > 0
    selected_model = get_model_for_task(message, has_image=has_image)
    routing = get_routing_info(message, has_image=has_image)

    # Limit chat history to last 10 messages for speed
    recent_history = chat_data["messages"][-10:] if len(chat_data["messages"]) > 10 else chat_data["messages"]
    messages = [{"role": "system", "content": system_content}]
    messages.extend(recent_history)

    final_user_prompt = user_prompt
    if "qwen3" in selected_model.lower() and not reasoning_type:
        final_user_prompt = user_prompt + " /no_think"

    user_msg_entry = {"role": "user", "content": final_user_prompt}
    if images:
        user_msg_entry["images"] = images
    messages.append(user_msg_entry)

    # Detect provider
    active_provider = get_active_provider()

    if active_provider == "groq":
        groq_model = get_groq_model()
        selected_model = f"groq:{groq_model}"

    payload = {
        "model": selected_model,
        "messages": messages,
        "stream": True,
        "options": {
            "num_ctx": 4096,
            "temperature": 0.7,
            "repeat_penalty": 1.1,
            "num_predict": 1024,
            "top_k": 40,
            "top_p": 0.9,
        },
    }

    _timings["prep"] = round(time.time() - _pipeline_start, 3)

    full_reply = []
    _perf_start = time.time()

    async def stream_response():
        _error_occurred = None
        _first_token_time = None

        # Send model info + pipeline timings as first SSE event
        yield f"data: {json.dumps({'model': selected_model, 'task_type': routing.get('task_type', 'chat'), 'provider': active_provider, 'stage': 'calling_ai', 'prep_ms': int(_timings.get('prep', 0) * 1000)})}\n\n"

        # ── CLOUD PROVIDER STREAMING (Groq / OpenAI / Anthropic / Gemini) ──
        if active_provider in ("groq", "openai", "anthropic", "gemini"):
            # Pick the right streaming function
            _cloud_streamers = {
                "groq": stream_groq_chat,
                "openai": stream_openai_chat,
                "anthropic": stream_anthropic_chat,
                "gemini": stream_gemini_chat,
            }
            _stream_fn = _cloud_streamers[active_provider]

            try:
                _api_start = time.time()
                token_count = 0
                async for token in _stream_fn(messages, temperature=0.7, max_tokens=1024):
                    if _first_token_time is None:
                        _first_token_time = time.time()
                        _timings["first_token"] = round(_first_token_time - _api_start, 3)
                        yield f"data: {json.dumps({'stage': 'streaming'})}\n\n"
                    if token.startswith("[ERROR]"):
                        _error_occurred = f"{active_provider}_error"
                        full_reply.append(token)
                        log_error(f"{active_provider}_error", token, {"model": selected_model, "user_msg": message[:80]})
                        yield f"data: {json.dumps({'token': token})}\n\n"
                    else:
                        full_reply.append(token)
                        token_count += 1
                        yield f"data: {json.dumps({'token': token})}\n\n"
            except Exception as e:
                _error_occurred = f"{active_provider}_exception"
                error_msg = f"❌ {active_provider.title()} API error: {str(e)[:200]}"
                full_reply.append(error_msg)
                log_error(f"{active_provider}_exception", str(e)[:300], {"model": selected_model})
                yield f"data: {json.dumps({'token': error_msg})}\n\n"

        # ── OLLAMA LOCAL PROVIDER ──
        else:
            try:
                _api_start = time.time()
                # Separate connect timeout (8s) from read timeout (120s)
                _ollama_timeout = httpx.Timeout(connect=8.0, read=120.0, write=10.0, pool=10.0)
                async with httpx.AsyncClient(timeout=_ollama_timeout) as client:
                    async with client.stream("POST", OLLAMA_URL, json=payload) as resp:
                        async for line in resp.aiter_lines():
                            if line:
                                data = json.loads(line)
                                token = data.get("message", {}).get("content", "")
                                if token:
                                    if _first_token_time is None:
                                        _first_token_time = time.time()
                                        _timings["first_token"] = round(_first_token_time - _api_start, 3)
                                        yield f"data: {json.dumps({'stage': 'streaming'})}\n\n"
                                    full_reply.append(token)
                                    yield f"data: {json.dumps({'token': token})}\n\n"
            except httpx.ConnectError:
                _error_occurred = "connect_error"
                error_msg = "⚠️ Boss, Ollama chal nahi raha! Terminal me `ollama serve` run karo, phir dubara try karo."
                full_reply.append(error_msg)
                log_error("connect_error", error_msg, {"model": selected_model, "user_msg": message[:80]})
                yield f"data: {json.dumps({'token': error_msg})}\n\n"
            except httpx.ReadTimeout:
                _error_occurred = "timeout"
                error_msg = "⏳ Ollama response dene me bahut time le raha hai. Model busy hai ya bahut bada question hai. Thoda wait karo ya chhota question pucho."
                full_reply.append(error_msg)
                log_error("timeout", error_msg, {"model": selected_model, "user_msg": message[:80], "timeout": 120})
                yield f"data: {json.dumps({'token': error_msg})}\n\n"
            except httpx.ConnectTimeout:
                _error_occurred = "connect_timeout"
                error_msg = "⚠️ Ollama se connect nahi ho pa raha. Check karo ki `ollama serve` chal raha hai aur port 11434 free hai."
                full_reply.append(error_msg)
                log_error("connect_timeout", error_msg, {"model": selected_model})
                yield f"data: {json.dumps({'token': error_msg})}\n\n"
            except Exception as e:
                error_str = str(e).lower()
                if "connect" in error_str or "refused" in error_str or "connection" in error_str:
                    _error_occurred = "connect_error"
                    error_msg = "⚠️ Ollama se connection fail ho gaya. `ollama serve` run karo terminal me!"
                elif "timeout" in error_str:
                    _error_occurred = "timeout"
                    error_msg = "⏳ Request timeout ho gaya. Ollama slow hai ya model load ho raha hai."
                elif "model" in error_str and "not found" in error_str:
                    _error_occurred = "model_not_found"
                    error_msg = f"❌ Model '{selected_model}' nahi mila. `ollama pull {selected_model}` run karo pehle."
                else:
                    _error_occurred = "unknown"
                    error_msg = f"❌ Kuch gadbad ho gayi: {str(e)[:200]}"
                full_reply.append(error_msg)
                log_error(_error_occurred, str(e)[:300], {"model": selected_model, "user_msg": message[:80]})
                yield f"data: {json.dumps({'token': error_msg})}\n\n"

        # Save to chat (show file label in history)
        display_msg = message + file_label
        chat_data["messages"].append({"role": "user", "content": display_msg})
        reply_text = "".join(full_reply)
        import re as _re
        reply_text = _re.sub(r'<think>[\s\S]*?</think>', '', reply_text).strip()
        chat_data["messages"].append({"role": "assistant", "content": reply_text})

        if chat_data["title"] == "New Chat":
            chat_data["title"] = message[:40]

        save_chat(chat_id, chat_data)

        # Record interaction (fast -- just file append)
        try:
            record_interaction(message, reply_text, brain_result.get("emotion", "neutral"))
            short_term.add_turn("assistant", reply_text[:500])  # V2: log assistant turn
        except Exception:
            pass

        # LLM-based fact extraction (async, non-blocking)
        try:
            llm_facts = await extract_and_store(message, reply_text)
            if llm_facts:
                new_facts.extend([f.content for f in llm_facts])
        except Exception:
            pass

        intelligence_info = {
            "web_searched": bool(search_context),
            "kb_used": bool(kb_context),
            "deep_reasoning": reasoning_type or "none",
            "context_memory": bool(context_memory_prompt),
        }

        _perf_time = round(time.time() - _perf_start, 2)
        _token_count = len(full_reply)
        perf_issues = log_performance(
            user_msg=message, model=selected_model, task_type=routing["task_type"],
            response_time=_perf_time, token_count=_token_count,
            success=(_error_occurred is None), error_msg=_error_occurred
        )

        issue_alerts = []
        for issue in (perf_issues or []):
            issue_alerts.append({"type": issue["type"], "msg": issue["message"], "severity": issue["severity"]})

        _timings["total"] = round(time.time() - _pipeline_start, 3)
        yield f"data: {json.dumps({'emotion': brain_result['emotion'], 'auto_memory': new_facts, 'model_used': routing['model'], 'task_type': routing['task_type'], 'intelligence': intelligence_info, 'perf_time': _perf_time, 'issues': issue_alerts, 'timings': _timings})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")


# ===== WEATHER ENDPOINT =====

@app.get("/weather")
async def weather_endpoint(city: str = "Gurgaon", days: int = 3):
    """Full structured weather data for widget rendering."""
    data = await get_weather_data(city, days)
    return data


@app.post("/weather")
async def weather_post_endpoint(req: dict):
    """Weather with POST body — supports lat/lon and city."""
    city = req.get("city", "")
    lat = req.get("lat")
    lon = req.get("lon")
    days = req.get("days", 3)
    # If lat/lon provided, use coordinates
    if lat and lon:
        city = f"{lat},{lon}"
    elif not city:
        city = "Gurgaon"
    data = await get_weather_data(city, days)
    return data


# ===== DIAGNOSTICS ENDPOINT =====

@app.get("/diagnostics")
async def diagnostics():
    """Self-learning diagnostic report — errors, performance, patterns."""
    return get_diagnostics()

@app.get("/diagnostics/issues")
async def live_issues():
    """Current active issues for orb alert."""
    return get_live_issues()


# ===== KNOWLEDGE BASE ENDPOINTS =====

@app.post("/knowledge-base/ingest")
async def kb_ingest(file: UploadFile = File(...)):
    """Upload a document to the knowledge base."""
    if not file.filename:
        return {"status": "error", "message": "No file provided"}

    content_bytes = await file.read()
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return {"status": "error", "message": "Could not read file — only text-based files supported"}

    result = ingest_document(file.filename, content)
    return result


@app.get("/knowledge-base")
async def kb_status():
    """Get knowledge base stats."""
    return get_kb_stats()


@app.post("/knowledge-base/search")
async def kb_search(body: dict):
    """Search the knowledge base."""
    query = body.get("query", "")
    if not query:
        return {"results": []}
    results = search_knowledge(query, top_k=5)
    return {"results": results}


@app.delete("/knowledge-base/{doc_id}")
async def kb_delete(doc_id: str):
    """Remove a document from the knowledge base."""
    return delete_document(doc_id)


# ===== CONTEXT MEMORY ENDPOINTS =====

@app.get("/context-memory")
async def context_memory_stats():
    """Get context memory learning stats."""
    return get_memory_stats()


# ===== SHORT-TERM MEMORY =====

@app.get("/short-term-memory")
async def short_term_stats():
    """Get short-term memory stats."""
    return short_term.get_stats()

@app.get("/short-term-memory/turns")
async def short_term_turns(n: int = 10):
    """Get recent conversation turns."""
    return {"turns": short_term.get_recent_turns(n)}

@app.post("/short-term-memory/set")
async def short_term_set(req: dict):
    """Set a scratchpad value."""
    key = req.get("key", "")
    value = req.get("value", "")
    ttl = req.get("ttl", 3600)
    if not key:
        return {"error": "key required"}
    short_term.set(key, value, ttl=ttl)
    return {"status": "ok", "key": key}

@app.get("/short-term-memory/slots")
async def short_term_slots():
    """Get all active scratchpad slots."""
    return {"slots": short_term.get_all_slots()}

@app.get("/short-term-memory/entities")
async def short_term_entities():
    """Get tracked entities from current session."""
    return {"entities": short_term.get_entities(min_count=1)}

@app.delete("/short-term-memory")
async def short_term_clear():
    """Clear short-term memory."""
    short_term.clear()
    return {"status": "cleared"}


# ===== USER PROFILE =====

@app.get("/user-profile")
async def user_profile_full():
    """Get full aggregated user profile."""
    return build_user_profile()

@app.get("/user-profile/summary")
async def user_profile_summary():
    """Get compact user profile summary."""
    return get_profile_summary()


# ===== MEMORY SEARCH (HYBRID) =====

@app.get("/memory-search")
async def memory_search(q: str, top_k: int = 5):
    """Hybrid search: semantic + keyword."""
    results = await hybrid_search(q, top_k=top_k)
    return {
        "query": q,
        "results": [
            {"content": f.content, "category": f.category, "score": round(s, 3),
             "source": f.source, "confidence": f.confidence}
            for f, s in results
        ],
        "count": len(results),
    }

@app.post("/memory-embed-all")
async def memory_embed_all():
    """Generate embeddings for all facts (requires Ollama with nomic-embed-text)."""
    from intelligence.memory_embeddings import embed_all_facts
    available = await is_ollama_embed_available()
    if not available:
        return {"error": "Ollama nomic-embed-text not available", "status": "unavailable"}
    count = await embed_all_facts()
    return {"status": "ok", "embedded": count}


# ===== INTELLIGENCE STATUS =====

@app.get("/intelligence")
async def intelligence_status():
    """Get status of all intelligence features."""
    kb = get_kb_stats()
    mem = get_memory_stats()
    return {
        "web_search": "active",
        "knowledge_base": {
            "status": "active" if kb["document_count"] > 0 else "empty",
            "documents": kb["document_count"],
            "chunks": kb["total_chunks"]
        },
        "context_memory": {
            "status": mem["learning_status"],
            "interactions": mem["total_interactions"],
            "preferred_language": mem["preferred_language"],
            "top_topics": mem["top_topics"]
        },
        "short_term_memory": short_term.get_stats(),
        "user_profile": get_profile_summary(),
        "multi_model_reasoning": "active"
    }


# ===== OLLAMA STATUS (Proactive Health) =====

@app.get("/ollama-status")
async def ollama_status():
    """Check if Ollama is running and which models are available."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                model_names = [m["name"] for m in models]
                # Auto-resolve any old Ollama/Health alerts
                for a in get_active_alerts():
                    if "Ollama" in a.get("title", "") or "Ollama" in a.get("message", ""):
                        resolve_alert(a["id"], "Ollama is back online")
                return {
                    "status": "online",
                    "models": model_names,
                    "model_count": len(model_names),
                    "active_model": load_model_config().get("active_model", model_names[0] if model_names else None),
                    "message": f"Ollama ready — {len(model_names)} models loaded"
                }
            return {"status": "error", "message": "Ollama responded but with an error", "models": []}
    except httpx.ConnectError:
        return {"status": "offline", "message": "Ollama chal nahi raha. Terminal me 'ollama serve' run karo.", "models": []}
    except httpx.ConnectTimeout:
        return {"status": "offline", "message": "Ollama se connect nahi ho pa raha. Port 11434 check karo.", "models": []}
    except Exception as e:
        return {"status": "error", "message": f"Ollama check failed: {str(e)[:100]}", "models": []}


# ===== WAKE WORD BRIEFING =====

@app.get("/wake-briefing")
async def wake_briefing():
    """
    Called when user says 'Hey MJ' for the first time after page load.
    Returns system status briefing: CPU, RAM, GPU, temp, issues, weather.
    """
    try:
        stats = get_system_stats()
    except Exception:
        stats = {}

    # Build briefing parts
    parts = ["Yes Boss! MJ online and ready."]

    # System stats
    cpu = stats.get("cpu", -1)
    ram_pct = stats.get("ram_percent", -1)
    ram_used = stats.get("ram_used", 0)
    ram_total = stats.get("ram_total", 0)
    gpu_util = stats.get("gpu_util", -1)
    gpu_temp = stats.get("gpu_temp", -1)
    gpu_name = stats.get("gpu_name", "N/A")
    gpu_mem_used = stats.get("gpu_mem_used", 0)
    gpu_mem_total = stats.get("gpu_mem_total", 0)
    process_count = stats.get("process_count", 0)
    uptime = stats.get("uptime", "unknown")

    if cpu >= 0:
        parts.append(f"CPU is at {cpu}%.")
    if ram_pct >= 0:
        parts.append(f"RAM usage {ram_pct}%, {ram_used} GB out of {ram_total} GB used.")
    if gpu_util >= 0:
        parts.append(f"GPU {gpu_name} at {gpu_util}% utilization, {gpu_mem_used} MB of {gpu_mem_total} MB VRAM used.")
    if gpu_temp >= 0:
        parts.append(f"GPU temperature is {gpu_temp} degrees Celsius.")
    if process_count > 0:
        parts.append(f"{process_count} processes running, system uptime {uptime}.")

    # Issues detection
    issues = []
    if cpu > 85:
        issues.append(f"CPU is running high at {cpu}%")
    if ram_pct > 85:
        issues.append(f"RAM is running high at {ram_pct}%")
    if gpu_temp > 80:
        issues.append(f"GPU temperature is high at {gpu_temp} degrees")
    if gpu_util > 90:
        issues.append(f"GPU utilization is very high at {gpu_util}%")

    # Check Ollama status
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            if resp.status_code == 200:
                ollama_ok = True
                model_count = len(resp.json().get("models", []))
                parts.append(f"Ollama is online with {model_count} models ready.")
    except Exception:
        issues.append("Ollama is not running")
        parts.append("Warning: Ollama is offline, run ollama serve.")

    # Weather (quick fetch, don't block if fails)
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            resp = await client.get(
                "https://wttr.in/Delhi?format=j1",
                headers={"User-Agent": "curl/7.68.0"}
            )
            if resp.status_code == 200:
                weather = resp.json()
                current = weather["current_condition"][0]
                temp = current["temp_C"]
                desc = current["weatherDesc"][0]["value"]
                parts.append(f"Current weather in Delhi: {temp} degrees, {desc}.")
    except Exception:
        pass

    if issues:
        parts.append("Issues detected: " + ". ".join(issues) + ".")
    else:
        parts.append("All systems nominal, no issues detected.")

    briefing_text = " ".join(parts)

    return {
        "briefing": briefing_text,
        "stats": stats,
        "issues": issues,
        "ollama": "online" if ollama_ok else "offline",
    }


# ===== OCR ENDPOINTS =====

@app.get("/ocr/screen")
async def ocr_screen():
    """Take screenshot and extract text via OCR."""
    result = ocr_screenshot()
    return result


@app.post("/ocr/file")
async def ocr_file(filepath: str = Form(...)):
    """Extract text from a given image file."""
    result = ocr_from_file(filepath)
    return result


# ===== GIT INTEGRATION =====

class GitRequest(BaseModel):
    command: str
    path: str = ""  # repo path, empty = auto-detect

@app.post("/git")
async def git_command(req: GitRequest):
    """Execute git commands for MJ project or any repo."""
    import subprocess as sp

    allowed = ["status", "log", "add", "commit", "push", "pull", "branch", "diff", "stash"]
    cmd_lower = req.command.strip().lower()

    # Parse the git command
    parts = cmd_lower.split()
    if not parts:
        return {"success": False, "message": "No git command provided"}

    git_action = parts[0]
    if git_action not in allowed:
        return {"success": False, "message": f"Git command '{git_action}' not allowed. Allowed: {', '.join(allowed)}"}

    # Build the actual git command
    repo_path = req.path if req.path else str(Path(__file__).parent.parent)  # Default: MJ-Assistant root

    full_cmd = ["git", "-C", repo_path] + parts

    # For commit, ensure message is provided
    if git_action == "commit" and "-m" not in cmd_lower:
        return {"success": False, "message": "Commit me message do: commit -m \"your message\""}

    try:
        r = sp.run(full_cmd, capture_output=True, text=True, timeout=30)
        output = r.stdout.strip() or r.stderr.strip() or "Done (no output)"
        success = r.returncode == 0

        return {
            "success": success,
            "command": " ".join(full_cmd),
            "output": output,
            "message": output if success else f"Git error: {output}"
        }
    except sp.TimeoutExpired:
        return {"success": False, "message": "Git command timed out (30s)"}
    except FileNotFoundError:
        return {"success": False, "message": "Git not installed or not in PATH"}
    except Exception as e:
        return {"success": False, "message": f"Git error: {str(e)[:200]}"}


@app.get("/git/status")
async def git_quick_status():
    """Quick git status for MJ project."""
    import subprocess as sp
    repo = str(Path(__file__).parent.parent)
    try:
        # Get branch
        branch = sp.run(["git", "-C", repo, "rev-parse", "--abbrev-ref", "HEAD"],
                        capture_output=True, text=True, timeout=5).stdout.strip()
        # Get status
        status = sp.run(["git", "-C", repo, "status", "--porcelain"],
                        capture_output=True, text=True, timeout=5).stdout.strip()
        # Get last commit
        last_commit = sp.run(["git", "-C", repo, "log", "-1", "--oneline"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        # Count changes
        changed = len([l for l in status.split("\n") if l.strip()]) if status else 0

        return {
            "success": True,
            "branch": branch,
            "changed_files": changed,
            "status": status or "Clean — no changes",
            "last_commit": last_commit,
            "clean": changed == 0
        }
    except Exception as e:
        return {"success": False, "message": f"Git status failed: {str(e)[:200]}"}


# ===== SMART SUGGESTIONS =====

@app.get("/suggestions")
async def smart_suggestions():
    """Get proactive smart suggestions based on time, system, usage."""
    try:
        stats = get_system_stats()
    except Exception:
        stats = {}

    # Get app usage
    try:
        from pc_control.app_tracker import app_usage
        usage = dict(app_usage) if app_usage else {}
    except Exception:
        usage = {}

    suggestions = await get_all_suggestions(stats=stats, app_usage=usage)
    return {"suggestions": suggestions, "count": len(suggestions)}


@app.get("/gesture/status")
async def gesture_status():
    """Return gesture control status."""
    return {
        "available": True,
        "gestures": {
            "wave": "Wake MJ / Say Hey MJ",
            "palm": "Mute / Pause audio",
            "swipe": "Dismiss alert / notification"
        },
        "status": "ready"
    }


class SpeakRequest(BaseModel):
    text: str
    emotion: str = "neutral"


@app.post("/speak")
async def speak(req: SpeakRequest):
    """Generate natural speech audio from text."""
    filename = await generate_speech(req.text, req.emotion)
    cleanup_old_audio()
    return {"audio_url": f"/audio/{filename}"}


@app.get("/voice-settings")
async def get_voice_settings():
    return {
        "settings": load_voice_settings(),
        "available_voices": AVAILABLE_VOICES,
    }


@app.post("/voice-settings")
async def update_voice_settings(settings: dict):
    save_voice_settings(settings)
    return {"status": "ok"}


class TestVoiceRequest(BaseModel):
    text: str
    voice: str
    rate: str
    pitch: str
    volume: str


@app.post("/test-voice")
async def test_voice_endpoint(req: TestVoiceRequest):
    filename = await test_voice(req.text, req.voice, req.rate, req.pitch, req.volume)
    cleanup_old_audio()
    return {"audio_url": f"/audio/{filename}"}


@app.post("/transcribe")
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None)
):
    """Transcribe uploaded audio using Whisper or fallback STT."""
    audio_bytes = await file.read()
    result = await save_and_transcribe(audio_bytes, file.filename, language)
    return result


@app.get("/stt-status")
async def stt_status():
    """Get STT engine status."""
    return get_stt_status()


@app.get("/")
async def root():
    # Serve React build if available, else fall back to old frontend
    react_index = REACT_DIST_DIR / "index.html"
    if react_index.exists():
        return FileResponse(str(react_index), media_type="text/html")
    return RedirectResponse("/static/index.html")


# ── Static file routes (MUST be before catch-all) ──────────

@app.get("/assets/{file_path:path}")
async def serve_react_assets(file_path: str):
    """Serve React build assets (JS, CSS, etc.)."""
    asset_file = REACT_DIST_DIR / "assets" / file_path
    if asset_file.exists() and asset_file.is_file():
        return FileResponse(str(asset_file))
    return JSONResponse({"error": "Not found"}, status_code=404)


@app.get("/favicon.svg")
async def serve_favicon_svg():
    for d in [REACT_DIST_DIR, FRONTEND_DIR]:
        f = d / "favicon.svg"
        if f.exists():
            return FileResponse(str(f), media_type="image/svg+xml")
    return JSONResponse({"error": "Not found"}, status_code=404)


@app.get("/icons.svg")
async def serve_icons_svg():
    f = REACT_DIST_DIR / "icons.svg"
    if f.exists():
        return FileResponse(str(f), media_type="image/svg+xml")
    return JSONResponse({"error": "Not found"}, status_code=404)


@app.get("/static/{file_path:path}")
async def serve_old_frontend(file_path: str):
    """Serve old frontend files."""
    target = FRONTEND_DIR / file_path
    if target.exists() and target.is_file():
        return FileResponse(str(target))
    # Default to index.html for old frontend
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index), media_type="text/html")
    return JSONResponse({"error": "Not found"}, status_code=404)


# Audio files
AUDIO_DIR = Path(__file__).parent / "audio_cache"
AUDIO_DIR.mkdir(exist_ok=True)

@app.get("/audio/{file_path:path}")
async def serve_audio(file_path: str):
    f = AUDIO_DIR / file_path
    if f.exists() and f.is_file():
        return FileResponse(str(f))
    return JSONResponse({"error": "Not found"}, status_code=404)


# Generated images
GEN_IMAGES_DIR = Path(__file__).parent / "generated_images"
GEN_IMAGES_DIR.mkdir(exist_ok=True)

@app.get("/static/generated/{file_path:path}")
async def serve_generated_images(file_path: str):
    f = GEN_IMAGES_DIR / file_path
    if f.exists() and f.is_file():
        return FileResponse(str(f))
    return JSONResponse({"error": "Not found"}, status_code=404)


# SPA catch-all: serve React index.html for client-side routes
@app.get("/{path:path}")
async def spa_catch_all(path: str):
    first_segment = path.split("/")[0] if path else ""
    backend_prefixes = {
        "auth", "chat", "chats", "history", "select-chat", "new-chat", "delete-chat",
        "core-memory", "remember", "context-memory", "execute", "system-stats",
        "top-processes", "processes", "network-stats", "notify", "reminders",
        "scheduled-tasks", "health", "errors", "alerts", "models", "provider",
        "plugins", "zeus", "knowledge-base", "intelligence", "diagnostics",
        "ollama-status", "wake-briefing", "ocr", "git", "suggestions",
        "gesture", "speak", "voice-settings", "test-voice", "email",
        "clipboard", "app-usage", "generated-images", "weather",
        "docs", "openapi.json",
        "vision", "sentinel", "safety", "reflection", "learning",
        "messaging", "message-bus", "events", "shared-memory", "task-queue",
        "mouse", "browser-control", "calendar",
    }
    if first_segment in backend_prefixes:
        return JSONResponse({"error": "Not found"}, status_code=404)

    react_index = REACT_DIST_DIR / "index.html"
    if react_index.exists():
        return FileResponse(str(react_index), media_type="text/html")
    return RedirectResponse("/static/index.html")


# ── Start Server ────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
