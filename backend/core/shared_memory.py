"""
Shared Memory — Key-value store accessible by all modules.
Supports namespaces, TTL (auto-expiry), persistence, and change notifications.
"""

import time
import json
import logging
import threading
from pathlib import Path
from typing import Any, Optional, Dict, List

logger = logging.getLogger("mj.shared_memory")

MEMORY_FILE = Path(__file__).parent.parent / "shared_memory.json"


class SharedMemory:
    """
    Thread-safe shared key-value store.
    Keys use namespace.key format: "athena.last_search", "zeus.active_plan".
    Supports TTL (seconds) — expired keys auto-removed on access.
    """

    def __init__(self, persist: bool = True):
        self._store: Dict[str, dict] = {}  # key -> {value, ttl, created, updated, namespace}
        self._lock = threading.Lock()
        self._persist = persist
        self._change_hooks: List = []
        self._load()

    def set(self, key: str, value: Any, ttl: Optional[int] = None, namespace: str = "global"):
        """Set a value. TTL in seconds (None = never expires)."""
        with self._lock:
            now = time.time()
            full_key = f"{namespace}.{key}" if namespace != "global" else key
            self._store[full_key] = {
                "value": value,
                "ttl": ttl,
                "expires_at": (now + ttl) if ttl else None,
                "created": self._store.get(full_key, {}).get("created", now),
                "updated": now,
                "namespace": namespace,
            }
            self._save()

        # Notify change hooks
        for hook in self._change_hooks:
            try:
                hook("set", full_key, value)
            except Exception:
                pass

    def get(self, key: str, default: Any = None, namespace: str = "global") -> Any:
        """Get a value. Returns default if not found or expired."""
        full_key = f"{namespace}.{key}" if namespace != "global" else key
        with self._lock:
            entry = self._store.get(full_key)
            if not entry:
                return default
            # Check TTL
            if entry["expires_at"] and time.time() > entry["expires_at"]:
                del self._store[full_key]
                self._save()
                return default
            return entry["value"]

    def delete(self, key: str, namespace: str = "global") -> bool:
        """Delete a key. Returns True if existed."""
        full_key = f"{namespace}.{key}" if namespace != "global" else key
        with self._lock:
            if full_key in self._store:
                del self._store[full_key]
                self._save()
                return True
            return False

    def exists(self, key: str, namespace: str = "global") -> bool:
        """Check if key exists and is not expired."""
        return self.get(key, namespace=namespace) is not None

    def get_namespace(self, namespace: str) -> Dict[str, Any]:
        """Get all keys in a namespace."""
        prefix = f"{namespace}."
        result = {}
        now = time.time()
        with self._lock:
            for key, entry in list(self._store.items()):
                if key.startswith(prefix):
                    if entry["expires_at"] and now > entry["expires_at"]:
                        del self._store[key]
                        continue
                    short_key = key[len(prefix):]
                    result[short_key] = entry["value"]
        return result

    def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in a namespace. Returns count removed."""
        prefix = f"{namespace}."
        count = 0
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]
                count += 1
            if count:
                self._save()
        return count

    def list_keys(self, namespace: Optional[str] = None) -> List[str]:
        """List all keys, optionally filtered by namespace."""
        now = time.time()
        with self._lock:
            keys = []
            for key, entry in list(self._store.items()):
                if entry["expires_at"] and now > entry["expires_at"]:
                    del self._store[key]
                    continue
                if namespace and not key.startswith(f"{namespace}."):
                    continue
                keys.append(key)
            return keys

    def get_all(self) -> Dict[str, Any]:
        """Get all non-expired key-value pairs."""
        now = time.time()
        result = {}
        with self._lock:
            for key, entry in list(self._store.items()):
                if entry["expires_at"] and now > entry["expires_at"]:
                    del self._store[key]
                    continue
                result[key] = {
                    "value": entry["value"],
                    "namespace": entry["namespace"],
                    "ttl": entry["ttl"],
                    "updated": entry["updated"],
                }
        return result

    def cleanup_expired(self) -> int:
        """Remove all expired keys. Returns count removed."""
        now = time.time()
        count = 0
        with self._lock:
            expired = [k for k, v in self._store.items() if v["expires_at"] and now > v["expires_at"]]
            for k in expired:
                del self._store[k]
                count += 1
            if count:
                self._save()
        return count

    def on_change(self, hook):
        """Register a change hook: hook(action, key, value)."""
        self._change_hooks.append(hook)

    def stats(self) -> dict:
        """Get memory stats."""
        now = time.time()
        total = len(self._store)
        expired = sum(1 for v in self._store.values() if v["expires_at"] and now > v["expires_at"])
        namespaces = set(v["namespace"] for v in self._store.values())
        return {
            "total_keys": total,
            "expired_pending": expired,
            "active_keys": total - expired,
            "namespaces": sorted(namespaces),
        }

    def _load(self):
        """Load from disk."""
        if self._persist and MEMORY_FILE.exists():
            try:
                data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
                self._store = data
            except Exception as e:
                logger.warning(f"Failed to load shared memory: {e}")

    def _save(self):
        """Persist to disk."""
        if self._persist:
            try:
                # Only save JSON-serializable values
                safe = {}
                for k, v in self._store.items():
                    try:
                        json.dumps(v["value"])
                        safe[k] = v
                    except (TypeError, ValueError):
                        pass  # Skip non-serializable
                MEMORY_FILE.write_text(json.dumps(safe, indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to save shared memory: {e}")


# Singleton
shared_memory = SharedMemory()
