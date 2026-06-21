"""
Argus Module -- System Monitoring & PC Stats
"""

import re
from modules.base_module import BaseModule


class ArgusModule(BaseModule):
    name = "argus"
    display_name = "Argus"
    icon = "\U0001f441️"
    description = "System monitoring: CPU, RAM, disk, battery, and PC status"
    version = "1.0"
    category = "system"
    enabled = True

    KEYWORDS = [
        "cpu", "ram", "disk", "battery", "system info", "pc status",
        "stats", "memory", "storage", "temperature", "system health",
        "performance", "uptime", "system status", "hardware",
        "processor", "usage", "free space",
    ]

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        lower = text.lower()

        for kw in self.KEYWORDS:
            if kw in lower:
                return 0.9

        if intent in ("system_monitor", "system_info", "pc_status"):
            return 0.85

        if re.search(r"\b(how much|check|show)\b.*(memory|space|cpu|ram|disk)", lower):
            return 0.8

        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        try:
            from pc_control.system_stats import get_system_stats
            stats = get_system_stats()
        except ImportError:
            return {
                "response": "System stats module (pc_control.system_stats) is not available.",
                "data": None,
                "action": "error",
            }
        except Exception as e:
            return {
                "response": f"Failed to retrieve system stats: {e}",
                "data": None,
                "action": "error",
            }

        # Format the stats into a readable response
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

            # Include any other keys
            for key in stats:
                if key not in ("cpu", "ram", "memory", "disk", "battery"):
                    lines.append(f"{key.replace('_', ' ').title()}: {stats[key]}")

        formatted = "\n".join(lines) if lines else str(stats)

        return {
            "response": f"System Stats:\n{formatted}",
            "data": stats,
            "action": "system_stats",
        }

    def get_system_prompt_addition(self) -> str:
        return (
            "You have access to real-time system monitoring. "
            "Present system stats clearly with units and context."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        return "[Argus System Monitor] User is asking about system/PC stats."

    def get_settings(self) -> dict:
        return {"enabled": self.enabled}

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
        ]
