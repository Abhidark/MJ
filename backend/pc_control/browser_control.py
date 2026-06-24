"""
Browser control module for MJ Assistant.
Manages browser tabs, navigation, bookmarks using keyboard shortcuts.
Works with Chrome/Edge/Firefox on Windows via pyautogui keyboard simulation.
"""

import os
import subprocess
import time
import ctypes


def _send_keys(keys: str):
    """Send keyboard shortcut using pyautogui."""
    try:
        import pyautogui
        pyautogui.hotkey(*keys.split("+"))
    except ImportError:
        subprocess.check_call(["pip", "install", "pyautogui", "-q"])
        import pyautogui
        pyautogui.hotkey(*keys.split("+"))


def open_url(url: str, new_tab: bool = True) -> dict:
    """Open a URL in the default browser."""
    try:
        if not url.startswith("http"):
            url = f"https://{url}"
        os.system(f'start "" "{url}"')
        return {"success": True, "message": f"Opened {url} in browser."}
    except Exception as e:
        return {"success": False, "message": f"Failed to open URL: {str(e)}"}


def new_tab() -> dict:
    """Open a new browser tab (Ctrl+T)."""
    try:
        _send_keys("ctrl+t")
        return {"success": True, "message": "New tab opened."}
    except Exception as e:
        return {"success": False, "message": f"New tab failed: {str(e)}"}


def close_tab() -> dict:
    """Close current browser tab (Ctrl+W)."""
    try:
        _send_keys("ctrl+w")
        return {"success": True, "message": "Tab closed."}
    except Exception as e:
        return {"success": False, "message": f"Close tab failed: {str(e)}"}


def next_tab() -> dict:
    """Switch to next tab (Ctrl+Tab)."""
    try:
        _send_keys("ctrl+tab")
        return {"success": True, "message": "Switched to next tab."}
    except Exception as e:
        return {"success": False, "message": f"Next tab failed: {str(e)}"}


def prev_tab() -> dict:
    """Switch to previous tab (Ctrl+Shift+Tab)."""
    try:
        _send_keys("ctrl+shift+tab")
        return {"success": True, "message": "Switched to previous tab."}
    except Exception as e:
        return {"success": False, "message": f"Previous tab failed: {str(e)}"}


def refresh_page() -> dict:
    """Refresh current page (F5)."""
    try:
        _send_keys("f5")
        return {"success": True, "message": "Page refreshed."}
    except Exception as e:
        return {"success": False, "message": f"Refresh failed: {str(e)}"}


def go_back() -> dict:
    """Go back in browser history (Alt+Left)."""
    try:
        _send_keys("alt+left")
        return {"success": True, "message": "Went back."}
    except Exception as e:
        return {"success": False, "message": f"Go back failed: {str(e)}"}


def go_forward() -> dict:
    """Go forward in browser history (Alt+Right)."""
    try:
        _send_keys("alt+right")
        return {"success": True, "message": "Went forward."}
    except Exception as e:
        return {"success": False, "message": f"Go forward failed: {str(e)}"}


def focus_address_bar() -> dict:
    """Focus the address bar (Ctrl+L)."""
    try:
        _send_keys("ctrl+l")
        return {"success": True, "message": "Address bar focused. Type a URL."}
    except Exception as e:
        return {"success": False, "message": f"Focus address bar failed: {str(e)}"}


def zoom_in() -> dict:
    """Zoom in (Ctrl+Plus)."""
    try:
        _send_keys("ctrl+=")
        return {"success": True, "message": "Zoomed in."}
    except Exception as e:
        return {"success": False, "message": f"Zoom in failed: {str(e)}"}


def zoom_out() -> dict:
    """Zoom out (Ctrl+Minus)."""
    try:
        _send_keys("ctrl+-")
        return {"success": True, "message": "Zoomed out."}
    except Exception as e:
        return {"success": False, "message": f"Zoom out failed: {str(e)}"}


def zoom_reset() -> dict:
    """Reset zoom to 100% (Ctrl+0)."""
    try:
        _send_keys("ctrl+0")
        return {"success": True, "message": "Zoom reset to 100%."}
    except Exception as e:
        return {"success": False, "message": f"Zoom reset failed: {str(e)}"}


def fullscreen() -> dict:
    """Toggle fullscreen (F11)."""
    try:
        _send_keys("f11")
        return {"success": True, "message": "Toggled fullscreen."}
    except Exception as e:
        return {"success": False, "message": f"Fullscreen toggle failed: {str(e)}"}


def open_devtools() -> dict:
    """Open developer tools (F12)."""
    try:
        _send_keys("f12")
        return {"success": True, "message": "DevTools opened."}
    except Exception as e:
        return {"success": False, "message": f"DevTools failed: {str(e)}"}


def reopen_closed_tab() -> dict:
    """Reopen last closed tab (Ctrl+Shift+T)."""
    try:
        _send_keys("ctrl+shift+t")
        return {"success": True, "message": "Reopened last closed tab."}
    except Exception as e:
        return {"success": False, "message": f"Reopen tab failed: {str(e)}"}


def execute_browser_command(cmd: dict) -> dict:
    """Execute a parsed browser command."""
    action = cmd.get("browser_action", "")
    params = cmd.get("params", {})

    actions = {
        "open_url": lambda: open_url(params.get("url", ""), params.get("new_tab", True)),
        "new_tab": new_tab,
        "close_tab": close_tab,
        "next_tab": next_tab,
        "prev_tab": prev_tab,
        "refresh": refresh_page,
        "go_back": go_back,
        "go_forward": go_forward,
        "focus_url": focus_address_bar,
        "zoom_in": zoom_in,
        "zoom_out": zoom_out,
        "zoom_reset": zoom_reset,
        "fullscreen": fullscreen,
        "devtools": open_devtools,
        "reopen_tab": reopen_closed_tab,
    }

    fn = actions.get(action)
    if fn:
        return fn()
    return {"success": False, "message": f"Unknown browser action: {action}"}
