"""
Sentinel Module -- Security Agent (V15)
Handles: passwords, hashing, permissions, secrets vault, audit logs, threat detection
"""

import re
import secrets
import string
import hashlib
from pathlib import Path
from modules.base_module import BaseModule


class SentinelModule(BaseModule):
    name = "sentinel"
    display_name = "Sentinel"
    icon = "\U0001f6e1"
    description = "Security agent: passwords, hashing, permissions, secrets vault, audit, threats"
    version = "3.0"
    category = "security"
    enabled = True

    # Original keywords (preserved)
    BASIC_KEYWORDS = [
        "password", "hash", "encrypt", "security check", "generate password",
        "strong password", "sha256", "md5", "checksum", "file hash",
        "security tip", "security", "secure", "passwd",
    ]

    # V15 new keywords
    SECURITY_KEYWORDS = [
        "permission", "permissions", "role", "roles", "access control",
        "secret", "secrets", "vault", "api key", "token", "credential",
        "audit", "audit log", "security log", "who accessed",
        "threat", "threats", "scan", "injection", "brute force",
        "block", "unblock", "blocked", "lockout",
        "security health", "health check", "security status",
        "store secret", "save secret", "get secret", "delete secret",
        "suraksha", "security check karo",
    ]

    SECURITY_REGEX = re.compile(
        r"\b(permission|role|secret|vault|audit|threat|scan|inject|"
        r"brute\s*force|block|unblock|lockout|credential|api\s*key|"
        r"security\s*health|security\s*check|access\s*control)\b",
        re.IGNORECASE
    )

    def __init__(self):
        self.password_length = 16
        self._sentinel_engine = None

    @property
    def sentinel_engine(self):
        if self._sentinel_engine is None:
            try:
                from intelligence.sentinel_engine import sentinel_engine
                self._sentinel_engine = sentinel_engine
            except ImportError:
                self._sentinel_engine = None
        return self._sentinel_engine

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        lower = text.lower()

        # V15 security keywords — highest priority
        for kw in self.SECURITY_KEYWORDS:
            if kw in lower:
                return 0.95

        if self.SECURITY_REGEX.search(lower):
            return 0.93

        if intent in ("security", "permissions", "vault", "audit",
                       "threat_detection", "secrets"):
            return 0.92

        # Original keywords
        for kw in self.BASIC_KEYWORDS:
            if kw in lower:
                return 0.9

        if intent in ("password_generation", "hashing"):
            return 0.85

        if re.search(r"\b(safe|protect|breach|leak)\b", lower):
            return 0.5

        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        lower = text.lower()

        # ── V15 Security Engine features ──
        if self._is_security_request(lower):
            return self._handle_security(lower, text, context)

        # ── Original features (preserved) ──
        if "generate password" in lower or "strong password" in lower or "passwd" in lower:
            return self._generate_password()

        if re.search(r"\bhash\b", lower) or "checksum" in lower or "sha" in lower or "md5" in lower:
            return self._hash_content(text, context)

        if "security tip" in lower or "security check" in lower:
            return self._security_tips()

        if "password" in lower:
            return self._generate_password()

        return self._security_tips()

    def _is_security_request(self, lower: str) -> bool:
        for kw in self.SECURITY_KEYWORDS:
            if kw in lower:
                return True
        return bool(self.SECURITY_REGEX.search(lower))

    def _handle_security(self, lower: str, text: str, context: dict) -> dict:
        # Permissions
        if any(kw in lower for kw in ["permission", "role", "access control"]):
            return self._handle_permissions(lower, text)

        # Secrets vault
        if any(kw in lower for kw in ["secret", "vault", "api key", "token",
                                       "credential", "store secret", "save secret",
                                       "get secret", "delete secret"]):
            return self._handle_vault(lower, text)

        # Audit logs
        if any(kw in lower for kw in ["audit", "security log", "who accessed"]):
            return self._handle_audit(lower, text)

        # Threat detection
        if any(kw in lower for kw in ["threat", "scan", "injection", "brute force",
                                       "block", "unblock", "lockout"]):
            return self._handle_threats(lower, text)

        # Health check
        if any(kw in lower for kw in ["health check", "security health", "security status",
                                       "suraksha"]):
            return self._health_check()

        # Default: health check
        return self._health_check()

    def _handle_permissions(self, lower: str, text: str) -> dict:
        if not self.sentinel_engine:
            return self._engine_unavailable()

        # List roles
        if "list" in lower or "show" in lower or "all" in lower:
            roles = self.sentinel_engine.get_roles()
            lines = ["Roles:"]
            for name, data in roles.items():
                perms = ", ".join(data.get("permissions", [])[:5])
                lines.append(f"  {name}: {data.get('description', '')} [{perms}]")
            return {"response": "\n".join(lines), "data": roles, "action": "roles_listed"}

        # Create role
        if "create" in lower or "add" in lower:
            name_match = re.search(r'role\s+["\']?(\w+)', text, re.I)
            if name_match:
                name = name_match.group(1)
                result = self.sentinel_engine.create_role(name, f"Custom role: {name}", ["chat", "search"])
                return {"response": result["message"], "data": result, "action": "role_created"}

        # Check permission
        if "check" in lower:
            result = self.sentinel_engine.check_permission("default", "chat")
            return {"response": f"Permission check: {'Allowed' if result['allowed'] else 'Denied'} (Role: {result['role']})",
                    "data": result, "action": "permission_checked"}

        roles = self.sentinel_engine.get_roles()
        return {"response": f"{len(roles)} roles configured. Ask to list, create, or check permissions.",
                "data": {"roles": list(roles.keys())}, "action": "permissions_info"}

    def _handle_vault(self, lower: str, text: str) -> dict:
        if not self.sentinel_engine:
            return self._engine_unavailable()

        # Store secret
        if any(kw in lower for kw in ["store", "save", "add"]):
            match = re.search(r'(?:store|save|add)\s+(?:secret\s+)?["\']?(\w+)["\']?\s*[:=]\s*["\']?(\S+)', text, re.I)
            if match:
                key, value = match.group(1), match.group(2)
                result = self.sentinel_engine.store_secret(key, value)
                return {"response": result["message"], "data": {"key": key}, "action": "secret_stored"}
            return {"response": "Usage: store secret KEY=VALUE", "data": None, "action": "info"}

        # Get secret
        if "get" in lower or "retrieve" in lower or "show" in lower:
            match = re.search(r'(?:get|retrieve|show)\s+(?:secret\s+)?["\']?(\w+)', text, re.I)
            if match:
                key = match.group(1)
                result = self.sentinel_engine.get_secret(key)
                if result["success"]:
                    # Mask value in response (show first 4 chars)
                    val = result["value"]
                    masked = val[:4] + "*" * max(0, len(val) - 4)
                    return {"response": f"Secret '{key}': {masked}", "data": {"key": key}, "action": "secret_retrieved"}
                return {"response": result["message"], "data": None, "action": "error"}

        # Delete secret
        if "delete" in lower or "remove" in lower:
            match = re.search(r'(?:delete|remove)\s+(?:secret\s+)?["\']?(\w+)', text, re.I)
            if match:
                key = match.group(1)
                result = self.sentinel_engine.delete_secret(key)
                return {"response": result["message"], "data": result, "action": "secret_deleted"}

        # List secrets
        result = self.sentinel_engine.list_secrets()
        lines = [f"Vault: {result['count']} secrets"]
        for s in result.get("secrets", [])[:10]:
            lines.append(f"  {s['key']} ({s['category']}) — accessed {s['access_count']}x")
        return {"response": "\n".join(lines), "data": result, "action": "secrets_listed"}

    def _handle_audit(self, lower: str, text: str) -> dict:
        if not self.sentinel_engine:
            return self._engine_unavailable()

        # Stats
        if "stats" in lower or "summary" in lower:
            stats = self.sentinel_engine.get_audit_stats()
            lines = [f"Audit Log: {stats['total']} entries"]
            lines.append(f"Last 24h: {stats.get('last_24h', {}).get('count', 0)}")
            top_events = stats.get("by_event", {})
            if top_events:
                top = list(top_events.items())[:5]
                lines.append("Top events: " + ", ".join(f"{k}({v})" for k, v in top))
            return {"response": "\n".join(lines), "data": stats, "action": "audit_stats"}

        # Clean old
        if "clean" in lower or "clear" in lower:
            days = 30
            d_match = re.search(r'(\d+)\s*days?', text)
            if d_match:
                days = int(d_match.group(1))
            result = self.sentinel_engine.clear_old_audit_logs(days)
            return {"response": f"Removed {result['removed']} old entries. {result['remaining']} remaining.",
                    "data": result, "action": "audit_cleaned"}

        # Show recent logs
        limit = 20
        logs = self.sentinel_engine.get_audit_log(limit=limit)
        lines = [f"Recent audit entries ({len(logs)}):"]
        for log in logs[-10:]:
            lines.append(f"  [{log.get('status', '')}] {log.get('event', '')} — {log.get('detail', '')[:60]}")
        return {"response": "\n".join(lines), "data": {"logs": logs}, "action": "audit_shown"}

    def _handle_threats(self, lower: str, text: str) -> dict:
        if not self.sentinel_engine:
            return self._engine_unavailable()

        # Scan text for threats
        if "scan" in lower:
            scan_text = text
            scan_match = re.search(r'scan\s*[:\-]?\s*(.+)', text, re.I)
            if scan_match:
                scan_text = scan_match.group(1)
            result = self.sentinel_engine.scan_input(scan_text)
            if result["safe"]:
                return {"response": "Scan complete: No threats detected.", "data": result, "action": "scan_clean"}
            lines = [f"Threats found: {result['count']} (highest: {result['highest_severity']})"]
            for t in result["threats"]:
                lines.append(f"  [{t['severity']}] {t['type']}")
            return {"response": "\n".join(lines), "data": result, "action": "threats_found"}

        # Unblock
        if "unblock" in lower:
            match = re.search(r'unblock\s+["\']?(\S+)', text, re.I)
            if match:
                result = self.sentinel_engine.unblock(match.group(1))
                return {"response": result["message"], "data": result, "action": "unblocked"}

        # Threat stats
        if "stats" in lower or "status" in lower:
            stats = self.sentinel_engine.get_threat_stats()
            lines = [f"Threat Stats: {stats['total_detected']} detected"]
            lines.append(f"Blocked: {stats['blocked_identifiers']}, Last 24h: {stats['last_24h']}")
            return {"response": "\n".join(lines), "data": stats, "action": "threat_stats"}

        # Show recent threats
        threats = self.sentinel_engine.get_threats(limit=10)
        if not threats:
            return {"response": "No threats detected.", "data": {"threats": []}, "action": "threats_clear"}
        lines = [f"Recent threats ({len(threats)}):"]
        for t in threats[-10:]:
            lines.append(f"  [{t.get('severity', '')}] {t.get('type', '')} from {t.get('source', 'unknown')}")
        return {"response": "\n".join(lines), "data": {"threats": threats}, "action": "threats_shown"}

    def _health_check(self) -> dict:
        if not self.sentinel_engine:
            return self._engine_unavailable()

        result = self.sentinel_engine.health_check()
        lines = [f"Security Health: {result['health'].upper()} (Score: {result['score']}/100)"]
        for issue in result.get("issues", []):
            lines.append(f"  [{issue['severity']}] {issue['issue']}")
            lines.append(f"    Fix: {issue['fix']}")
        if not result.get("issues"):
            lines.append("  No issues found.")
        return {"response": "\n".join(lines), "data": result, "action": "health_check"}

    def _engine_unavailable(self) -> dict:
        return {"response": "Sentinel security engine not available.", "data": None, "action": "error"}

    # ── Original features (preserved) ──

    def _generate_password(self) -> dict:
        length = self.password_length
        alphabet = string.ascii_letters + string.digits + string.punctuation

        while True:
            password = "".join(secrets.choice(alphabet) for _ in range(length))
            if (
                any(c in string.ascii_lowercase for c in password)
                and any(c in string.ascii_uppercase for c in password)
                and any(c in string.digits for c in password)
                and any(c in string.punctuation for c in password)
            ):
                break

        strength = "Strong" if length >= 16 else "Medium" if length >= 12 else "Moderate"
        return {
            "response": (
                f"Generated {strength} Password ({length} chars):\n"
                f"`{password}`\n\n"
                "Copy it and store it in a password manager."
            ),
            "data": {"password": password, "length": length, "strength": strength},
            "action": "password_generated",
        }

    def _hash_content(self, text: str, context: dict) -> dict:
        file_match = re.search(r'["\']?([a-zA-Z]:\\[^"\']+|/[^"\']+)["\']?', text)

        if file_match:
            file_path = Path(file_match.group(1))
            if file_path.exists() and file_path.is_file():
                try:
                    sha256 = hashlib.sha256()
                    md5 = hashlib.md5()
                    with open(file_path, "rb") as f:
                        for chunk in iter(lambda: f.read(8192), b""):
                            sha256.update(chunk)
                            md5.update(chunk)
                    return {
                        "response": (
                            f"File: {file_path.name}\n"
                            f"SHA-256: {sha256.hexdigest()}\n"
                            f"MD5: {md5.hexdigest()}"
                        ),
                        "data": {"file": str(file_path), "sha256": sha256.hexdigest(), "md5": md5.hexdigest()},
                        "action": "file_hash",
                    }
                except OSError as e:
                    return {"response": f"Could not read file: {e}", "data": None, "action": "error"}
            else:
                return {"response": f"File not found: {file_path}", "data": None, "action": "error"}

        content = text.encode("utf-8")
        return {
            "response": (
                f"Text Hash:\n"
                f"SHA-256: {hashlib.sha256(content).hexdigest()}\n"
                f"MD5: {hashlib.md5(content).hexdigest()}"
            ),
            "data": {"sha256": hashlib.sha256(content).hexdigest(), "md5": hashlib.md5(content).hexdigest()},
            "action": "text_hash",
        }

    def _security_tips(self) -> dict:
        tips = [
            "Use a unique password for every account.",
            "Enable two-factor authentication (2FA) wherever possible.",
            "Keep your operating system and software up to date.",
            "Be cautious of phishing emails and suspicious links.",
            "Use a password manager to store credentials securely.",
            "Regularly review app permissions on your devices.",
            "Back up important data using the 3-2-1 rule.",
            "Use a VPN on public Wi-Fi networks.",
        ]
        selected = secrets.SystemRandom().sample(tips, min(3, len(tips)))
        formatted = "\n".join(f"  {i+1}. {tip}" for i, tip in enumerate(selected))
        return {"response": f"Security Tips:\n{formatted}", "data": {"tips": selected}, "action": "security_tips"}

    # ── Module interface ──

    def get_system_prompt_addition(self) -> str:
        return (
            "You have full security capabilities: password generation, file hashing, "
            "role-based permissions, encrypted secrets vault, audit logging, "
            "and threat detection (injection, brute force, credential exposure)."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        parts = ["[Sentinel Security Module]"]
        lower = text.lower()
        if self._is_security_request(lower):
            parts.append("User wants security features.")
            if self.sentinel_engine:
                stats = self.sentinel_engine.get_stats()
                parts.append(f"Secrets: {stats.get('secrets_stored', 0)}, "
                             f"Threats: {stats.get('threats_detected', 0)}")
        else:
            parts.append("User is asking about security, passwords, or hashing.")
        return " ".join(parts)

    def get_settings(self) -> dict:
        return {"enabled": self.enabled, "password_length": self.password_length}

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "password_length" in settings:
            val = int(settings["password_length"])
            self.password_length = max(8, min(32, val))

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {"key": "password_length", "label": "Password Length", "type": "range",
             "value": self.password_length, "min": 8, "max": 32, "step": 1},
        ]
