"""
MJ Self-Healing: FastAPI Middleware
Catches all unhandled exceptions, logs them, sends notifications, and triggers auto-fix.
"""

import asyncio
import subprocess
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from self_healer.error_tracker import log_error, get_error_stats
from self_healer.auto_fixer import attempt_fix, analyze_error
from self_healer.alert_system import create_alert, resolve_alert, SEVERITY_ERROR, SEVERITY_CRITICAL, SEVERITY_INFO, CAT_ERROR, CAT_SELF_HEAL


class SelfHealingMiddleware(BaseHTTPMiddleware):
    """
    Catches unhandled exceptions in any endpoint:
    1. Logs the error with full traceback
    2. Sends Windows desktop notification
    3. Attempts auto-fix via Ollama (async, non-blocking)
    4. Returns a user-friendly error response
    """

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response

        except Exception as error:
            # Get user input if available
            user_input = ""
            try:
                if request.method == "POST":
                    # Try to get form data or body
                    body = await request.body()
                    user_input = body.decode("utf-8", errors="ignore")[:200]
            except Exception:
                pass

            # Log the error
            error_entry = log_error(
                error=error,
                source="middleware",
                endpoint=f"{request.method} {request.url.path}",
                user_input=user_input,
            )

            # Create alert for dashboard
            alert = create_alert(
                title=f"{error_entry['type']}: {error_entry['message'][:80]}",
                message=f"Endpoint: {error_entry['endpoint']}\nFile: {error_entry.get('file_path','')}\nLine: {error_entry.get('line_number','')}\nAuto-fix attempting...",
                severity=SEVERITY_CRITICAL if "critical" in str(error_entry['type']).lower() else SEVERITY_ERROR,
                category=CAT_ERROR,
                source=error_entry.get("source", "middleware"),
                error_id=error_entry["id"],
            )

            # Send Windows notification (non-blocking)
            _send_error_notification(error_entry)

            # Attempt auto-fix (non-blocking background task)
            asyncio.create_task(_auto_fix_background(error_entry, alert["id"]))

            # Return user-friendly error
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "error_id": error_entry["id"],
                    "message": f"Error aaya: {error_entry['type']} - {error_entry['message']}",
                    "fix_status": "attempting",
                    "detail": "MJ khud fix karne ki koshish kar raha hai...",
                }
            )


async def _auto_fix_background(error_entry: dict, alert_id: str = ""):
    """Background task to attempt auto-fix."""
    try:
        result = await attempt_fix(error_entry)

        if result["success"]:
            _send_fix_notification(
                f"Fix Applied: {error_entry['type']}",
                result["message"]
            )
            # Create success alert and resolve the error alert
            create_alert(
                title=f"Auto-Fix Applied: {error_entry['type']}",
                message=result["message"][:200],
                severity=SEVERITY_INFO,
                category=CAT_SELF_HEAL,
                source="auto_fixer",
                auto_resolve_seconds=60,
            )
            if alert_id:
                resolve_alert(alert_id, f"Auto-fixed: {result['message'][:100]}")
        else:
            _send_fix_notification(
                f"Fix Failed: {error_entry['type']}",
                result["message"]
            )
            # Create failure alert
            create_alert(
                title=f"Auto-Fix Failed: {error_entry['type']}",
                message=f"Manual intervention needed. {result['message'][:150]}",
                severity=SEVERITY_ERROR,
                category=CAT_SELF_HEAL,
                source="auto_fixer",
            )
    except Exception as e:
        pass


def _send_error_notification(error_entry: dict):
    """Send Windows notification about error."""
    title = f"MJ Error: {error_entry['type']}"
    message = f"{error_entry['message'][:100]}\nEndpoint: {error_entry['endpoint']}\nAuto-fix attempt..."

    ps = f'''
Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Error
$n.Visible = $true
$n.ShowBalloonTip(8000, "{_escape_ps(title)}", "{_escape_ps(message)}", [System.Windows.Forms.ToolTipIcon]::Error)
Start-Sleep -Seconds 9
$n.Dispose()
'''
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps],
            creationflags=0x08000000
        )
    except Exception:
        pass


def _send_fix_notification(title: str, message: str):
    """Send notification about fix result."""
    icon_type = "Info" if "Apply" in title or "Fixed" in title else "Warning"
    ps = f'''
Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::{icon_type}
$n.Visible = $true
$n.ShowBalloonTip(8000, "{_escape_ps(title)}", "{_escape_ps(message[:150])}", [System.Windows.Forms.ToolTipIcon]::{icon_type})
Start-Sleep -Seconds 9
$n.Dispose()
'''
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps],
            creationflags=0x08000000
        )
    except Exception:
        pass


def _escape_ps(text: str) -> str:
    """Escape text for PowerShell strings."""
    return text.replace('"', '`"').replace("'", "`'").replace("\n", " ")
