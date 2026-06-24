"""
MJ Intelligence: Advanced Web Browser & Search v2
- DuckDuckGo search (no API key)
- Web page scraping & content extraction
- Multi-source deep research with parallel scraping
- Source quality ranking & citation generation
- Article summarization
"""

import httpx
import re
import asyncio
import time
import logging
from datetime import datetime
from typing import Optional, List, Dict

logger = logging.getLogger("mj.web_browser")


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


async def deep_research(query: str, max_sources: int = 5, scrape_top: int = 3) -> dict:
    """
    Multi-source deep research: search → scrape top N pages in parallel →
    extract key facts → generate citations.
    Returns structured research with sources and citations.
    """
    start = time.time()
    results = await _ddg_search(query, max_sources)

    if not results:
        return {
            "query": query, "timestamp": datetime.now().isoformat(),
            "sources": [], "findings": [], "citations": [],
            "duration_ms": round((time.time() - start) * 1000),
        }

    # Scrape top N pages in parallel
    scrape_targets = results[:scrape_top]
    scrape_tasks = [scrape_page(r["url"], max_chars=3000, timeout=6) for r in scrape_targets]
    scraped = await asyncio.gather(*scrape_tasks, return_exceptions=True)

    sources = []
    findings = []
    citations = []

    for i, (result, content) in enumerate(zip(scrape_targets, scraped)):
        source = {
            "index": i + 1,
            "title": result["title"],
            "url": result["url"],
            "snippet": result.get("snippet", ""),
            "scraped": False,
            "content_length": 0,
        }

        if isinstance(content, str) and content and len(content) > 50:
            source["scraped"] = True
            source["content_length"] = len(content)

            # Extract key sentences (first 5 meaningful sentences)
            sentences = _extract_key_sentences(content, query, max_sentences=5)
            for sent in sentences:
                findings.append({
                    "text": sent,
                    "source_index": i + 1,
                    "source_title": result["title"],
                    "source_url": result["url"],
                })

            # Generate citation
            citations.append({
                "index": i + 1,
                "title": result["title"],
                "url": result["url"],
                "accessed": datetime.now().strftime("%Y-%m-%d"),
                "inline": f"[{i + 1}]",
                "full": f'[{i + 1}] "{result["title"]}." {result["url"]}. Accessed {datetime.now().strftime("%d %b %Y")}.',
            })

        sources.append(source)

    # Also add non-scraped results as sources
    for i, result in enumerate(results[scrape_top:], scrape_top + 1):
        sources.append({
            "index": i,
            "title": result["title"],
            "url": result["url"],
            "snippet": result.get("snippet", ""),
            "scraped": False,
            "content_length": 0,
        })

    duration = round((time.time() - start) * 1000)
    return {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "sources": sources,
        "findings": findings,
        "citations": citations,
        "stats": {
            "total_results": len(results),
            "pages_scraped": sum(1 for s in sources if s["scraped"]),
            "findings_extracted": len(findings),
            "duration_ms": duration,
        },
    }


def _extract_key_sentences(text: str, query: str, max_sentences: int = 5) -> List[str]:
    """Extract the most relevant sentences from scraped content."""
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 30 and len(s.strip()) < 500]

    if not sentences:
        return []

    # Score sentences by query term overlap
    query_terms = set(re.findall(r'\w+', query.lower()))
    scored = []
    for sent in sentences:
        sent_terms = set(re.findall(r'\w+', sent.lower()))
        overlap = len(query_terms & sent_terms)
        # Bonus for sentences with numbers/data
        data_bonus = 0.5 if re.search(r'\d+', sent) else 0
        scored.append((sent, overlap + data_bonus))

    scored.sort(key=lambda x: -x[1])
    return [s[0] for s in scored[:max_sentences] if s[1] > 0]


def format_research_for_llm(research: dict) -> str:
    """Format deep research results into LLM context with citations."""
    if not research or not research.get("findings"):
        return format_search_for_llm(research) if research else ""

    parts = [f"DEEP RESEARCH RESULTS for '{research['query']}':"]
    stats = research.get("stats", {})
    parts.append(f"({stats.get('pages_scraped', 0)} sources scraped, "
                 f"{stats.get('findings_extracted', 0)} findings)\n")

    # Findings grouped by source
    by_source = {}
    for f in research["findings"]:
        idx = f["source_index"]
        if idx not in by_source:
            by_source[idx] = {"title": f["source_title"], "url": f["source_url"], "facts": []}
        by_source[idx]["facts"].append(f["text"])

    for idx, src in sorted(by_source.items()):
        parts.append(f"\n[{idx}] {src['title']}")
        parts.append(f"    Source: {src['url']}")
        for fact in src["facts"]:
            parts.append(f"    - {fact}")

    # Citations footer
    if research.get("citations"):
        parts.append("\n\nSOURCES:")
        for c in research["citations"]:
            parts.append(c["full"])

    parts.append("\nIMPORTANT: Cite sources using [N] notation when using this information.")
    return "\n".join(parts)


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
        r"(?:latest|current|today|aaj|abhi|recent|new|naya|live).+(?:news|score|price|rate|weather|update|version|match)",
        r"(?:ipl|world cup|cricket|football|match|game|t20|odi|test match).+(?:score|result|winner|schedule|update|kya hua|live)",
        r"(?:score|result|winner|schedule).+(?:ipl|cricket|football|match|game|t20|odi|test)",
        r"(?:live|abhi ka|aaj ka|current)\s+(?:score|match|game|cricket|football|ipl|news)",
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
        r"(?:score|scor)\s*(?:bata|dikha|kya hai|batao|dikhao)",
        r"(?:kaun|kon)\s+(?:jeet|haar|win|lose|jit|playing)",
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
