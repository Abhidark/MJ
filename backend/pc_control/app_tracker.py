"""
MJ App Usage Tracker
Tracks active window, app usage time, generates productivity reports.
Background thread polls active window every 5 seconds.
"""

import subprocess
import threading
import time
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

TRACKER_FILE = Path(__file__).parent.parent / "app_usage.json"

# In-memory tracking
app_usage = {}  # {"app_name": total_seconds}
session_start = datetime.now()
_tracker_running = False
_current_app = ""
_current_start = datetime.now()

# Productivity categories
PRODUCTIVE_APPS = {
    "code", "visual studio", "vs code", "pycharm", "intellij", "android studio",
    "notepad", "sublime", "atom", "vim", "terminal", "cmd", "powershell",
    "word", "excel", "powerpoint", "outlook", "teams",
    "figma", "photoshop", "illustrator", "blender",
    "notion", "obsidian", "trello",
}

DISTRACTION_APPS = {
    "youtube", "instagram", "facebook", "twitter", "reddit", "tiktok",
    "netflix", "prime video", "disney", "hotstar",
    "whatsapp", "telegram", "discord",
    "spotify",
}


def _load_usage():
    global app_usage
    try:
        if TRACKER_FILE.exists():
            data = json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
            # Only load today's data
            if data.get("date") == datetime.now().strftime("%Y-%m-%d"):
                app_usage = data.get("apps", {})
            else:
                app_usage = {}
    except Exception:
        app_usage = {}


def _save_usage():
    try:
        data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "apps": app_usage,
            "session_start": session_start.isoformat(),
        }
        TRACKER_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _get_active_window() -> str:
    """Get the currently active window title."""
    ps = '''
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WinAPI {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
}
"@
$h = [WinAPI]::GetForegroundWindow()
$sb = New-Object System.Text.StringBuilder 256
[WinAPI]::GetWindowText($h, $sb, 256) | Out-Null
$sb.ToString()
'''
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip()
    except Exception:
        return ""


def _extract_app_name(window_title: str) -> str:
    """Extract app name from window title."""
    if not window_title:
        return "Unknown"

    title_lower = window_title.lower()

    # Known app patterns
    app_map = {
        "chrome": "Google Chrome",
        "firefox": "Firefox",
        "edge": "Microsoft Edge",
        "code": "VS Code",
        "visual studio code": "VS Code",
        "notepad": "Notepad",
        "explorer": "File Explorer",
        "discord": "Discord",
        "whatsapp": "WhatsApp",
        "spotify": "Spotify",
        "youtube": "YouTube",
        "outlook": "Outlook",
        "word": "Microsoft Word",
        "excel": "Microsoft Excel",
        "powerpoint": "PowerPoint",
        "teams": "Microsoft Teams",
        "terminal": "Terminal",
        "cmd": "Command Prompt",
        "powershell": "PowerShell",
    }

    for key, name in app_map.items():
        if key in title_lower:
            return name

    # Fallback: use last part after " - " or whole title
    parts = window_title.split(" - ")
    if len(parts) > 1:
        return parts[-1].strip()[:30]
    return window_title[:30]


def _monitor_apps():
    """Background thread to track active apps."""
    global _tracker_running, _current_app, _current_start
    _tracker_running = True
    _current_app = ""
    _current_start = datetime.now()

    while _tracker_running:
        try:
            window = _get_active_window()
            app_name = _extract_app_name(window)

            if app_name != _current_app:
                # Save time for previous app
                if _current_app:
                    elapsed = (datetime.now() - _current_start).total_seconds()
                    app_usage[_current_app] = app_usage.get(_current_app, 0) + elapsed

                _current_app = app_name
                _current_start = datetime.now()

            # Save periodically
            _save_usage()

        except Exception:
            pass
        time.sleep(5)


def start_app_tracker():
    """Start app tracking in background."""
    _load_usage()
    thread = threading.Thread(target=_monitor_apps, daemon=True)
    thread.start()


def stop_app_tracker():
    global _tracker_running
    _tracker_running = False


def get_usage_report() -> dict:
    """Get app usage report."""
    # Add current app's time
    current_usage = dict(app_usage)
    if _current_app:
        elapsed = (datetime.now() - _current_start).total_seconds()
        current_usage[_current_app] = current_usage.get(_current_app, 0) + elapsed

    if not current_usage:
        return {"success": True, "message": "Abhi koi usage data nahi hai.", "apps": []}

    # Sort by usage time
    sorted_apps = sorted(current_usage.items(), key=lambda x: x[1], reverse=True)

    # Calculate totals
    total_seconds = sum(v for _, v in sorted_apps)
    productive_seconds = 0
    distraction_seconds = 0

    for app, secs in sorted_apps:
        app_lower = app.lower()
        if any(p in app_lower for p in PRODUCTIVE_APPS):
            productive_seconds += secs
        elif any(d in app_lower for d in DISTRACTION_APPS):
            distraction_seconds += secs

    productivity_score = int((productive_seconds / max(total_seconds, 1)) * 100)

    # Format report
    lines = [f"App Usage Report ({datetime.now().strftime('%d %B %Y')}):"]
    lines.append(f"Total screen time: {_format_time(total_seconds)}")
    lines.append(f"Productivity score: {productivity_score}%")
    lines.append("")

    for app, secs in sorted_apps[:10]:
        pct = int((secs / max(total_seconds, 1)) * 100)
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        lines.append(f"  {app:<20} {_format_time(secs):>8}  {bar} {pct}%")

    if productive_seconds > 0:
        lines.append(f"\nProductive: {_format_time(productive_seconds)}")
    if distraction_seconds > 0:
        lines.append(f"Distraction: {_format_time(distraction_seconds)}")

    return {
        "success": True,
        "message": "\n".join(lines),
        "apps": [{"name": a, "seconds": int(s)} for a, s in sorted_apps],
        "productivity_score": productivity_score,
        "total_seconds": int(total_seconds),
    }


def get_current_app() -> str:
    """Get currently active app."""
    window = _get_active_window()
    return _extract_app_name(window)


def parse_tracker_command(text: str) -> Optional[dict]:
    """Parse app tracker commands."""
    lower = text.lower().strip()

    if any(w in lower for w in ["app usage", "screen time", "usage report", "app report",
                                 "productivity", "kitna use kiya", "kya kya use kiya",
                                 "app tracker", "usage dikhao", "aaj kya kiya"]):
        return {"action": "report"}

    if any(w in lower for w in ["current app", "kya chal raha", "active app", "abhi kya hai",
                                 "konsa app", "which app"]):
        return {"action": "current"}

    if any(w in lower for w in ["reset tracker", "tracker reset", "usage clear"]):
        return {"action": "reset"}

    return None


def handle_tracker_command(cmd: dict) -> dict:
    """Handle tracker commands."""
    if cmd["action"] == "report":
        return get_usage_report()
    elif cmd["action"] == "current":
        app = get_current_app()
        return {"success": True, "message": f"Abhi active hai: {app}"}
    elif cmd["action"] == "reset":
        global app_usage
        app_usage = {}
        _save_usage()
        return {"success": True, "message": "App usage tracker reset kar diya."}

    return {"success": False, "message": "Unknown tracker command."}


def _format_time(seconds: float) -> str:
    """Format seconds to readable time."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h {m}m"
