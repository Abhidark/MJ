"""
Sherlock Module — Deep Search for MJ Assistant.
Wraps web search to answer current events, fact-checking, and research queries.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.base_module import BaseModule


class SherlockModule(BaseModule):
    name = "sherlock"
    display_name = "Sherlock"
    icon = "🔍"
    description = "Deep Search — web search for current events, facts, and research"
    version = "1.0"
    category = "utility"
    enabled = True

    _max_results = 3

    SEARCH_KEYWORDS = re.compile(
        r"\b(search|google|dhundho|dhoondho|look\s+up|find\s+(?:out|me)|"
        r"search\s+(?:for|karo)|web\s+search|internet\s+pe|online\s+dekho|"
        r"/search|kya\s+hua|latest|trending|news|current)\b",
        re.IGNORECASE,
    )

    # Patterns that suggest the user wants real-time / current info
    CURRENT_INFO_PATTERNS = re.compile(
        r"\b(today|yesterday|this\s+week|aaj|kal|abhi|right\s+now|"
        r"latest|current|recent|new|breaking|score|weather|"
        r"price\s+of|stock|crypto|bitcoin|election|match|ipl|"
        r"who\s+won|results?\s+of|happening)\b",
        re.IGNORECASE,
    )

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        if self.SEARCH_KEYWORDS.search(text):
            return 0.9

        if intent in ("web_search", "search", "current_events"):
            return 0.88

        # Check with needs_web_search if available
        try:
            from pc_control.web_search import needs_web_search

            query = needs_web_search(text)
            if query:
                return 0.85
        except ImportError:
            pass

        # Current events / real-time info
        if self.CURRENT_INFO_PATTERNS.search(text):
            return 0.7

        # Questions that might need web search
        if re.match(r"^(who|what|when|where|why|how)\s+", text, re.IGNORECASE) and len(text) > 15:
            return 0.3

        return 0.0

    def _extract_query(self, text: str) -> str:
        """Extract the actual search query from user text."""
        # Try needs_web_search first
        try:
            from pc_control.web_search import needs_web_search

            query = needs_web_search(text)
            if query:
                return query
        except ImportError:
            pass

        # Strip search trigger words
        query = self.SEARCH_KEYWORDS.sub("", text).strip()
        # Clean up common prefixes
        query = re.sub(r"^(for|about|regarding|ke\s+bare\s+me|ke\s+baare\s+mein)\s+", "", query, flags=re.IGNORECASE)
        return query.strip() if query.strip() else text

    def execute(self, text: str, context: dict) -> dict:
        """Sync fallback — returns query info for the caller to search."""
        query = self._extract_query(text)
        return {
            "response": f"Searching for: {query}",
            "data": {"query": query, "status": "pending_async"},
            "action": "web_search",
        }

    async def execute_async(self, text: str, context: dict) -> dict:
        """Async execution — performs actual web search."""
        query = self._extract_query(text)

        try:
            from pc_control.web_search import web_search

            results = await web_search(query, max_results=self._max_results)

            if results and not results.startswith("Web search failed"):
                return {
                    "response": results,
                    "data": {
                        "query": query,
                        "results": results,
                        "source": "web_search",
                    },
                    "action": "web_search_complete",
                }
            else:
                return {
                    "response": f"Search for '{query}' didn't return useful results. Try rephrasing?",
                    "data": {"query": query, "error": results},
                    "action": "web_search_failed",
                }
        except ImportError:
            return {
                "response": f"Web search module not available. Query was: {query}",
                "data": {"query": query},
                "action": "error",
            }
        except Exception as e:
            return {
                "response": f"Search failed: {e}",
                "data": {"query": query, "error": str(e)},
                "action": "error",
            }

    def get_system_prompt_addition(self) -> str:
        return (
            "You have web search capability. When the user asks about current events, "
            "recent news, live scores, prices, or anything that requires up-to-date information, "
            "use the search module. Present search results clearly with sources."
        )

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "max_results": self._max_results,
        }

    def update_settings(self, settings: dict):
        super().update_settings(settings)
        if "max_results" in settings:
            self._max_results = max(1, min(10, int(settings["max_results"])))

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "max_results",
                "label": "Max Search Results",
                "type": "range",
                "value": self._max_results,
                "min": 1,
                "max": 10,
                "step": 1,
            },
        ]
