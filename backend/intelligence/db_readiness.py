"""
Database Readiness Stubs for MJ-Assistant (V2 upgrade).
Provides interface stubs for Qdrant vector DB and PostgreSQL.
Currently uses JSON file storage; these stubs enable future migration
to production databases without changing the module API.
"""

import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger("mj.db_readiness")


# ========================
# QDRANT VECTOR DB STUB
# ========================

class QdrantStub:
    """
    Stub for Qdrant vector database.
    Mirrors the Qdrant client API so modules can be written against it.
    Currently stores nothing — the real MemoryStore handles persistence.
    When Qdrant is installed, swap this for the real qdrant_client.
    """

    def __init__(self, url: str = "localhost", port: int = 6333):
        self.url = url
        self.port = port
        self._available = False
        self._check()

    def _check(self):
        try:
            import httpx
            resp = httpx.get(f"http://{self.url}:{self.port}/dashboard", timeout=2)
            self._available = resp.status_code == 200
        except Exception:
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def create_collection(self, name: str, vector_size: int = 384) -> dict:
        if not self._available:
            return {"success": False, "reason": "Qdrant not running", "stub": True}
        return {"success": True, "collection": name, "stub": True}

    def upsert(self, collection: str, points: list) -> dict:
        if not self._available:
            return {"success": False, "reason": "Qdrant not running", "stub": True}
        return {"success": True, "upserted": len(points), "stub": True}

    def search(self, collection: str, query_vector: list, limit: int = 10) -> list:
        if not self._available:
            return []
        return []

    def get_status(self) -> dict:
        return {
            "available": self._available,
            "url": f"{self.url}:{self.port}",
            "backend": "stub" if not self._available else "qdrant",
            "note": "Install Qdrant for production vector search. Current: JSON + TF-IDF fallback.",
        }


# ========================
# POSTGRESQL STUB
# ========================

class PostgreSQLStub:
    """
    Stub for PostgreSQL database.
    When connected, enables structured storage for memories, user profiles, chat history.
    Currently uses JSON files. Swap this for asyncpg/psycopg when PostgreSQL is available.
    """

    def __init__(self, dsn: str = ""):
        self.dsn = dsn or "postgresql://localhost:5432/mj_assistant"
        self._available = False
        self._check()

    def _check(self):
        try:
            import psycopg2
            conn = psycopg2.connect(self.dsn, connect_timeout=2)
            conn.close()
            self._available = True
        except Exception:
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def execute(self, query: str, params: tuple = ()) -> dict:
        if not self._available:
            return {"success": False, "reason": "PostgreSQL not connected", "stub": True}
        return {"success": True, "stub": True}

    def fetch(self, query: str, params: tuple = ()) -> list:
        if not self._available:
            return []
        return []

    def get_status(self) -> dict:
        return {
            "available": self._available,
            "dsn": self.dsn.split("@")[-1] if "@" in self.dsn else self.dsn,
            "backend": "stub" if not self._available else "postgresql",
            "note": "Install PostgreSQL for production storage. Current: JSON file storage.",
        }


# ========================
# UNIFIED STATUS
# ========================

# Singletons
qdrant = QdrantStub()
postgres = PostgreSQLStub()


def get_db_status() -> dict:
    """Get status of all database backends."""
    return {
        "qdrant": qdrant.get_status(),
        "postgresql": postgres.get_status(),
        "current_backend": "json_files",
        "ready_for_migration": True,
        "analytics": get_memory_analytics(),
    }


# ========================
# MEMORY ANALYTICS (V2 → 100%)
# ========================

import os
import glob

DATA_DIR = Path(__file__).parent.parent / "data"

def get_memory_analytics() -> dict:
    """Analyze all JSON data files for memory stats."""
    analytics = {"total_files": 0, "total_size_kb": 0, "files": [], "stale_count": 0}
    if not DATA_DIR.exists():
        return analytics

    import time as _time
    now = _time.time()
    for fp in DATA_DIR.glob("*.json"):
        try:
            stat = fp.stat()
            size_kb = round(stat.st_size / 1024, 1)
            age_days = round((now - stat.st_mtime) / 86400, 1)
            record_count = 0
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    record_count = len(data)
                elif isinstance(data, dict):
                    record_count = len(data)
            except Exception:
                pass
            is_stale = age_days > 30
            analytics["files"].append({
                "name": fp.name, "size_kb": size_kb,
                "records": record_count, "age_days": age_days,
                "stale": is_stale,
            })
            analytics["total_size_kb"] += size_kb
            analytics["total_files"] += 1
            if is_stale:
                analytics["stale_count"] += 1
        except Exception:
            pass

    analytics["total_size_kb"] = round(analytics["total_size_kb"], 1)
    return analytics


def export_data(format: str = "json") -> dict:
    """Export all data files info for migration."""
    if not DATA_DIR.exists():
        return {"error": "No data directory"}

    exports = []
    for fp in DATA_DIR.glob("*.json"):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            exports.append({
                "file": fp.name,
                "type": "list" if isinstance(data, list) else "dict",
                "count": len(data) if isinstance(data, (list, dict)) else 0,
                "size_kb": round(fp.stat().st_size / 1024, 1),
            })
        except Exception:
            exports.append({"file": fp.name, "error": "parse_failed"})

    return {"format": format, "files": exports, "total": len(exports), "data_dir": str(DATA_DIR)}


def garbage_collect(max_age_days: int = 90) -> dict:
    """Identify and optionally clean stale data entries."""
    import time as _time
    now = _time.time()
    cutoff = now - (max_age_days * 86400)
    cleaned = []

    for fp in DATA_DIR.glob("*.json"):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            if isinstance(data, list) and len(data) > 0:
                # Only clean lists with timestamp fields
                if isinstance(data[0], dict) and any(k in data[0] for k in ("timestamp", "ts", "created_at", "time")):
                    ts_key = next(k for k in ("timestamp", "ts", "created_at", "time") if k in data[0])
                    before = len(data)
                    # Don't actually delete — just report what WOULD be cleaned
                    stale = [d for d in data if _parse_ts(d.get(ts_key, 0)) < cutoff]
                    if stale:
                        cleaned.append({"file": fp.name, "total": before, "stale": len(stale)})
        except Exception:
            pass

    return {"max_age_days": max_age_days, "would_clean": cleaned, "dry_run": True}


def _parse_ts(val) -> float:
    """Parse various timestamp formats to epoch float."""
    if isinstance(val, (int, float)):
        return float(val) if val > 1e9 else 0
    if isinstance(val, str):
        try:
            from datetime import datetime
            return datetime.fromisoformat(val.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0
    return 0


def get_migration_plan() -> dict:
    """Generate a migration plan from JSON to database."""
    analytics = get_memory_analytics()
    files = analytics.get("files", [])

    plan = {
        "current": "json_files",
        "target": "postgresql + qdrant",
        "steps": [
            {"step": 1, "action": "Install PostgreSQL", "status": "ready" if postgres.available else "needed"},
            {"step": 2, "action": "Install Qdrant", "status": "ready" if qdrant.available else "needed"},
            {"step": 3, "action": "Create schemas", "detail": "Run migration scripts to create tables"},
            {"step": 4, "action": "Migrate data", "detail": f"Transfer {len(files)} JSON files to DB"},
            {"step": 5, "action": "Update imports", "detail": "Switch modules from JSON to DB backends"},
            {"step": 6, "action": "Verify", "detail": "Run integrity checks on migrated data"},
        ],
        "estimated_records": sum(f.get("records", 0) for f in files),
        "estimated_size_kb": analytics.get("total_size_kb", 0),
    }
    return plan
