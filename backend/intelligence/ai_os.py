"""
MJ AI Operating System (V23)
Adds: multi-user, API gateway, role-based permissions,
session management, background task runner.
"""

import json
import time
import hashlib
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "os_users.json"
SESSIONS_FILE = DATA_DIR / "os_sessions.json"
PERMISSIONS_FILE = DATA_DIR / "os_permissions.json"
BG_TASKS_FILE = DATA_DIR / "os_bg_tasks.json"
API_KEYS_FILE = DATA_DIR / "os_api_keys.json"
GATEWAY_LOG_FILE = DATA_DIR / "os_gateway_log.json"


def _load_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def _save_json(path, data):
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# ========================
# USER MANAGEMENT
# ========================

ROLES = {
    "admin": {
        "level": 100,
        "permissions": ["*"],
        "description": "Full system access",
    },
    "power_user": {
        "level": 75,
        "permissions": [
            "chat", "memory", "tools", "plugins", "workflows",
            "agents", "calendar", "settings_self",
        ],
        "description": "All features except admin settings",
    },
    "user": {
        "level": 50,
        "permissions": [
            "chat", "memory", "tools", "calendar", "settings_self",
        ],
        "description": "Standard user access",
    },
    "guest": {
        "level": 10,
        "permissions": ["chat"],
        "description": "Chat only, no tools or memory",
    },
}


class UserManager:
    """Multi-user management with roles and profiles."""

    def __init__(self):
        self.users: dict = {}
        self._load()

    def _load(self):
        self.users = _load_json(USERS_FILE, {})
        if not self.users:
            # Create default admin user
            self.create_user("admin", "MJ Admin", "admin", is_default=True)

    def _save(self):
        _save_json(USERS_FILE, self.users)

    def create_user(self, username: str, display_name: str, role: str = "user",
                    is_default: bool = False) -> dict:
        if username in self.users:
            return {"success": False, "error": f"User '{username}' already exists"}
        if role not in ROLES:
            return {"success": False, "error": f"Invalid role: {role}"}

        self.users[username] = {
            "username": username,
            "display_name": display_name,
            "role": role,
            "created": datetime.now().isoformat(),
            "last_login": None,
            "is_default": is_default,
            "preferences": {},
            "stats": {"total_queries": 0, "total_sessions": 0},
        }
        self._save()
        return {"success": True, "user": self.users[username]}

    def get_user(self, username: str) -> dict:
        return self.users.get(username, {"error": "User not found"})

    def list_users(self) -> dict:
        users = [
            {"username": u["username"], "display_name": u["display_name"],
             "role": u["role"], "last_login": u.get("last_login")}
            for u in self.users.values()
        ]
        return {"users": users, "total": len(users), "roles": list(ROLES.keys())}

    def update_role(self, username: str, new_role: str) -> dict:
        if username not in self.users:
            return {"error": "User not found"}
        if new_role not in ROLES:
            return {"error": f"Invalid role: {new_role}"}
        self.users[username]["role"] = new_role
        self._save()
        return {"success": True, "username": username, "new_role": new_role}

    def delete_user(self, username: str) -> dict:
        if username not in self.users:
            return {"error": "User not found"}
        if self.users[username].get("is_default"):
            return {"error": "Cannot delete default admin user"}
        del self.users[username]
        self._save()
        return {"success": True}


# ========================
# SESSION MANAGEMENT
# ========================

class SessionManager:
    """Manage user sessions with token-based auth."""

    def __init__(self):
        self.sessions: dict = {}
        self._load()

    def _load(self):
        self.sessions = _load_json(SESSIONS_FILE, {})

    def _save(self):
        _save_json(SESSIONS_FILE, self.sessions)

    def create_session(self, username: str) -> dict:
        token = str(uuid.uuid4())
        self.sessions[token] = {
            "username": username,
            "created": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "expires_in": 3600 * 24,  # 24h
            "active": True,
        }
        self._save()
        return {"token": token, "username": username, "expires_in": "24h"}

    def validate_session(self, token: str) -> dict:
        session = self.sessions.get(token)
        if not session:
            return {"valid": False, "error": "Session not found"}
        if not session.get("active"):
            return {"valid": False, "error": "Session expired"}
        session["last_active"] = datetime.now().isoformat()
        self._save()
        return {"valid": True, "username": session["username"]}

    def end_session(self, token: str) -> dict:
        if token in self.sessions:
            self.sessions[token]["active"] = False
            self._save()
            return {"success": True}
        return {"error": "Session not found"}

    def get_active_sessions(self) -> dict:
        active = [
            {"token": t[:8] + "...", "username": s["username"],
             "last_active": s["last_active"]}
            for t, s in self.sessions.items() if s.get("active")
        ]
        return {"active_sessions": active, "total": len(active)}

    def cleanup_expired(self, max_age_hours: int = 24) -> dict:
        cutoff = time.time() - (max_age_hours * 3600)
        cleaned = 0
        for token, session in list(self.sessions.items()):
            try:
                created_ts = datetime.fromisoformat(session["created"]).timestamp()
                if created_ts < cutoff:
                    session["active"] = False
                    cleaned += 1
            except Exception:
                pass
        self._save()
        return {"cleaned": cleaned}


# ========================
# PERMISSION ENGINE
# ========================

class PermissionEngine:
    """Role-based access control for modules and features."""

    def __init__(self):
        self.overrides: dict = {}
        self._load()

    def _load(self):
        self.overrides = _load_json(PERMISSIONS_FILE, {})

    def _save(self):
        _save_json(PERMISSIONS_FILE, self.overrides)

    def check_permission(self, username: str, permission: str, user_role: str = "user") -> dict:
        # Check overrides first
        user_overrides = self.overrides.get(username, {})
        if permission in user_overrides:
            return {"allowed": user_overrides[permission], "source": "override"}

        # Check role permissions
        role = ROLES.get(user_role, ROLES["guest"])
        if "*" in role["permissions"]:
            return {"allowed": True, "source": "role_wildcard"}
        allowed = permission in role["permissions"]
        return {"allowed": allowed, "source": "role", "role": user_role}

    def set_override(self, username: str, permission: str, allowed: bool) -> dict:
        if username not in self.overrides:
            self.overrides[username] = {}
        self.overrides[username][permission] = allowed
        self._save()
        return {"success": True, "username": username, "permission": permission, "allowed": allowed}

    def get_user_permissions(self, username: str, role: str = "user") -> dict:
        role_perms = ROLES.get(role, ROLES["guest"])["permissions"]
        overrides = self.overrides.get(username, {})
        return {
            "role": role,
            "role_permissions": role_perms,
            "overrides": overrides,
            "effective": list(set(role_perms) | set(k for k, v in overrides.items() if v)),
        }

    def get_all_roles(self) -> dict:
        return {"roles": ROLES}


# ========================
# API GATEWAY
# ========================

class APIGateway:
    """API key management and rate limiting."""

    def __init__(self):
        self.api_keys: dict = {}
        self.request_log: list = []
        self._load()

    def _load(self):
        self.api_keys = _load_json(API_KEYS_FILE, {})
        self.request_log = _load_json(GATEWAY_LOG_FILE, [])
        if not isinstance(self.request_log, list):
            self.request_log = []

    def _save_keys(self):
        _save_json(API_KEYS_FILE, self.api_keys)

    def _save_log(self):
        _save_json(GATEWAY_LOG_FILE, self.request_log[-500:])

    def create_api_key(self, name: str, username: str, rate_limit: int = 100) -> dict:
        """Create an API key for external access."""
        key = f"mj_{hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]}"
        self.api_keys[key[:12]] = {
            "name": name,
            "key_preview": key[:12] + "...",
            "username": username,
            "rate_limit_per_hour": rate_limit,
            "created": datetime.now().isoformat(),
            "requests_today": 0,
            "active": True,
        }
        self._save_keys()
        return {"success": True, "key": key, "name": name, "rate_limit": rate_limit}

    def validate_key(self, key_prefix: str) -> dict:
        info = self.api_keys.get(key_prefix[:12])
        if not info:
            return {"valid": False, "error": "Invalid API key"}
        if not info.get("active"):
            return {"valid": False, "error": "API key disabled"}

        # Check rate limit
        if info.get("requests_today", 0) >= info.get("rate_limit_per_hour", 100):
            return {"valid": False, "error": "Rate limit exceeded"}

        info["requests_today"] = info.get("requests_today", 0) + 1
        self._save_keys()
        return {"valid": True, "username": info["username"], "name": info["name"]}

    def log_request(self, key_prefix: str, endpoint: str, status: int = 200) -> dict:
        entry = {
            "key": key_prefix[:8] + "...",
            "endpoint": endpoint,
            "status": status,
            "ts": time.time(),
        }
        self.request_log.append(entry)
        self._save_log()
        return {"logged": True}

    def get_api_keys(self) -> dict:
        keys = [
            {"name": v["name"], "key_preview": v["key_preview"],
             "username": v["username"], "active": v["active"],
             "requests_today": v.get("requests_today", 0)}
            for v in self.api_keys.values()
        ]
        return {"keys": keys, "total": len(keys)}

    def revoke_key(self, key_prefix: str) -> dict:
        info = self.api_keys.get(key_prefix[:12])
        if not info:
            return {"error": "Key not found"}
        info["active"] = False
        self._save_keys()
        return {"success": True, "revoked": info["name"]}

    def get_gateway_stats(self) -> dict:
        cutoff = time.time() - 3600
        recent = [r for r in self.request_log if r.get("ts", 0) > cutoff]
        return {
            "total_keys": len(self.api_keys),
            "active_keys": sum(1 for k in self.api_keys.values() if k.get("active")),
            "requests_last_hour": len(recent),
            "total_requests": len(self.request_log),
        }


# ========================
# BACKGROUND TASK RUNNER
# ========================

class BackgroundTaskRunner:
    """Manage and track background tasks."""

    def __init__(self):
        self.tasks: dict = {}
        self._load()

    def _load(self):
        self.tasks = _load_json(BG_TASKS_FILE, {})

    def _save(self):
        _save_json(BG_TASKS_FILE, self.tasks)

    def submit_task(self, name: str, task_type: str, params: dict = None) -> dict:
        tid = f"bg_{int(time.time())}_{hashlib.md5(name.encode()).hexdigest()[:6]}"
        self.tasks[tid] = {
            "id": tid,
            "name": name,
            "type": task_type,
            "params": params or {},
            "status": "queued",
            "progress": 0,
            "submitted": datetime.now().isoformat(),
            "started": None,
            "completed": None,
            "result": None,
            "error": None,
        }
        self._save()
        return {"success": True, "task_id": tid, "status": "queued"}

    def update_task(self, task_id: str, status: str = "", progress: float = 0,
                    result: dict = None, error: str = "") -> dict:
        if task_id not in self.tasks:
            return {"error": "Task not found"}
        t = self.tasks[task_id]
        if status:
            t["status"] = status
        if progress:
            t["progress"] = min(100, progress)
        if status == "running" and not t["started"]:
            t["started"] = datetime.now().isoformat()
        if status in ("completed", "failed"):
            t["completed"] = datetime.now().isoformat()
        if result:
            t["result"] = result
        if error:
            t["error"] = error
        self._save()
        return {"success": True, "task": t}

    def get_task(self, task_id: str) -> dict:
        return self.tasks.get(task_id, {"error": "Not found"})

    def list_tasks(self, status: str = "") -> dict:
        items = list(self.tasks.values())
        if status:
            items = [t for t in items if t.get("status") == status]
        items.sort(key=lambda x: x.get("submitted", ""), reverse=True)
        return {"tasks": items[:30], "total": len(items)}

    def cancel_task(self, task_id: str) -> dict:
        if task_id not in self.tasks:
            return {"error": "Not found"}
        self.tasks[task_id]["status"] = "cancelled"
        self.tasks[task_id]["completed"] = datetime.now().isoformat()
        self._save()
        return {"success": True}

    def get_stats(self) -> dict:
        statuses = {}
        for t in self.tasks.values():
            s = t.get("status", "unknown")
            statuses[s] = statuses.get(s, 0) + 1
        return {
            "total": len(self.tasks),
            "by_status": statuses,
            "running": statuses.get("running", 0),
            "queued": statuses.get("queued", 0),
        }


# ========================
# SINGLETONS
# ========================

user_manager = UserManager()
session_manager = SessionManager()
permission_engine = PermissionEngine()
api_gateway = APIGateway()
bg_task_runner = BackgroundTaskRunner()


def get_os_status() -> dict:
    """Get overall AI OS status."""
    return {
        "users": user_manager.list_users(),
        "sessions": session_manager.get_active_sessions(),
        "api_gateway": api_gateway.get_gateway_stats(),
        "background_tasks": bg_task_runner.get_stats(),
        "roles": list(ROLES.keys()),
    }
