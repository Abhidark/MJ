"""
MJ Alert System
Unified real-time alert system for errors, health issues, system warnings, and module failures.
Tracks all alerts with severity levels, timestamps, and auto-resolution.
Broadcasts alerts to connected dashboards via SSE.
"""

import json
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

ALERT_FILE = Path(__file__).parent.parent / "error_logs" / "alerts.json"
Path(ALERT_FILE).parent.mkdir(exist_ok=True)

# Severity levels
SEVERITY_CRITICAL = "critical"   # System down, major failure
SEVERITY_ERROR = "error"         # Something broke, needs attention
SEVERITY_WARNING = "warning"     # Degraded, but still working
SEVERITY_INFO = "info"           # FYI, no action needed

# Alert categories
CAT_ERROR = "error"              # Code exception / runtime error
CAT_HEALTH = "health"            # Module import fail, Ollama down
CAT_SYSTEM = "system"            # High CPU, low disk, low battery
CAT_NETWORK = "network"         # API timeout, connection failed
CAT_SELF_HEAL = "self_heal"     # Auto-fix attempted / succeeded / failed
CAT_MODULE = "module"            # Plugin crash, Zeus module fail

# In-memory alert store
alerts = []
MAX_ALERTS = 100

# SSE subscribers (asyncio.Queue per client)
_subscribers = []
_lock = threading.Lock()


def _load_alerts():
    global alerts
    try:
        if ALERT_FILE.exists():
            alerts = json.loads(ALERT_FILE.read_text(encoding="utf-8"))
    except Exception:
        alerts = []


def _save_alerts():
    try:
        ALERT_FILE.write_text(
            json.dumps(alerts[:MAX_ALERTS], ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception:
        pass


def create_alert(
    title: str,
    message: str,
    severity: str = SEVERITY_ERROR,
    category: str = CAT_ERROR,
    source: str = "",
    error_id: str = "",
    auto_resolve_seconds: int = 0,
) -> dict:
    """
    Create a new alert and broadcast to all connected clients.
    """
    alert = {
        "id": f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
        "timestamp": datetime.now().isoformat(),
        "time_display": datetime.now().strftime("%I:%M:%S %p"),
        "title": title,
        "message": message[:300],
        "severity": severity,
        "category": category,
        "source": source,
        "error_id": error_id,
        "resolved": False,
        "resolved_at": "",
        "resolve_message": "",
    }

    alerts.insert(0, alert)
    if len(alerts) > MAX_ALERTS:
        alerts.pop()

    _save_alerts()

    # Broadcast to all SSE subscribers
    _broadcast(alert)

    # Auto-resolve if set
    if auto_resolve_seconds > 0:
        def _auto_resolve():
            import time
            time.sleep(auto_resolve_seconds)
            resolve_alert(alert["id"], "Auto-resolved after timeout")
        t = threading.Thread(target=_auto_resolve, daemon=True)
        t.start()

    return alert


def resolve_alert(alert_id: str, resolve_message: str = "Resolved"):
    """Mark an alert as resolved."""
    for a in alerts:
        if a["id"] == alert_id:
            a["resolved"] = True
            a["resolved_at"] = datetime.now().isoformat()
            a["resolve_message"] = resolve_message
            break
    _save_alerts()

    # Broadcast resolution
    _broadcast({
        "type": "resolve",
        "alert_id": alert_id,
        "resolve_message": resolve_message,
        "time": datetime.now().strftime("%I:%M:%S %p"),
    })


def get_active_alerts() -> list:
    """Get all unresolved alerts."""
    return [a for a in alerts if not a.get("resolved")]


def get_all_alerts(limit: int = 50) -> list:
    """Get all alerts (active + resolved)."""
    return alerts[:limit]


def get_alert_stats() -> dict:
    """Get alert statistics."""
    active = [a for a in alerts if not a.get("resolved")]
    return {
        "total": len(alerts),
        "active": len(active),
        "critical": sum(1 for a in active if a["severity"] == SEVERITY_CRITICAL),
        "errors": sum(1 for a in active if a["severity"] == SEVERITY_ERROR),
        "warnings": sum(1 for a in active if a["severity"] == SEVERITY_WARNING),
        "info": sum(1 for a in active if a["severity"] == SEVERITY_INFO),
        "last_alert": alerts[0]["time_display"] if alerts else None,
    }


def clear_resolved():
    """Clear all resolved alerts."""
    global alerts
    alerts = [a for a in alerts if not a.get("resolved")]
    _save_alerts()


def clear_all_alerts():
    """Clear everything."""
    global alerts
    alerts = []
    _save_alerts()


# --- SSE Broadcasting ---

def subscribe() -> asyncio.Queue:
    """Subscribe to real-time alerts. Returns an asyncio.Queue."""
    q = asyncio.Queue()
    with _lock:
        _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue):
    """Unsubscribe from alerts."""
    with _lock:
        if q in _subscribers:
            _subscribers.remove(q)


def _broadcast(data: dict):
    """Send alert to all connected SSE clients."""
    msg = json.dumps(data, ensure_ascii=False)
    dead = []
    with _lock:
        for q in _subscribers:
            try:
                q.put_nowait(msg)
            except Exception:
                dead.append(q)
        for d in dead:
            _subscribers.remove(d)


# --- System Warning Generator ---

def check_system_warnings(stats: dict):
    """
    Called from system stats polling.
    Creates alerts for dangerous system conditions.
    """
    cpu = stats.get("cpu", 0)
    ram = stats.get("ram_percent", 0)
    disk = stats.get("disk_percent", 0)
    battery = stats.get("battery", -1)

    # Critical CPU
    if cpu > 95:
        # Don't spam — check if similar alert exists in last 60 seconds
        if not _has_recent_alert("CPU Critical", 60):
            create_alert(
                title="CPU Critical",
                message=f"CPU usage is at {cpu}%! System may freeze or crash.",
                severity=SEVERITY_CRITICAL,
                category=CAT_SYSTEM,
                source="system_monitor",
                auto_resolve_seconds=120,
            )
    elif cpu > 85:
        if not _has_recent_alert("CPU High", 120):
            create_alert(
                title="CPU High",
                message=f"CPU usage is at {cpu}%. Performance may degrade.",
                severity=SEVERITY_WARNING,
                category=CAT_SYSTEM,
                source="system_monitor",
                auto_resolve_seconds=180,
            )

    # Critical RAM
    if ram > 95:
        if not _has_recent_alert("RAM Critical", 60):
            create_alert(
                title="RAM Critical",
                message=f"RAM usage is at {ram}%! Out of memory risk.",
                severity=SEVERITY_CRITICAL,
                category=CAT_SYSTEM,
                source="system_monitor",
                auto_resolve_seconds=120,
            )
    elif ram > 85:
        if not _has_recent_alert("RAM High", 120):
            create_alert(
                title="RAM High",
                message=f"RAM usage is at {ram}%. Close unused apps.",
                severity=SEVERITY_WARNING,
                category=CAT_SYSTEM,
                source="system_monitor",
                auto_resolve_seconds=180,
            )

    # Disk almost full
    if disk > 95:
        if not _has_recent_alert("Disk Critical", 300):
            create_alert(
                title="Disk Critical",
                message=f"Disk is {disk}% full! Free up space immediately.",
                severity=SEVERITY_CRITICAL,
                category=CAT_SYSTEM,
                source="system_monitor",
            )
    elif disk > 85:
        if not _has_recent_alert("Disk Warning", 600):
            create_alert(
                title="Disk Warning",
                message=f"Disk is {disk}% full. Consider cleanup.",
                severity=SEVERITY_WARNING,
                category=CAT_SYSTEM,
                source="system_monitor",
            )

    # Battery low
    if 0 < battery < 10 and not stats.get("charging"):
        if not _has_recent_alert("Battery Critical", 120):
            create_alert(
                title="Battery Critical",
                message=f"Battery at {battery}%! Plug in charger NOW.",
                severity=SEVERITY_CRITICAL,
                category=CAT_SYSTEM,
                source="system_monitor",
            )
    elif 0 < battery < 20 and not stats.get("charging"):
        if not _has_recent_alert("Battery Low", 300):
            create_alert(
                title="Battery Low",
                message=f"Battery at {battery}%. Plug in charger soon.",
                severity=SEVERITY_WARNING,
                category=CAT_SYSTEM,
                source="system_monitor",
            )


def _has_recent_alert(title: str, seconds: int) -> bool:
    """Check if a similar alert was created recently."""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(seconds=seconds)
    for a in alerts[:20]:
        if a["title"] == title:
            try:
                t = datetime.fromisoformat(a["timestamp"])
                if t > cutoff:
                    return True
            except Exception:
                pass
    return False


# Load on import
_load_alerts()
