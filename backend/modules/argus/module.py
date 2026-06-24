"""
Argus Module -- Vision & System Monitoring Agent (V12)
Handles: screenshots, camera, object detection, screen AI, system stats
"""

import re
from modules.base_module import BaseModule


class ArgusModule(BaseModule):
    name = "argus"
    display_name = "Argus"
    icon = "\U0001f441️"
    description = "Vision & monitoring: screenshots, camera, object detection, screen AI, system stats"
    version = "3.0"
    category = "vision"
    enabled = True

    SYSTEM_KEYWORDS = [
        "cpu", "ram", "disk", "battery", "system info", "pc status",
        "stats", "memory usage", "storage", "temperature", "system health",
        "performance", "uptime", "system status", "hardware",
        "processor", "usage", "free space",
    ]

    VISION_KEYWORDS = [
        "screenshot", "screen capture", "screen shot", "take screenshot",
        "capture screen", "screen grab", "snip", "screen pe kya hai",
        "camera", "webcam", "photo le", "selfie", "cam capture", "camera se",
        "object detection", "detect objects", "kya dikh raha", "identify",
        "what is on screen", "screen analyze", "screen ai", "read screen",
        "screen content", "ui detect", "layout", "screen mein kya hai",
        "compare screenshot", "diff screen", "monitor info", "monitors",
        "vision", "image analyze", "detect", "recognize",
    ]

    VISION_REGEX = re.compile(
        r"\b(screenshot|screen\s*shot|screen\s*capture|webcam|camera|capture|"
        r"detect\s*object|object\s*detect|screen\s*ai|analyze\s*screen|"
        r"screen\s*read|read\s*screen|compare\s*screen|monitor\s*info|"
        r"identify|recognize|what.*screen|screen.*kya|dikhai|dikhao|"
        r"photo\s*le|tasveer|snap)\b",
        re.IGNORECASE
    )

    def __init__(self):
        self._vision_engine = None

    @property
    def vision_engine(self):
        if self._vision_engine is None:
            try:
                from intelligence.vision_engine import vision_engine
                self._vision_engine = vision_engine
            except ImportError:
                self._vision_engine = None
        return self._vision_engine

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        lower = text.lower()

        for kw in self.VISION_KEYWORDS:
            if kw in lower:
                return 0.95

        if self.VISION_REGEX.search(lower):
            return 0.93

        if intent in ("screenshot", "camera", "object_detection", "screen_analysis",
                       "vision", "image_analysis", "screen_ai"):
            return 0.92

        for kw in self.SYSTEM_KEYWORDS:
            if kw in lower:
                return 0.9

        if intent in ("system_monitor", "system_info", "pc_status"):
            return 0.85

        if re.search(r"\b(how much|check|show)\b.*(memory|space|cpu|ram|disk)", lower):
            return 0.8

        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        lower = text.lower()
        if self._is_vision_request(lower):
            return self._handle_vision(lower, text, context)
        return self._handle_system_stats(text, context)

    def _is_vision_request(self, lower: str) -> bool:
        for kw in self.VISION_KEYWORDS:
            if kw in lower:
                return True
        return bool(self.VISION_REGEX.search(lower))

    def _handle_vision(self, lower: str, text: str, context: dict) -> dict:
        if any(kw in lower for kw in ["screenshot", "screen capture", "screen shot",
                                       "screen grab", "snip", "capture screen"]):
            return self._take_screenshot(lower, text)

        if any(kw in lower for kw in ["camera", "webcam", "selfie", "photo le",
                                       "cam capture", "tasveer", "snap"]):
            return self._capture_camera(lower)

        if any(kw in lower for kw in ["detect object", "object detect", "identify",
                                       "recognize", "kya dikh"]):
            return self._detect_objects(text, context)

        if any(kw in lower for kw in ["screen ai", "analyze screen", "screen content",
                                       "read screen", "screen mein kya", "ui detect",
                                       "layout", "what is on screen", "screen pe kya"]):
            return self._analyze_screen(text, context)

        if "compare" in lower and "screen" in lower:
            return self._compare_screenshots(text)

        if "monitor" in lower and ("info" in lower or "list" in lower or "kitne" in lower):
            return self._list_monitors()

        return self._analyze_screen(text, context)

    def _take_screenshot(self, lower: str, text: str) -> dict:
        if not self.vision_engine:
            return self._vision_unavailable()

        region = None
        region_match = re.search(r'(\d+)\s*[,x]\s*(\d+)\s*[,x]\s*(\d+)\s*[,x]\s*(\d+)', text)
        if region_match:
            region = {
                "x": int(region_match.group(1)), "y": int(region_match.group(2)),
                "width": int(region_match.group(3)), "height": int(region_match.group(4)),
            }

        monitor = 0
        mon_match = re.search(r'monitor\s*(\d+)', lower)
        if mon_match:
            monitor = int(mon_match.group(1))

        result = self.vision_engine.take_screenshot(region=region, monitor=monitor)
        if result.get("success"):
            response = result['message']
            if result.get("monitor_info"):
                mi = result["monitor_info"]
                response += f"\nMonitor {mi.get('monitor', 0)}: {mi.get('width', '?')}x{mi.get('height', '?')}"
            return {"response": response, "data": result, "action": "screenshot_taken"}
        return {"response": f"Screenshot failed: {result.get('message', '')}", "data": result, "action": "error"}

    def _capture_camera(self, lower: str) -> dict:
        if not self.vision_engine:
            return self._vision_unavailable()

        camera_idx = 0
        idx_match = re.search(r'camera\s*(\d+)', lower)
        if idx_match:
            camera_idx = int(idx_match.group(1))

        result = self.vision_engine.capture_camera(camera_index=camera_idx)
        if result.get("success"):
            return {"response": result['message'], "data": result, "action": "camera_captured"}
        return {"response": result.get("message", "Camera capture failed"), "data": result, "action": "error"}

    def _detect_objects(self, text: str, context: dict) -> dict:
        if not self.vision_engine:
            return self._vision_unavailable()

        path_match = re.search(r'["\']?([a-zA-Z]:\\[^"\']+\.(png|jpg|jpeg|bmp))', text, re.I)
        if path_match:
            image_path = path_match.group(1)
        else:
            ss = self.vision_engine.take_screenshot()
            if not ss.get("success"):
                return {"response": "Could not capture screen for detection", "data": None, "action": "error"}
            image_path = ss["filepath"]

        result = self.vision_engine.detect_objects(image_path)
        if result.get("success"):
            detections = result.get("detections", [])
            lines = [f"Detected {len(detections)} elements:"]
            for d in detections[:10]:
                conf = round(d.get("confidence", 0) * 100)
                lines.append(f"  - {d['label']} ({d['type']}) — {conf}% confidence")
            return {"response": "\n".join(lines), "data": result, "action": "objects_detected"}
        return {"response": result.get("message", "Detection failed"), "data": result, "action": "error"}

    def _analyze_screen(self, text: str, context: dict) -> dict:
        if not self.vision_engine:
            return self._vision_unavailable()

        path_match = re.search(r'["\']?([a-zA-Z]:\\[^"\']+\.(png|jpg|jpeg|bmp))', text, re.I)
        image_path = path_match.group(1) if path_match else None

        result = self.vision_engine.analyze_screen(image_path)
        if result.get("success"):
            lines = [f"Screen Analysis — {result.get('content_type', 'unknown')}"]
            if result.get("active_app"):
                lines.append(f"Active: {result['active_app']}")
            lines.append(f"Text regions: {len(result.get('text_regions', []))}")
            lines.append(f"UI elements: {len(result.get('ui_elements', []))}")

            for tr in result.get("text_regions", [])[:3]:
                lines.append(f"  [{tr['type']}] {tr['text'][:80]}...")

            suggestions = result.get("suggestions", [])
            if suggestions:
                lines.append("\nSuggestions:")
                for s in suggestions:
                    lines.append(f"  {s}")

            return {"response": "\n".join(lines), "data": result, "action": "screen_analyzed"}
        return {"response": result.get("message", "Analysis failed"), "data": result, "action": "error"}

    def _compare_screenshots(self, text: str) -> dict:
        if not self.vision_engine:
            return self._vision_unavailable()

        paths = re.findall(r'["\']?([a-zA-Z]:\\[^"\']+\.(png|jpg|jpeg|bmp))', text, re.I)
        if len(paths) >= 2:
            result = self.vision_engine.compare_screenshots(paths[0][0], paths[1][0])
        else:
            history = self.vision_engine.get_history(limit=2, type_filter="screenshot")
            if len(history) < 2:
                return {"response": "Need at least 2 screenshots to compare.", "data": None, "action": "error"}
            result = self.vision_engine.compare_screenshots(history[-2]["filepath"], history[-1]["filepath"])

        if result.get("success"):
            return {"response": result['message'], "data": result, "action": "screenshots_compared"}
        return {"response": result.get("message", "Comparison failed"), "data": result, "action": "error"}

    def _list_monitors(self) -> dict:
        if not self.vision_engine:
            return self._vision_unavailable()

        result = self.vision_engine.get_monitors()
        monitors = result.get("monitors", [])
        lines = [f"{len(monitors)} monitor(s) detected:"]
        for i, m in enumerate(monitors):
            primary = " (Primary)" if m.get("primary") else ""
            lines.append(f"  Monitor {i}{primary}: {m.get('width', '?')}x{m.get('height', '?')}")
        return {"response": "\n".join(lines), "data": result, "action": "monitors_listed"}

    def _vision_unavailable(self) -> dict:
        return {"response": "Vision engine not available.", "data": None, "action": "error"}

    # ── System Stats (original, preserved) ──

    def _handle_system_stats(self, text: str, context: dict) -> dict:
        try:
            from pc_control.system_stats import get_system_stats
            stats = get_system_stats()
        except ImportError:
            return {
                "response": "System stats module (pc_control.system_stats) is not available.",
                "data": None, "action": "error",
            }
        except Exception as e:
            return {
                "response": f"Failed to retrieve system stats: {e}",
                "data": None, "action": "error",
            }

        lines = []
        if isinstance(stats, dict):
            if "cpu" in stats:
                cpu = stats["cpu"]
                if isinstance(cpu, dict):
                    lines.append(f"CPU: {cpu.get('percent', 'N/A')}% usage ({cpu.get('cores', '?')} cores)")
                else:
                    lines.append(f"CPU: {cpu}%")

            if "ram" in stats or "memory" in stats:
                mem = stats.get("ram") or stats.get("memory", {})
                if isinstance(mem, dict):
                    lines.append(
                        f"RAM: {mem.get('used_gb', '?')} / {mem.get('total_gb', '?')} GB "
                        f"({mem.get('percent', '?')}%)"
                    )
                else:
                    lines.append(f"RAM: {mem}")

            if "disk" in stats:
                disk = stats["disk"]
                if isinstance(disk, dict):
                    lines.append(
                        f"Disk: {disk.get('used_gb', '?')} / {disk.get('total_gb', '?')} GB "
                        f"({disk.get('percent', '?')}%)"
                    )
                else:
                    lines.append(f"Disk: {disk}")

            if "battery" in stats:
                bat = stats["battery"]
                if isinstance(bat, dict):
                    status = "Charging" if bat.get("charging") else "Discharging"
                    lines.append(f"Battery: {bat.get('percent', '?')}% ({status})")
                elif bat is not None:
                    lines.append(f"Battery: {bat}%")

            for key in stats:
                if key not in ("cpu", "ram", "memory", "disk", "battery"):
                    lines.append(f"{key.replace('_', ' ').title()}: {stats[key]}")

        formatted = "\n".join(lines) if lines else str(stats)
        return {"response": f"System Stats:\n{formatted}", "data": stats, "action": "system_stats"}

    def get_system_prompt_addition(self) -> str:
        return (
            "You have full vision capabilities: screenshots (multi-monitor, region), "
            "camera capture, object detection, screen AI analysis, UI layout detection, "
            "and real-time system monitoring."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        parts = ["[Argus Vision Module]"]
        lower = text.lower()
        if self._is_vision_request(lower):
            parts.append("User wants vision/screen analysis.")
            if self.vision_engine:
                stats = self.vision_engine.get_stats()
                parts.append(f"Captures: {stats.get('total_captures', 0)}, "
                             f"Detections: {stats.get('total_detections', 0)}")
        else:
            parts.append("User is asking about system/PC stats.")
        return " ".join(parts)

    def get_settings(self) -> dict:
        return {"enabled": self.enabled}

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
        ]
