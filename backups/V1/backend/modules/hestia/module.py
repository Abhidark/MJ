"""
Hestia Module -- Smart Home
Placeholder for IoT / smart home device control and monitoring.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.base_module import BaseModule


class HestiaModule(BaseModule):
    name = "hestia"
    display_name = "Hestia"
    icon = "\U0001f3e0"  # house
    description = "Smart Home -- control lights, fans, AC, and IoT devices"
    version = "1.0"
    category = "lifestyle"
    enabled = True

    KEYWORDS = [
        r"\blight\w*\b", r"\bfan\b", r"\bac\b", r"\bair\s*condition\w*\b",
        r"\btemperature\b", r"\bsmart\s*home\b", r"\biot\b", r"\bdevice\w*\b",
        r"\bswitch\b.*\b(on|off)\b", r"\bturn\b.*\b(on|off)\b", r"\bbulb\b",
        r"\bthermostat\b", r"\bheater\b", r"\bcooler\b", r"\bhumidity\b",
        r"\bsensor\b", r"\bmotion\b", r"\bdoor\s*(lock|bell)\b",
        r"\bcamera\b.*\b(home|security)\b", r"\bplug\b", r"\bsocket\b",
    ]

    DEVICE_TYPES = {
        "light": {"icon": "\U0001f4a1", "actions": ["on", "off", "dim", "color", "brightness"]},
        "fan": {"icon": "\U0001fa81", "actions": ["on", "off", "speed"]},
        "ac": {"icon": "❄️", "actions": ["on", "off", "temperature", "mode"]},
        "thermostat": {"icon": "\U0001f321️", "actions": ["set", "schedule"]},
        "camera": {"icon": "\U0001f4f7", "actions": ["view", "record", "snapshot"]},
        "lock": {"icon": "\U0001f512", "actions": ["lock", "unlock", "status"]},
        "plug": {"icon": "\U0001f50c", "actions": ["on", "off", "schedule"]},
        "sensor": {"icon": "\U0001f4e1", "actions": ["read", "status"]},
    }

    # Simulated device states
    MOCK_DEVICES = [
        {"id": "light_living", "name": "Living Room Light", "type": "light", "status": "off", "room": "Living Room"},
        {"id": "light_bedroom", "name": "Bedroom Light", "type": "light", "status": "on", "room": "Bedroom"},
        {"id": "fan_living", "name": "Living Room Fan", "type": "fan", "status": "off", "speed": 0, "room": "Living Room"},
        {"id": "ac_bedroom", "name": "Bedroom AC", "type": "ac", "status": "off", "temp": 24, "room": "Bedroom"},
        {"id": "lock_main", "name": "Main Door Lock", "type": "lock", "status": "locked", "room": "Entrance"},
    ]

    def __init__(self):
        self.mqtt_broker = ""
        self.devices = list(self.MOCK_DEVICES)
        self.connected = False

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        text_lower = text.lower()
        for pattern in self.KEYWORDS:
            if re.search(pattern, text_lower):
                return 0.85
        if intent in ("smart_home", "iot", "device_control", "home_automation"):
            return 0.9
        return 0.0

    def _detect_device_type(self, text: str) -> str | None:
        text_lower = text.lower()
        mappings = {
            "light": ["light", "bulb", "lamp"],
            "fan": ["fan"],
            "ac": ["ac", "air condition", "cooling", "cooler"],
            "thermostat": ["thermostat", "temperature", "heater"],
            "camera": ["camera", "cctv"],
            "lock": ["lock", "door lock"],
            "plug": ["plug", "socket", "switch"],
            "sensor": ["sensor", "motion"],
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
        if re.search(r"\bstatus\b|\bstate\b|\bkya\s+hai\b", text_lower):
            return "status"
        if re.search(r"\blist\b|\bshow\b|\bdevices\b|\bsab\b", text_lower):
            return "list"
        return "info"

    def _detect_room(self, text: str) -> str | None:
        text_lower = text.lower()
        rooms = ["living room", "bedroom", "kitchen", "bathroom", "entrance", "hall", "office"]
        for room in rooms:
            if room in text_lower:
                return room.title()
        return None

    def execute(self, text: str, context: dict) -> dict:
        device_type = self._detect_device_type(text)
        action = self._detect_action(text)
        room = self._detect_room(text)

        # List all devices
        if action == "list" or (not device_type and action == "info"):
            return self._list_devices(room)

        # Device status
        if action == "status":
            return self._device_status(device_type, room)

        # Device control (placeholder)
        if action in ("on", "off"):
            return self._control_device(device_type, action, room)

        # General info
        if not self.connected and not self.mqtt_broker:
            return {
                "response": (
                    "\U0001f3e0 **Hestia -- Smart Home Hub**\n\n"
                    "No IoT devices connected yet.\n\n"
                    "**To get started:**\n"
                    "1. Go to Hestia settings and enter your MQTT broker address\n"
                    "2. Connect your smart home devices (lights, fans, AC, etc.)\n"
                    "3. Supported protocols: MQTT, HTTP, WebSocket\n\n"
                    "**Supported devices:** Lights, Fans, AC, Thermostats, Cameras, Locks, Plugs, Sensors\n\n"
                    "*Currently running in demo mode with simulated devices.*"
                ),
                "data": {"connected": False, "demo_mode": True},
                "action": "setup_info",
            }

        return self._list_devices(room)

    def _list_devices(self, room: str | None) -> dict:
        devices = self.devices
        if room:
            devices = [d for d in devices if d["room"].lower() == room.lower()]

        if not devices:
            return {
                "response": f"No devices found{' in ' + room if room else ''}.",
                "data": None,
                "action": "no_devices",
            }

        lines = [f"\U0001f3e0 **Smart Home Devices{' - ' + room if room else ''}:**\n"]
        for d in devices:
            dtype_info = self.DEVICE_TYPES.get(d["type"], {})
            icon = dtype_info.get("icon", "\U0001f4e6")
            status_icon = "\U0001f7e2" if d["status"] in ("on", "locked") else "\U0001f534"
            extra = ""
            if d.get("temp"):
                extra = f" | {d['temp']}°C"
            if d.get("speed") is not None and d["type"] == "fan":
                extra = f" | Speed: {d['speed']}"
            lines.append(f"  {icon} {status_icon} {d['name']} ({d['room']}) -- {d['status']}{extra}")

        lines.append("\n*Demo mode -- connect MQTT broker in settings for real devices*")
        return {
            "response": "\n".join(lines),
            "data": {"devices": devices, "demo_mode": not self.connected},
            "action": "device_list",
        }

    def _device_status(self, device_type: str | None, room: str | None) -> dict:
        devices = self.devices
        if device_type:
            devices = [d for d in devices if d["type"] == device_type]
        if room:
            devices = [d for d in devices if d["room"].lower() == room.lower()]

        if not devices:
            return {
                "response": "No matching devices found.",
                "data": None,
                "action": "not_found",
            }

        return self._list_devices(room)

    def _control_device(self, device_type: str | None, action: str, room: str | None) -> dict:
        matched = []
        for d in self.devices:
            if device_type and d["type"] != device_type:
                continue
            if room and d["room"].lower() != room.lower():
                continue
            matched.append(d)

        if not matched:
            return {
                "response": f"No {device_type or 'device'} found{' in ' + room if room else ''} to turn {action}.",
                "data": None,
                "action": "not_found",
            }

        results = []
        for d in matched:
            old_status = d["status"]
            d["status"] = action
            dtype_info = self.DEVICE_TYPES.get(d["type"], {})
            icon = dtype_info.get("icon", "\U0001f4e6")
            results.append(f"  {icon} {d['name']}: {old_status} -> **{action}**")

        response = f"\U0001f3e0 **Device{'s' if len(matched) > 1 else ''} Updated:**\n\n" + "\n".join(results)
        if not self.connected:
            response += "\n\n*Demo mode -- changes are simulated*"

        return {
            "response": response,
            "data": {"updated": [d["id"] for d in matched], "action": action},
            "action": f"device_{action}",
        }

    def get_system_prompt_addition(self) -> str:
        return (
            "You can control smart home devices. When the user asks to control lights, "
            "fans, AC, or other IoT devices, use the Hestia module."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        device_count = len(self.devices)
        on_count = sum(1 for d in self.devices if d["status"] in ("on", "locked"))
        return f"[Hestia] {device_count} devices registered, {on_count} active. Connected: {self.connected}"

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "mqtt_broker": self.mqtt_broker,
            "device_count": len(self.devices),
        }

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "mqtt_broker" in settings:
            self.mqtt_broker = settings["mqtt_broker"]
            self.connected = bool(self.mqtt_broker)

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "mqtt_broker", "label": "MQTT Broker Address",
                "type": "text", "value": self.mqtt_broker,
                "placeholder": "e.g., mqtt://192.168.1.100:1883",
            },
        ]
