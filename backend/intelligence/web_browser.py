"""
MJ Intelligence: Advanced Web Browser & Search
- DuckDuckGo search (no API key)
- Web page scraping & content extraction
- Article summarization
- Multi-source answer synthesis
"""

import httpx
import re
from datetime import datetime
from typing import Optional


async def deep_search(query: str, max_results: int = 3) -> dict:
    """
    Perform web search — fetch results + scrape top page for context.
    Optimized: only scrape 1 page, reduced timeout.
    """
    results = await _ddg_search(query, max_results)

    # Scrape only top 1 result for speed (saves 1-3 seconds)
    detailed = []
    if results:
        try:
            content = await scrape_page(results[0]["url"], timeout=5)
            if content and len(content) > 100:
                detailed.append({
                    "title": results[0]["title"],
                    "url": results[0]["url"],
                    "content": content[:1500]  # Cap at 1500 chars
                })
        except Exception:
            pass

    return {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "detailed": detailed,
        "result_count": len(results)
    }


async def _ddg_search(query: str, max_results: int = 5) -> list:
    """Search DuckDuckGo and return structured results."""
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            resp = await client.post(url, data={"q": query}, headers=headers)
            html = resp.text

        results = []
        blocks = re.findall(
            r'<a rel="nofollow" class="result__a".*?href="(.*?)".*?>(.*?)</a>.*?'
            r'<a class="result__snippet".*?>(.*?)</a>',
            html,
            re.DOTALL
        )

        for href, title, snippet in blocks[:max_results]:
            title = re.sub(r'<.*?>', '', title).strip()
            snippet = re.sub(r'<.*?>', '', snippet).strip()
            # Clean URL
            clean_url = href
            if "uddg=" in href:
                match = re.search(r'uddg=([^&]+)', href)
                if match:
                    from urllib.parse import unquote
                    clean_url = unquote(match.group(1))

            if title and snippet:
                results.append({
                    "title": title,
                    "snippet": snippet,
                    "url": clean_url
                })

        return results

    except Exception as e:
        return [{"title": "Search Error", "snippet": str(e), "url": ""}]


async def scrape_page(url: str, max_chars: int = 3000, timeout: int = 8) -> Optional[str]:
    """
    Scrape a web page and extract clean text content.
    Removes scripts, styles, nav, ads etc.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9"
        }

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return None
            html = resp.text

        # Remove unwanted tags
        for tag in ['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'noscript']:
            html = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML comments
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

        # Try to extract article/main content first
        article = re.search(r'<(?:article|main)[^>]*>(.*?)</(?:article|main)>', html, re.DOTALL | re.IGNORECASE)
        if article:
            html = article.group(1)

        # Extract text from paragraphs
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
        if paragraphs:
            text = '\n'.join(re.sub(r'<[^>]+>', '', p).strip() for p in paragraphs)
        else:
            # Fallback: strip all tags
            text = re.sub(r'<[^>]+>', ' ', html)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\n\s*\n+', '\n\n', text)

        # Remove very short results (likely navigation remnants)
        if len(text) < 50:
            return None

        return text[:max_chars]

    except Exception:
        return None


def format_search_for_llm(search_data: dict) -> str:
    """Format search results into context string for LLM."""
    if not search_data or not search_data.get("results"):
        return ""

    parts = [f"WEB SEARCH RESULTS for '{search_data['query']}':"]
    parts.append(f"(searched at {search_data['timestamp'][:19]})\n")

    # Quick results
    for i, r in enumerate(search_data["results"], 1):
        parts.append(f"{i}. {r['title']}")
        parts.append(f"   {r['snippet']}")
        if r.get("url"):
            parts.append(f"   Source: {r['url']}")
        parts.append("")

    # Detailed content from scraped pages
    if search_data.get("detailed"):
        parts.append("\nDETAILED CONTENT FROM TOP SOURCES:")
        for d in search_data["detailed"]:
            parts.append(f"\n--- {d['title']} ({d['url']}) ---")
            parts.append(d["content"])
            parts.append("")

    return "\n".join(parts)


def needs_web_search_v2(text: str) -> Optional[str]:
    """
    Enhanced detection for web search needs.
    Returns search query if needed, None otherwise.
    """
    lower = text.lower().strip()

    # Explicit search triggers (Hindi + English)
    explicit_patterns = [
        r"(?:search|google|look up|find out|browse|dhundho|search karo|khojo)\s+(.+)",
        r"(.+)\s+(?:search karo|google karo|dhundho|ke baare me bata|khojo)",
        r"(?:what is|what are|who is|kya hai|kaun hai)\s+(.+)",
    ]
    for pat in explicit_patterns:
        m = re.search(pat, lower)
        if m:
            query = m.group(1).strip()
            for filler in ["for", "about", "on", "please", "karo", "do", "na", "the", "a"]:
                query = re.sub(r'\b' + filler + r'\b', '', query).strip()
            if len(query) > 2:
                return query

    # Current/real-time info patterns
    realtime_patterns = [
        r"(?:who is|kaun hai).+(?:president|pm|prime minister|ceo|captain|minister|leader)",
        r"(?:latest|current|today|aaj|abhi|recent|new|naya).+(?:news|score|price|rate|weather|update|version)",
        r"(?:ipl|world cup|cricket|football|match|game).+(?:score|result|winner|schedule)",
        r"(?:stock|share|bitcoin|crypto|nifty|sensex).+(?:price|rate|value|today)",
        r"(?:what happened|kya hua|news).+(?:today|yesterday|aaj|kal)",
        r"(?:release date|launch|when.+(?:release|launch|come out|aayega))",
        r"(?:how much|kitna|price|cost|keemat|salary).+(?:cost|price|hai|earn)",
        r"(?:top|best|popular|trending).+(?:movies|songs|games|apps|phones|laptops|books)",
        r"(?:compare|vs|versus|difference).+(?:between|and|aur|ya)",
        r"(?:how to|tutorial|guide|steps|tarika).+(?:install|setup|fix|solve|make|create|build)",
        r"(?:review|rating|opinion).+(?:of|about|ka)",
        r"(?:download|install|get|paao).+(?:app|software|tool|game)",
        r"(?:recipe|ingredients|kaise banaye|how to (?:cook|make|bake))",
        r"(?:weather|mausam|temperature|barish).*(?:today|tomorrow|aaj|kal|week)?",
        r"(?:meaning|matlab|definition|translate)\s+(?:of\s+)?",
    ]

    for pat in realtime_patterns:
        if re.search(pat, lower):
            return text.strip()

    # Question words that likely need external info
    question_starters = ["who is", "what is", "where is", "when did", "how does",
                         "why does", "which is", "can you tell me about",
                         "kaun hai", "kya hai", "kahan hai", "kab hua", "kaise"]
    for q in question_starters:
        if lower.startswith(q):
            return text.strip()

    return None
