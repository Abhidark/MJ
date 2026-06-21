"""
MJ Clipboard Manager
Track clipboard history, search, paste previous items.
Uses PowerShell to read/write clipboard. Background thread monitors changes.
"""

import subprocess
import threading
import time
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

CLIPBOARD_FILE = Path(__file__).parent.parent / "clipboard_history.json"

# In-memory clipboard history
clipboard_history = []
MAX_HISTORY = 50
_monitor_running = False
_last_content = ""


def _load_history():
    global clipboard_history
    try:
        if CLIPBOARD_FILE.exists():
            clipboard_history = json.loads(CLIPBOARD_FILE.read_text(encoding="utf-8"))
    except Exception:
        clipboard_history = []


def _save_history():
    try:
        CLIPBOARD_FILE.write_text(
            json.dumps(clipboard_history[:MAX_HISTORY], ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception:
        pass


def get_clipboard() -> str:
    """Get current clipboard text."""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip()
    except Exception:
        return ""


def set_clipboard(text: str):
    """Set clipboard content."""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value '{text}'"],
            capture_output=True, timeout=5
        )
    except Exception:
        pass


def _monitor_clipboard():
    """Background thread to monitor clipboard changes."""
    global _last_content, _monitor_running
    _monitor_running = True
    _last_content = get_clipboard()

    while _monitor_running:
        try:
            current = get_clipboard()
            if current and current != _last_content:
                _last_content = current
                # Add to history
                entry = {
                    "content": current[:500],
                    "time": datetime.now().strftime("%I:%M %p"),
                    "timestamp": datetime.now().isoformat(),
                    "preview": current[:80].replace("\n", " "),
                }
                clipboard_history.insert(0, entry)
                if len(clipboard_history) > MAX_HISTORY:
                    clipboard_history.pop()
                _save_history()
        except Exception:
            pass
        time.sleep(2)


def start_clipboard_monitor():
    """Start monitoring clipboard in background."""
    _load_history()
    thread = threading.Thread(target=_monitor_clipboard, daemon=True)
    thread.start()


def stop_clipboard_monitor():
    global _monitor_running
    _monitor_running = False


def get_history(count: int = 10) -> list:
    """Get clipboard history."""
    return clipboard_history[:count]


def search_history(query: str) -> list:
    """Search clipboard history."""
    results = []
    for item in clipboard_history:
        if query.lower() in item["content"].lower():
            results.append(item)
        if len(results) >= 10:
            break
    return results


def parse_clipboard_command(text: str) -> Optional[dict]:
    """Parse clipboard commands."""
    lower = text.lower().strip()

    # Current clipboard
    if any(w in lower for w in ["clipboard kya hai", "last copy", "kya copy kiya",
                                 "clipboard dikhao", "what's copied", "clipboard check",
                                 "paste kya hai", "last copied"]):
        return {"action": "current"}

    # Clipboard history
    if any(w in lower for w in ["clipboard history", "copy history", "clipboard log",
                                 "sab copy dikhao", "clipboard list"]):
        return {"action": "history"}

    # Search clipboard
    m = re.search(r"(?:clipboard|copy)\s+(?:me|mein)\s+(?:search|find|dhundho)\s+(.+)", lower)
    if m:
        return {"action": "search", "query": m.group(1).strip()}

    # Copy to clipboard
    m = re.search(r"(?:copy|clipboard me daal|clipboard me rakh)\s+(.+)", lower)
    if m:
        return {"action": "copy", "text": m.group(1).strip()}

    # Paste from history (#N)
    m = re.search(r"(?:paste|use)\s+(?:clipboard|copy)\s+#?(\d+)", lower)
    if m:
        return {"action": "paste_history", "index": int(m.group(1)) - 1}

    # Clear clipboard
    if any(w in lower for w in ["clear clipboard", "clipboard clear", "clipboard saaf"]):
        return {"action": "clear"}

    return None


def handle_clipboard_command(cmd: dict) -> dict:
    """Handle clipboard commands."""
    action = cmd["action"]

    if action == "current":
        content = get_clipboard()
        if content:
            preview = content[:200].replace("\n", " ")
            return {"success": True, "message": f"Clipboard me hai: {preview}"}
        return {"success": True, "message": "Clipboard empty hai."}

    elif action == "history":
        history = get_history(10)
        if not history:
            return {"success": True, "message": "Clipboard history empty hai."}
        lines = [f"Last {len(history)} clipboard items:"]
        for i, item in enumerate(history, 1):
            lines.append(f"  #{i} [{item['time']}] {item['preview']}")
        return {"success": True, "message": "\n".join(lines)}

    elif action == "search":
        results = search_history(cmd["query"])
        if not results:
            return {"success": True, "message": f"'{cmd['query']}' clipboard history me nahi mila."}
        lines = [f"{len(results)} matches:"]
        for item in results:
            lines.append(f"  [{item['time']}] {item['preview']}")
        return {"success": True, "message": "\n".join(lines)}

    elif action == "copy":
        set_clipboard(cmd["text"])
        return {"success": True, "message": f"Copied to clipboard: {cmd['text'][:50]}"}

    elif action == "paste_history":
        idx = cmd["index"]
        if 0 <= idx < len(clipboard_history):
            content = clipboard_history[idx]["content"]
            set_clipboard(content)
            return {"success": True, "message": f"Clipboard me set kar diya: {content[:50]}..."}
        return {"success": False, "message": "Item number galat hai."}

    elif action == "clear":
        clipboard_history.clear()
        _save_history()
        set_clipboard("")
        return {"success": True, "message": "Clipboard cleared."}

    return {"success": False, "message": "Unknown clipboard command."}
