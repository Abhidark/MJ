"""
Vulcan Module — PC Control for MJ Assistant.
Wraps command parsing and execution for system commands like opening apps,
controlling volume, taking screenshots, etc.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.base_module import BaseModule


class VulcanModule(BaseModule):
    name = "vulcan"
    display_name = "Vulcan"
    icon = "🧑‍💻"
    description = "PC Control — open apps, control volume, take screenshots, manage system"
    version = "1.0"
    category = "system"
    enabled = True

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        """Use parse_command to check if this is a system command."""
        try:
            from pc_control.command_parser import parse_command

            cmd = parse_command(text)
            if cmd is not None:
                return 0.95
        except ImportError:
            pass

        # Fallback keyword detection
        pc_keywords = re.compile(
            r"\b(open|close|volume|mute|unmute|screenshot|brightness|wifi|bluetooth|"
            r"shutdown|restart|lock|sleep|kholo|band\s+karo|chalao|screen)\b",
            re.IGNORECASE,
        )
        if pc_keywords.search(text):
            return 0.8

        if intent in ("system_command", "app_control", "pc_control"):
            return 0.85

        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        try:
            from pc_control.command_parser import parse_command
            from pc_control.executor import execute_command

            cmd = parse_command(text)
            if cmd is None:
                return {
                    "response": "I couldn't understand that as a PC command. Can you rephrase?",
                    "data": None,
                    "action": "none",
                }

            result = execute_command(cmd)
            success = result.get("success", False)
            message = result.get("message", "Command executed.")

            return {
                "response": message,
                "data": {
                    "command": cmd,
                    "result": result,
                    "success": success,
                },
                "action": f"pc_control:{cmd.get('action', 'unknown')}",
            }
        except ImportError as e:
            return {
                "response": f"PC control module not available: {e}",
                "data": None,
                "action": "error",
            }
        except Exception as e:
            return {
                "response": f"Error executing command: {e}",
                "data": {"error": str(e)},
                "action": "error",
            }

    def get_system_prompt_addition(self) -> str:
        return (
            "You can control the user's PC. Available actions include: opening/closing apps, "
            "adjusting volume, taking screenshots, controlling brightness, toggling WiFi/Bluetooth, "
            "and system operations (shutdown/restart/lock/sleep). "
            "When the user asks to perform a system action, execute it directly."
        )

    def get_settings(self) -> dict:
        return {"enabled": self.enabled}

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
        ]
