"""
Parse user text to detect PC control commands.
Returns command dict if detected, None if it's a normal chat message.
"""

import re

# App name mappings (user might say different names)
APP_ALIASES = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "browser": "chrome",
    "google": "chrome",
    "notepad": "notepad",
    "note pad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "file explorer": "explorer",
    "explorer": "explorer",
    "files": "explorer",
    "folder": "explorer",
    "my computer": "explorer",
    "command prompt": "cmd",
    "cmd": "cmd",
    "terminal": "cmd",
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    "control panel": "control",
    "paint": "mspaint",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "spotify": "spotify",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    "discord": "discord",
    "vlc": "vlc",
    "media player": "wmplayer",
    "snipping tool": "snippingtool",
    "camera": "microsoft.windows.camera:",
    "clock": "ms-clock:",
    "alarm": "ms-clock:",
    "photos": "ms-photos:",
    "store": "ms-windows-store:",
    "maps": "bingmaps:",
    "weather": "bingweather:",
    "mail": "outlookmail:",
    "calendar": "outlookcal:",
    "outlook": "outlook",
}

# Website shortcuts
WEBSITE_ALIASES = {
    "youtube": "https://youtube.com",
    "google": "https://google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "chatgpt": "https://chat.openai.com",
    "facebook": "https://facebook.com",
    "instagram": "https://instagram.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "linkedin": "https://linkedin.com",
    "reddit": "https://reddit.com",
    "whatsapp web": "https://web.whatsapp.com",
    "amazon": "https://amazon.in",
    "flipkart": "https://flipkart.com",
    "stack overflow": "https://stackoverflow.com",
    "stackoverflow": "https://stackoverflow.com",
}


def parse_command(text: str) -> dict | None:
    """
    Parse user text for PC control commands.
    Returns: {"action": "...", "target": "...", "params": {...}} or None
    """
    lower = text.lower().strip()

    # ---- OPEN APP ----
    open_patterns = [
        r"(?:open|launch|start|run|chalu|kholo|khol do|open kar|start kar|chalu kar)\s+(.+)",
        r"(.+)\s+(?:open karo|kholo|chalu karo|start karo|launch karo)",
    ]
    for pat in open_patterns:
        m = re.search(pat, lower)
        if m:
            target = m.group(1).strip().rstrip(".")
            # Remove filler words
            for filler in ["please", "plz", "pls", "bhi", "ek", "mera", "meri", "the", "a", "an", "kar", "karo", "do", "na"]:
                target = target.replace(filler, "").strip()

            if not target:
                continue

            # Check if it's a website
            for site, url in WEBSITE_ALIASES.items():
                if site in target:
                    return {"action": "open_website", "target": url, "name": site}

            # Check URL pattern
            if re.search(r'\.\w{2,}', target) or target.startswith("http"):
                url = target if target.startswith("http") else f"https://{target}"
                return {"action": "open_website", "target": url, "name": target}

            # Check app alias
            for alias, app in APP_ALIASES.items():
                if alias in target:
                    return {"action": "open_app", "target": app, "name": alias}

            # Try raw name
            return {"action": "open_app", "target": target, "name": target}

    # ---- CLOSE APP ----
    close_patterns = [
        r"(?:close|quit|exit|band|band karo|hatao|close kar)\s+(.+)",
        r"(.+)\s+(?:band karo|close karo|hatao|quit karo)",
    ]
    for pat in close_patterns:
        m = re.search(pat, lower)
        if m:
            target = m.group(1).strip().rstrip(".")
            for filler in ["please", "plz", "the", "a", "kar", "karo", "do"]:
                target = target.replace(filler, "").strip()
            if target:
                for alias, app in APP_ALIASES.items():
                    if alias in target:
                        return {"action": "close_app", "target": app, "name": alias}
                return {"action": "close_app", "target": target, "name": target}

    # ---- SCREENSHOT ----
    if any(w in lower for w in ["screenshot", "screen shot", "ss le", "screenshot le", "screen capture", "screenshot lo"]):
        return {"action": "screenshot", "target": None, "name": "screenshot"}

    # ---- VOLUME ----
    if any(w in lower for w in ["volume up", "volume badha", "awaz badha", "sound up", "volume increase"]):
        return {"action": "volume", "target": "up", "name": "volume up"}
    if any(w in lower for w in ["volume down", "volume kam", "awaz kam", "sound down", "volume decrease"]):
        return {"action": "volume", "target": "down", "name": "volume down"}
    if any(w in lower for w in ["mute", "mute karo", "silent", "awaz band"]):
        return {"action": "volume", "target": "mute", "name": "mute"}

    # ---- BRIGHTNESS ----
    if any(w in lower for w in ["brightness up", "brightness badha", "brighter"]):
        return {"action": "brightness", "target": "up", "name": "brightness up"}
    if any(w in lower for w in ["brightness down", "brightness kam", "dimmer", "dim"]):
        return {"action": "brightness", "target": "down", "name": "brightness down"}

    # ---- SYSTEM ----
    if any(w in lower for w in ["lock screen", "lock pc", "screen lock", "lock karo", "pc lock"]):
        return {"action": "system", "target": "lock", "name": "lock screen"}
    if any(w in lower for w in ["shutdown", "shut down", "pc band", "computer band"]):
        return {"action": "system", "target": "shutdown", "name": "shutdown"}
    if any(w in lower for w in ["restart", "reboot", "restart karo", "reboot karo"]):
        return {"action": "system", "target": "restart", "name": "restart"}
    if any(w in lower for w in ["sleep", "sleep mode", "sone do", "sleep karo"]):
        return {"action": "system", "target": "sleep", "name": "sleep"}

    # ---- SEARCH WEB ----
    search_patterns = [
        r"(?:search|google|search karo|dhundho|find)\s+(.+)",
        r"(.+)\s+(?:search karo|dhundho|google karo)",
    ]
    for pat in search_patterns:
        m = re.search(pat, lower)
        if m:
            query = m.group(1).strip()
            for filler in ["for", "about", "on", "ke baare me", "ke bare me", "ka", "ki"]:
                query = query.replace(filler, "").strip()
            if query and len(query) > 2:
                return {"action": "search", "target": query, "name": f"search: {query}"}

    # ---- MEDIA CONTROL ----
    if any(w in lower for w in ["pause", "pause karo", "ruko", "ruk"]):
        return {"action": "media", "target": "pause", "name": "pause"}
    if lower in ["play", "play karo", "chala", "bajao"]:
        return {"action": "media", "target": "play", "name": "play"}
    if any(w in lower for w in ["next song", "agla gaana", "next track", "skip"]):
        return {"action": "media", "target": "next", "name": "next track"}
    if any(w in lower for w in ["previous song", "pichla gaana", "previous track"]):
        return {"action": "media", "target": "prev", "name": "previous track"}

    # No command detected
    return None
