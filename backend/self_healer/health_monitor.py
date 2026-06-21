"""
MJ Self-Healing: Health Monitor
Checks all modules, Ollama, and system health.
"""

import httpx
import importlib
import sys
from pathlib import Path


async def check_health() -> dict:
    """Run full health check on MJ system."""
    results = {
        "status": "healthy",
        "ollama": False,
        "modules": {},
        "issues": [],
    }

    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            results["ollama"] = resp.status_code == 200
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                results["ollama_models"] = [m["name"] for m in models]
    except Exception:
        results["ollama"] = False
        results["issues"].append("Ollama not running -- 'ollama serve' run karo")

    # Check all MJ modules
    modules_to_check = [
        ("human_layer.human_brain", "Human Brain"),
        ("human_layer.auto_memory", "Auto Memory"),
        ("human_layer.emotion_detector", "Emotion Detector"),
        ("human_layer.intent_detector", "Intent Detector"),
        ("human_layer.personality", "Personality"),
        ("human_layer.response_builder", "Response Builder"),
        ("voice_layer.tts_engine", "TTS Engine"),
        ("voice_layer.voice_config", "Voice Config"),
        ("voice_layer.language_detector", "Language Detector"),
        ("pc_control.command_parser", "Command Parser"),
        ("pc_control.executor", "PC Executor"),
        ("pc_control.system_stats", "System Stats"),
        ("pc_control.web_search", "Web Search"),
        ("pc_control.reminder", "Reminder"),
        ("pc_control.daily_briefing", "Daily Briefing"),
        ("pc_control.file_manager", "File Manager"),
        ("pc_control.screen_recorder", "Screen Recorder"),
        ("self_healer.error_tracker", "Error Tracker"),
        ("self_healer.auto_fixer", "Auto Fixer"),
        ("pc_control.email_manager", "Email Manager"),
        ("pc_control.clipboard_manager", "Clipboard Manager"),
        ("pc_control.app_tracker", "App Usage Tracker"),
        ("pc_control.image_gen", "Image Generator"),
        ("self_healer.alert_system", "Alert System"),
    ]

    for module_path, name in modules_to_check:
        try:
            mod = importlib.import_module(module_path)
            results["modules"][name] = "ok"
        except Exception as e:
            results["modules"][name] = f"error: {str(e)}"
            results["issues"].append(f"{name} module load failed: {str(e)}")

    # Check critical files
    backend_dir = Path(__file__).parent.parent
    critical_files = [
        backend_dir / "main.py",
        backend_dir / "human_layer" / "prompts" / "mj_system_prompt.txt",
    ]
    for f in critical_files:
        if not f.exists():
            results["issues"].append(f"Critical file missing: {f.name}")

    # Check data directories
    data_dirs = [
        backend_dir / "chats",
        backend_dir / "audio",
        backend_dir / "error_logs",
    ]
    for d in data_dirs:
        if not d.exists():
            try:
                d.mkdir(parents=True, exist_ok=True)
            except Exception:
                results["issues"].append(f"Can't create directory: {d.name}")

    # Set overall status
    if not results["ollama"]:
        results["status"] = "degraded"
    if any("error" in str(v) for v in results["modules"].values()):
        results["status"] = "unhealthy"
    if len(results["issues"]) > 3:
        results["status"] = "critical"

    return results


def get_module_status() -> dict:
    """Quick module status check (no async)."""
    status = {}
    backend_dir = Path(__file__).parent.parent

    module_files = {
        "human_layer": backend_dir / "human_layer" / "human_brain.py",
        "voice_layer": backend_dir / "voice_layer" / "tts_engine.py",
        "pc_control": backend_dir / "pc_control" / "command_parser.py",
        "self_healer": backend_dir / "self_healer" / "error_tracker.py",
        "main": backend_dir / "main.py",
    }

    for name, path in module_files.items():
        if path.exists():
            try:
                code = path.read_text(encoding="utf-8")
                compile(code, str(path), "exec")
                status[name] = "ok"
            except SyntaxError as e:
                status[name] = f"syntax_error: line {e.lineno}"
        else:
            status[name] = "missing"

    return status
