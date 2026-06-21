"""
Sentinel Module -- Security Tools
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
    description = "Security tools: password generation, file hashing, and security tips"
    version = "1.0"
    category = "utility"
    enabled = True

    KEYWORDS = [
        "password", "hash", "encrypt", "security check", "generate password",
        "strong password", "sha256", "md5", "checksum", "file hash",
        "security tip", "security", "secure", "passwd",
    ]

    def __init__(self):
        self.password_length = 16

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        lower = text.lower()

        for kw in self.KEYWORDS:
            if kw in lower:
                return 0.9

        if intent in ("security", "password_generation", "hashing"):
            return 0.85

        if re.search(r"\b(safe|protect|breach|leak)\b", lower):
            return 0.5

        return 0.0

    def execute(self, text: str, context: dict) -> dict:
        lower = text.lower()

        if "generate password" in lower or "strong password" in lower or "passwd" in lower:
            return self._generate_password()

        if re.search(r"\bhash\b", lower) or "checksum" in lower or "sha" in lower or "md5" in lower:
            return self._hash_content(text, context)

        if "security tip" in lower or "security check" in lower:
            return self._security_tips()

        # Default to password generation
        if "password" in lower:
            return self._generate_password()

        return self._security_tips()

    def _generate_password(self) -> dict:
        """Generate a cryptographically strong password."""
        length = self.password_length
        alphabet = string.ascii_letters + string.digits + string.punctuation

        # Ensure at least one of each character type
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
            "data": {
                "password": password,
                "length": length,
                "strength": strength,
            },
            "action": "password_generated",
        }

    def _hash_content(self, text: str, context: dict) -> dict:
        """Hash text or file content."""
        # Check if a file path is mentioned
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
                        "data": {
                            "file": str(file_path),
                            "sha256": sha256.hexdigest(),
                            "md5": md5.hexdigest(),
                        },
                        "action": "file_hash",
                    }
                except OSError as e:
                    return {
                        "response": f"Could not read file: {e}",
                        "data": None,
                        "action": "error",
                    }
            else:
                return {
                    "response": f"File not found: {file_path}",
                    "data": None,
                    "action": "error",
                }

        # Hash the text itself
        content = text.encode("utf-8")
        return {
            "response": (
                f"Text Hash:\n"
                f"SHA-256: {hashlib.sha256(content).hexdigest()}\n"
                f"MD5: {hashlib.md5(content).hexdigest()}"
            ),
            "data": {
                "sha256": hashlib.sha256(content).hexdigest(),
                "md5": hashlib.md5(content).hexdigest(),
            },
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
        # Pick 3 random tips
        selected = secrets.SystemRandom().sample(tips, min(3, len(tips)))
        formatted = "\n".join(f"  {i+1}. {tip}" for i, tip in enumerate(selected))

        return {
            "response": f"Security Tips:\n{formatted}",
            "data": {"tips": selected},
            "action": "security_tips",
        }

    def get_system_prompt_addition(self) -> str:
        return (
            "You have security tools available: password generation, "
            "file hashing (SHA-256, MD5), and security advice."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        return "[Sentinel Security Module] User is asking about security, passwords, or hashing."

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "password_length": self.password_length,
        }

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "password_length" in settings:
            val = int(settings["password_length"])
            self.password_length = max(8, min(32, val))

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "password_length",
                "label": "Password Length",
                "type": "range",
                "value": self.password_length,
                "min": 8,
                "max": 32,
                "step": 1,
            },
        ]
