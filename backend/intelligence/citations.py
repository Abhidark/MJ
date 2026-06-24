"""
MJ Intelligence: Citation Manager
Tracks sources used in responses, generates formatted citations,
and maintains a citation history for audit/reference.
"""

import json
import time
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("mj.citations")

CITATIONS_FILE = Path(__file__).parent.parent / "knowledge_base" / "citations.json"


class CitationManager:
    """
    Manages citations from KB documents and web sources.
    Formats: inline [N], APA, footnote.
    Tracks citation history across sessions.
    """

    def __init__(self):
        self._session_citations: List[dict] = []  # Current session
        self._history: List[dict] = []  # Persistent
        self._counter = 0
        self._load()

    def cite_kb(self, source: str, text: str, page: int = None,
                relevance: float = 0.0) -> dict:
        """Create a citation from a knowledge base document."""
        self._counter += 1
        citation = {
            "id": self._counter,
            "type": "knowledge_base",
            "source": source,
            "text_preview": text[:150] + "..." if len(text) > 150 else text,
            "page": page,
            "relevance": round(relevance, 3),
            "timestamp": time.time(),
            "inline": f"[{self._counter}]",
            "apa": self._format_apa_kb(source, page),
            "footnote": self._format_footnote_kb(source, page, self._counter),
        }
        self._session_citations.append(citation)
        return citation

    def cite_web(self, title: str, url: str, snippet: str = "",
                 accessed: str = None) -> dict:
        """Create a citation from a web source."""
        self._counter += 1
        accessed = accessed or datetime.now().strftime("%d %b %Y")
        citation = {
            "id": self._counter,
            "type": "web",
            "title": title,
            "url": url,
            "text_preview": snippet[:150] + "..." if len(snippet) > 150 else snippet,
            "accessed": accessed,
            "timestamp": time.time(),
            "inline": f"[{self._counter}]",
            "apa": self._format_apa_web(title, url, accessed),
            "footnote": self._format_footnote_web(title, url, accessed, self._counter),
        }
        self._session_citations.append(citation)
        return citation

    def cite_from_search(self, search_results: List[dict]) -> List[dict]:
        """Bulk-create citations from search results."""
        citations = []
        for result in search_results:
            cite = self.cite_web(
                title=result.get("title", "Unknown"),
                url=result.get("url", ""),
                snippet=result.get("snippet", ""),
            )
            citations.append(cite)
        return citations

    def cite_from_kb_results(self, kb_results: List[dict]) -> List[dict]:
        """Bulk-create citations from KB search results."""
        citations = []
        for result in kb_results:
            cite = self.cite_kb(
                source=result.get("source", "Unknown"),
                text=result.get("text", ""),
                page=result.get("page"),
                relevance=result.get("score", 0),
            )
            citations.append(cite)
        return citations

    def get_session_citations(self) -> List[dict]:
        """Get all citations from current session."""
        return self._session_citations

    def get_bibliography(self, format: str = "apa") -> str:
        """Generate formatted bibliography from session citations."""
        if not self._session_citations:
            return ""

        lines = ["REFERENCES:"]
        for cite in self._session_citations:
            if format == "apa":
                lines.append(f"  {cite['apa']}")
            elif format == "footnote":
                lines.append(f"  {cite['footnote']}")
            else:  # inline
                source = cite.get("source") or cite.get("title", "Unknown")
                lines.append(f"  {cite['inline']} {source}")

        return "\n".join(lines)

    def get_citation_context(self) -> str:
        """Generate citation context string for LLM prompt injection."""
        if not self._session_citations:
            return ""

        parts = ["\nAVAILABLE CITATIONS (use [N] to reference):"]
        for cite in self._session_citations:
            source = cite.get("source") or cite.get("title", "Unknown")
            parts.append(f"  {cite['inline']} {source}" +
                         (f" (Page {cite['page']})" if cite.get("page") else "") +
                         (f" - {cite['text_preview'][:80]}" if cite.get("text_preview") else ""))
        return "\n".join(parts)

    def clear_session(self):
        """Archive session citations to history and reset."""
        if self._session_citations:
            self._history.append({
                "session_time": datetime.now().isoformat(),
                "citations": self._session_citations,
                "count": len(self._session_citations),
            })
            self._save()
        self._session_citations = []
        self._counter = 0

    def get_history(self, limit: int = 20) -> List[dict]:
        """Get citation history."""
        return self._history[-limit:]

    def get_stats(self) -> dict:
        """Get citation statistics."""
        total_kb = sum(1 for c in self._session_citations if c["type"] == "knowledge_base")
        total_web = sum(1 for c in self._session_citations if c["type"] == "web")
        return {
            "session_total": len(self._session_citations),
            "session_kb": total_kb,
            "session_web": total_web,
            "history_sessions": len(self._history),
            "history_total": sum(s["count"] for s in self._history),
        }

    # ========================
    # FORMAT HELPERS
    # ========================

    @staticmethod
    def _format_apa_kb(source: str, page: int = None) -> str:
        """APA-style citation for KB document."""
        cite = f"{source}."
        if page:
            cite += f" (p. {page})."
        cite += f" Personal Knowledge Base."
        return cite

    @staticmethod
    def _format_apa_web(title: str, url: str, accessed: str) -> str:
        """APA-style citation for web source."""
        return f"{title}. Retrieved {accessed}, from {url}"

    @staticmethod
    def _format_footnote_kb(source: str, page: int, num: int) -> str:
        """Footnote-style citation for KB document."""
        cite = f"[{num}] {source}"
        if page:
            cite += f", p. {page}"
        return cite

    @staticmethod
    def _format_footnote_web(title: str, url: str, accessed: str, num: int) -> str:
        """Footnote-style citation for web source."""
        return f'[{num}] "{title}," {url} (accessed {accessed})'

    # ========================
    # PERSISTENCE
    # ========================

    def _load(self):
        if CITATIONS_FILE.exists():
            try:
                data = json.loads(CITATIONS_FILE.read_text(encoding="utf-8"))
                self._history = data.get("history", [])
            except Exception:
                pass

    def _save(self):
        try:
            CITATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {"history": self._history[-50:], "saved": time.time()}  # Keep last 50 sessions
            CITATIONS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save citations: {e}")


# Singleton
citation_manager = CitationManager()
