"""
MJ Intelligence: Sentinel Security Engine (V15)
- Permissions System: role-based access control for modules and actions
- Secrets Vault: encrypted storage for API keys, tokens, credentials
- Audit Logs: track all security-relevant events with timestamps
- Threat Detection: detect brute force, injection, suspicious patterns
"""

import json
import time
import re
import logging
import hashlib
import hmac
import secrets
import base64
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict

logger = logging.getLogger("mj.sentinel")

DATA_DIR = Path(__file__).parent.parent / "security_data"
DATA_DIR.mkdir(exist_ok=True)

PERMISSIONS_FILE = DATA_DIR / "permissions.json"
VAULT_FILE = DATA_DIR / "vault.enc.json"
AUDIT_FILE = DATA_DIR / "audit_log.json"
THREATS_FILE = DATA_DIR / "threats.json"
CONFIG_FILE = DATA_DIR / "sentinel_config.json"


class SentinelEngine:
    """
    Full security layer for MJ — permissions, secrets, audit, threats.
    Runs locally, no external dependencies.
    """

    def __init__(self):
        self.config: Dict = self._load(CONFIG_FILE, {
            "max_login_attempts": 5,
            "lockout_minutes": 15,
            "audit_retention_days": 30,
            "threat_sensitivity": "medium",  # low, medium, high
            "auto_block_threats": True,
        })
        self.permissions: Dict = self._load(PERMISSIONS_FILE, {
            "roles": {
                "admin": {
                    "description": "Full access to all features",
                    "permissions": ["*"],
                },
                "user": {
                    "description": "Standard user access",
                    "permissions": [
                        "chat", "search", "knowledge", "weather",
                        "calculator", "notes", "reminders", "voice",
                    ],
                },
                "restricted": {
                    "description": "Limited access — read only",
                    "permissions": ["chat", "search", "weather"],
                },
            },
            "users": {
                "default": {"role": "admin", "created": time.time()},
            },
            "module_permissions": {},
            "blocked_actions": [],
        })
        self.vault: Dict = self._load(VAULT_FILE, {
            "secrets": {},
            "metadata": {},
        })
        self.audit_log: List[dict] = self._load(AUDIT_FILE, [])
        self.threats: Dict = self._load(THREATS_FILE, {
            "detected": [],
            "blocked_ips": [],
            "failed_attempts": {},
            "patterns": [],
        })

        # In-memory encryption key (derived from machine-specific data)
        self._vault_key = self._derive_key()

    # ========================
    # PERMISSIONS SYSTEM
    # ========================

    def check_permission(self, user: str, action: str, module: str = "") -> dict:
        """Check if a user has permission for an action."""
        user_data = self.permissions["users"].get(user, {})
        role = user_data.get("role", "user")
        role_data = self.permissions["roles"].get(role, {})
        perms = role_data.get("permissions", [])

        # Admin has everything
        if "*" in perms:
            self._audit("permission_check", user, f"Allowed: {action} (admin)", "allowed")
            return {"allowed": True, "role": role, "reason": "admin_access"}

        # Check blocked actions
        if action in self.permissions.get("blocked_actions", []):
            self._audit("permission_check", user, f"Blocked: {action}", "denied")
            return {"allowed": False, "role": role, "reason": "action_blocked"}

        # Check module-specific permissions
        if module and module in self.permissions.get("module_permissions", {}):
            mod_perms = self.permissions["module_permissions"][module]
            if action in mod_perms.get("denied", []):
                self._audit("permission_check", user, f"Denied by module: {module}/{action}", "denied")
                return {"allowed": False, "role": role, "reason": f"module_{module}_denied"}

        # Check role permissions
        allowed = action in perms or any(
            action.startswith(p.rstrip("*")) for p in perms if p.endswith("*")
        )

        status = "allowed" if allowed else "denied"
        self._audit("permission_check", user, f"{status}: {action}", status)

        return {
            "allowed": allowed,
            "role": role,
            "reason": "role_permission" if allowed else "insufficient_permissions",
        }

    def get_roles(self) -> Dict:
        return self.permissions["roles"]

    def create_role(self, name: str, description: str, permissions: List[str]) -> dict:
        """Create a new role."""
        if name in self.permissions["roles"]:
            return {"success": False, "message": f"Role '{name}' already exists"}

        self.permissions["roles"][name] = {
            "description": description,
            "permissions": permissions,
        }
        self._save(PERMISSIONS_FILE, self.permissions)
        self._audit("role_created", "system", f"Role created: {name}")
        return {"success": True, "message": f"Role '{name}' created", "role": name}

    def assign_role(self, user: str, role: str) -> dict:
        """Assign a role to a user."""
        if role not in self.permissions["roles"]:
            return {"success": False, "message": f"Role '{role}' not found"}

        if user not in self.permissions["users"]:
            self.permissions["users"][user] = {"created": time.time()}

        old_role = self.permissions["users"][user].get("role", "none")
        self.permissions["users"][user]["role"] = role
        self._save(PERMISSIONS_FILE, self.permissions)
        self._audit("role_assigned", "system", f"User '{user}': {old_role} -> {role}")
        return {"success": True, "message": f"User '{user}' assigned role '{role}'"}

    def block_action(self, action: str) -> dict:
        """Block a specific action globally."""
        if action not in self.permissions["blocked_actions"]:
            self.permissions["blocked_actions"].append(action)
            self._save(PERMISSIONS_FILE, self.permissions)
            self._audit("action_blocked", "system", f"Action blocked: {action}")
        return {"success": True, "message": f"Action '{action}' blocked"}

    def unblock_action(self, action: str) -> dict:
        """Unblock a specific action."""
        if action in self.permissions["blocked_actions"]:
            self.permissions["blocked_actions"].remove(action)
            self._save(PERMISSIONS_FILE, self.permissions)
            self._audit("action_unblocked", "system", f"Action unblocked: {action}")
        return {"success": True, "message": f"Action '{action}' unblocked"}

    def set_module_permission(self, module: str, denied_actions: List[str]) -> dict:
        """Set denied actions for a specific module."""
        self.permissions["module_permissions"][module] = {"denied": denied_actions}
        self._save(PERMISSIONS_FILE, self.permissions)
        self._audit("module_permission", "system", f"Module '{module}' denied: {denied_actions}")
        return {"success": True, "module": module, "denied": denied_actions}

    # ========================
    # SECRETS VAULT
    # ========================

    def store_secret(self, key: str, value: str, category: str = "general") -> dict:
        """Store a secret (encrypted at rest)."""
        encrypted = self._encrypt(value)
        self.vault["secrets"][key] = encrypted
        self.vault["metadata"][key] = {
            "category": category,
            "created": time.time(),
            "updated": time.time(),
            "access_count": 0,
        }
        self._save(VAULT_FILE, self.vault)
        self._audit("secret_stored", "system", f"Secret stored: {key} ({category})")
        return {"success": True, "message": f"Secret '{key}' stored securely", "key": key}

    def get_secret(self, key: str) -> dict:
        """Retrieve a secret."""
        if key not in self.vault["secrets"]:
            self._audit("secret_access", "system", f"Secret not found: {key}", "denied")
            return {"success": False, "message": f"Secret '{key}' not found"}

        encrypted = self.vault["secrets"][key]
        value = self._decrypt(encrypted)

        # Update access count
        if key in self.vault["metadata"]:
            self.vault["metadata"][key]["access_count"] = \
                self.vault["metadata"][key].get("access_count", 0) + 1
            self.vault["metadata"][key]["last_accessed"] = time.time()
            self._save(VAULT_FILE, self.vault)

        self._audit("secret_accessed", "system", f"Secret accessed: {key}")

        if value is None:
            return {"success": False, "message": f"Failed to decrypt secret '{key}'"}

        return {"success": True, "key": key, "value": value}

    def delete_secret(self, key: str) -> dict:
        """Delete a secret from the vault."""
        if key not in self.vault["secrets"]:
            return {"success": False, "message": f"Secret '{key}' not found"}

        del self.vault["secrets"][key]
        self.vault["metadata"].pop(key, None)
        self._save(VAULT_FILE, self.vault)
        self._audit("secret_deleted", "system", f"Secret deleted: {key}")
        return {"success": True, "message": f"Secret '{key}' deleted"}

    def list_secrets(self) -> dict:
        """List all secret keys with metadata (no values)."""
        entries = []
        for key, meta in self.vault.get("metadata", {}).items():
            entries.append({
                "key": key,
                "category": meta.get("category", "general"),
                "created": meta.get("created"),
                "access_count": meta.get("access_count", 0),
                "last_accessed": meta.get("last_accessed"),
            })
        return {
            "success": True,
            "secrets": entries,
            "count": len(entries),
        }

    def _encrypt(self, plaintext: str) -> str:
        """Simple XOR-based encryption (upgrade to Fernet on PC with cryptography)."""
        key_bytes = self._vault_key.encode("utf-8")
        plain_bytes = plaintext.encode("utf-8")
        encrypted = bytes(
            pb ^ key_bytes[i % len(key_bytes)]
            for i, pb in enumerate(plain_bytes)
        )
        return base64.b64encode(encrypted).decode("utf-8")

    def _decrypt(self, ciphertext: str) -> Optional[str]:
        """Decrypt a stored secret."""
        try:
            key_bytes = self._vault_key.encode("utf-8")
            encrypted = base64.b64decode(ciphertext)
            decrypted = bytes(
                eb ^ key_bytes[i % len(key_bytes)]
                for i, eb in enumerate(encrypted)
            )
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None

    def _derive_key(self) -> str:
        """Derive an encryption key from machine-specific data."""
        import platform
        machine_data = f"{platform.node()}-{platform.machine()}-MJ-SENTINEL-V15"
        return hashlib.sha256(machine_data.encode()).hexdigest()[:32]

    # ========================
    # AUDIT LOGS
    # ========================

    def _audit(self, event_type: str, user: str, detail: str,
               status: str = "info"):
        """Record an audit event."""
        entry = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "event": event_type,
            "user": user,
            "detail": detail,
            "status": status,
        }
        self.audit_log.append(entry)

        # Retention limit
        max_entries = 5000
        if len(self.audit_log) > max_entries:
            self.audit_log = self.audit_log[-max_entries:]

        self._save(AUDIT_FILE, self.audit_log)

    def get_audit_log(self, limit: int = 100, event_type: str = "",
                      user: str = "", status: str = "") -> List[dict]:
        """Query audit logs with optional filters."""
        logs = self.audit_log
        if event_type:
            logs = [l for l in logs if l.get("event") == event_type]
        if user:
            logs = [l for l in logs if l.get("user") == user]
        if status:
            logs = [l for l in logs if l.get("status") == status]
        return logs[-limit:]

    def get_audit_stats(self) -> dict:
        """Get audit log statistics."""
        if not self.audit_log:
            return {"total": 0, "by_event": {}, "by_status": {}}

        by_event = Counter(l.get("event", "") for l in self.audit_log)
        by_status = Counter(l.get("status", "") for l in self.audit_log)

        # Last 24h
        cutoff = time.time() - 86400
        recent = [l for l in self.audit_log if l.get("timestamp", 0) > cutoff]
        recent_by_event = Counter(l.get("event", "") for l in recent)

        return {
            "total": len(self.audit_log),
            "by_event": dict(by_event.most_common(20)),
            "by_status": dict(by_status),
            "last_24h": {
                "count": len(recent),
                "by_event": dict(recent_by_event.most_common(10)),
            },
            "oldest": self.audit_log[0].get("datetime", "") if self.audit_log else "",
            "newest": self.audit_log[-1].get("datetime", "") if self.audit_log else "",
        }

    def clear_old_audit_logs(self, days: int = 30) -> dict:
        """Remove audit logs older than N days."""
        cutoff = time.time() - (days * 86400)
        before = len(self.audit_log)
        self.audit_log = [l for l in self.audit_log if l.get("timestamp", 0) > cutoff]
        removed = before - len(self.audit_log)
        self._save(AUDIT_FILE, self.audit_log)
        return {"success": True, "removed": removed, "remaining": len(self.audit_log)}

    # ========================
    # THREAT DETECTION
    # ========================

    # Patterns that indicate security threats
    INJECTION_PATTERNS = [
        (r"(?:union\s+select|drop\s+table|delete\s+from|insert\s+into|update\s+set)", "sql_injection", "critical"),
        (r"<script[\s>]|javascript:|on\w+\s*=\s*[\"']", "xss_attempt", "high"),
        (r"\.\./\.\./|%2e%2e|/etc/passwd|/etc/shadow", "path_traversal", "high"),
        (r";\s*(rm|del|format|shutdown|reboot)\s", "command_injection", "critical"),
        (r"\b(exec|eval|system|os\.popen|subprocess)\s*\(", "code_injection", "critical"),
        (r"(\||\$\(|`)\s*(cat|ls|wget|curl|nc|netcat)\s", "shell_injection", "high"),
    ]

    SUSPICIOUS_PATTERNS = [
        (r"password\s*[:=]\s*\S+", "password_exposure", "medium"),
        (r"(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*\S+", "credential_exposure", "high"),
        (r"(BEGIN\s+(RSA|DSA|EC)\s+PRIVATE\s+KEY)", "private_key_exposure", "critical"),
        (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "credit_card_pattern", "high"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "ssn_pattern", "high"),
    ]

    BRUTE_FORCE_THRESHOLD = 5
    BRUTE_FORCE_WINDOW = 300  # 5 minutes

    def scan_input(self, text: str, source: str = "user") -> dict:
        """Scan input for security threats."""
        threats_found = []

        # Check injection patterns
        for pattern, threat_type, severity in self.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                threats_found.append({
                    "type": threat_type,
                    "severity": severity,
                    "pattern": pattern[:50],
                    "source": source,
                })

        # Check suspicious patterns
        for pattern, threat_type, severity in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                threats_found.append({
                    "type": threat_type,
                    "severity": severity,
                    "pattern": pattern[:50],
                    "source": source,
                })

        if threats_found:
            for threat in threats_found:
                threat["timestamp"] = time.time()
                threat["text_preview"] = text[:100]
                self.threats["detected"].append(threat)
                self._audit("threat_detected", source,
                            f"{threat['type']} ({threat['severity']})",
                            "warning")

            self.threats["detected"] = self.threats["detected"][-500:]
            self._save(THREATS_FILE, self.threats)

        return {
            "safe": len(threats_found) == 0,
            "threats": threats_found,
            "count": len(threats_found),
            "highest_severity": max(
                (t["severity"] for t in threats_found),
                key=lambda s: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(s, 0),
                default="none"
            ) if threats_found else "none",
        }

    def record_failed_attempt(self, identifier: str, action: str = "login") -> dict:
        """Record a failed authentication/access attempt."""
        now = time.time()
        key = f"{identifier}:{action}"

        if key not in self.threats["failed_attempts"]:
            self.threats["failed_attempts"][key] = []

        self.threats["failed_attempts"][key].append(now)

        # Clean old attempts
        window = self.BRUTE_FORCE_WINDOW
        self.threats["failed_attempts"][key] = [
            t for t in self.threats["failed_attempts"][key]
            if now - t < window
        ]

        attempts = len(self.threats["failed_attempts"][key])
        threshold = self.config.get("max_login_attempts", self.BRUTE_FORCE_THRESHOLD)

        result = {
            "attempts": attempts,
            "threshold": threshold,
            "locked": False,
        }

        if attempts >= threshold:
            result["locked"] = True
            self._audit("brute_force", identifier,
                        f"Brute force detected: {attempts} attempts in {window}s",
                        "critical")

            # Auto-block if configured
            if self.config.get("auto_block_threats", True):
                if identifier not in self.threats["blocked_ips"]:
                    self.threats["blocked_ips"].append(identifier)

            self.threats["detected"].append({
                "type": "brute_force",
                "severity": "critical",
                "source": identifier,
                "action": action,
                "attempts": attempts,
                "timestamp": now,
            })

        self._save(THREATS_FILE, self.threats)
        return result

    def is_blocked(self, identifier: str) -> bool:
        """Check if an identifier (IP, user) is blocked."""
        return identifier in self.threats.get("blocked_ips", [])

    def unblock(self, identifier: str) -> dict:
        """Unblock an identifier."""
        if identifier in self.threats.get("blocked_ips", []):
            self.threats["blocked_ips"].remove(identifier)
            self._save(THREATS_FILE, self.threats)
            self._audit("unblocked", "system", f"Unblocked: {identifier}")
            return {"success": True, "message": f"Unblocked: {identifier}"}
        return {"success": False, "message": f"'{identifier}' was not blocked"}

    def get_threats(self, limit: int = 50, severity: str = "") -> List[dict]:
        """Get detected threats."""
        threats = self.threats.get("detected", [])
        if severity:
            threats = [t for t in threats if t.get("severity") == severity]
        return threats[-limit:]

    def get_threat_stats(self) -> dict:
        """Get threat detection statistics."""
        detected = self.threats.get("detected", [])
        by_type = Counter(t.get("type", "") for t in detected)
        by_severity = Counter(t.get("severity", "") for t in detected)

        cutoff_24h = time.time() - 86400
        recent = [t for t in detected if t.get("timestamp", 0) > cutoff_24h]

        return {
            "total_detected": len(detected),
            "blocked_identifiers": len(self.threats.get("blocked_ips", [])),
            "by_type": dict(by_type.most_common(15)),
            "by_severity": dict(by_severity),
            "last_24h": len(recent),
            "active_lockouts": sum(
                1 for v in self.threats.get("failed_attempts", {}).values()
                if len(v) >= self.config.get("max_login_attempts", 5)
            ),
        }

    # ========================
    # SECURITY HEALTH CHECK
    # ========================

    def health_check(self) -> dict:
        """Run a comprehensive security health check."""
        issues = []
        score = 100

        # Check if default password is still in use
        try:
            from auth import verify_password
            if verify_password("jarvis"):
                issues.append({
                    "issue": "Default password still active",
                    "severity": "critical",
                    "fix": "Change password via Settings > Security",
                })
                score -= 30
        except Exception:
            pass

        # Check vault health
        if len(self.vault.get("secrets", {})) == 0:
            issues.append({
                "issue": "No secrets stored in vault",
                "severity": "info",
                "fix": "Store API keys and tokens in the secure vault",
            })

        # Check for recent threats
        cutoff = time.time() - 86400
        recent_critical = [
            t for t in self.threats.get("detected", [])
            if t.get("timestamp", 0) > cutoff and t.get("severity") == "critical"
        ]
        if recent_critical:
            issues.append({
                "issue": f"{len(recent_critical)} critical threats in last 24h",
                "severity": "high",
                "fix": "Review threat log and take appropriate action",
            })
            score -= 20

        # Check blocked list
        if len(self.threats.get("blocked_ips", [])) > 10:
            issues.append({
                "issue": f"{len(self.threats['blocked_ips'])} blocked identifiers",
                "severity": "medium",
                "fix": "Review and clean up blocked list",
            })
            score -= 5

        # Check audit log size
        if len(self.audit_log) > 4000:
            issues.append({
                "issue": "Audit log getting large",
                "severity": "low",
                "fix": "Run audit cleanup to remove old entries",
            })
            score -= 5

        # Check permissions
        admin_count = sum(
            1 for u in self.permissions.get("users", {}).values()
            if u.get("role") == "admin"
        )
        if admin_count > 3:
            issues.append({
                "issue": f"{admin_count} admin users — consider restricting",
                "severity": "medium",
                "fix": "Review user roles and remove unnecessary admin access",
            })
            score -= 10

        score = max(0, score)
        health = "healthy" if score >= 80 else "warning" if score >= 50 else "critical"

        return {
            "health": health,
            "score": score,
            "issues": issues,
            "issue_count": len(issues),
            "timestamp": datetime.now().isoformat(),
        }

    # ========================
    # CONFIG & STATS
    # ========================

    def get_config(self) -> dict:
        return self.config

    def update_config(self, updates: dict) -> dict:
        """Update sentinel configuration."""
        allowed_keys = {
            "max_login_attempts", "lockout_minutes",
            "audit_retention_days", "threat_sensitivity",
            "auto_block_threats",
        }
        updated = []
        for key, value in updates.items():
            if key in allowed_keys:
                self.config[key] = value
                updated.append(key)

        if updated:
            self._save(CONFIG_FILE, self.config)
            self._audit("config_updated", "system", f"Updated: {updated}")

        return {"success": True, "updated": updated, "config": self.config}

    def get_stats(self) -> dict:
        """Get overall sentinel statistics."""
        return {
            "roles": len(self.permissions.get("roles", {})),
            "users": len(self.permissions.get("users", {})),
            "secrets_stored": len(self.vault.get("secrets", {})),
            "audit_entries": len(self.audit_log),
            "threats_detected": len(self.threats.get("detected", [])),
            "blocked_identifiers": len(self.threats.get("blocked_ips", [])),
            "blocked_actions": len(self.permissions.get("blocked_actions", [])),
            "health": self.health_check().get("health", "unknown"),
        }

    # ========================
    # PERSISTENCE
    # ========================

    @staticmethod
    def _load(filepath: Path, default):
        if filepath.exists():
            try:
                return json.loads(filepath.read_text(encoding="utf-8"))
            except Exception:
                pass
        return default if not callable(default) else default()

    @staticmethod
    def _save(filepath: Path, data):
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(
                json.dumps(data, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"Failed to save {filepath.name}: {e}")


# Singleton
sentinel_engine = SentinelEngine()
