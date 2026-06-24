"""
Circuit Breaker for MJ Modules
If a module fails 3+ times in a row, auto-disable it.
Re-enable after cooldown period.
Prevents cascade failures.
"""

import time
import threading
from datetime import datetime

# Config
MAX_FAILURES = 3           # failures before tripping
COOLDOWN_SECONDS = 300     # 5 min cooldown before retry
HALF_OPEN_TRIES = 1        # attempts allowed in half-open state

# States
STATE_CLOSED = "closed"       # normal, module working
STATE_OPEN = "open"           # tripped, module disabled
STATE_HALF_OPEN = "half_open" # testing if module recovered

_breakers = {}
_lock = threading.Lock()


class _BreakerState:
    def __init__(self, module_name):
        self.module_name = module_name
        self.state = STATE_CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.tripped_at = 0
        self.total_trips = 0
        self.last_error = ""


def get_or_create(module_name):
    with _lock:
        if module_name not in _breakers:
            _breakers[module_name] = _BreakerState(module_name)
        return _breakers[module_name]


def is_allowed(module_name):
    """Check if a module is allowed to execute. Returns True if allowed."""
    b = get_or_create(module_name)

    if b.state == STATE_CLOSED:
        return True

    if b.state == STATE_OPEN:
        # Check if cooldown expired
        elapsed = time.time() - b.tripped_at
        if elapsed >= COOLDOWN_SECONDS:
            b.state = STATE_HALF_OPEN
            b.failure_count = 0
            return True
        return False

    if b.state == STATE_HALF_OPEN:
        # Allow limited tries
        return b.success_count < HALF_OPEN_TRIES

    return True


def record_success(module_name):
    """Record a successful execution."""
    b = get_or_create(module_name)

    if b.state == STATE_HALF_OPEN:
        b.success_count += 1
        if b.success_count >= HALF_OPEN_TRIES:
            # Module recovered -- close breaker
            b.state = STATE_CLOSED
            b.failure_count = 0
            b.success_count = 0
            _notify_recovered(module_name)
    elif b.state == STATE_CLOSED:
        # Reset failure count on success
        b.failure_count = 0
        b.success_count += 1


def record_failure(module_name, error_msg=""):
    """Record a failed execution. May trip the breaker."""
    b = get_or_create(module_name)
    b.failure_count += 1
    b.last_failure_time = time.time()
    b.last_error = error_msg[:200]

    if b.state == STATE_HALF_OPEN:
        # Failed during test -- reopen
        b.state = STATE_OPEN
        b.tripped_at = time.time()
        b.total_trips += 1
        _notify_tripped(module_name, error_msg)
        return

    if b.failure_count >= MAX_FAILURES and b.state == STATE_CLOSED:
        b.state = STATE_OPEN
        b.tripped_at = time.time()
        b.total_trips += 1
        _notify_tripped(module_name, error_msg)


def reset(module_name):
    """Manually reset a breaker."""
    with _lock:
        if module_name in _breakers:
            _breakers[module_name] = _BreakerState(module_name)


def get_all_states():
    """Get all breaker states for dashboard."""
    with _lock:
        result = {}
        for name, b in _breakers.items():
            result[name] = {
                "state": b.state,
                "failure_count": b.failure_count,
                "total_trips": b.total_trips,
                "last_error": b.last_error,
                "cooldown_remaining": max(0, round(COOLDOWN_SECONDS - (time.time() - b.tripped_at))) if b.state == STATE_OPEN else 0,
            }
        return result


def get_tripped():
    """Get list of currently tripped (disabled) modules."""
    with _lock:
        return [name for name, b in _breakers.items() if b.state == STATE_OPEN]


def _notify_tripped(module_name, error_msg):
    """Create alert when breaker trips."""
    try:
        from self_healer.alert_system import create_alert, SEVERITY_WARNING, CAT_MODULE
        create_alert(
            title="Circuit Breaker: " + module_name,
            message="Module '" + module_name + "' disabled after " + str(MAX_FAILURES) + " consecutive failures. Last error: " + error_msg[:100] + ". Will retry in " + str(COOLDOWN_SECONDS) + "s.",
            severity=SEVERITY_WARNING,
            category=CAT_MODULE,
            source="circuit_breaker",
            auto_resolve_seconds=COOLDOWN_SECONDS,
        )
    except Exception:
        pass


def _notify_recovered(module_name):
    """Create alert when module recovers."""
    try:
        from self_healer.alert_system import create_alert, SEVERITY_INFO
        create_alert(
            title="Module Recovered: " + module_name,
            message="Module '" + module_name + "' is working again after circuit breaker cooldown.",
            severity=SEVERITY_INFO,
            category="module",
            source="circuit_breaker",
            auto_resolve_seconds=60,
        )
    except Exception:
        pass
