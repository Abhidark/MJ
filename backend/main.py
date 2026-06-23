from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse
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

# Add backend dir to path for human_layer import
sys.path.insert(0, str(Path(__file__).parent))
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

# Intelligence Layer
from intelligence.web_browser import deep_search, format_search_for_llm, needs_web_search_v2
from intelligence.knowledge_base import (
    ingest_document, search_knowledge, format_kb_context,
    get_kb_stats, delete_document, needs_kb_search
)
from intelligence.context_memory import (
    record_interaction, get_context_prompt, get_memory_stats
)
from intelligence.multi_model import needs_deep_reasoning, chain_of_thought, multi_perspective
from intelligence.live_data import detect_live_data_request, get_live_cricket_scores, get_live_weather, extract_city_from_text
from intelligence.error_learner import log_error as el_log_error, log_performance, get_diagnostics, get_live_issues
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
from human_layer.model_manager import parse_model_command, handle_model_command, get_model_for_task, get_available_models, load_model_config, save_model_config, get_routing_info, set_active_model, toggle_auto_select, set_model_for_task
from plugins.plugin_manager import load_plugins, match_plugin, run_plugin, notify_plugins, parse_plugin_command, handle_plugin_management, get_plugin_list
from self_healer.error_tracker import log_error, get_recent_errors, get_error_stats, clear_errors
from self_healer.auto_fixer import attempt_fix, analyze_error
from self_healer.health_monitor import check_health
from self_healer.middleware import SelfHealingMiddleware
from self_healer.alert_system import (
    create_alert, resolve_alert, get_active_alerts, get_all_alerts,
    get_alert_stats, clear_all_alerts, clear_resolved, subscribe, unsubscribe,
    check_system_warnings, SEVERITY_WARNING, SEVERITY_ERROR, CAT_HEALTH
)

app = FastAPI()

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

# Load MJ system prompt from file
MJ_PROMPT_FILE = Path(__file__).parent / "human_layer" / "prompts" / "mj_system_prompt.txt"
MJ_BASE_PROMPT = MJ_PROMPT_FILE.read_text(encoding="utf-8") if MJ_PROMPT_FILE.exists() else ""

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# Load plugins and start background services on boot
load_plugins()
start_all_tasks()
start_clipboard_monitor()
start_app_tracker()

# Self-Healing Middleware — catches all unhandled errors
app.add_middleware(SelfHealingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"facts": load_core_memory()}


@app.post("/remember")
async def remember(req: RememberRequest):
    facts = load_core_memory()
    facts.append(req.fact)
    save_core_memory(facts)
    return {"status": "ok", "facts": facts}


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
        result = execute_command(cmd)
        return result
    return {"success": False, "message": "Command samajh nahi aaya."}


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


@app.get("/models")
async def list_models():
    """List available Ollama models."""
    models = await get_available_models()
    config = load_model_config()
    return {
        "models": models,
        "active": config.get("active_model"),
        "auto_select": config.get("auto_select"),
        "model_map": config.get("model_map", {}),
    }


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
            live_result = await get_live_weather(city)
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

    chat_id = get_active_chat_id()
    if not chat_id:
        chat_id = str(uuid.uuid4())[:8]
        set_active_chat_id(chat_id)

    chat_data = load_chat(chat_id)

    # Auto-remember facts from user message
    new_facts = auto_remember(message)

    # Notify plugins (passive hook)
    notify_plugins(message)

    core_facts = load_core_memory()

    memory_context = ""
    if core_facts:
        memory_context = "User facts: " + ", ".join(core_facts)

    # === INTELLIGENCE LAYER (Optimized — parallel where possible) ===
    import asyncio as _aio

    # Quick regex checks first (instant)
    search_query = needs_web_search_v2(message)
    kb_needed = needs_kb_search(message)
    reasoning_type = needs_deep_reasoning(message)
    context_memory_prompt = get_context_prompt()

    # Run web search + KB search in parallel (if both needed)
    search_context = ""
    kb_context = ""

    async def _do_search():
        if search_query:
            data = await deep_search(search_query, max_results=3)  # Reduced from 5
            return format_search_for_llm(data)
        return ""

    async def _do_kb():
        if kb_needed:
            results = search_knowledge(message, top_k=2)  # Reduced from 3
            return format_kb_context(results)
        elif not search_query:
            results = search_knowledge(message, top_k=1)  # Reduced from 2
            if results and results[0]["score"] > 0.15:  # Stricter threshold
                return format_kb_context(results)
        return ""

    search_context, kb_context = await _aio.gather(_do_search(), _do_kb())

    # Process through Human Brain
    brain_result = mj_brain.process(
        user_text=message,
        memory_context=memory_context
    )

    # Build system prompt
    system_content = MJ_BASE_PROMPT
    system_content += f"\n\nCurrent date: {datetime.now().strftime('%A, %d %B %Y')}"
    system_content += f"\nCurrent time: {datetime.now().strftime('%I:%M %p')}"

    if core_facts:
        system_content += "\n\nIMPORTANT - Things you must always remember about the user:\n"
        for fact in core_facts:
            system_content += f"- {fact}\n"

    if file_context:
        system_content += "\n\nWhen a user shares a file, analyze its content thoroughly and provide helpful insights."

    if search_context:
        system_content += f"\n\n{search_context}"

    if kb_context:
        system_content += f"\n\n{kb_context}"

    if context_memory_prompt:
        system_content += context_memory_prompt

    if reasoning_type:
        system_content += f"\n\nDEEP REASONING MODE: Use step-by-step {reasoning_type} reasoning for this question."

    # Append file context to user message for LLM
    user_prompt = brain_result["response_prompt"] + file_context

    # Zeus Smart Router — pick best model (vision if image attached)
    has_image = len(images) > 0
    selected_model = get_model_for_task(message, has_image=has_image)
    routing = get_routing_info(message, has_image=has_image)

    # Deep reasoning — SKIP for speed. The main model handles reasoning via system prompt.
    # Only trigger for explicit "analyze deeply" / "think step by step" requests.
    # Previously this ran 3-4 EXTRA LLM calls before the actual response — massive delay.
    if reasoning_type and not file_context:
        system_content += f"\n\nDEEP REASONING MODE: Use step-by-step {reasoning_type} reasoning. Think carefully before answering."

    # Rebuild messages with updated system content
    # Limit chat history to last 10 messages for speed (long history = slow inference)
    recent_history = chat_data["messages"][-10:] if len(chat_data["messages"]) > 10 else chat_data["messages"]
    messages = [{"role": "system", "content": system_content}]
    messages.extend(recent_history)
    # For Qwen3 models: append /no_think to skip internal thinking (huge speed boost)
    # Only use thinking for deep reasoning requests
    final_user_prompt = user_prompt
    if "qwen3" in selected_model.lower() and not reasoning_type:
        final_user_prompt = user_prompt + " /no_think"

    user_msg_entry = {"role": "user", "content": final_user_prompt}
    if images:
        user_msg_entry["images"] = images
    messages.append(user_msg_entry)

    payload = {
        "model": selected_model,
        "messages": messages,
        "stream": True,
        "options": {
            "num_ctx": 4096,         # Smaller context = faster (was default 8192)
            "temperature": 0.7,
            "repeat_penalty": 1.1,
            "num_predict": 1024,     # Max tokens to generate (prevents endless responses)
            "top_k": 40,
            "top_p": 0.9,
        },
    }

    full_reply = []
    _perf_start = time.time()

    async def stream_response():
        _error_occurred = None
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                async with client.stream("POST", OLLAMA_URL, json=payload) as resp:
                    async for line in resp.aiter_lines():
                        if line:
                            data = json.loads(line)
                            token = data.get("message", {}).get("content", "")
                            if token:
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
            log_error("timeout", error_msg, {"model": selected_model, "user_msg": message[:80], "timeout": 180})
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
        # Strip <think>...</think> blocks from Qwen3 models before saving
        import re as _re
        reply_text = _re.sub(r'<think>[\s\S]*?</think>', '', reply_text).strip()
        chat_data["messages"].append({"role": "assistant", "content": reply_text})

        if chat_data["title"] == "New Chat":
            chat_data["title"] = message[:40]

        save_chat(chat_id, chat_data)

        # Record interaction for context memory learning
        try:
            record_interaction(message, reply_text, brain_result.get("emotion", "neutral"))
        except Exception:
            pass

        intelligence_info = {
            "web_searched": bool(search_context),
            "kb_used": bool(kb_context),
            "deep_reasoning": reasoning_type or "none",
            "context_memory": bool(context_memory_prompt),
        }

        # Performance tracking
        _perf_time = round(time.time() - _perf_start, 2)
        _token_count = len(full_reply)
        perf_issues = log_performance(
            user_msg=message, model=selected_model, task_type=routing["task_type"],
            response_time=_perf_time, token_count=_token_count,
            success=(_error_occurred is None), error_msg=_error_occurred
        )

        # Send issues to frontend for orb alert
        issue_alerts = []
        for issue in (perf_issues or []):
            issue_alerts.append({"type": issue["type"], "msg": issue["message"], "severity": issue["severity"]})

        yield f"data: {json.dumps({'emotion': brain_result['emotion'], 'auto_memory': new_facts, 'model_used': routing['model'], 'task_type': routing['task_type'], 'intelligence': intelligence_info, 'perf_time': _perf_time, 'issues': issue_alerts})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_response(), media_type="text/event-stream")


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
    return RedirectResponse("/static/index.html")


# Mount audio files
AUDIO_DIR = Path(__file__).parent / "audio_cache"
AUDIO_DIR.mkdir(exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")

# Serve generated images
# Serve generated images
GEN_IMAGES_DIR = Path(__file__).parent / "generated_images"
GEN_IMAGES_DIR.mkdir(exist_ok=True)
app.mount("/static/generated", StaticFiles(directory=str(GEN_IMAGES_DIR)), name="generated_images")

# Mount frontend static files (must be AFTER API routes)
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
