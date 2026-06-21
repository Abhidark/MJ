"""
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
