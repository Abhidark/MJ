"""
MJ Auth System — Simple token-based authentication.
Protects the assistant from unauthorized access.

Default password: "jarvis" (user should change via /auth/change-password)
Stores hashed password in auth_config.json.
Sessions use random tokens stored in memory (cleared on restart).
"""

import json
import hashlib
import secrets
import time
from pathlib import Path
from typing import Optional

AUTH_FILE = Path(__file__).parent / "auth_config.json"
DEFAULT_PASSWORD = "jarvis"

# Active sessions: {token: {"created": timestamp, "last_active": timestamp}}
_sessions: dict = {}

# Session expires after 24 hours of inactivity
SESSION_TIMEOUT = 24 * 60 * 60  # 24 hours


def _hash_password(password: str) -> str:
    """Hash password with SHA-256 + salt."""
    salt = "mj_jarvis_2024"
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


def _load_auth_config() -> dict:
    """Load auth config from file."""
    if AUTH_FILE.exists():
        try:
            return json.loads(AUTH_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_auth_config(config: dict):
    """Save auth config to file."""
    AUTH_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def is_auth_enabled() -> bool:
    """Check if auth is enabled. Disabled by default — user enables from Security panel."""
    config = _load_auth_config()
    return config.get("enabled", False)


def setup_default_password():
    """Create default auth config if none exists. Auth disabled by default."""
    if not AUTH_FILE.exists():
        config = {
            "enabled": False,
            "password_hash": _hash_password(DEFAULT_PASSWORD),
            "created": time.time(),
        }
        _save_auth_config(config)
    else:
        # Migration: if config exists but was created before disable-by-default change,
        # and user never explicitly toggled it, disable auth
        config = _load_auth_config()
        if "user_toggled" not in config:
            config["enabled"] = False
            _save_auth_config(config)


def verify_password(password: str) -> bool:
    """Check if password matches stored hash."""
    config = _load_auth_config()
    stored_hash = config.get("password_hash", _hash_password(DEFAULT_PASSWORD))
    return _hash_password(password) == stored_hash


def change_password(old_password: str, new_password: str) -> dict:
    """Change password. Requires old password verification."""
    if not verify_password(old_password):
        return {"success": False, "message": "Current password is wrong"}
    if len(new_password) < 4:
        return {"success": False, "message": "Password must be at least 4 characters"}

    config = _load_auth_config()
    config["password_hash"] = _hash_password(new_password)
    config["updated"] = time.time()
    _save_auth_config(config)

    # Invalidate all sessions (force re-login)
    _sessions.clear()
    return {"success": True, "message": "Password changed. Please login again."}


def create_session() -> str:
    """Create a new session token."""
    token = secrets.token_hex(32)
    _sessions[token] = {
        "created": time.time(),
        "last_active": time.time(),
    }
    return token


def validate_session(token: str) -> bool:
    """Check if session token is valid and not expired."""
    if not token or token not in _sessions:
        return False

    session = _sessions[token]
    now = time.time()

    # Check timeout
    if now - session["last_active"] > SESSION_TIMEOUT:
        del _sessions[token]
        return False

    # Update last active
    session["last_active"] = now
    return True


def invalidate_session(token: str):
    """Logout — remove session."""
    _sessions.pop(token, None)


def cleanup_expired_sessions():
    """Remove all expired sessions."""
    now = time.time()
    expired = [t for t, s in _sessions.items() if now - s["last_active"] > SESSION_TIMEOUT]
    for t in expired:
        del _sessions[t]


def get_session_count() -> int:
    """Return number of active sessions."""
    cleanup_expired_sessions()
    return len(_sessions)


def toggle_auth(enabled: bool, password: str) -> dict:
    """Enable or disable auth. Requires password to disable."""
    if not verify_password(password):
        return {"success": False, "message": "Wrong password"}

    config = _load_auth_config()
    config["enabled"] = enabled
    config["user_toggled"] = True
    _save_auth_config(config)
    return {"success": True, "message": f"Auth {'enabled' if enabled else 'disabled'}"}
