"""
MJ Live Data Fetcher
Fetches real-time data: cricket scores, weather, stock prices, news headlines.
No API keys needed — uses free sources.
"""

import httpx
import re
import json
from typing import Optional


async def get_live_cricket_scores() -> str:
    """Fetch live cricket scores from Cricbuzz."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # Try Cricbuzz API (used by their mobile app)
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            # Cricbuzz matches API
            resp = await client.get(
                "https://www.cricbuzz.com/cricket-match/live-scores",
                headers=headers
            )
            html = resp.text

        # Clean HTML first
        clean_html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        clean_html = re.sub(r'<style[^>]*>.*?</style>', '', clean_html, flags=re.DOTALL)

        # Extract match cards from Cricbuzz HTML
        matches = []

        # Find match blocks
        match_blocks = re.findall(
            r'<div[^>]*class="[^"]*cb-mtch-lst[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>',
            clean_html, re.DOTALL | re.IGNORECASE
        )

        if not match_blocks:
            match_blocks = re.findall(
                r'<div[^>]*class="[^"]*cb-lv-main[^"]*"[^>]*>(.*?)</div>\s*</div>',
                clean_html, re.DOTALL | re.IGNORECASE
            )

        for block in match_blocks[:8]:
            text = _strip_html(block)
            if len(text) > 15 and any(w in text.lower() for w in ['vs', 'v ', 'won', 'lead', 'trail', 'need', 'score', '/', 'overs']):
                matches.append(text[:200])

        # Fallback: find "vs" patterns in clean text
        if not matches:
            full_text = _strip_html(clean_html)
            lines = full_text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 15 and any(w in line.lower() for w in ['vs', 'won by', '/', 'need', 'trail', 'lead']):
                    if not any(skip in line.lower() for skip in ['cookie', 'privacy', 'download', 'app', 'sign']):
                        matches.append(line[:200])

        if not matches:
            # Fallback: try ESPN Cricinfo
            return await _try_espn_scores()

        result = "🏏 LIVE CRICKET SCORES:\n\n"
        for i, match in enumerate(matches[:6], 1):
            result += f"{i}. {match}\n\n"

        result += "Source: Cricbuzz"
        return result

    except Exception as e:
        # Fallback
        return await _try_espn_scores()


async def _try_espn_scores() -> str:
    """Fallback: try Cricbuzz mobile for scores."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
            "Accept": "text/html",
        }

        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(
                "https://m.cricbuzz.com/cricket-match/live-scores",
                headers=headers
            )
            html = resp.text

        # Mobile site is simpler to parse
        clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
        clean = _strip_html(clean)

        # Find lines with scores
        lines = clean.split('\n')
        score_lines = []
        for line in lines:
            line = line.strip()
            if len(line) > 10 and any(w in line.lower() for w in ['vs', 'won by', '/', 'need', 'trail', 'lead', 'overs']):
                if not any(skip in line.lower() for skip in ['cookie', 'privacy', 'download', 'app', 'sign', 'login']):
                    score_lines.append(line[:200])

        if score_lines:
            result = "🏏 LIVE CRICKET SCORES:\n\n"
            seen = set()
            count = 0
            for line in score_lines:
                if line not in seen and count < 6:
                    seen.add(line)
                    count += 1
                    result += f"{count}. {line}\n\n"
            result += "Source: Cricbuzz"
            return result

        return "🏏 Abhi koi live match nahi chal raha, ya scores fetch nahi ho paye. Cricbuzz.com pe check karo."

    except Exception as e:
        return f"🏏 Live scores fetch nahi ho paye: {str(e)[:100]}. Check cricbuzz.com manually."


def _strip_html(text: str) -> str:
    """Aggressively strip ALL HTML tags, attributes, entities from text."""
    # Remove all HTML tags completely
    text = re.sub(r'<[^>]+>', ' ', text)
    # Decode common HTML entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    # Remove any remaining HTML-like artifacts
    text = re.sub(r'(?:href|class|title|id|style|data-\w+)\s*=\s*["\'][^"\']*["\']', '', text)
    text = re.sub(r'(?:href|class|title|id|style)\s*=\s*\S+', '', text)
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n', text)
    return text.strip()


async def get_live_weather(city: str = "Delhi") -> str:
    """Fetch current weather using wttr.in (free, no API key)."""
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                f"https://wttr.in/{city}?format=j1",
                headers={"User-Agent": "curl/7.68.0"}
            )
            data = resp.json()

        current = data["current_condition"][0]
        area = data["nearest_area"][0]

        temp = current["temp_C"]
        feels = current["FeelsLikeC"]
        desc = current["weatherDesc"][0]["value"]
        humidity = current["humidity"]
        wind = current["windspeedKmph"]
        city_name = area["areaName"][0]["value"]

        return (
            f"🌤️ Weather in {city_name}:\n"
            f"Temperature: {temp}°C (feels like {feels}°C)\n"
            f"Condition: {desc}\n"
            f"Humidity: {humidity}%\n"
            f"Wind: {wind} km/h"
        )
    except Exception as e:
        return f"Weather fetch failed: {str(e)[:100]}"


def detect_live_data_request(text: str) -> Optional[str]:
    """
    Detect if user wants live data (not just web search).
    Returns type: 'cricket', 'weather', 'stock', or None.
    """
    lower = text.lower().strip()

    # Cricket score patterns
    cricket_patterns = [
        r"(?:live|aaj ka|abhi ka|current)\s*(?:cricket|ipl|match|t20|odi|test)\s*(?:score|update|result)?",
        r"(?:cricket|ipl|match|t20|odi|test)\s*(?:score|update|result)\s*(?:bata|dikha|kya hai|batao|dikhao|de)?",
        r"(?:score|scor)\s*(?:bata|dikha|kya hai|batao|dikhao|de)",
        r"(?:kaun|kon)\s+(?:jeet|haar|win|lose|jit|playing|khel)\s*(?:raha|rahe|raaha)?",
        r"(?:match|game)\s*(?:ka|ki|ke)?\s*(?:score|result|update|kya hua|chal raha)",
        r"(?:live score|score live|cricket live|ipl live)",
        r"kon jeet raha|kaun khel raha|match.*chal raha|score.*bata",
    ]

    for pat in cricket_patterns:
        if re.search(pat, lower):
            return "cricket"

    # Weather patterns
    weather_patterns = [
        r"(?:weather|mausam|temperature|temp|garmi|sardi|barish|baarish)\s*(?:kya hai|bata|aaj|today|abhi)?",
        r"(?:aaj|today|abhi).*(?:weather|mausam|temperature|garmi|kitni|temp)",
        r"(?:kitni|kya).*(?:garmi|sardi|temperature|temp)\s*(?:hai)?",
    ]

    for pat in weather_patterns:
        if re.search(pat, lower):
            return "weather"

    return None


def extract_city_from_text(text: str) -> str:
    """Extract city name from weather query. Default: Delhi."""
    lower = text.lower()
    # Common Indian cities
    cities = [
        "delhi", "mumbai", "bangalore", "bengaluru", "chennai", "kolkata",
        "hyderabad", "pune", "jaipur", "lucknow", "ahmedabad", "noida",
        "gurgaon", "gurugram", "chandigarh", "bhopal", "indore", "patna",
        "new york", "london", "dubai", "tokyo", "singapore",
    ]
    for city in cities:
        if city in lower:
            return city.title()
    return "Delhi"
