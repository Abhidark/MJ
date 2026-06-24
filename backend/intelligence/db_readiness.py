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
    }
