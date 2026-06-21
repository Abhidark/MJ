"""
MJ Plugin System
Drop .py files in plugins/ folder — auto-detected and loaded.
Each plugin must define:
  - PLUGIN_NAME: str
  - PLUGIN_DESCRIPTION: str
  - PLUGIN_COMMANDS: list of trigger words
  - handle(text: str) -> dict  (returns {"success": bool, "message": str})

Optional:
  - on_load() -> called when plugin loads
  - on_message(text: str) -> called on every message (for passive plugins)
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Optional

PLUGINS_DIR = Path(__file__).parent
EXAMPLE_PLUGIN = PLUGINS_DIR / "_example_plugin.py"

# Loaded plugins
loaded_plugins = {}


def _create_example():
    """Create an example plugin file for reference."""
    if EXAMPLE_PLUGIN.exists():
        return
    code = '''"""
Example MJ Plugin — Math Calculator
Drop this file in backend/plugins/ to activate.
"""

PLUGIN_NAME = "calculator"
PLUGIN_DESCRIPTION = "Advanced calculator — solve math expressions"
PLUGIN_COMMANDS = ["calculate", "calc", "math", "hisaab", "ganit"]


def on_load():
    """Called when plugin loads."""
    print(f"[Plugin] {PLUGIN_NAME} loaded!")


def handle(text: str) -> dict:
    """Handle a command matched to this plugin."""
    import re
    # Extract math expression
    expr = text.lower()
    for trigger in PLUGIN_COMMANDS:
        expr = expr.replace(trigger, "").strip()

    # Clean up
    for word in ["what is", "kya hai", "kitna", "solve", "calculate", "of", "ka"]:
        expr = expr.replace(word, "").strip()

    if not expr:
        return {"success": False, "message": "Kya calculate karna hai? Expression do."}

    try:
        # Safe eval (only math)
        allowed = set("0123456789+-*/.() %")
        clean = "".join(c for c in expr if c in allowed)
        if clean:
            result = eval(clean)
            return {"success": True, "message": f"{clean} = {result}"}
        return {"success": False, "message": f"'{expr}' samajh nahi aaya."}
    except Exception as e:
        return {"success": False, "message": f"Calculate nahi ho paya: {str(e)}"}


def on_message(text: str) -> None:
    """Called on every message (optional, for passive plugins)."""
    pass
'''
    EXAMPLE_PLUGIN.write_text(code, encoding="utf-8")


def load_plugins():
    """Discover and load all plugins from plugins/ directory."""
    global loaded_plugins
    loaded_plugins = {}

    _create_example()

    for py_file in PLUGINS_DIR.glob("*.py"):
        if py_file.name.startswith("_") and py_file.name != "_example_plugin.py":
            continue
        if py_file.name in ("__init__.py", "plugin_manager.py"):
            continue

        try:
            module_name = f"plugins.{py_file.stem}"

            # Remove old module if reloading
            if module_name in sys.modules:
                del sys.modules[module_name]

            spec = importlib.util.spec_from_file_location(module_name, py_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Validate required attributes
            name = getattr(module, "PLUGIN_NAME", None)
            desc = getattr(module, "PLUGIN_DESCRIPTION", "No description")
            commands = getattr(module, "PLUGIN_COMMANDS", [])
            handler = getattr(module, "handle", None)

            if not name or not handler:
                continue

            loaded_plugins[name] = {
                "name": name,
                "description": desc,
                "commands": commands,
                "module": module,
                "file": str(py_file),
            }

            # Call on_load if exists
            on_load = getattr(module, "on_load", None)
            if on_load:
                on_load()

        except Exception as e:
            print(f"[Plugin Error] Failed to load {py_file.name}: {e}")

    return loaded_plugins


def reload_plugins():
    """Hot-reload all plugins."""
    return load_plugins()


def get_plugin_list() -> list:
    """Get list of loaded plugins."""
    return [
        {
            "name": p["name"],
            "description": p["description"],
            "commands": p["commands"],
            "file": Path(p["file"]).name,
        }
        for p in loaded_plugins.values()
    ]


def match_plugin(text: str) -> Optional[dict]:
    """Check if text matches any plugin command."""
    lower = text.lower().strip()

    for name, plugin in loaded_plugins.items():
        for cmd in plugin["commands"]:
            if cmd.lower() in lower:
                return plugin

    return None


def run_plugin(plugin: dict, text: str) -> dict:
    """Execute a plugin's handle function."""
    try:
        handler = plugin["module"].handle
        result = handler(text)
        return result
    except Exception as e:
        return {"success": False, "message": f"Plugin '{plugin['name']}' error: {str(e)}"}


def notify_plugins(text: str):
    """Notify all plugins about a message (passive hook)."""
    for name, plugin in loaded_plugins.items():
        try:
            on_msg = getattr(plugin["module"], "on_message", None)
            if on_msg:
                on_msg(text)
        except Exception:
            pass


def parse_plugin_command(text: str) -> Optional[dict]:
    """Parse plugin management commands."""
    lower = text.lower().strip()

    if any(w in lower for w in ["list plugin", "show plugin", "plugins dikhao", "kaun se plugin", "plugin list"]):
        return {"action": "list"}

    if any(w in lower for w in ["reload plugin", "plugin reload", "refresh plugin"]):
        return {"action": "reload"}

    return None


def handle_plugin_management(cmd: dict) -> dict:
    """Handle plugin management commands."""
    if cmd["action"] == "list":
        plugins = get_plugin_list()
        if not plugins:
            return {"success": True, "message": "Koi plugin loaded nahi hai. plugins/ folder me .py files daalo."}
        lines = [f"{len(plugins)} plugin(s) loaded:"]
        for p in plugins:
            lines.append(f"  • {p['name']}: {p['description']}")
            lines.append(f"    Triggers: {', '.join(p['commands'])}")
        return {"success": True, "message": "\n".join(lines)}

    elif cmd["action"] == "reload":
        loaded = reload_plugins()
        return {"success": True, "message": f"Plugins reloaded! {len(loaded)} plugin(s) active."}

    return {"success": False, "message": "Unknown plugin command."}
