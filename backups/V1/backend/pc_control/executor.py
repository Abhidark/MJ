"""
Execute PC control commands on Windows.
"""

import subprocess
import os
import ctypes
from datetime import datetime
from pathlib import Path

SCREENSHOT_DIR = Path(__file__).parent.parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)


def execute_command(cmd: dict) -> dict:
    """
    Execute a parsed command.
    Returns: {"success": bool, "message": str}
    """
    action = cmd["action"]
    target = cmd["target"]
    name = cmd["name"]

    try:
        if action == "open_app":
            return open_app(target, name)
        elif action == "open_website":
            return open_website(target, name)
        elif action == "close_app":
            return close_app(target, name)
        elif action == "screenshot":
            return take_screenshot()
        elif action == "volume":
            return control_volume(target)
        elif action == "brightness":
            return control_brightness(target)
        elif action == "system":
            return system_action(target, name)
        elif action == "search":
            return web_search(target)
        elif action == "media":
            return media_control(target)
        else:
            return {"success": False, "message": f"Unknown action: {action}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


def open_app(target: str, name: str) -> dict:
    """Open an application."""
    try:
        # For UWP/protocol apps (ms-settings:, etc.)
        if ":" in target:
            os.system(f'start "" "{target}"')
        else:
            subprocess.Popen(target, shell=True)
        return {"success": True, "message": f"{name.title()} open kar diya."}
    except FileNotFoundError:
        # Try via start command
        try:
            os.system(f'start "" "{target}"')
            return {"success": True, "message": f"{name.title()} open kar diya."}
        except:
            return {"success": False, "message": f"{name.title()} nahi mila system me."}


def open_website(url: str, name: str) -> dict:
    """Open a website in default browser."""
    os.system(f'start "" "{url}"')
    return {"success": True, "message": f"{name.title()} open kar diya browser me."}


def close_app(target: str, name: str) -> dict:
    """Close an application."""
    # Map common app names to process names
    process_map = {
        "chrome": "chrome.exe",
        "notepad": "notepad.exe",
        "calc": "Calculator.exe",
        "explorer": "explorer.exe",
        "cmd": "cmd.exe",
        "code": "Code.exe",
        "vlc": "vlc.exe",
        "spotify": "Spotify.exe",
        "mspaint": "mspaint.exe",
        "taskmgr": "Taskmgr.exe",
        "discord": "Discord.exe",
        "whatsapp": "WhatsApp.exe",
    }

    proc = process_map.get(target, f"{target}.exe")
    result = os.system(f'taskkill /im {proc} /f >nul 2>&1')

    if result == 0:
        return {"success": True, "message": f"{name.title()} band kar diya."}
    else:
        return {"success": False, "message": f"{name.title()} chal nahi raha tha."}


def take_screenshot() -> dict:
    """Take a screenshot using PowerShell."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = SCREENSHOT_DIR / filename

    ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bitmap.Save("{filepath}")
$graphics.Dispose()
$bitmap.Dispose()
'''
    subprocess.run(["powershell", "-Command", ps_script], capture_output=True)

    if filepath.exists():
        return {"success": True, "message": f"Screenshot le liya. Saved: {filepath.name}", "file": str(filepath)}
    else:
        return {"success": False, "message": "Screenshot lene me error aaya."}


def control_volume(direction: str) -> dict:
    """Control system volume using keyboard simulation via ctypes."""
    VK_VOLUME_UP = 0xAF
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_MUTE = 0xAD

    if direction == "up":
        for _ in range(5):
            ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
        return {"success": True, "message": "Volume badha diya."}

    elif direction == "down":
        for _ in range(5):
            ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
        return {"success": True, "message": "Volume kam kar diya."}

    elif direction == "mute":
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
        return {"success": True, "message": "Mute kar diya."}

    return {"success": False, "message": "Unknown volume command."}


def control_brightness(direction: str) -> dict:
    """Control screen brightness - tries multiple methods."""

    change = 20 if direction == "up" else -20

    # Method 1: WMI (works on most laptops)
    ps_wmi = f'''
try {{
    $b = (Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness
    $n = [Math]::Max(10, [Math]::Min(100, $b + ({change})))
    $m = Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods
    $m.WmiSetBrightness(1, $n)
    Write-Output "OK:$n"
}} catch {{
    Write-Output "FAIL"
}}
'''
    r = subprocess.run(["powershell", "-Command", ps_wmi], capture_output=True, text=True, timeout=10)
    out = r.stdout.strip()

    if out.startswith("OK:"):
        level = out.split(":")[1]
        msg = f"Brightness {'badha' if direction == 'up' else 'kam kar'} di. Ab {level}% hai."
        return {"success": True, "message": msg}

    # Method 2: PowerShell Set-DisplayBrightness (Win 10/11)
    ps_alt = f'''
try {{
    $current = (Get-Ciminstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness
}} catch {{
    $current = 50
}}
$new = [Math]::Max(10, [Math]::Min(100, $current + ({change})))
try {{
    powershell -Command "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,$new)"
    Write-Output "OK:$new"
}} catch {{
    Write-Output "FAIL"
}}
'''
    r2 = subprocess.run(["powershell", "-Command", ps_alt], capture_output=True, text=True, timeout=10)
    out2 = r2.stdout.strip()

    if out2.startswith("OK:"):
        level = out2.split(":")[1]
        msg = f"Brightness {'badha' if direction == 'up' else 'kam kar'} di. Ab {level}% hai."
        return {"success": True, "message": msg}

    # Method 3: Use SendKeys shortcut (Fn key simulation won't work, but try settings)
    # Open Windows brightness settings as fallback
    os.system('start ms-settings:display')
    return {"success": True, "message": f"Brightness direct control nahi ho paya. Display settings khol di — wahan se adjust karo."}


def system_action(target: str, name: str) -> dict:
    """System-level actions."""
    if target == "lock":
        ctypes.windll.user32.LockWorkStation()
        return {"success": True, "message": "Screen lock kar diya."}

    elif target == "shutdown":
        os.system("shutdown /s /t 30")
        return {"success": True, "message": "PC 30 seconds me shutdown ho jayega. Cancel: shutdown /a"}

    elif target == "restart":
        os.system("shutdown /r /t 30")
        return {"success": True, "message": "PC 30 seconds me restart hoga. Cancel: shutdown /a"}

    elif target == "sleep":
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return {"success": True, "message": "Sleep mode me jaa raha hai."}

    return {"success": False, "message": f"Unknown system action: {target}"}


def web_search(query: str) -> dict:
    """Open web search in browser."""
    import urllib.parse
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    os.system(f'start "" "{url}"')
    return {"success": True, "message": f"Google pe search kar diya: {query}"}


def media_control(action: str) -> dict:
    """Media playback control using keyboard simulation."""
    key_map = {
        "play": 179,   # VK_MEDIA_PLAY_PAUSE
        "pause": 179,
        "next": 176,    # VK_MEDIA_NEXT_TRACK
        "prev": 177,    # VK_MEDIA_PREV_TRACK
    }

    vk = key_map.get(action)
    if vk:
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)  # key up

        names = {"play": "Play", "pause": "Pause", "next": "Next track", "prev": "Previous track"}
        return {"success": True, "message": f"{names.get(action, action)} kar diya."}

    return {"success": False, "message": f"Unknown media action: {action}"}
