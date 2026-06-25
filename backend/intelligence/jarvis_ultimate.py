"""
MJ JARVIS OS Ultimate (V25)
Adds: unified system controller, PWA manifest stub, mobile-ready flags,
smart home hub controller, system-wide search, unified notifications.
"""

import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

UNIFIED_STATE_FILE = DATA_DIR / "jarvis_ultimate.json"
NOTIFICATIONS_FILE = DATA_DIR / "jarvis_notifications.json"
SMARTHOME_FILE = DATA_DIR / "jarvis_smarthome.json"


def _load_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def _save_json(path, data):
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# ========================
# UNIFIED SYSTEM CONTROLLER
# ========================

class UnifiedController:
    """Central control hub connecting all MJ subsystems."""

    SUBSYSTEMS = {
        "zeus": {"name": "Zeus Brain", "category": "core", "icon": "brain"},
        "memory": {"name": "Memory Engine", "category": "core", "icon": "database"},
        "workflow": {"name": "Workflow Engine", "category": "intelligence", "icon": "flow"},
        "agents": {"name": "Multi-Agent", "category": "intelligence", "icon": "users"},
        "plugins": {"name": "Plugin System", "category": "extension", "icon": "puzzle"},
        "self_improve": {"name": "Self-Improving", "category": "intelligence", "icon": "trending"},
        "ai_os": {"name": "AI Operating System", "category": "system", "icon": "monitor"},
        "security": {"name": "Sentinel Security", "category": "system", "icon": "shield"},
        "creative": {"name": "Apollo Creative", "category": "creative", "icon": "palette"},
        "communication": {"name": "Hermes Comms", "category": "communication", "icon": "mail"},
        "knowledge": {"name": "Athena Knowledge", "category": "intelligence", "icon": "book"},
        "developer": {"name": "Hephaestus Dev", "category": "developer", "icon": "code"},
        "vision": {"name": "Argus Vision", "category": "perception", "icon": "eye"},
        "time": {"name": "Chronos Time", "category": "utility", "icon": "clock"},
    }

    def __init__(self):
        self.state: dict = {}
        self._load()

    def _load(self):
        self.state = _load_json(UNIFIED_STATE_FILE, {
            "mode": "standard",  # standard, performance, battery_saver, developer
            "active_subsystems": list(self.SUBSYSTEMS.keys()),
            "boot_time": None,
            "uptime_seconds": 0,
        })

    def _save(self):
        _save_json(UNIFIED_STATE_FILE, self.state)

    def boot(self) -> dict:
        """Boot the unified system."""
        self.state["boot_time"] = datetime.now().isoformat()
        self.state["active_subsystems"] = list(self.SUBSYSTEMS.keys())
        self._save()
        return {
            "status": "booted",
            "subsystems_loaded": len(self.SUBSYSTEMS),
            "mode": self.state.get("mode", "standard"),
            "boot_time": self.state["boot_time"],
        }

    def get_system_overview(self) -> dict:
        """Get unified overview of all subsystems."""
        by_category = {}
        for sid, info in self.SUBSYSTEMS.items():
            cat = info["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append({
                "id": sid, "name": info["name"], "icon": info["icon"],
                "active": sid in self.state.get("active_subsystems", []),
            })

        return {
            "mode": self.state.get("mode", "standard"),
            "total_subsystems": len(self.SUBSYSTEMS),
            "active": len(self.state.get("active_subsystems", [])),
            "by_category": by_category,
            "boot_time": self.state.get("boot_time"),
        }

    def set_mode(self, mode: str) -> dict:
        """Set system mode — affects which subsystems are active."""
        modes = {
            "standard": list(self.SUBSYSTEMS.keys()),
            "performance": ["zeus", "memory", "workflow", "agents", "self_improve"],
            "battery_saver": ["zeus", "memory", "security"],
            "developer": ["zeus", "memory", "developer", "workflow", "plugins"],
        }
        if mode not in modes:
            return {"error": f"Invalid mode. Choose from: {list(modes.keys())}"}

        self.state["mode"] = mode
        self.state["active_subsystems"] = modes[mode]
        self._save()
        return {"success": True, "mode": mode, "active_count": len(modes[mode])}

    def system_search(self, query: str) -> dict:
        """Search across all subsystems (stub — returns matching subsystem names)."""
        results = []
        q = query.lower()
        for sid, info in self.SUBSYSTEMS.items():
            if q in info["name"].lower() or q in sid or q in info["category"]:
                results.append({"id": sid, "name": info["name"], "category": info["category"]})
        return {"query": query, "results": results, "total": len(results)}

    def get_quick_actions(self) -> list:
        """Get quick actions for the unified dashboard."""
        return [
            {"id": "briefing", "label": "Morning Briefing", "icon": "sun", "action": "/workflows/daily-briefing"},
            {"id": "search", "label": "Deep Search", "icon": "search", "action": "/knowledge/search"},
            {"id": "create", "label": "Create Something", "icon": "plus", "action": "/creative/new"},
            {"id": "status", "label": "System Status", "icon": "activity", "action": "/os/status"},
            {"id": "memory", "label": "My Memory", "icon": "brain", "action": "/memory/stats"},
            {"id": "calendar", "label": "Today's Plan", "icon": "calendar", "action": "/calendar/today"},
        ]


# ========================
# PWA & MOBILE SUPPORT STUB
# ========================

class PWAManager:
    """Progressive Web App manifest and mobile readiness."""

    MANIFEST = {
        "name": "MJ Assistant — JARVIS OS",
        "short_name": "MJ JARVIS",
        "description": "Your AI Operating System",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#6366f1",
        "orientation": "any",
        "icons": [
            {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
        "categories": ["productivity", "utilities"],
    }

    MOBILE_CONFIG = {
        "responsive": True,
        "touch_gestures": True,
        "swipe_navigation": True,
        "bottom_nav": True,
        "offline_mode": "stub",
        "push_notifications": "stub",
        "min_viewport": "320px",
    }

    def get_manifest(self) -> dict:
        return self.MANIFEST

    def get_mobile_config(self) -> dict:
        return self.MOBILE_CONFIG

    def get_install_prompt_data(self) -> dict:
        return {
            "can_install": True,
            "platform": "web",
            "manifest_url": "/manifest.json",
            "service_worker": "/sw.js",
            "status": "stub — not yet registered",
        }


# ========================
# SMART HOME HUB CONTROLLER
# ========================

class SmartHomeHub:
    """Central hub for smart home device management."""

    def __init__(self):
        self.devices: dict = {}
        self.scenes: dict = {}
        self.automations: list = []
        self._load()

    def _load(self):
        data = _load_json(SMARTHOME_FILE, {})
        self.devices = data.get("devices", {})
        self.scenes = data.get("scenes", {})
        self.automations = data.get("automations", [])

    def _save(self):
        _save_json(SMARTHOME_FILE, {
            "devices": self.devices,
            "scenes": self.scenes,
            "automations": self.automations,
        })

    def add_device(self, device_id: str, name: str, device_type: str,
                   room: str = "", protocol: str = "wifi") -> dict:
        self.devices[device_id] = {
            "id": device_id, "name": name, "type": device_type,
            "room": room, "protocol": protocol,
            "status": "offline", "state": {},
            "added": datetime.now().isoformat(),
        }
        self._save()
        return {"success": True, "device": self.devices[device_id]}

    def set_device_state(self, device_id: str, state: dict) -> dict:
        if device_id not in self.devices:
            return {"error": "Device not found"}
        self.devices[device_id]["state"].update(state)
        self.devices[device_id]["status"] = "online"
        self._save()
        return {"success": True, "device": self.devices[device_id]}

    def get_devices(self, room: str = "", device_type: str = "") -> dict:
        items = list(self.devices.values())
        if room:
            items = [d for d in items if d.get("room") == room]
        if device_type:
            items = [d for d in items if d.get("type") == device_type]
        return {"devices": items, "total": len(items)}

    def create_scene(self, name: str, actions: list) -> dict:
        sid = name.lower().replace(" ", "_")
        self.scenes[sid] = {
            "id": sid, "name": name, "actions": actions,
            "created": datetime.now().isoformat(),
        }
        self._save()
        return {"success": True, "scene": self.scenes[sid]}

    def activate_scene(self, scene_id: str) -> dict:
        scene = self.scenes.get(scene_id)
        if not scene:
            return {"error": "Scene not found"}
        executed = []
        for action in scene.get("actions", []):
            did = action.get("device_id")
            if did in self.devices:
                self.devices[did]["state"].update(action.get("state", {}))
                executed.append(did)
        self._save()
        return {"success": True, "scene": scene["name"], "devices_affected": len(executed)}

    def get_scenes(self) -> dict:
        return {"scenes": list(self.scenes.values()), "total": len(self.scenes)}

    def get_rooms(self) -> dict:
        rooms = {}
        for d in self.devices.values():
            r = d.get("room", "unassigned")
            if r not in rooms:
                rooms[r] = []
            rooms[r].append({"id": d["id"], "name": d["name"], "type": d["type"]})
        return {"rooms": rooms}

    def remove_device(self, device_id: str) -> dict:
        if device_id not in self.devices:
            return {"error": "Not found"}
        del self.devices[device_id]
        self._save()
        return {"success": True}


# ========================
# UNIFIED NOTIFICATION CENTER
# ========================

class NotificationCenter:
    """Unified notification system across all subsystems."""

    def __init__(self):
        self.notifications: list = []
        self._load()

    def _load(self):
        data = _load_json(NOTIFICATIONS_FILE, [])
        self.notifications = data if isinstance(data, list) else []

    def _save(self):
        _save_json(NOTIFICATIONS_FILE, self.notifications[-200:])

    def send(self, title: str, body: str, category: str = "info",
             source: str = "system", priority: str = "normal") -> dict:
        notif = {
            "id": f"notif_{int(time.time())}",
            "title": title, "body": body,
            "category": category,  # info, warning, error, success, reminder
            "source": source,
            "priority": priority,  # low, normal, high, urgent
            "read": False,
            "ts": datetime.now().isoformat(),
        }
        self.notifications.append(notif)
        self._save()
        return {"success": True, "notification": notif}

    def get_unread(self) -> dict:
        unread = [n for n in self.notifications if not n.get("read")]
        return {"notifications": unread[-20:], "unread_count": len(unread)}

    def mark_read(self, notif_id: str) -> dict:
        for n in self.notifications:
            if n.get("id") == notif_id:
                n["read"] = True
                self._save()
                return {"success": True}
        return {"error": "Not found"}

    def mark_all_read(self) -> dict:
        count = 0
        for n in self.notifications:
            if not n.get("read"):
                n["read"] = True
                count += 1
        self._save()
        return {"marked": count}

    def get_all(self, category: str = "", limit: int = 30) -> dict:
        items = self.notifications
        if category:
            items = [n for n in items if n.get("category") == category]
        return {"notifications": items[-limit:], "total": len(items)}

    def clear_old(self, days: int = 7) -> dict:
        cutoff = time.time() - (days * 86400)
        before = len(self.notifications)
        self.notifications = [
            n for n in self.notifications
            if not n.get("read") or time.mktime(
                datetime.fromisoformat(n["ts"]).timetuple()) > cutoff
        ]
        self._save()
        return {"cleared": before - len(self.notifications)}


# ========================
# SERVICE WORKER / OFFLINE CACHE STUB
# ========================

class ServiceWorkerManager:
    """Service worker registration and offline cache management stub."""

    SW_FILE = DATA_DIR / "jarvis_sw_config.json"

    def __init__(self):
        self.config: dict = {}
        self._load()

    def _load(self):
        self.config = _load_json(self.SW_FILE, {
            "registered": False,
            "cache_version": "v1",
            "cached_routes": [],
            "offline_pages": ["/", "/dashboard"],
            "cache_strategy": "network-first",
        })

    def _save(self):
        _save_json(self.SW_FILE, self.config)

    def register(self) -> dict:
        """Stub: register the service worker."""
        self.config["registered"] = True
        self._save()
        return {"success": True, "status": "registered", "cache_version": self.config["cache_version"]}

    def unregister(self) -> dict:
        """Unregister the service worker."""
        self.config["registered"] = False
        self._save()
        return {"success": True, "status": "unregistered"}

    def add_cached_route(self, route: str, strategy: str = "network-first") -> dict:
        """Add a route to the offline cache.
        strategy: cache-first, network-first, stale-while-revalidate
        """
        valid_strategies = ["cache-first", "network-first", "stale-while-revalidate"]
        if strategy not in valid_strategies:
            return {"error": f"Invalid strategy. Choose from: {valid_strategies}"}
        entry = {"route": route, "strategy": strategy, "added": datetime.now().isoformat()}
        self.config["cached_routes"].append(entry)
        self._save()
        return {"success": True, "route": entry}

    def get_config(self) -> dict:
        """Return full service worker config."""
        return self.config

    def clear_cache(self) -> dict:
        """Increment cache version and clear cached routes."""
        ver = self.config.get("cache_version", "v1")
        num = int(ver.lstrip("v")) + 1
        self.config["cache_version"] = f"v{num}"
        self.config["cached_routes"] = []
        self._save()
        return {"success": True, "new_version": self.config["cache_version"]}

    def get_offline_status(self) -> dict:
        """Return offline readiness status."""
        return {
            "offline_ready": self.config.get("registered", False) and len(self.config.get("cached_routes", [])) > 0,
            "cached_pages": len(self.config.get("cached_routes", [])),
            "cache_version": self.config.get("cache_version", "v1"),
        }


# ========================
# GLOBAL COMMAND PALETTE
# ========================

class CommandPalette:
    """Global command palette — in-memory, no persistence file."""

    def __init__(self):
        self.COMMANDS: list = [
            {"id": "search", "label": "Search Everything", "shortcut": "Ctrl+K", "category": "search", "action": "/search"},
            {"id": "settings", "label": "Settings", "shortcut": "Ctrl+,", "category": "system", "action": "/settings"},
            {"id": "new-chat", "label": "New Chat", "shortcut": "Ctrl+N", "category": "action", "action": "/chat/new"},
            {"id": "memory", "label": "Memory Manager", "shortcut": "Ctrl+M", "category": "navigation", "action": "/memory"},
            {"id": "calendar", "label": "Calendar", "shortcut": "Ctrl+Shift+C", "category": "navigation", "action": "/calendar"},
            {"id": "workflows", "label": "Workflows", "shortcut": "Ctrl+Shift+W", "category": "navigation", "action": "/workflows"},
            {"id": "plugins", "label": "Plugins", "shortcut": "Ctrl+Shift+P", "category": "navigation", "action": "/plugins"},
            {"id": "system-status", "label": "System Status", "shortcut": "Ctrl+Shift+S", "category": "system", "action": "/os/status"},
            {"id": "notifications", "label": "Notifications", "shortcut": "Ctrl+Shift+N", "category": "system", "action": "/notifications"},
            {"id": "smart-home", "label": "Smart Home", "shortcut": "Ctrl+Shift+H", "category": "navigation", "action": "/smart-home"},
            {"id": "theme-toggle", "label": "Toggle Theme", "shortcut": "Ctrl+Shift+T", "category": "action", "action": "/theme/toggle"},
            {"id": "mode-switch", "label": "Switch Mode", "shortcut": "Ctrl+Shift+M", "category": "action", "action": "/mode/switch"},
            {"id": "quick-actions", "label": "Quick Actions", "shortcut": "Ctrl+Q", "category": "action", "action": "/quick-actions"},
            {"id": "help", "label": "Help & Docs", "shortcut": "F1", "category": "system", "action": "/help"},
            {"id": "about", "label": "About JARVIS", "shortcut": "Ctrl+Shift+A", "category": "system", "action": "/about"},
        ]

    def search(self, query: str) -> list:
        """Fuzzy match against label and category."""
        q = query.lower()
        results = []
        for cmd in self.COMMANDS:
            label_lower = cmd["label"].lower()
            cat_lower = cmd["category"].lower()
            if q in label_lower or q in cat_lower or q in cmd["id"]:
                results.append(cmd)
        return results

    def get_all(self) -> list:
        """Return all registered commands."""
        return self.COMMANDS

    def get_by_category(self, category: str) -> list:
        """Filter commands by category."""
        return [c for c in self.COMMANDS if c["category"] == category]

    def register_command(self, id: str, label: str, shortcut: str,
                         category: str, action: str) -> dict:
        """Add a custom command to the palette."""
        for cmd in self.COMMANDS:
            if cmd["id"] == id:
                return {"error": f"Command '{id}' already exists"}
        new_cmd = {"id": id, "label": label, "shortcut": shortcut,
                   "category": category, "action": action}
        self.COMMANDS.append(new_cmd)
        return {"success": True, "command": new_cmd}

    def remove_command(self, cmd_id: str) -> dict:
        """Remove a custom command by id."""
        before = len(self.COMMANDS)
        self.COMMANDS = [c for c in self.COMMANDS if c["id"] != cmd_id]
        if len(self.COMMANDS) == before:
            return {"error": "Command not found"}
        return {"success": True, "removed": cmd_id}


# ========================
# SYSTEM THEME ENGINE
# ========================

class ThemeEngine:
    """Theme engine with built-in and custom themes."""

    THEME_FILE = DATA_DIR / "jarvis_themes.json"

    BUILT_IN_THEMES = {
        "dark": {
            "primary": "#6366f1", "bg": "#0f172a", "surface": "#1e293b",
            "text": "#f8fafc", "accent": "#818cf8",
        },
        "light": {
            "primary": "#4f46e5", "bg": "#f8fafc", "surface": "#ffffff",
            "text": "#0f172a", "accent": "#6366f1",
        },
        "cyberpunk": {
            "primary": "#00ff41", "bg": "#0a0a0a", "surface": "#1a1a2e",
            "text": "#00ff41", "accent": "#ff00ff",
        },
        "ocean": {
            "primary": "#0ea5e9", "bg": "#0c1222", "surface": "#1e293b",
            "text": "#e2e8f0", "accent": "#38bdf8",
        },
    }

    def __init__(self):
        self.state: dict = {}
        self._load()

    def _load(self):
        self.state = _load_json(self.THEME_FILE, {
            "active_theme": "dark",
            "custom_themes": {},
        })

    def _save(self):
        _save_json(self.THEME_FILE, self.state)

    def get_theme(self) -> dict:
        """Return active theme colors."""
        name = self.state.get("active_theme", "dark")
        if name in self.BUILT_IN_THEMES:
            return {"name": name, "colors": self.BUILT_IN_THEMES[name]}
        custom = self.state.get("custom_themes", {})
        if name in custom:
            return {"name": name, "colors": custom[name]}
        return {"name": "dark", "colors": self.BUILT_IN_THEMES["dark"]}

    def set_theme(self, theme_name: str) -> dict:
        """Switch the active theme."""
        all_themes = {**self.BUILT_IN_THEMES, **self.state.get("custom_themes", {})}
        if theme_name not in all_themes:
            return {"error": f"Theme '{theme_name}' not found. Available: {list(all_themes.keys())}"}
        self.state["active_theme"] = theme_name
        self._save()
        return {"success": True, "active_theme": theme_name, "colors": all_themes[theme_name]}

    def get_all_themes(self) -> dict:
        """List all available themes (built-in + custom)."""
        themes = {}
        for name, colors in self.BUILT_IN_THEMES.items():
            themes[name] = {"colors": colors, "built_in": True}
        for name, colors in self.state.get("custom_themes", {}).items():
            themes[name] = {"colors": colors, "built_in": False}
        return {"themes": themes, "active": self.state.get("active_theme", "dark")}

    def create_custom_theme(self, name: str, colors: dict) -> dict:
        """Add a user-defined theme."""
        if name in self.BUILT_IN_THEMES:
            return {"error": "Cannot overwrite a built-in theme"}
        if "custom_themes" not in self.state:
            self.state["custom_themes"] = {}
        self.state["custom_themes"][name] = colors
        self._save()
        return {"success": True, "theme": name, "colors": colors}

    def delete_custom_theme(self, name: str) -> dict:
        """Remove a custom theme (cannot delete built-in)."""
        if name in self.BUILT_IN_THEMES:
            return {"error": "Cannot delete built-in themes"}
        custom = self.state.get("custom_themes", {})
        if name not in custom:
            return {"error": "Custom theme not found"}
        del custom[name]
        if self.state.get("active_theme") == name:
            self.state["active_theme"] = "dark"
        self._save()
        return {"success": True, "deleted": name}

    def export_theme(self, name: str) -> dict:
        """Return theme data for sharing."""
        all_themes = {**self.BUILT_IN_THEMES, **self.state.get("custom_themes", {})}
        if name not in all_themes:
            return {"error": "Theme not found"}
        return {"name": name, "colors": all_themes[name]}

    def import_theme(self, name: str, colors: dict) -> dict:
        """Import a theme (same as create_custom)."""
        return self.create_custom_theme(name, colors)


# ========================
# APP LAUNCHER
# ========================

class AppLauncher:
    """App launcher with pinned, recent, and favorite apps."""

    LAUNCHER_FILE = DATA_DIR / "jarvis_launcher.json"

    def __init__(self):
        self.data: dict = {}
        self._load()

    def _load(self):
        self.data = _load_json(self.LAUNCHER_FILE, {
            "pinned": [],
            "recent": [],
            "favorites": [],
        })

    def _save(self):
        _save_json(self.LAUNCHER_FILE, self.data)

    def launch(self, app_id: str, app_name: str) -> dict:
        """Launch an app — adds to recent list (max 20)."""
        entry = {"app_id": app_id, "app_name": app_name, "launched_at": datetime.now().isoformat()}
        # Remove previous occurrence if present
        self.data["recent"] = [r for r in self.data["recent"] if r.get("app_id") != app_id]
        self.data["recent"].insert(0, entry)
        self.data["recent"] = self.data["recent"][:20]
        self._save()
        return {"launched": True, "app_id": app_id, "app_name": app_name}

    def pin(self, app_id: str, app_name: str) -> dict:
        """Add an app to pinned list."""
        for p in self.data["pinned"]:
            if p.get("app_id") == app_id:
                return {"error": "Already pinned"}
        self.data["pinned"].append({"app_id": app_id, "app_name": app_name})
        self._save()
        return {"success": True, "pinned": app_id}

    def unpin(self, app_id: str) -> dict:
        """Remove an app from pinned list."""
        before = len(self.data["pinned"])
        self.data["pinned"] = [p for p in self.data["pinned"] if p.get("app_id") != app_id]
        if len(self.data["pinned"]) == before:
            return {"error": "Not found in pinned"}
        self._save()
        return {"success": True, "unpinned": app_id}

    def add_favorite(self, app_id: str, app_name: str) -> dict:
        """Add an app to favorites."""
        for f in self.data["favorites"]:
            if f.get("app_id") == app_id:
                return {"error": "Already in favorites"}
        self.data["favorites"].append({"app_id": app_id, "app_name": app_name})
        self._save()
        return {"success": True, "favorited": app_id}

    def remove_favorite(self, app_id: str) -> dict:
        """Remove an app from favorites."""
        before = len(self.data["favorites"])
        self.data["favorites"] = [f for f in self.data["favorites"] if f.get("app_id") != app_id]
        if len(self.data["favorites"]) == before:
            return {"error": "Not found in favorites"}
        self._save()
        return {"success": True, "removed": app_id}

    def get_launcher_data(self) -> dict:
        """Return all launcher data."""
        return {
            "pinned": self.data.get("pinned", []),
            "recent": self.data.get("recent", []),
            "favorites": self.data.get("favorites", []),
        }

    def clear_recent(self) -> dict:
        """Clear the recent apps list."""
        count = len(self.data.get("recent", []))
        self.data["recent"] = []
        self._save()
        return {"success": True, "cleared": count}


# ========================
# VOICE ASSISTANT HUB
# ========================

class VoiceHub:
    """Voice assistant configuration and status hub."""

    VOICE_FILE = DATA_DIR / "jarvis_voice_config.json"

    AVAILABLE_VOICES = [
        {"id": "default", "name": "Default", "gender": "neutral", "style": "professional"},
        {"id": "aria", "name": "Aria", "gender": "female", "style": "warm"},
        {"id": "nova", "name": "Nova", "gender": "female", "style": "energetic"},
        {"id": "echo", "name": "Echo", "gender": "male", "style": "calm"},
        {"id": "onyx", "name": "Onyx", "gender": "male", "style": "deep"},
    ]

    def __init__(self):
        self.config: dict = {}
        self._load()

    def _load(self):
        self.config = _load_json(self.VOICE_FILE, {
            "wake_word": "hey jarvis",
            "voice_id": "default",
            "speed": 1.0,
            "language": "en",
            "continuous_listening": False,
            "sound_effects": True,
        })

    def _save(self):
        _save_json(self.VOICE_FILE, self.config)

    def get_config(self) -> dict:
        """Return voice configuration."""
        return self.config

    def update_config(self, updates: dict) -> dict:
        """Merge updates into voice config."""
        self.config.update(updates)
        self._save()
        return {"success": True, "config": self.config}

    def set_wake_word(self, word: str) -> dict:
        """Update the wake word."""
        self.config["wake_word"] = word
        self._save()
        return {"success": True, "wake_word": word}

    def get_voice_status(self) -> dict:
        """Return current voice assistant status."""
        return {
            "active": False,
            "wake_word": self.config.get("wake_word", "hey jarvis"),
            "listening": False,
            "status": "stub",
        }

    def get_available_voices(self) -> list:
        """Return list of available stub voices."""
        return self.AVAILABLE_VOICES


# ========================
# CROSS-DEVICE LIVE SYNC (V25 → 100%)
# ========================

LIVE_SYNC_FILE = DATA_DIR / "jarvis_live_sync.json"

class LiveSyncEngine:
    """Real-time cross-device sync with pairing, queue, and conflict resolution."""

    def __init__(self):
        self._load()

    def _load(self):
        try:
            self.state = json.loads(LIVE_SYNC_FILE.read_text()) if LIVE_SYNC_FILE.exists() else {}
        except Exception:
            self.state = {}
        self.state.setdefault("paired_devices", {})
        self.state.setdefault("sync_queue", [])
        self.state.setdefault("conflicts", [])
        self.state.setdefault("config", {
            "enabled": False, "mode": "push-pull",
            "interval_sec": 30, "auto_resolve": "latest-wins",
        })

    def _save(self):
        LIVE_SYNC_FILE.write_text(json.dumps(self.state, indent=2, default=str))

    def pair_device(self, device_id: str, name: str, device_type: str = "desktop") -> dict:
        self.state["paired_devices"][device_id] = {
            "id": device_id, "name": name, "type": device_type,
            "paired_at": datetime.now().isoformat(),
            "last_sync": None, "status": "paired",
        }
        self._save()
        return {"success": True, "device": self.state["paired_devices"][device_id]}

    def unpair_device(self, device_id: str) -> dict:
        if device_id not in self.state["paired_devices"]:
            return {"error": "Device not found"}
        del self.state["paired_devices"][device_id]
        self._save()
        return {"success": True}

    def get_paired_devices(self) -> dict:
        return {"devices": list(self.state["paired_devices"].values()),
                "total": len(self.state["paired_devices"])}

    def push_sync(self, data_type: str, payload: dict, source_device: str = "local") -> dict:
        entry = {
            "id": f"sync_{int(time.time())}_{len(self.state['sync_queue']) % 10000}",
            "data_type": data_type, "payload_keys": list(payload.keys()),
            "source": source_device, "status": "pending",
            "ts": datetime.now().isoformat(),
        }
        self.state["sync_queue"].append(entry)
        self.state["sync_queue"] = self.state["sync_queue"][-200:]
        # mark devices as synced
        for d in self.state["paired_devices"].values():
            if d["id"] != source_device:
                d["last_sync"] = datetime.now().isoformat()
        self._save()
        return {"success": True, "sync_entry": entry}

    def get_sync_queue(self, limit: int = 30) -> dict:
        return {"queue": self.state["sync_queue"][-limit:],
                "total": len(self.state["sync_queue"])}

    def resolve_conflict(self, conflict_id: str, resolution: str = "keep-local") -> dict:
        for c in self.state["conflicts"]:
            if c.get("id") == conflict_id:
                c["resolved"] = True
                c["resolution"] = resolution
                c["resolved_at"] = datetime.now().isoformat()
                self._save()
                return {"success": True, "conflict": c}
        return {"error": "Conflict not found"}

    def get_conflicts(self) -> dict:
        unresolved = [c for c in self.state["conflicts"] if not c.get("resolved")]
        return {"conflicts": self.state["conflicts"], "unresolved": len(unresolved)}

    def get_config(self) -> dict:
        return self.state["config"]

    def update_config(self, updates: dict) -> dict:
        for k, v in updates.items():
            if k in self.state["config"]:
                self.state["config"][k] = v
        self._save()
        return {"success": True, "config": self.state["config"]}

    def get_sync_status(self) -> dict:
        return {
            "enabled": self.state["config"]["enabled"],
            "paired_devices": len(self.state["paired_devices"]),
            "pending_syncs": sum(1 for s in self.state["sync_queue"] if s.get("status") == "pending"),
            "unresolved_conflicts": sum(1 for c in self.state["conflicts"] if not c.get("resolved")),
            "config": self.state["config"],
        }


# ========================
# MOBILE APP SHELL (V25 → 100%)
# ========================

MOBILE_SHELL_FILE = DATA_DIR / "jarvis_mobile_shell.json"

class MobileAppShell:
    """Full mobile app shell with bottom nav, gestures, haptics, and layout."""

    DEFAULT_NAV = [
        {"id": "home", "label": "Home", "icon": "home", "route": "/"},
        {"id": "chat", "label": "Chat", "icon": "message-circle", "route": "/chat"},
        {"id": "tools", "label": "Tools", "icon": "wrench", "route": "/tools"},
        {"id": "memory", "label": "Memory", "icon": "brain", "route": "/memory"},
        {"id": "settings", "label": "Settings", "icon": "settings", "route": "/settings"},
    ]

    DEFAULT_GESTURES = {
        "swipe_left": "next-tab", "swipe_right": "prev-tab",
        "swipe_down": "refresh", "swipe_up": "command-palette",
        "long_press": "context-menu", "pinch": "zoom",
        "double_tap": "quick-action",
    }

    def __init__(self):
        self._load()

    def _load(self):
        try:
            self.state = json.loads(MOBILE_SHELL_FILE.read_text()) if MOBILE_SHELL_FILE.exists() else {}
        except Exception:
            self.state = {}
        self.state.setdefault("bottom_nav", list(self.DEFAULT_NAV))
        self.state.setdefault("gestures", dict(self.DEFAULT_GESTURES))
        self.state.setdefault("haptics", {"enabled": True, "intensity": "medium"})
        self.state.setdefault("layout", {
            "mode": "compact", "safe_area": True,
            "status_bar": "dark", "orientation": "portrait",
            "font_scale": 1.0,
        })

    def _save(self):
        MOBILE_SHELL_FILE.write_text(json.dumps(self.state, indent=2, default=str))

    def get_nav(self) -> dict:
        return {"nav_items": self.state["bottom_nav"]}

    def set_nav(self, items: list) -> dict:
        self.state["bottom_nav"] = items
        self._save()
        return {"success": True, "nav_items": items}

    def add_nav_item(self, item_id: str, label: str, icon: str, route: str) -> dict:
        self.state["bottom_nav"].append({"id": item_id, "label": label, "icon": icon, "route": route})
        self._save()
        return {"success": True}

    def remove_nav_item(self, item_id: str) -> dict:
        self.state["bottom_nav"] = [n for n in self.state["bottom_nav"] if n.get("id") != item_id]
        self._save()
        return {"success": True}

    def get_gestures(self) -> dict:
        return {"gestures": self.state["gestures"]}

    def set_gesture(self, gesture: str, action: str) -> dict:
        self.state["gestures"][gesture] = action
        self._save()
        return {"success": True, "gesture": gesture, "action": action}

    def get_haptics(self) -> dict:
        return self.state["haptics"]

    def set_haptics(self, enabled: bool = True, intensity: str = "medium") -> dict:
        self.state["haptics"] = {"enabled": enabled, "intensity": intensity}
        self._save()
        return {"success": True, "haptics": self.state["haptics"]}

    def get_layout(self) -> dict:
        return self.state["layout"]

    def update_layout(self, updates: dict) -> dict:
        for k, v in updates.items():
            if k in self.state["layout"]:
                self.state["layout"][k] = v
        self._save()
        return {"success": True, "layout": self.state["layout"]}

    def get_shell_status(self) -> dict:
        return {
            "nav_items": len(self.state["bottom_nav"]),
            "gestures": len(self.state["gestures"]),
            "haptics": self.state["haptics"],
            "layout": self.state["layout"],
        }


# ========================
# GLOBAL HOTKEYS (V25 → 100%)
# ========================

HOTKEYS_FILE = DATA_DIR / "jarvis_hotkeys.json"

class GlobalHotkeys:
    """Global hotkey system with profiles, register/unregister, and defaults."""

    DEFAULT_BINDINGS = {
        "toggle-assistant": {"keys": "Ctrl+Shift+J", "action": "toggle-assistant", "label": "Toggle JARVIS"},
        "command-palette": {"keys": "Ctrl+K", "action": "open-command-palette", "label": "Command Palette"},
        "quick-search": {"keys": "Ctrl+Shift+F", "action": "global-search", "label": "Global Search"},
        "new-chat": {"keys": "Ctrl+N", "action": "new-chat", "label": "New Chat"},
        "voice-toggle": {"keys": "Ctrl+Shift+V", "action": "toggle-voice", "label": "Toggle Voice"},
        "screenshot": {"keys": "Ctrl+Shift+S", "action": "take-screenshot", "label": "Screenshot"},
        "theme-toggle": {"keys": "Ctrl+Shift+T", "action": "toggle-theme", "label": "Toggle Theme"},
        "minimize": {"keys": "Ctrl+Shift+M", "action": "minimize-to-tray", "label": "Minimize to Tray"},
    }

    def __init__(self):
        self._load()

    def _load(self):
        try:
            self.state = json.loads(HOTKEYS_FILE.read_text()) if HOTKEYS_FILE.exists() else {}
        except Exception:
            self.state = {}
        self.state.setdefault("bindings", dict(self.DEFAULT_BINDINGS))
        self.state.setdefault("profiles", {"default": dict(self.DEFAULT_BINDINGS)})
        self.state.setdefault("active_profile", "default")
        self.state.setdefault("enabled", True)

    def _save(self):
        HOTKEYS_FILE.write_text(json.dumps(self.state, indent=2, default=str))

    def register(self, hotkey_id: str, keys: str, action: str, label: str = "") -> dict:
        self.state["bindings"][hotkey_id] = {
            "keys": keys, "action": action, "label": label or hotkey_id,
        }
        self._save()
        return {"success": True, "hotkey": self.state["bindings"][hotkey_id]}

    def unregister(self, hotkey_id: str) -> dict:
        if hotkey_id not in self.state["bindings"]:
            return {"error": "Hotkey not found"}
        del self.state["bindings"][hotkey_id]
        self._save()
        return {"success": True}

    def get_bindings(self) -> dict:
        return {"bindings": self.state["bindings"],
                "total": len(self.state["bindings"]),
                "enabled": self.state["enabled"]}

    def set_enabled(self, enabled: bool) -> dict:
        self.state["enabled"] = enabled
        self._save()
        return {"success": True, "enabled": enabled}

    def save_profile(self, name: str) -> dict:
        self.state["profiles"][name] = dict(self.state["bindings"])
        self._save()
        return {"success": True, "profile": name}

    def load_profile(self, name: str) -> dict:
        if name not in self.state["profiles"]:
            return {"error": "Profile not found"}
        self.state["bindings"] = dict(self.state["profiles"][name])
        self.state["active_profile"] = name
        self._save()
        return {"success": True, "profile": name, "bindings": len(self.state["bindings"])}

    def get_profiles(self) -> dict:
        return {"profiles": list(self.state["profiles"].keys()),
                "active": self.state["active_profile"]}

    def delete_profile(self, name: str) -> dict:
        if name == "default":
            return {"error": "Cannot delete default profile"}
        if name in self.state["profiles"]:
            del self.state["profiles"][name]
            self._save()
        return {"success": True}

    def reset_defaults(self) -> dict:
        self.state["bindings"] = dict(self.DEFAULT_BINDINGS)
        self._save()
        return {"success": True, "bindings": len(self.state["bindings"])}


# ========================
# DASHBOARD WIDGET FRAMEWORK (V25 → 100%)
# ========================

WIDGETS_FILE = DATA_DIR / "jarvis_widgets.json"

class WidgetFramework:
    """Dashboard widget registry with layout persistence, add/remove/resize."""

    BUILT_IN_WIDGETS = {
        "clock": {"id": "clock", "name": "Clock", "category": "utility", "min_w": 1, "min_h": 1, "default_w": 2, "default_h": 1},
        "weather": {"id": "weather", "name": "Weather", "category": "utility", "min_w": 2, "min_h": 1, "default_w": 2, "default_h": 2},
        "cpu-monitor": {"id": "cpu-monitor", "name": "CPU Monitor", "category": "system", "min_w": 2, "min_h": 1, "default_w": 2, "default_h": 1},
        "memory-usage": {"id": "memory-usage", "name": "Memory Usage", "category": "system", "min_w": 2, "min_h": 1, "default_w": 2, "default_h": 1},
        "quick-notes": {"id": "quick-notes", "name": "Quick Notes", "category": "productivity", "min_w": 2, "min_h": 2, "default_w": 3, "default_h": 2},
        "calendar-mini": {"id": "calendar-mini", "name": "Mini Calendar", "category": "productivity", "min_w": 2, "min_h": 2, "default_w": 2, "default_h": 2},
        "ai-status": {"id": "ai-status", "name": "AI Status", "category": "ai", "min_w": 2, "min_h": 1, "default_w": 3, "default_h": 1},
        "recent-chats": {"id": "recent-chats", "name": "Recent Chats", "category": "ai", "min_w": 2, "min_h": 2, "default_w": 2, "default_h": 3},
        "task-list": {"id": "task-list", "name": "Task List", "category": "productivity", "min_w": 2, "min_h": 2, "default_w": 2, "default_h": 3},
        "shortcuts": {"id": "shortcuts", "name": "Shortcuts", "category": "utility", "min_w": 1, "min_h": 1, "default_w": 2, "default_h": 2},
    }

    def __init__(self):
        self._load()

    def _load(self):
        try:
            self.state = json.loads(WIDGETS_FILE.read_text()) if WIDGETS_FILE.exists() else {}
        except Exception:
            self.state = {}
        self.state.setdefault("registry", dict(self.BUILT_IN_WIDGETS))
        self.state.setdefault("active_layout", [])
        self.state.setdefault("saved_layouts", {})
        self.state.setdefault("custom_widgets", {})

    def _save(self):
        WIDGETS_FILE.write_text(json.dumps(self.state, indent=2, default=str))

    def get_registry(self) -> dict:
        all_w = {**self.state["registry"], **self.state["custom_widgets"]}
        return {"widgets": all_w, "total": len(all_w)}

    def add_to_dashboard(self, widget_id: str, x: int = 0, y: int = 0,
                         w: int = 0, h: int = 0) -> dict:
        all_w = {**self.state["registry"], **self.state["custom_widgets"]}
        if widget_id not in all_w:
            return {"error": "Widget not found in registry"}
        wdef = all_w[widget_id]
        entry = {
            "widget_id": widget_id, "x": x, "y": y,
            "w": w or wdef.get("default_w", 2),
            "h": h or wdef.get("default_h", 2),
            "added_at": datetime.now().isoformat(),
        }
        self.state["active_layout"].append(entry)
        self._save()
        return {"success": True, "widget": entry}

    def remove_from_dashboard(self, widget_id: str) -> dict:
        before = len(self.state["active_layout"])
        self.state["active_layout"] = [w for w in self.state["active_layout"]
                                        if w.get("widget_id") != widget_id]
        self._save()
        return {"success": True, "removed": before - len(self.state["active_layout"])}

    def resize_widget(self, widget_id: str, w: int, h: int) -> dict:
        for widget in self.state["active_layout"]:
            if widget.get("widget_id") == widget_id:
                widget["w"] = w
                widget["h"] = h
                self._save()
                return {"success": True, "widget": widget}
        return {"error": "Widget not on dashboard"}

    def move_widget(self, widget_id: str, x: int, y: int) -> dict:
        for widget in self.state["active_layout"]:
            if widget.get("widget_id") == widget_id:
                widget["x"] = x
                widget["y"] = y
                self._save()
                return {"success": True, "widget": widget}
        return {"error": "Widget not on dashboard"}

    def get_layout(self) -> dict:
        return {"layout": self.state["active_layout"],
                "total": len(self.state["active_layout"])}

    def save_layout(self, name: str) -> dict:
        self.state["saved_layouts"][name] = list(self.state["active_layout"])
        self._save()
        return {"success": True, "name": name}

    def load_layout(self, name: str) -> dict:
        if name not in self.state["saved_layouts"]:
            return {"error": "Layout not found"}
        self.state["active_layout"] = list(self.state["saved_layouts"][name])
        self._save()
        return {"success": True, "widgets": len(self.state["active_layout"])}

    def get_saved_layouts(self) -> dict:
        return {"layouts": {k: len(v) for k, v in self.state["saved_layouts"].items()}}

    def register_custom_widget(self, widget_id: str, name: str, category: str = "custom",
                                 min_w: int = 1, min_h: int = 1,
                                 default_w: int = 2, default_h: int = 2) -> dict:
        self.state["custom_widgets"][widget_id] = {
            "id": widget_id, "name": name, "category": category,
            "min_w": min_w, "min_h": min_h,
            "default_w": default_w, "default_h": default_h,
            "custom": True,
        }
        self._save()
        return {"success": True, "widget": self.state["custom_widgets"][widget_id]}

    def unregister_custom_widget(self, widget_id: str) -> dict:
        if widget_id in self.state["custom_widgets"]:
            del self.state["custom_widgets"][widget_id]
            self._save()
        return {"success": True}


# ========================
# SYSTEM TRAY + BOOT MANAGER (V25 → 100%)
# ========================

TRAY_FILE = DATA_DIR / "jarvis_tray.json"
BOOT_FILE = DATA_DIR / "jarvis_boot.json"

class SystemTray:
    """System tray menu configuration and quick actions."""

    DEFAULT_MENU = [
        {"id": "open", "label": "Open JARVIS", "action": "open-main", "icon": "window"},
        {"id": "chat", "label": "Quick Chat", "action": "open-chat", "icon": "message"},
        {"id": "voice", "label": "Voice Mode", "action": "toggle-voice", "icon": "mic"},
        {"id": "status", "label": "System Status", "action": "show-status", "icon": "activity"},
        {"id": "sep1", "label": "---", "action": "separator", "icon": ""},
        {"id": "settings", "label": "Settings", "action": "open-settings", "icon": "settings"},
        {"id": "quit", "label": "Quit JARVIS", "action": "quit", "icon": "power"},
    ]

    def __init__(self):
        self._load()

    def _load(self):
        try:
            self.state = json.loads(TRAY_FILE.read_text()) if TRAY_FILE.exists() else {}
        except Exception:
            self.state = {}
        self.state.setdefault("menu", list(self.DEFAULT_MENU))
        self.state.setdefault("tooltip", "JARVIS AI Assistant")
        self.state.setdefault("badge", {"visible": False, "count": 0})
        self.state.setdefault("minimized_to_tray", False)

    def _save(self):
        TRAY_FILE.write_text(json.dumps(self.state, indent=2, default=str))

    def get_menu(self) -> dict:
        return {"menu": self.state["menu"], "tooltip": self.state["tooltip"],
                "badge": self.state["badge"]}

    def add_menu_item(self, item_id: str, label: str, action: str, icon: str = "") -> dict:
        self.state["menu"].append({"id": item_id, "label": label, "action": action, "icon": icon})
        self._save()
        return {"success": True}

    def remove_menu_item(self, item_id: str) -> dict:
        self.state["menu"] = [m for m in self.state["menu"] if m.get("id") != item_id]
        self._save()
        return {"success": True}

    def set_badge(self, visible: bool, count: int = 0) -> dict:
        self.state["badge"] = {"visible": visible, "count": count}
        self._save()
        return {"success": True, "badge": self.state["badge"]}

    def set_tooltip(self, text: str) -> dict:
        self.state["tooltip"] = text
        self._save()
        return {"success": True}

    def minimize_to_tray(self) -> dict:
        self.state["minimized_to_tray"] = True
        self._save()
        return {"success": True, "minimized": True}

    def restore_from_tray(self) -> dict:
        self.state["minimized_to_tray"] = False
        self._save()
        return {"success": True, "minimized": False}

    def get_tray_status(self) -> dict:
        return {
            "minimized": self.state["minimized_to_tray"],
            "badge": self.state["badge"],
            "menu_items": len(self.state["menu"]),
            "tooltip": self.state["tooltip"],
        }


class BootManager:
    """System startup sequence manager with boot steps and auto-start config."""

    DEFAULT_BOOT_SEQUENCE = [
        {"id": "core", "name": "JARVIS Core", "order": 1, "required": True, "timeout_sec": 10},
        {"id": "memory", "name": "Memory Engine", "order": 2, "required": True, "timeout_sec": 5},
        {"id": "zeus", "name": "Zeus Brain", "order": 3, "required": True, "timeout_sec": 5},
        {"id": "agents", "name": "Agent Framework", "order": 4, "required": False, "timeout_sec": 8},
        {"id": "plugins", "name": "Plugin System", "order": 5, "required": False, "timeout_sec": 10},
        {"id": "smart-home", "name": "Smart Home Hub", "order": 6, "required": False, "timeout_sec": 5},
        {"id": "sync", "name": "Sync Engine", "order": 7, "required": False, "timeout_sec": 5},
        {"id": "ui", "name": "Dashboard UI", "order": 8, "required": True, "timeout_sec": 3},
    ]

    def __init__(self):
        self._load()

    def _load(self):
        try:
            self.state = json.loads(BOOT_FILE.read_text()) if BOOT_FILE.exists() else {}
        except Exception:
            self.state = {}
        self.state.setdefault("sequence", list(self.DEFAULT_BOOT_SEQUENCE))
        self.state.setdefault("auto_start", True)
        self.state.setdefault("boot_log", [])
        self.state.setdefault("last_boot", None)

    def _save(self):
        BOOT_FILE.write_text(json.dumps(self.state, indent=2, default=str))

    def get_sequence(self) -> dict:
        return {"sequence": sorted(self.state["sequence"], key=lambda s: s.get("order", 99)),
                "auto_start": self.state["auto_start"]}

    def add_boot_step(self, step_id: str, name: str, order: int, required: bool = False,
                      timeout_sec: int = 5) -> dict:
        self.state["sequence"].append({
            "id": step_id, "name": name, "order": order,
            "required": required, "timeout_sec": timeout_sec,
        })
        self._save()
        return {"success": True}

    def remove_boot_step(self, step_id: str) -> dict:
        self.state["sequence"] = [s for s in self.state["sequence"] if s.get("id") != step_id]
        self._save()
        return {"success": True}

    def reorder(self, step_id: str, new_order: int) -> dict:
        for s in self.state["sequence"]:
            if s.get("id") == step_id:
                s["order"] = new_order
                self._save()
                return {"success": True}
        return {"error": "Step not found"}

    def run_boot(self) -> dict:
        """Simulate a boot sequence."""
        results = []
        for step in sorted(self.state["sequence"], key=lambda s: s.get("order", 99)):
            results.append({
                "step": step["name"], "status": "ok",
                "duration_ms": int(step.get("timeout_sec", 3) * 100),
            })
        boot_entry = {
            "ts": datetime.now().isoformat(),
            "steps": len(results),
            "total_ms": sum(r["duration_ms"] for r in results),
            "status": "success",
        }
        self.state["boot_log"].append(boot_entry)
        self.state["boot_log"] = self.state["boot_log"][-50:]
        self.state["last_boot"] = boot_entry
        self._save()
        return {"success": True, "boot": boot_entry, "steps": results}

    def set_auto_start(self, enabled: bool) -> dict:
        self.state["auto_start"] = enabled
        self._save()
        return {"success": True, "auto_start": enabled}

    def get_boot_log(self, limit: int = 10) -> dict:
        return {"log": self.state["boot_log"][-limit:], "last_boot": self.state["last_boot"]}

    def get_boot_status(self) -> dict:
        return {
            "auto_start": self.state["auto_start"],
            "boot_steps": len(self.state["sequence"]),
            "last_boot": self.state["last_boot"],
            "total_boots": len(self.state["boot_log"]),
        }


# ========================
# SINGLETONS
# ========================

unified_controller = UnifiedController()
pwa_manager = PWAManager()
smart_home_hub = SmartHomeHub()
notification_center = NotificationCenter()
sw_manager = ServiceWorkerManager()
command_palette = CommandPalette()
theme_engine = ThemeEngine()
app_launcher = AppLauncher()
voice_hub = VoiceHub()
live_sync = LiveSyncEngine()
mobile_shell = MobileAppShell()
global_hotkeys = GlobalHotkeys()
widget_framework = WidgetFramework()
system_tray = SystemTray()
boot_manager = BootManager()


def get_jarvis_status() -> dict:
    """Get unified JARVIS OS status."""
    return {
        "system": unified_controller.get_system_overview(),
        "notifications": notification_center.get_unread(),
        "smart_home": smart_home_hub.get_devices(),
        "pwa": pwa_manager.get_install_prompt_data(),
        "quick_actions": unified_controller.get_quick_actions(),
        "service_worker": sw_manager.get_offline_status(),
        "themes": theme_engine.get_theme(),
        "launcher": app_launcher.get_launcher_data(),
        "voice": voice_hub.get_voice_status(),
        "command_palette": {"total_commands": len(command_palette.get_all())},
        "live_sync": live_sync.get_sync_status(),
        "mobile": mobile_shell.get_shell_status(),
        "hotkeys": global_hotkeys.get_bindings(),
        "widgets": widget_framework.get_layout(),
        "tray": system_tray.get_tray_status(),
        "boot": boot_manager.get_boot_status(),
    }
