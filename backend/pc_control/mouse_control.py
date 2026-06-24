"""
Mouse control module for MJ Assistant.
Provides mouse automation: move, click, scroll, position.
Uses pyautogui for cross-platform mouse control on Windows.
"""

import subprocess
import sys

# Lazy import pyautogui — install if missing
_pyautogui = None

def _get_pyautogui():
    global _pyautogui
    if _pyautogui is None:
        try:
            import pyautogui
            pyautogui.FAILSAFE = True  # Move mouse to corner to abort
            pyautogui.PAUSE = 0.1
            _pyautogui = pyautogui
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui", "-q"])
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
            _pyautogui = pyautogui
    return _pyautogui


def get_position() -> dict:
    """Get current mouse cursor position."""
    try:
        pag = _get_pyautogui()
        x, y = pag.position()
        screen_w, screen_h = pag.size()
        return {
            "success": True,
            "message": f"Mouse position: ({x}, {y}) — Screen: {screen_w}x{screen_h}",
            "data": {"x": x, "y": y, "screen_width": screen_w, "screen_height": screen_h}
        }
    except Exception as e:
        return {"success": False, "message": f"Position check failed: {str(e)}"}


def move_to(x: int, y: int, duration: float = 0.3) -> dict:
    """Move mouse to absolute position."""
    try:
        pag = _get_pyautogui()
        screen_w, screen_h = pag.size()
        x = max(0, min(x, screen_w - 1))
        y = max(0, min(y, screen_h - 1))
        pag.moveTo(x, y, duration=duration)
        return {"success": True, "message": f"Mouse moved to ({x}, {y})."}
    except Exception as e:
        return {"success": False, "message": f"Move failed: {str(e)}"}


def move_relative(dx: int, dy: int, duration: float = 0.2) -> dict:
    """Move mouse relative to current position."""
    try:
        pag = _get_pyautogui()
        pag.moveRel(dx, dy, duration=duration)
        x, y = pag.position()
        return {"success": True, "message": f"Mouse moved by ({dx}, {dy}). Now at ({x}, {y})."}
    except Exception as e:
        return {"success": False, "message": f"Relative move failed: {str(e)}"}


def click(x: int = None, y: int = None, button: str = "left", clicks: int = 1) -> dict:
    """Click at position (or current position if x,y not given)."""
    try:
        pag = _get_pyautogui()
        if x is not None and y is not None:
            pag.click(x, y, clicks=clicks, button=button)
            action = "Double-clicked" if clicks == 2 else "Right-clicked" if button == "right" else "Clicked"
            return {"success": True, "message": f"{action} at ({x}, {y})."}
        else:
            pag.click(clicks=clicks, button=button)
            cx, cy = pag.position()
            action = "Double-clicked" if clicks == 2 else "Right-clicked" if button == "right" else "Clicked"
            return {"success": True, "message": f"{action} at current position ({cx}, {cy})."}
    except Exception as e:
        return {"success": False, "message": f"Click failed: {str(e)}"}


def double_click(x: int = None, y: int = None) -> dict:
    """Double-click at position."""
    return click(x, y, button="left", clicks=2)


def right_click(x: int = None, y: int = None) -> dict:
    """Right-click at position."""
    return click(x, y, button="right", clicks=1)


def scroll(amount: int, x: int = None, y: int = None) -> dict:
    """Scroll up (positive) or down (negative)."""
    try:
        pag = _get_pyautogui()
        if x is not None and y is not None:
            pag.scroll(amount, x, y)
        else:
            pag.scroll(amount)
        direction = "up" if amount > 0 else "down"
        return {"success": True, "message": f"Scrolled {direction} by {abs(amount)} units."}
    except Exception as e:
        return {"success": False, "message": f"Scroll failed: {str(e)}"}


def drag_to(x: int, y: int, duration: float = 0.5, button: str = "left") -> dict:
    """Drag from current position to target."""
    try:
        pag = _get_pyautogui()
        sx, sy = pag.position()
        pag.dragTo(x, y, duration=duration, button=button)
        return {"success": True, "message": f"Dragged from ({sx}, {sy}) to ({x}, {y})."}
    except Exception as e:
        return {"success": False, "message": f"Drag failed: {str(e)}"}


def execute_mouse_command(cmd: dict) -> dict:
    """Execute a parsed mouse command."""
    action = cmd.get("mouse_action", "")
    params = cmd.get("params", {})

    if action == "position":
        return get_position()
    elif action == "move":
        return move_to(params.get("x", 0), params.get("y", 0), params.get("duration", 0.3))
    elif action == "move_rel":
        return move_relative(params.get("dx", 0), params.get("dy", 0))
    elif action == "click":
        return click(params.get("x"), params.get("y"), params.get("button", "left"))
    elif action == "double_click":
        return double_click(params.get("x"), params.get("y"))
    elif action == "right_click":
        return right_click(params.get("x"), params.get("y"))
    elif action == "scroll_up":
        return scroll(params.get("amount", 3), params.get("x"), params.get("y"))
    elif action == "scroll_down":
        return scroll(-params.get("amount", 3), params.get("x"), params.get("y"))
    elif action == "drag":
        return drag_to(params.get("x", 0), params.get("y", 0))
    else:
        return {"success": False, "message": f"Unknown mouse action: {action}"}
