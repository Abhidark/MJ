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
# SYSTEM SERVICE MANAGER (V23 → 75%)
# ========================

SERVICES_FILE = DATA_DIR / "os_services.json"

class SystemServiceManager:
    """Manage system services — auto-start, health, dependencies."""

    DEFAULT_SERVICES = {
        "zeus_brain": {"name": "Zeus Brain", "type": "core", "auto_start": True, "priority": 1},
        "memory_engine": {"name": "Memory Engine", "type": "core", "auto_start": True, "priority": 2},
        "model_router": {"name": "Model Router", "type": "core", "auto_start": True, "priority": 3},
        "workflow_engine": {"name": "Workflow Engine", "type": "intelligence", "auto_start": True, "priority": 5},
        "plugin_loader": {"name": "Plugin Loader", "type": "extension", "auto_start": True, "priority": 8},
        "health_monitor": {"name": "Health Monitor", "type": "system", "auto_start": True, "priority": 4},
        "self_healer": {"name": "Self-Healer", "type": "system", "auto_start": False, "priority": 9},
        "event_bus": {"name": "Event Bus", "type": "core", "auto_start": True, "priority": 2},
    }

    def __init__(self):
        self.services: dict = {}
        self._load()

    def _load(self):
        self.services = _load_json(SERVICES_FILE, {})
        if not self.services:
            for sid, svc in self.DEFAULT_SERVICES.items():
                self.services[sid] = {
                    **svc, "id": sid, "status": "stopped",
                    "started_at": None, "restarts": 0,
                }
            self._save()

    def _save(self):
        _save_json(SERVICES_FILE, self.services)

    def start_service(self, service_id: str) -> dict:
        svc = self.services.get(service_id)
        if not svc:
            return {"error": f"Service '{service_id}' not found"}
        svc["status"] = "running"
        svc["started_at"] = datetime.now().isoformat()
        self._save()
        return {"success": True, "service": svc["name"], "status": "running"}

    def stop_service(self, service_id: str) -> dict:
        svc = self.services.get(service_id)
        if not svc:
            return {"error": "Not found"}
        svc["status"] = "stopped"
        svc["started_at"] = None
        self._save()
        return {"success": True, "service": svc["name"], "status": "stopped"}

    def restart_service(self, service_id: str) -> dict:
        svc = self.services.get(service_id)
        if not svc:
            return {"error": "Not found"}
        svc["status"] = "running"
        svc["started_at"] = datetime.now().isoformat()
        svc["restarts"] = svc.get("restarts", 0) + 1
        self._save()
        return {"success": True, "restarts": svc["restarts"]}

    def list_services(self) -> dict:
        items = sorted(self.services.values(), key=lambda x: x.get("priority", 99))
        running = sum(1 for s in items if s.get("status") == "running")
        return {"services": items, "running": running, "total": len(items)}

    def auto_start_all(self) -> dict:
        started = []
        for sid, svc in sorted(self.services.items(), key=lambda x: x[1].get("priority", 99)):
            if svc.get("auto_start") and svc.get("status") != "running":
                svc["status"] = "running"
                svc["started_at"] = datetime.now().isoformat()
                started.append(svc["name"])
        self._save()
        return {"started": started, "total": len(started)}


# ========================
# APP REGISTRY (V23 → 75%)
# ========================

APP_REGISTRY_FILE = DATA_DIR / "os_app_registry.json"

class AppRegistry:
    """Registry of installed apps/modules within the AI OS."""

    def __init__(self):
        self.apps: dict = {}
        self._load()

    def _load(self):
        self.apps = _load_json(APP_REGISTRY_FILE, {})

    def _save(self):
        _save_json(APP_REGISTRY_FILE, self.apps)

    def register_app(self, app_id: str, name: str, app_type: str, version: str = "1.0.0",
                     permissions: list = None) -> dict:
        self.apps[app_id] = {
            "id": app_id, "name": name, "type": app_type,
            "version": version, "permissions": permissions or [],
            "installed": datetime.now().isoformat(),
            "launches": 0, "last_used": None,
        }
        self._save()
        return {"success": True, "app": self.apps[app_id]}

    def launch_app(self, app_id: str) -> dict:
        if app_id not in self.apps:
            return {"error": "App not registered"}
        self.apps[app_id]["launches"] = self.apps[app_id].get("launches", 0) + 1
        self.apps[app_id]["last_used"] = datetime.now().isoformat()
        self._save()
        return {"success": True, "app": self.apps[app_id]}

    def list_apps(self, app_type: str = "") -> dict:
        items = list(self.apps.values())
        if app_type:
            items = [a for a in items if a.get("type") == app_type]
        return {"apps": items, "total": len(items)}

    def unregister_app(self, app_id: str) -> dict:
        if app_id not in self.apps:
            return {"error": "Not found"}
        del self.apps[app_id]
        self._save()
        return {"success": True}


# ========================
# CROSS-DEVICE SYNC STUB (V23 → 75%)
# ========================

SYNC_FILE = DATA_DIR / "os_sync_state.json"

class CrossDeviceSync:
    """Cross-device sync stub — tracks sync state and pending changes."""

    def __init__(self):
        self.sync_state: dict = {}
        self._load()

    def _load(self):
        self.sync_state = _load_json(SYNC_FILE, {
            "devices": {},
            "pending_changes": [],
            "last_sync": None,
            "sync_enabled": False,
        })

    def _save(self):
        _save_json(SYNC_FILE, self.sync_state)

    def register_device(self, device_id: str, device_name: str, device_type: str = "pc") -> dict:
        self.sync_state["devices"][device_id] = {
            "name": device_name, "type": device_type,
            "registered": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "status": "online",
        }
        self._save()
        return {"success": True, "device": self.sync_state["devices"][device_id]}

    def queue_change(self, change_type: str, data: dict) -> dict:
        self.sync_state["pending_changes"].append({
            "type": change_type, "data": data,
            "ts": datetime.now().isoformat(), "synced": False,
        })
        if len(self.sync_state["pending_changes"]) > 100:
            self.sync_state["pending_changes"] = self.sync_state["pending_changes"][-100:]
        self._save()
        return {"queued": True, "pending": len(self.sync_state["pending_changes"])}

    def get_sync_status(self) -> dict:
        return {
            "devices": self.sync_state["devices"],
            "pending_changes": len(self.sync_state.get("pending_changes", [])),
            "last_sync": self.sync_state.get("last_sync"),
            "sync_enabled": self.sync_state.get("sync_enabled", False),
            "status": "stub_mode",
        }

    def trigger_sync(self) -> dict:
        """Trigger sync (stub — marks changes as synced)."""
        pending = self.sync_state.get("pending_changes", [])
        synced = 0
        for change in pending:
            if not change.get("synced"):
                change["synced"] = True
                synced += 1
        self.sync_state["last_sync"] = datetime.now().isoformat()
        self._save()
        return {"synced": synced, "status": "stub_sync_complete"}


# ========================
# CLOUD SYNC ENGINE
# ========================

class CloudSyncEngine:
    """Cloud backup sync engine — supports s3/gcs/azure stubs."""

    CLOUD_FILE = DATA_DIR / "os_cloud_sync.json"

    def __init__(self):
        self.state: dict = {}
        self._load()

    def _load(self):
        self.state = _load_json(self.CLOUD_FILE, {
            "config": {},
            "uploads": [],
            "last_upload": None,
        })

    def _save(self):
        _save_json(self.CLOUD_FILE, self.state)

    def configure(self, provider: str, bucket: str, credentials_ref: str) -> dict:
        """Configure cloud sync provider (s3/gcs/azure stub)."""
        if provider not in ("s3", "gcs", "azure"):
            return {"error": f"Unsupported provider: {provider}. Use s3, gcs, or azure."}
        self.state["config"] = {
            "provider": provider,
            "bucket": bucket,
            "credentials_ref": credentials_ref,
            "configured_at": datetime.now().isoformat(),
        }
        self._save()
        return {"success": True, "provider": provider, "bucket": bucket}

    def upload_backup(self, data_type: str, content: str) -> dict:
        """Stub: logs an upload entry with timestamp, data_type, size."""
        entry = {
            "id": f"upload_{int(time.time())}_{hashlib.md5(data_type.encode()).hexdigest()[:6]}",
            "data_type": data_type,
            "size": len(content) if content else 0,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
        }
        self.state["uploads"].append(entry)
        if len(self.state["uploads"]) > 200:
            self.state["uploads"] = self.state["uploads"][-200:]
        self.state["last_upload"] = entry["timestamp"]
        self._save()
        return {"success": True, "upload": entry}

    def download_backup(self, data_type: str) -> dict:
        """Stub: returns stub mode response for download."""
        return {"status": "stub_mode", "data_type": data_type}

    def get_cloud_status(self) -> dict:
        """Returns config, last_upload, total_uploads."""
        return {
            "config": self.state.get("config", {}),
            "last_upload": self.state.get("last_upload"),
            "total_uploads": len(self.state.get("uploads", [])),
        }

    def list_backups(self) -> list:
        """Returns list of logged upload entries."""
        return self.state.get("uploads", [])


# ========================
# SYSTEM BACKUP / RESTORE
# ========================

class SystemBackupManager:
    """System backup and restore manager."""

    BACKUP_FILE = DATA_DIR / "os_backups.json"

    def __init__(self):
        self.state: dict = {}
        self._load()

    def _load(self):
        self.state = _load_json(self.BACKUP_FILE, {
            "backups": {},
            "auto_backup": {
                "enabled": False,
                "frequency": "daily",
                "include": [],
            },
        })

    def _save(self):
        _save_json(self.BACKUP_FILE, self.state)

    def create_backup(self, name: str, include: list) -> dict:
        """Create a backup record with timestamp, included modules, status, size estimate."""
        backup_id = f"bak_{int(time.time())}_{hashlib.md5(name.encode()).hexdigest()[:6]}"
        size_estimate = len(include) * 50 * 1024  # 50KB per included item
        self.state["backups"][backup_id] = {
            "id": backup_id,
            "name": name,
            "include": include,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
            "size_estimate": size_estimate,
            "restored_at": None,
        }
        self._save()
        return {"success": True, "backup_id": backup_id, "size_estimate": size_estimate}

    def list_backups(self) -> dict:
        """Return all backups sorted by timestamp desc."""
        items = sorted(
            self.state.get("backups", {}).values(),
            key=lambda x: x.get("timestamp", ""),
            reverse=True,
        )
        return {"backups": items, "total": len(items)}

    def get_backup(self, backup_id: str) -> dict:
        """Get single backup record."""
        return self.state.get("backups", {}).get(backup_id, {"error": "Backup not found"})

    def restore_backup(self, backup_id: str) -> dict:
        """Stub: marks backup as restored_at, returns status."""
        backups = self.state.get("backups", {})
        if backup_id not in backups:
            return {"error": "Backup not found"}
        backups[backup_id]["restored_at"] = datetime.now().isoformat()
        self._save()
        return {"success": True, "backup_id": backup_id, "status": "restored"}

    def delete_backup(self, backup_id: str) -> dict:
        """Remove backup record."""
        backups = self.state.get("backups", {})
        if backup_id not in backups:
            return {"error": "Backup not found"}
        del backups[backup_id]
        self._save()
        return {"success": True}

    def get_auto_backup_config(self) -> dict:
        """Returns auto-backup settings."""
        return self.state.get("auto_backup", {
            "enabled": False,
            "frequency": "daily",
            "include": [],
        })

    def set_auto_backup(self, enabled: bool, frequency: str, include: list) -> dict:
        """Configure auto-backup schedule."""
        self.state["auto_backup"] = {
            "enabled": enabled,
            "frequency": frequency,
            "include": include,
            "updated_at": datetime.now().isoformat(),
        }
        self._save()
        return {"success": True, "auto_backup": self.state["auto_backup"]}


# ========================
# NOTIFICATION RULES ENGINE
# ========================

class NotificationRules:
    """Notification rules engine — trigger actions on events."""

    RULES_FILE = DATA_DIR / "os_notification_rules.json"

    def __init__(self):
        self.state: dict = {}
        self._load()

    def _load(self):
        self.state = _load_json(self.RULES_FILE, {
            "rules": {},
            "history": [],
        })

    def _save(self):
        _save_json(self.RULES_FILE, self.state)

    def add_rule(self, name: str, event_type: str, condition: str,
                 action: str, target: str) -> dict:
        """Add a notification rule (e.g., when error count > 5, notify admin)."""
        rule_id = f"rule_{int(time.time())}_{hashlib.md5(name.encode()).hexdigest()[:6]}"
        self.state["rules"][rule_id] = {
            "id": rule_id,
            "name": name,
            "event_type": event_type,
            "condition": condition,
            "action": action,
            "target": target,
            "created": datetime.now().isoformat(),
            "enabled": True,
            "trigger_count": 0,
        }
        self._save()
        return {"success": True, "rule_id": rule_id}

    def remove_rule(self, rule_id: str) -> dict:
        """Delete rule."""
        rules = self.state.get("rules", {})
        if rule_id not in rules:
            return {"error": "Rule not found"}
        del rules[rule_id]
        self._save()
        return {"success": True}

    def list_rules(self) -> dict:
        """List all rules."""
        items = list(self.state.get("rules", {}).values())
        return {"rules": items, "total": len(items)}

    def evaluate(self, event_type: str, event_data: dict) -> dict:
        """Stub: checks if any rule matches event_type, returns list of triggered rules."""
        triggered = []
        for rule in self.state.get("rules", {}).values():
            if rule.get("event_type") == event_type and rule.get("enabled"):
                rule["trigger_count"] = rule.get("trigger_count", 0) + 1
                triggered.append({
                    "rule_id": rule["id"],
                    "name": rule["name"],
                    "action": rule["action"],
                    "target": rule["target"],
                })
                # Log to history
                self.state["history"].append({
                    "rule_id": rule["id"],
                    "event_type": event_type,
                    "event_data": event_data,
                    "timestamp": datetime.now().isoformat(),
                })
        # Keep history bounded
        if len(self.state["history"]) > 500:
            self.state["history"] = self.state["history"][-500:]
        self._save()
        return {"triggered": triggered, "total_matched": len(triggered)}

    def get_rule_history(self, limit: int = 20) -> dict:
        """Recent rule trigger history."""
        history = self.state.get("history", [])
        recent = history[-limit:] if limit else history
        recent = list(reversed(recent))
        return {"history": recent, "total": len(history)}


# ========================
# SYSTEM MONITOR
# ========================

class SystemMonitor:
    """System metrics monitor — records and retrieves metric data points."""

    MONITOR_FILE = DATA_DIR / "os_system_monitor.json"

    def __init__(self):
        self.state: dict = {}
        self._load()

    def _load(self):
        self.state = _load_json(self.MONITOR_FILE, {
            "metrics": {},
        })

    def _save(self):
        _save_json(self.MONITOR_FILE, self.state)

    def record_metric(self, name: str, value: float, unit: str) -> dict:
        """Record a metric data point with timestamp. Keeps last 200 per name."""
        if name not in self.state["metrics"]:
            self.state["metrics"][name] = []
        self.state["metrics"][name].append({
            "value": value,
            "unit": unit,
            "timestamp": datetime.now().isoformat(),
        })
        # Keep last 200 per metric name
        if len(self.state["metrics"][name]) > 200:
            self.state["metrics"][name] = self.state["metrics"][name][-200:]
        self._save()
        return {"success": True, "name": name, "value": value, "unit": unit}

    def get_metrics(self, name: str, limit: int = 50) -> dict:
        """Get recent metrics for a name."""
        points = self.state.get("metrics", {}).get(name, [])
        recent = points[-limit:] if limit else points
        return {"name": name, "data": recent, "total": len(points)}

    def get_all_metric_names(self) -> dict:
        """List all recorded metric names."""
        names = list(self.state.get("metrics", {}).keys())
        return {"names": names, "total": len(names)}

    def get_summary(self) -> dict:
        """Returns per-metric: latest value, min, max, avg of last 50."""
        summary = {}
        for name, points in self.state.get("metrics", {}).items():
            recent = points[-50:]
            values = [p["value"] for p in recent if isinstance(p.get("value"), (int, float))]
            if values:
                summary[name] = {
                    "latest": values[-1],
                    "min": min(values),
                    "max": max(values),
                    "avg": round(sum(values) / len(values), 4),
                    "count": len(values),
                    "unit": recent[-1].get("unit", ""),
                }
            else:
                summary[name] = {"latest": None, "count": 0}
        return {"summary": summary, "total_metrics": len(summary)}


# ========================
# SINGLETONS
# ========================

user_manager = UserManager()
session_manager = SessionManager()
permission_engine = PermissionEngine()
api_gateway = APIGateway()
bg_task_runner = BackgroundTaskRunner()
service_manager = SystemServiceManager()
app_registry = AppRegistry()
cross_device_sync = CrossDeviceSync()
cloud_sync = CloudSyncEngine()
backup_manager = SystemBackupManager()
notification_rules = NotificationRules()
system_monitor = SystemMonitor()


def get_os_status() -> dict:
    """Get overall AI OS status."""
    return {
        "users": user_manager.list_users(),
        "sessions": session_manager.get_active_sessions(),
        "api_gateway": api_gateway.get_gateway_stats(),
        "background_tasks": bg_task_runner.get_stats(),
        "services": service_manager.list_services(),
        "apps": app_registry.list_apps(),
        "sync": cross_device_sync.get_sync_status(),
        "cloud_sync": cloud_sync.get_cloud_status(),
        "backups": backup_manager.list_backups(),
        "notification_rules": notification_rules.list_rules(),
        "system_monitor": system_monitor.get_summary(),
        "roles": list(ROLES.keys()),
    }
