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
# SINGLETONS
# ========================

unified_controller = UnifiedController()
pwa_manager = PWAManager()
smart_home_hub = SmartHomeHub()
notification_center = NotificationCenter()


def get_jarvis_status() -> dict:
    """Get unified JARVIS OS status."""
    return {
        "system": unified_controller.get_system_overview(),
        "notifications": notification_center.get_unread(),
        "smart_home": smart_home_hub.get_devices(),
        "pwa": pwa_manager.get_install_prompt_data(),
        "quick_actions": unified_controller.get_quick_actions(),
    }
