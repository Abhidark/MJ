"""
Web Search for MJ — fetches real search results using DuckDuckGo HTML.
No API key needed.
"""

import httpx
import re


async def web_search(query: str, max_results: int = 3) -> str:
    """
    Search the web and return a summary string for the LLM.
    Uses DuckDuckGo HTML version (no API key needed).
    """
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, data={"q": query}, headers=headers)
            html = resp.text

        # Extract results from HTML
        results = []
        # Find result blocks
        blocks = re.findall(
            r'<a rel="nofollow" class="result__a".*?href="(.*?)".*?>(.*?)</a>.*?'
            r'<a class="result__snippet".*?>(.*?)</a>',
            html,
            re.DOTALL
        )

        for href, title, snippet in blocks[:max_results]:
            title = re.sub(r'<.*?>', '', title).strip()
            snippet = re.sub(r'<.*?>', '', snippet).strip()
            if title and snippet:
                results.append(f"- {title}: {snippet}")

        if results:
            return f"Web search results for '{query}':\n" + "\n".join(results)
        else:
            return f"No web results found for '{query}'."

    except Exception as e:
        return f"Web search failed: {str(e)}"


def needs_web_search(text: str) -> str | None:
    """
    Detect if user's question needs web search.
    Returns search query if yes, None if no.
    """
    lower = text.lower().strip()

    # Explicit search requests
    search_triggers = [
        r"(?:search|google|look up|find out|dhundho|search karo)\s+(.+)",
        r"(.+)\s+(?:search karo|google karo|dhundho|ke baare me bata)",
    ]
    for pat in search_triggers:
        m = re.search(pat, lower)
        if m:
            query = m.group(1).strip()
            for filler in ["for", "about", "on", "please", "karo", "do", "na"]:
                query = query.replace(filler, "").strip()
            if len(query) > 2:
                return query

    # Questions that likely need current info
    current_info_patterns = [
        r"(?:who is|kaun hai).+(?:president|pm|prime minister|ceo|captain|minister)",
        r"(?:latest|current|today|aaj|abhi).+(?:news|score|price|rate|weather|update)",
        r"(?:ipl|world cup|cricket|football|match).+(?:score|result|winner)",
        r"(?:stock|share|bitcoin|crypto).+(?:price|rate|value)",
        r"(?:what happened|kya hua).+(?:today|yesterday|aaj|kal)",
        r"(?:release date|launch date|when.+(?:release|launch|come out))",
        r"(?:how much|kitna|price|cost|keemat).+(?:cost|price|hai)",
    ]

    for pat in current_info_patterns:
        if re.search(pat, lower):
            # Use the original text as search query
            return text.strip()

    return None
