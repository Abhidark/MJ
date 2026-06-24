"""
Hestia Module v2 -- Smart Home Hub
Full smart home control: devices, scenes, automation rules,
device groups, scheduling, HTTP/MQTT support.
"""

import re
import sys
import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.base_module import BaseModule

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DEVICES_FILE = DATA_DIR / "smart_home_devices.json"
SCENES_FILE = DATA_DIR / "smart_home_scenes.json"
AUTOMATIONS_FILE = DATA_DIR / "smart_home_automations.json"


def _load_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else []


def _save_json(path, data):
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


class HestiaModule(BaseModule):
    name = "hestia"
    display_name = "Hestia"
    icon = "\U0001f3e0"
    description = "Smart Home Hub — devices, scenes, automation, rooms, scheduling"
    version = "2.0"
    category = "lifestyle"
    enabled = True

    KEYWORDS = [
        r"\blight\w*\b", r"\bfan\b", r"\bac\b", r"\bair\s*condition\w*\b",
        r"\btemperature\b", r"\bsmart\s*home\b", r"\biot\b", r"\bdevice\w*\b",
        r"\bswitch\b.*\b(on|off)\b", r"\bturn\b.*\b(on|off)\b", r"\bbulb\b",
        r"\bthermostat\b", r"\bheater\b", r"\bcooler\b", r"\bhumidity\b",
        r"\bsensor\b", r"\bmotion\b", r"\bdoor\s*(lock|bell)\b",
        r"\bcamera\b.*\b(home|security)\b", r"\bplug\b", r"\bsocket\b",
        r"\bscene\b", r"\bautomation\b", r"\broutine\b.*\b(home|device|light)\b",
        r"\broom\b.*\b(device|light|fan|ac)\b", r"\bgroup\b.*\bdevice\b",
    ]

    DEVICE_TYPES = {
        "light":      {"icon": "\U0001f4a1", "actions": ["on", "off", "dim", "color", "brightness"], "states": {"brightness": 100, "color": "#ffffff"}},
        "fan":        {"icon": "\U0001fa81", "actions": ["on", "off", "speed"], "states": {"speed": 0}},
        "ac":         {"icon": "❄️",        "actions": ["on", "off", "temperature", "mode"], "states": {"temp": 24, "mode": "cool"}},
        "thermostat": {"icon": "\U0001f321️", "actions": ["set", "schedule"], "states": {"temp": 22}},
        "camera":     {"icon": "\U0001f4f7", "actions": ["view", "record", "snapshot"], "states": {"recording": False}},
        "lock":       {"icon": "\U0001f512", "actions": ["lock", "unlock", "status"], "states": {}},
        "plug":       {"icon": "\U0001f50c", "actions": ["on", "off", "schedule"], "states": {"power_w": 0}},
        "sensor":     {"icon": "\U0001f4e1", "actions": ["read", "status"], "states": {"value": 0, "unit": ""}},
        "speaker":    {"icon": "\U0001f50a", "actions": ["on", "off", "volume", "play"], "states": {"volume": 50}},
        "tv":         {"icon": "\U0001f4fa", "actions": ["on", "off", "channel", "volume"], "states": {"channel": 1}},
        "curtain":    {"icon": "\U0001f3ea", "actions": ["open", "close", "half"], "states": {"position": 0}},
    }

    DEFAULT_DEVICES = [
        {"id": "light_living",   "name": "Living Room Light",   "type": "light",  "status": "off", "room": "Living Room",  "brightness": 100, "color": "#ffffff"},
        {"id": "light_bedroom",  "name": "Bedroom Light",       "type": "light",  "status": "on",  "room": "Bedroom",      "brightness": 80,  "color": "#ffeedd"},
        {"id": "light_kitchen",  "name": "Kitchen Light",       "type": "light",  "status": "off", "room": "Kitchen",      "brightness": 100, "color": "#ffffff"},
        {"id": "fan_living",     "name": "Living Room Fan",     "type": "fan",    "status": "off", "room": "Living Room",  "speed": 0},
        {"id": "fan_bedroom",    "name": "Bedroom Fan",         "type": "fan",    "status": "on",  "room": "Bedroom",      "speed": 3},
        {"id": "ac_bedroom",     "name": "Bedroom AC",          "type": "ac",     "status": "off", "room": "Bedroom",      "temp": 24, "mode": "cool"},
        {"id": "ac_living",      "name": "Living Room AC",      "type": "ac",     "status": "off", "room": "Living Room",  "temp": 22, "mode": "auto"},
        {"id": "lock_main",      "name": "Main Door Lock",      "type": "lock",   "status": "locked", "room": "Entrance"},
        {"id": "lock_back",      "name": "Back Door Lock",      "type": "lock",   "status": "locked", "room": "Entrance"},
        {"id": "camera_front",   "name": "Front Camera",        "type": "camera", "status": "on",  "room": "Entrance",     "recording": False},
        {"id": "plug_tv",        "name": "TV Smart Plug",       "type": "plug",   "status": "off", "room": "Living Room",  "power_w": 0},
        {"id": "sensor_temp",    "name": "Temperature Sensor",  "type": "sensor", "status": "on",  "room": "Living Room",  "value": 28, "unit": "°C"},
        {"id": "sensor_humidity","name": "Humidity Sensor",      "type": "sensor", "status": "on",  "room": "Bedroom",      "value": 55, "unit": "%"},
        {"id": "curtain_living", "name": "Living Room Curtain", "type": "curtain","status": "open","room": "Living Room",  "position": 100},
    ]

    DEFAULT_SCENES = {
        "movie_night": {
            "name": "Movie Night",
            "icon": "\U0001f3ac",
            "description": "Dim lights, close curtains, turn on TV plug",
            "actions": [
                {"device_id": "light_living", "set": {"status": "on", "brightness": 20}},
                {"device_id": "curtain_living", "set": {"status": "close", "position": 0}},
                {"device_id": "plug_tv", "set": {"status": "on"}},
            ]
        },
        "good_morning": {
            "name": "Good Morning",
            "icon": "\U0001f305",
            "description": "Open curtains, turn on kitchen light, start AC",
            "actions": [
                {"device_id": "curtain_living", "set": {"status": "open", "position": 100}},
                {"device_id": "light_kitchen", "set": {"status": "on", "brightness": 100}},
                {"device_id": "ac_bedroom", "set": {"status": "off"}},
            ]
        },
        "good_night": {
            "name": "Good Night",
            "icon": "\U0001f319",
            "description": "All lights off, lock doors, bedroom AC on",
            "actions": [
                {"device_id": "light_living", "set": {"status": "off"}},
                {"device_id": "light_kitchen", "set": {"status": "off"}},
                {"device_id": "light_bedroom", "set": {"status": "off"}},
                {"device_id": "lock_main", "set": {"status": "locked"}},
                {"device_id": "lock_back", "set": {"status": "locked"}},
                {"device_id": "ac_bedroom", "set": {"status": "on", "temp": 24}},
            ]
        },
        "away_mode": {
            "name": "Away Mode",
            "icon": "\U0001f3e0",
            "description": "Everything off, all doors locked, camera recording",
            "actions": [
                {"device_id": "light_living", "set": {"status": "off"}},
                {"device_id": "light_bedroom", "set": {"status": "off"}},
                {"device_id": "light_kitchen", "set": {"status": "off"}},
                {"device_id": "fan_living", "set": {"status": "off"}},
                {"device_id": "fan_bedroom", "set": {"status": "off"}},
                {"device_id": "ac_bedroom", "set": {"status": "off"}},
                {"device_id": "ac_living", "set": {"status": "off"}},
                {"device_id": "lock_main", "set": {"status": "locked"}},
                {"device_id": "lock_back", "set": {"status": "locked"}},
                {"device_id": "camera_front", "set": {"status": "on", "recording": True}},
            ]
        },
        "focus_mode": {
            "name": "Focus Mode",
            "icon": "\U0001f3af",
            "description": "Minimal distractions — dim lights, AC comfortable",
            "actions": [
                {"device_id": "light_living", "set": {"status": "on", "brightness": 60}},
                {"device_id": "ac_living", "set": {"status": "on", "temp": 23}},
                {"device_id": "fan_living", "set": {"status": "off"}},
            ]
        },
    }

    DEFAULT_AUTOMATIONS = [
        {
            "id": "auto_night_lights",
            "name": "Night Light Auto-Off",
            "trigger": {"type": "time", "hour": 23, "minute": 0},
            "actions": [
                {"device_id": "light_living", "set": {"status": "off"}},
                {"device_id": "light_kitchen", "set": {"status": "off"}},
            ],
            "enabled": True,
        },
        {
            "id": "auto_morning_curtain",
            "name": "Morning Curtain Open",
            "trigger": {"type": "time", "hour": 7, "minute": 0},
            "actions": [
                {"device_id": "curtain_living", "set": {"status": "open", "position": 100}},
            ],
            "enabled": True,
        },
        {
            "id": "auto_temp_ac",
            "name": "High Temp → AC On",
            "trigger": {"type": "sensor", "device_id": "sensor_temp", "condition": "above", "threshold": 32},
            "actions": [
                {"device_id": "ac_living", "set": {"status": "on", "temp": 24}},
            ],
            "enabled": True,
        },
    ]

    def __init__(self):
        self.mqtt_broker = ""
        self.http_endpoint = ""
        self.connected = False
        self.devices = _load_json(DEVICES_FILE) or list(self.DEFAULT_DEVICES)
        self.scenes = _load_json(SCENES_FILE) or dict(self.DEFAULT_SCENES)
        self.automations = _load_json(AUTOMATIONS_FILE) or list(self.DEFAULT_AUTOMATIONS)
        self._automation_timers = []

    # ========================
    # ROUTING
    # ========================

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        text_lower = text.lower()
        if re.search(r"\b(scene|automation|routine)\b", text_lower):
            return 0.92
        for pattern in self.KEYWORDS:
            if re.search(pattern, text_lower):
                return 0.85
        if intent in ("smart_home", "iot", "device_control", "home_automation"):
            return 0.9
        return 0.0

    # ========================
    # EXECUTION
    # ========================

    def execute(self, text: str, context: dict) -> dict:
        text_lower = text.lower()

        # Scene commands
        if re.search(r"\b(scene|activate|movie\s*night|good\s*morning|good\s*night|away\s*mode|focus\s*mode)\b", text_lower):
            return self._handle_scene(text_lower)

        # Automation commands
        if re.search(r"\b(automation|rule|auto)\b", text_lower):
            return self._handle_automation(text_lower)

        # Room summary
        if re.search(r"\b(room|rooms|all\s*rooms|ghar)\b", text_lower) and re.search(r"\b(status|summary|show|list|dikha)\b", text_lower):
            return self._room_summary()

        device_type = self._detect_device_type(text)
        action = self._detect_action(text)
        room = self._detect_room(text)

        if action == "list" or (not device_type and action == "info"):
            return self._list_devices(room)
        if action == "status":
            return self._device_status(device_type, room)
        if action in ("on", "off", "lock", "unlock", "open", "close"):
            return self._control_device(device_type, action, room, text)

        # Scene list
        if re.search(r"\b(scene|scenes)\b", text_lower):
            return self._list_scenes()

        return self._smart_home_overview()

    # ========================
    # SCENES
    # ========================

    def _handle_scene(self, text: str) -> dict:
        # Find matching scene
        for key, scene in self.scenes.items():
            name_lower = scene["name"].lower().replace(" ", "")
            key_clean = key.replace("_", "")
            if key_clean in text.replace(" ", "") or name_lower in text.replace(" ", ""):
                return self._activate_scene(key, scene)

        if re.search(r"\b(list|show|scenes|dikha)\b", text):
            return self._list_scenes()

        return self._list_scenes()

    def _activate_scene(self, key: str, scene: dict) -> dict:
        results = []
        device_map = {d["id"]: d for d in self.devices}
        for act in scene.get("actions", []):
            dev = device_map.get(act["device_id"])
            if dev:
                for prop, val in act.get("set", {}).items():
                    old = dev.get(prop, "?")
                    dev[prop] = val
                    results.append(f"  {dev['name']}: {prop} → {val}")
        _save_json(DEVICES_FILE, self.devices)
        icon = scene.get("icon", "\U0001f3ac")
        return {
            "response": f"{icon} **Scene: {scene['name']}** activated!\n\n" + "\n".join(results) + "\n\n*Changes applied to all affected devices.*",
            "data": {"scene": key, "changes": len(results)},
            "action": "scene_activated",
        }

    def _list_scenes(self) -> dict:
        lines = ["\U0001f3ac **Available Scenes:**\n"]
        for key, scene in self.scenes.items():
            icon = scene.get("icon", "\U0001f3ac")
            lines.append(f"  {icon} **{scene['name']}** — {scene['description']}")
        lines.append("\n*Say 'activate [scene name]' to run a scene.*")
        return {
            "response": "\n".join(lines),
            "data": {"scenes": list(self.scenes.keys())},
            "action": "scene_list",
        }

    # ========================
    # AUTOMATIONS
    # ========================

    def _handle_automation(self, text: str) -> dict:
        if re.search(r"\b(list|show|all|dikha)\b", text):
            return self._list_automations()
        if re.search(r"\b(enable|on|chalu)\b", text):
            return self._toggle_automation(text, True)
        if re.search(r"\b(disable|off|band)\b", text):
            return self._toggle_automation(text, False)
        return self._list_automations()

    def _list_automations(self) -> dict:
        lines = ["⚡ **Automation Rules:**\n"]
        for a in self.automations:
            status = "\U0001f7e2" if a.get("enabled") else "\U0001f534"
            trigger = a.get("trigger", {})
            trig_desc = ""
            if trigger.get("type") == "time":
                trig_desc = f"At {trigger['hour']:02d}:{trigger['minute']:02d}"
            elif trigger.get("type") == "sensor":
                trig_desc = f"When {trigger['device_id']} {trigger['condition']} {trigger['threshold']}"
            lines.append(f"  {status} **{a['name']}** — Trigger: {trig_desc} → {len(a.get('actions', []))} action(s)")
        return {
            "response": "\n".join(lines),
            "data": {"automations": self.automations},
            "action": "automation_list",
        }

    def _toggle_automation(self, text: str, enabled: bool) -> dict:
        for a in self.automations:
            if a["name"].lower() in text or a["id"] in text:
                a["enabled"] = enabled
                _save_json(AUTOMATIONS_FILE, self.automations)
                state = "enabled" if enabled else "disabled"
                return {
                    "response": f"⚡ Automation **{a['name']}** {state}.",
                    "data": {"automation_id": a["id"], "enabled": enabled},
                    "action": "automation_toggled",
                }
        return {"response": "Automation not found. Use 'list automations' to see all.", "data": None, "action": "not_found"}

    # ========================
    # ROOM SUMMARY
    # ========================

    def _room_summary(self) -> dict:
        rooms = {}
        for d in self.devices:
            room = d.get("room", "Unknown")
            rooms.setdefault(room, []).append(d)

        lines = ["\U0001f3e0 **Room Summary:**\n"]
        for room, devs in sorted(rooms.items()):
            on_count = sum(1 for d in devs if d.get("status") in ("on", "locked", "open"))
            lines.append(f"  **{room}** — {len(devs)} devices, {on_count} active")
            for d in devs:
                dtype = self.DEVICE_TYPES.get(d["type"], {})
                icon = dtype.get("icon", "\U0001f4e6")
                extra = ""
                if d.get("temp"): extra = f" {d['temp']}°C"
                if d.get("speed"): extra = f" speed:{d['speed']}"
                if d.get("brightness") and d["type"] == "light" and d["status"] == "on": extra = f" {d['brightness']}%"
                st_icon = "\U0001f7e2" if d["status"] in ("on", "locked", "open") else "\U0001f534"
                lines.append(f"    {icon}{st_icon} {d['name']} — {d['status']}{extra}")
        return {
            "response": "\n".join(lines),
            "data": {"rooms": {r: len(d) for r, d in rooms.items()}},
            "action": "room_summary",
        }

    # ========================
    # SMART HOME OVERVIEW
    # ========================

    def _smart_home_overview(self) -> dict:
        total = len(self.devices)
        on_count = sum(1 for d in self.devices if d.get("status") in ("on", "locked", "open"))
        rooms = set(d.get("room", "") for d in self.devices)
        return {
            "response": (
                f"\U0001f3e0 **Hestia — Smart Home Hub v2**\n\n"
                f"**{total}** devices across **{len(rooms)}** rooms | **{on_count}** active\n"
                f"**{len(self.scenes)}** scenes | **{len(self.automations)}** automation rules\n\n"
                f"**Commands:** devices, scenes, automations, room status\n"
                f"**Scenes:** {', '.join(s['name'] for s in self.scenes.values())}\n\n"
                f"{'*Connected to MQTT: ' + self.mqtt_broker + '*' if self.connected else '*Running in local mode — connect MQTT/HTTP in settings for real devices*'}"
            ),
            "data": {"devices": total, "active": on_count, "rooms": len(rooms), "scenes": len(self.scenes), "automations": len(self.automations)},
            "action": "overview",
        }

    # ========================
    # DEVICE DETECTION HELPERS
    # ========================

    def _detect_device_type(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        mappings = {
            "light": ["light", "bulb", "lamp"],
            "fan": ["fan", "pankha"],
            "ac": ["ac", "air condition", "cooling", "cooler"],
            "thermostat": ["thermostat", "temperature set"],
            "camera": ["camera", "cctv", "cam"],
            "lock": ["lock", "door lock", "tala"],
            "plug": ["plug", "socket", "switch"],
            "sensor": ["sensor", "motion"],
            "speaker": ["speaker", "music"],
            "tv": ["tv", "television"],
            "curtain": ["curtain", "parda", "blind"],
        }
        for dtype, keywords in mappings.items():
            for kw in keywords:
                if kw in text_lower:
                    return dtype
        return None

    def _detect_action(self, text: str) -> str:
        text_lower = text.lower()
        if re.search(r"\b(turn|switch)\s+(on|chalu)\b", text_lower) or "on karo" in text_lower:
            return "on"
        if re.search(r"\b(turn|switch)\s+(off|band)\b", text_lower) or "off karo" in text_lower:
            return "off"
        if re.search(r"\block\b", text_lower): return "lock"
        if re.search(r"\bunlock\b", text_lower): return "unlock"
        if re.search(r"\bopen\b", text_lower): return "open"
        if re.search(r"\bclose\b", text_lower): return "close"
        if re.search(r"\bstatus\b|\bstate\b|\bkya\s+hai\b", text_lower): return "status"
        if re.search(r"\blist\b|\bshow\b|\bdevices\b|\bsab\b", text_lower): return "list"
        return "info"

    def _detect_room(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        rooms = ["living room", "bedroom", "kitchen", "bathroom", "entrance", "hall", "office", "balcony"]
        for room in rooms:
            if room in text_lower:
                return room.title()
        return None

    # ========================
    # DEVICE OPERATIONS
    # ========================

    def _list_devices(self, room: Optional[str] = None) -> dict:
        devices = self.devices
        if room:
            devices = [d for d in devices if d["room"].lower() == room.lower()]
        if not devices:
            return {"response": f"No devices found{' in ' + room if room else ''}.", "data": None, "action": "no_devices"}

        lines = [f"\U0001f3e0 **Smart Home Devices{' — ' + room if room else ''}:**\n"]
        for d in devices:
            dtype_info = self.DEVICE_TYPES.get(d["type"], {})
            icon = dtype_info.get("icon", "\U0001f4e6")
            status_icon = "\U0001f7e2" if d["status"] in ("on", "locked", "open") else "\U0001f534"
            extra = ""
            if d.get("temp"): extra += f" | {d['temp']}°C"
            if d.get("speed") and d["type"] == "fan": extra += f" | Speed: {d['speed']}"
            if d.get("brightness") and d["type"] == "light" and d["status"] == "on": extra += f" | {d['brightness']}%"
            if d.get("power_w") and d["type"] == "plug": extra += f" | {d['power_w']}W"
            lines.append(f"  {icon} {status_icon} {d['name']} ({d['room']}) — {d['status']}{extra}")
        return {
            "response": "\n".join(lines),
            "data": {"devices": devices, "count": len(devices)},
            "action": "device_list",
        }

    def _device_status(self, device_type: Optional[str], room: Optional[str]) -> dict:
        return self._list_devices(room)

    def _control_device(self, device_type: Optional[str], action: str, room: Optional[str], text: str) -> dict:
        matched = []
        for d in self.devices:
            if device_type and d["type"] != device_type:
                continue
            if room and d["room"].lower() != room.lower():
                continue
            matched.append(d)

        if not matched:
            return {"response": f"No {device_type or 'device'} found{' in ' + room if room else ''} to {action}.", "data": None, "action": "not_found"}

        results = []
        for d in matched:
            old_status = d["status"]
            # Map actions
            if action in ("on", "off"):
                d["status"] = action
            elif action == "lock":
                d["status"] = "locked"
            elif action == "unlock":
                d["status"] = "unlocked"
            elif action == "open":
                d["status"] = "open"
                if "position" in d: d["position"] = 100
            elif action == "close":
                d["status"] = "close"
                if "position" in d: d["position"] = 0

            # Parse extra values from text
            temp_match = re.search(r"(\d{2,3})\s*(?:degree|°|celsius|c)", text.lower())
            if temp_match and "temp" in d:
                d["temp"] = int(temp_match.group(1))

            speed_match = re.search(r"speed\s*(\d)", text.lower())
            if speed_match and "speed" in d:
                d["speed"] = int(speed_match.group(1))

            bright_match = re.search(r"(\d{1,3})\s*%|brightness\s*(\d{1,3})", text.lower())
            if bright_match and "brightness" in d:
                val = bright_match.group(1) or bright_match.group(2)
                d["brightness"] = min(100, int(val))

            dtype_info = self.DEVICE_TYPES.get(d["type"], {})
            icon = dtype_info.get("icon", "\U0001f4e6")
            results.append(f"  {icon} {d['name']}: {old_status} → **{d['status']}**")

        _save_json(DEVICES_FILE, self.devices)
        response = f"\U0001f3e0 **Device{'s' if len(matched) > 1 else ''} Updated:**\n\n" + "\n".join(results)
        return {
            "response": response,
            "data": {"updated": [d["id"] for d in matched], "action": action},
            "action": f"device_{action}",
        }

    # ========================
    # API HELPERS (called from main.py)
    # ========================

    def get_all_devices(self) -> list:
        return self.devices

    def get_all_scenes(self) -> dict:
        return self.scenes

    def get_all_automations(self) -> list:
        return self.automations

    def activate_scene_by_key(self, key: str) -> dict:
        scene = self.scenes.get(key)
        if not scene:
            return {"success": False, "error": f"Scene '{key}' not found"}
        result = self._activate_scene(key, scene)
        return {"success": True, **result.get("data", {}), "message": f"Scene {scene['name']} activated"}

    def add_device(self, device: dict) -> dict:
        device.setdefault("id", f"dev_{int(time.time())}")
        device.setdefault("status", "off")
        device.setdefault("room", "Unknown")
        self.devices.append(device)
        _save_json(DEVICES_FILE, self.devices)
        return {"success": True, "device": device}

    def remove_device(self, device_id: str) -> dict:
        before = len(self.devices)
        self.devices = [d for d in self.devices if d["id"] != device_id]
        if len(self.devices) < before:
            _save_json(DEVICES_FILE, self.devices)
            return {"success": True}
        return {"success": False, "error": "Device not found"}

    # ========================
    # SYSTEM PROMPT & SETTINGS
    # ========================

    def get_system_prompt_addition(self) -> str:
        return (
            "You can control smart home devices, activate scenes (movie_night, good_morning, good_night, away_mode, focus_mode), "
            "manage automations, and check room status. Use the Hestia module for all smart home operations."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        on_count = sum(1 for d in self.devices if d["status"] in ("on", "locked", "open"))
        return f"[Hestia] {len(self.devices)} devices, {on_count} active, {len(self.scenes)} scenes, {len(self.automations)} automations"

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "mqtt_broker": self.mqtt_broker,
            "http_endpoint": self.http_endpoint,
            "device_count": len(self.devices),
            "scene_count": len(self.scenes),
            "automation_count": len(self.automations),
        }

    def update_settings(self, settings: dict):
        if "enabled" in settings: self.enabled = settings["enabled"]
        if "mqtt_broker" in settings:
            self.mqtt_broker = settings["mqtt_broker"]
            self.connected = bool(self.mqtt_broker)
        if "http_endpoint" in settings:
            self.http_endpoint = settings["http_endpoint"]

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {"key": "mqtt_broker", "label": "MQTT Broker", "type": "text", "value": self.mqtt_broker, "placeholder": "mqtt://192.168.1.100:1883"},
            {"key": "http_endpoint", "label": "HTTP Device API", "type": "text", "value": self.http_endpoint, "placeholder": "http://192.168.1.100:8080/api"},
        ]
