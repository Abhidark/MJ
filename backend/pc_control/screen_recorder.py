"""
Screen Recording for MJ.
Uses PowerShell + .NET to record screen as video frames, then ffmpeg to encode.
Fallback: Uses built-in Game Bar (Win+G).
"""

import subprocess
import os
import re
from pathlib import Path
from datetime import datetime

RECORDING_DIR = Path(__file__).parent.parent / "recordings"
RECORDING_DIR.mkdir(exist_ok=True)

# Track recording state
_recording_state = {"active": False, "process": None, "file": None}


def parse_recording_command(text: str) -> dict | None:
    """Parse screen recording commands."""
    lower = text.lower().strip()

    start_patterns = [
        "screen record start", "start screen record", "recording start",
        "start recording", "screen record shuru", "record start",
        "screen record karo", "recording shuru", "rec start",
    ]
    stop_patterns = [
        "screen record stop", "stop screen record", "recording stop",
        "stop recording", "screen record band", "record stop",
        "recording band karo", "rec stop", "recording roko",
    ]

    for p in start_patterns:
        if p in lower:
            return {"action": "start"}

    for p in stop_patterns:
        if p in lower:
            return {"action": "stop"}

    return None


def start_recording() -> dict:
    """Start screen recording."""
    global _recording_state

    if _recording_state["active"]:
        return {"success": False, "message": "Recording already chal rahi hai! Stop bolke pehle band karo."}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = RECORDING_DIR / f"recording_{timestamp}.mp4"

    # Check if ffmpeg is available
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
        has_ffmpeg = r.returncode == 0
    except Exception:
        has_ffmpeg = False

    if has_ffmpeg:
        # Use ffmpeg with GDI screen capture
        cmd = [
            "ffmpeg", "-y",
            "-f", "gdigrab",
            "-framerate", "15",
            "-i", "desktop",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-pix_fmt", "yuv420p",
            str(output_file)
        ]
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            _recording_state = {"active": True, "process": proc, "file": str(output_file), "method": "ffmpeg"}
            return {"success": True, "message": f"Screen recording start ho gayi! Stop bolna jab band karni ho."}
        except Exception as e:
            return {"success": False, "message": f"FFmpeg se recording start nahi hui: {str(e)}"}
    else:
        # Fallback: Use Windows Game Bar shortcut
        try:
            # Simulate Win+Alt+R (Game Bar record toggle)
            import ctypes
            # Use PowerShell to send keys
            ps = '''
            Add-Type -TypeDefinition @"
            using System;
            using System.Runtime.InteropServices;
            public class KeySender {
                [DllImport("user32.dll")]
                public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
                public const byte VK_LWIN = 0x5B;
                public const byte VK_MENU = 0x12;
                public const byte VK_R = 0x52;
                public const uint KEYEVENTF_KEYUP = 0x0002;
            }
"@
            [KeySender]::keybd_event([KeySender]::VK_LWIN, 0, 0, [UIntPtr]::Zero)
            [KeySender]::keybd_event([KeySender]::VK_MENU, 0, 0, [UIntPtr]::Zero)
            [KeySender]::keybd_event([KeySender]::VK_R, 0, 0, [UIntPtr]::Zero)
            Start-Sleep -Milliseconds 100
            [KeySender]::keybd_event([KeySender]::VK_R, 0, [KeySender]::KEYEVENTF_KEYUP, [UIntPtr]::Zero)
            [KeySender]::keybd_event([KeySender]::VK_MENU, 0, [KeySender]::KEYEVENTF_KEYUP, [UIntPtr]::Zero)
            [KeySender]::keybd_event([KeySender]::VK_LWIN, 0, [KeySender]::KEYEVENTF_KEYUP, [UIntPtr]::Zero)
            '''
            subprocess.Popen(["powershell", "-NoProfile", "-Command", ps], creationflags=0x08000000)
            _recording_state = {"active": True, "process": None, "file": "Game Bar", "method": "gamebar"}
            return {"success": True, "message": "Windows Game Bar se recording start ki! Stop bolna band karne ke liye."}
        except Exception as e:
            return {"success": False, "message": f"Recording start nahi ho payi. FFmpeg install karo: winget install ffmpeg"}


def stop_recording() -> dict:
    """Stop screen recording."""
    global _recording_state

    if not _recording_state["active"]:
        return {"success": False, "message": "Koi recording chal nahi rahi abhi."}

    method = _recording_state.get("method", "ffmpeg")

    if method == "ffmpeg" and _recording_state["process"]:
        try:
            # Send 'q' to ffmpeg to stop gracefully
            _recording_state["process"].stdin.write(b"q")
            _recording_state["process"].stdin.flush()
            _recording_state["process"].wait(timeout=10)
        except Exception:
            try:
                _recording_state["process"].terminate()
            except Exception:
                pass

        file_path = _recording_state["file"]
        _recording_state = {"active": False, "process": None, "file": None}

        if Path(file_path).exists():
            size = Path(file_path).stat().st_size
            size_mb = size / (1024 * 1024)
            return {"success": True, "message": f"Recording save ho gayi! File: {Path(file_path).name} ({size_mb:.1f} MB)"}
        else:
            return {"success": True, "message": "Recording band kar di."}

    elif method == "gamebar":
        # Send Win+Alt+R again to stop
        ps = '''
        Add-Type -TypeDefinition @"
        using System;
        using System.Runtime.InteropServices;
        public class KeySender2 {
            [DllImport("user32.dll")]
            public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
        }
"@
        [KeySender2]::keybd_event(0x5B, 0, 0, [UIntPtr]::Zero)
        [KeySender2]::keybd_event(0x12, 0, 0, [UIntPtr]::Zero)
        [KeySender2]::keybd_event(0x52, 0, 0, [UIntPtr]::Zero)
        Start-Sleep -Milliseconds 100
        [KeySender2]::keybd_event(0x52, 0, 2, [UIntPtr]::Zero)
        [KeySender2]::keybd_event(0x12, 0, 2, [UIntPtr]::Zero)
        [KeySender2]::keybd_event(0x5B, 0, 2, [UIntPtr]::Zero)
        '''
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=5)
        except Exception:
            pass

        _recording_state = {"active": False, "process": None, "file": None}
        return {"success": True, "message": "Game Bar recording band kar di! Video Captures folder me milegi."}

    _recording_state = {"active": False, "process": None, "file": None}
    return {"success": True, "message": "Recording band kar di."}
