"""
Atlas Module -- Web Fetching & API Calls
"""

import re
from modules.base_module import BaseModule


class AtlasModule(BaseModule):
    name = "atlas"
    display_name = "Atlas"
    icon = "\U0001f310"
    description = "Web fetching, URL content retrieval, and API calls"
    version = "1.0"
    category = "utility"
    enabled = True

    KEYWORDS = [
        "fetch", "website", "url", "api call", "download page",
        "web page", "http", "get url", "scrape", "web content",
        "open url", "read website", "visit",
    ]

    URL_PATTERN = re.compile(
        r"https?://[^\s<>\"']+|www\.[^\s<>\"']+",
        re.IGNORECASE,
    )

    def __init__(self):
        self.timeout = 10        # seconds
        self.max_content_length = 5000  # characters

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        lower = text.lower()

        # URL present in text is a strong signal
        if self.URL_PATTERN.search(text):
            return 0.9

        for kw in self.KEYWORDS:
            if kw in lower:
                return 0.85

        if intent in ("web_fetch", "api_call", "url_fetch"):
            return 0.85

        return 0.0

    def _extract_url(self, text: str) -> str | None:
        """Extract the first URL from text."""
        match = self.URL_PATTERN.search(text)
        if match:
            url = match.group(0)
            if not url.startswith("http"):
                url = "https://" + url
            return url
        return None

    def execute(self, text: str, context: dict) -> dict:
        """Synchronous fallback -- just extracts the URL and signals async is needed."""
        url = self._extract_url(text)
        if not url:
            return {
                "response": (
                    "Please provide a URL to fetch. "
                    "Example: 'fetch https://example.com'"
                ),
                "data": None,
                "action": "need_url",
            }

        return {
            "response": f"URL detected: {url}. Use async execution for fetching.",
            "data": {"url": url},
            "action": "url_detected",
        }

    async def execute_async(self, text: str, context: dict) -> dict:
        """Fetch URL content asynchronously using httpx."""
        url = self._extract_url(text)
        if not url:
            return {
                "response": (
                    "Please provide a URL to fetch. "
                    "Example: 'fetch https://example.com'"
                ),
                "data": None,
                "action": "need_url",
            }

        try:
            import httpx
        except ImportError:
            return {
                "response": "httpx is not installed. Install it with: pip install httpx",
                "data": None,
                "action": "error",
            }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": "MJ-Assistant/1.0"},
            ) as client:
                response = await client.get(url)

            status = response.status_code
            content_type = response.headers.get("content-type", "unknown")

            if "text/html" in content_type or "text/plain" in content_type:
                body = response.text
                # Strip HTML tags for a rough text extraction
                clean = re.sub(r"<script[^>]*>.*?</script>", "", body, flags=re.DOTALL)
                clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL)
                clean = re.sub(r"<[^>]+>", " ", clean)
                clean = re.sub(r"\s+", " ", clean).strip()

                if len(clean) > self.max_content_length:
                    clean = clean[: self.max_content_length] + "... (truncated)"
            elif "application/json" in content_type:
                clean = response.text
                if len(clean) > self.max_content_length:
                    clean = clean[: self.max_content_length] + "... (truncated)"
            else:
                clean = f"[Binary content: {content_type}, {len(response.content)} bytes]"

            return {
                "response": (
                    f"Fetched: {url}\n"
                    f"Status: {status}\n"
                    f"Type: {content_type}\n\n"
                    f"Content:\n{clean}"
                ),
                "data": {
                    "url": url,
                    "status_code": status,
                    "content_type": content_type,
                    "content": clean,
                    "content_length": len(response.content),
                },
                "action": "web_fetch",
            }

        except httpx.TimeoutException:
            return {
                "response": f"Request to {url} timed out after {self.timeout}s.",
                "data": {"url": url},
                "action": "error",
            }
        except httpx.RequestError as e:
            return {
                "response": f"Failed to fetch {url}: {e}",
                "data": {"url": url, "error": str(e)},
                "action": "error",
            }

    def get_system_prompt_addition(self) -> str:
        return (
            "You can fetch web pages and API endpoints. "
            "Provide URLs to retrieve their content."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        url = self._extract_url(text)
        if url:
            return f"[Atlas Web Module] User wants to fetch: {url}"
        return "[Atlas Web Module] User is asking about web fetching or API calls."

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "timeout": self.timeout,
            "max_content_length": self.max_content_length,
        }

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "timeout" in settings:
            self.timeout = max(5, min(30, int(settings["timeout"])))
        if "max_content_length" in settings:
            self.max_content_length = max(1000, min(50000, int(settings["max_content_length"])))

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "timeout",
                "label": "Request Timeout (seconds)",
                "type": "range",
                "value": self.timeout,
                "min": 5,
                "max": 30,
                "step": 1,
            },
            {
                "key": "max_content_length",
                "label": "Max Content Length (chars)",
                "type": "range",
                "value": self.max_content_length,
                "min": 1000,
                "max": 50000,
                "step": 1000,
            },
        ]
