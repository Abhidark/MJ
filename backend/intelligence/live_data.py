"""
MJ Live Data Fetcher
Fetches real-time data: cricket scores, weather, stock prices, news headlines.
Weather uses WeatherAPI.com (free tier, 1M calls/month).
"""

import httpx
import os
import re
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

# ── Weather cache (avoid repeated API calls) ──
_weather_cache = {}  # key: city_lower → {data, timestamp}
WEATHER_CACHE_TTL = 600  # 10 minutes

def _get_weather_api_key() -> Optional[str]:
    """Load WEATHER_API_KEY from env or .env file."""
    key = os.environ.get("WEATHER_API_KEY")
    if key:
        return key
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("WEATHER_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                if key:
                    os.environ["WEATHER_API_KEY"] = key
                    return key
    return None


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
    """Fetch weather and return short text summary (for backward compat)."""
    data = await get_weather_data(city)
    if data.get("error"):
        return f"Weather fetch failed: {data['error']}"
    c = data["current"]
    return (
        f"🌤️ Weather in {data['city']}, {data['country']}:\n"
        f"Temperature: {c['temp_c']}°C (feels like {c['feels_like_c']}°C)\n"
        f"Condition: {c['condition']}\n"
        f"Humidity: {c['humidity']}%\n"
        f"Wind: {c['wind_kph']} km/h\n"
        f"UV Index: {c['uv']} | AQI: {c.get('aqi', 'N/A')}\n"
        f"Sunrise: {data['astronomy']['sunrise']} | Sunset: {data['astronomy']['sunset']}"
    )


async def get_weather_data(city: str = "Delhi", days: int = 3) -> dict:
    """
    Fetch full structured weather data from WeatherAPI.com.
    Returns dict with current + hourly + forecast + astronomy + AQI.
    Cached for 10 minutes per city.
    """
    cache_key = city.lower().strip()

    # Check cache
    if cache_key in _weather_cache:
        cached = _weather_cache[cache_key]
        if time.time() - cached["timestamp"] < WEATHER_CACHE_TTL:
            return cached["data"]

    api_key = _get_weather_api_key()

    # Fallback to wttr.in if no API key
    if not api_key:
        return await _weather_fallback_wttr(city)

    try:
        url = "https://api.weatherapi.com/v1/forecast.json"
        params = {
            "key": api_key,
            "q": city,
            "days": min(days, 7),
            "aqi": "yes",
            "alerts": "yes",
        }

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 400:
                err = resp.json().get("error", {}).get("message", "Invalid city")
                return {"error": err}
            if resp.status_code == 403:
                return {"error": "Weather API key invalid or expired"}
            resp.raise_for_status()
            raw = resp.json()

        # Parse into clean structure
        loc = raw["location"]
        cur = raw["current"]
        forecast_days = raw.get("forecast", {}).get("forecastday", [])

        # AQI data
        aqi_data = cur.get("air_quality", {})
        aqi_index = aqi_data.get("us-epa-index", None)
        aqi_labels = {1: "Good", 2: "Moderate", 3: "Unhealthy (Sensitive)", 4: "Unhealthy", 5: "Very Unhealthy", 6: "Hazardous"}

        # Astronomy from first forecast day
        astro = forecast_days[0].get("astro", {}) if forecast_days else {}

        # Today's hourly forecast
        today_hours = forecast_days[0].get("hour", []) if forecast_days else []
        hourly = []
        for h in today_hours:
            hourly.append({
                "time": h["time"].split(" ")[1] if " " in h["time"] else h["time"],
                "temp_c": h["temp_c"],
                "condition": h["condition"]["text"],
                "icon": h["condition"]["icon"],
                "chance_of_rain": h.get("chance_of_rain", 0),
                "wind_kph": h["wind_kph"],
                "humidity": h["humidity"],
            })

        # Multi-day forecast
        daily = []
        for d in forecast_days:
            day = d["day"]
            daily.append({
                "date": d["date"],
                "max_temp_c": day["maxtemp_c"],
                "min_temp_c": day["mintemp_c"],
                "avg_temp_c": day["avgtemp_c"],
                "condition": day["condition"]["text"],
                "icon": day["condition"]["icon"],
                "chance_of_rain": day.get("daily_chance_of_rain", 0),
                "max_wind_kph": day["maxwind_kph"],
                "avg_humidity": day["avghumidity"],
                "uv": day["uv"],
                "sunrise": d.get("astro", {}).get("sunrise", ""),
                "sunset": d.get("astro", {}).get("sunset", ""),
            })

        # Alerts
        alerts = []
        for a in raw.get("alerts", {}).get("alert", []):
            alerts.append({
                "headline": a.get("headline", ""),
                "severity": a.get("severity", ""),
                "event": a.get("event", ""),
            })

        result = {
            "city": loc["name"],
            "region": loc["region"],
            "country": loc["country"],
            "lat": loc["lat"],
            "lon": loc["lon"],
            "localtime": loc["localtime"],
            "current": {
                "temp_c": cur["temp_c"],
                "temp_f": cur["temp_f"],
                "feels_like_c": cur["feelslike_c"],
                "feels_like_f": cur["feelslike_f"],
                "condition": cur["condition"]["text"],
                "icon": cur["condition"]["icon"],
                "wind_kph": cur["wind_kph"],
                "wind_dir": cur["wind_dir"],
                "humidity": cur["humidity"],
                "pressure_mb": cur["pressure_mb"],
                "visibility_km": cur["vis_km"],
                "uv": cur["uv"],
                "cloud": cur["cloud"],
                "aqi": aqi_labels.get(aqi_index, "N/A") if aqi_index else "N/A",
                "aqi_index": aqi_index,
                "is_day": cur["is_day"],
            },
            "astronomy": {
                "sunrise": astro.get("sunrise", ""),
                "sunset": astro.get("sunset", ""),
                "moonrise": astro.get("moonrise", ""),
                "moonset": astro.get("moonset", ""),
                "moon_phase": astro.get("moon_phase", ""),
            },
            "hourly": hourly,
            "forecast": daily,
            "alerts": alerts,
            "cached": False,
        }

        # Cache it
        _weather_cache[cache_key] = {"data": result, "timestamp": time.time()}
        return result

    except httpx.ConnectError:
        return {"error": "Cannot connect to Weather API. Check internet."}
    except httpx.ReadTimeout:
        return {"error": "Weather API timeout. Try again."}
    except Exception as e:
        return {"error": f"Weather fetch failed: {str(e)[:150]}"}


async def _weather_fallback_wttr(city: str) -> dict:
    """Fallback to wttr.in when no WeatherAPI.com key is set."""
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                f"https://wttr.in/{city}?format=j1",
                headers={"User-Agent": "curl/7.68.0"}
            )
            data = resp.json()

        current = data["current_condition"][0]
        area = data["nearest_area"][0]
        return {
            "city": area["areaName"][0]["value"],
            "region": area.get("region", [{}])[0].get("value", ""),
            "country": area.get("country", [{}])[0].get("value", ""),
            "localtime": "",
            "current": {
                "temp_c": float(current["temp_C"]),
                "temp_f": float(current["temp_F"]),
                "feels_like_c": float(current["FeelsLikeC"]),
                "feels_like_f": float(current["FeelsLikeF"]),
                "condition": current["weatherDesc"][0]["value"],
                "icon": "",
                "wind_kph": float(current["windspeedKmph"]),
                "wind_dir": current.get("winddir16Point", ""),
                "humidity": int(current["humidity"]),
                "pressure_mb": float(current.get("pressure", 0)),
                "visibility_km": float(current.get("visibility", 0)),
                "uv": float(current.get("uvIndex", 0)),
                "cloud": int(current.get("cloudcover", 0)),
                "aqi": "N/A",
                "aqi_index": None,
                "is_day": 1,
            },
            "astronomy": {"sunrise": "", "sunset": "", "moonrise": "", "moonset": "", "moon_phase": ""},
            "hourly": [],
            "forecast": [],
            "alerts": [],
            "cached": False,
            "fallback": True,
        }
    except Exception as e:
        return {"error": f"Weather fetch failed: {str(e)[:100]}"}


STOCK_ALIASES = {
    "reliance": "RELIANCE.NS", "tcs": "TCS.NS", "infosys": "INFY.NS",
    "hdfc": "HDFCBANK.NS", "sbi": "SBIN.NS", "icici": "ICICIBANK.NS",
    "wipro": "WIPRO.NS", "hcl": "HCLTECH.NS", "adani": "ADANIENT.NS",
    "tata motors": "TATAMOTORS.NS", "tatamotors": "TATAMOTORS.NS",
    "tata steel": "TATASTEEL.NS", "tatasteel": "TATASTEEL.NS",
    "bajaj": "BAJFINANCE.NS", "maruti": "MARUTI.NS", "airtel": "BHARTIARTL.NS",
    "sensex": "^BSESN", "nifty": "^NSEI", "nifty 50": "^NSEI",
    "apple": "AAPL", "google": "GOOGL", "microsoft": "MSFT",
    "amazon": "AMZN", "tesla": "TSLA", "meta": "META", "nvidia": "NVDA",
}


async def get_live_stock_price(query: str) -> str:
    """Fetch stock price from Yahoo Finance (no API key needed)."""
    try:
        lower = query.lower().strip()
        symbol = STOCK_ALIASES.get(lower, lower.upper())

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
            resp = await client.get(url, headers=headers)
            data = resp.json()

        result_data = data.get("chart", {}).get("result", [])
        if not result_data:
            return f"📈 '{query}' ka stock data nahi mila. Symbol check karo."

        meta = result_data[0].get("meta", {})
        price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("chartPreviousClose", 0)
        currency = meta.get("currency", "INR")
        name = meta.get("shortName", symbol)

        change = price - prev_close if prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0
        arrow = "🟢 +" if change >= 0 else "🔴 "

        # Get day high/low from indicators
        indicators = result_data[0].get("indicators", {}).get("quote", [{}])[0]
        highs = [h for h in (indicators.get("high") or []) if h is not None]
        lows = [l for l in (indicators.get("low") or []) if l is not None]
        day_high = max(highs[-1:]) if highs else 0
        day_low = min(lows[-1:]) if lows else 0

        result = f"📈 {name} ({symbol})\n"
        result += f"Price: {currency} {price:,.2f}\n"
        result += f"Change: {arrow}{change:,.2f} ({change_pct:+.2f}%)\n"
        if day_high and day_low:
            result += f"Day Range: {currency} {day_low:,.2f} - {day_high:,.2f}\n"
        result += f"Prev Close: {currency} {prev_close:,.2f}"

        return result

    except Exception as e:
        return f"📈 Stock data fetch nahi ho paya: {str(e)[:100]}"


async def get_live_news(topic: str = "india") -> str:
    """Fetch latest news headlines from Google News RSS (no API key needed)."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        # Build Google News RSS URL
        if topic.lower() in ["india", "top", "latest", "aaj", "today", "headlines"]:
            url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
        else:
            url = f"https://news.google.com/rss/search?q={topic}&hl=en-IN&gl=IN&ceid=IN:en"

        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)

        # Parse RSS XML
        root = ET.fromstring(resp.text)
        items = root.findall(".//item")

        if not items:
            return f"📰 '{topic}' se koi news nahi mili."

        result = f"📰 Latest News — {topic.title()}:\n\n"
        for i, item in enumerate(items[:8], 1):
            title = item.findtext("title", "")
            source = item.findtext("source", "")
            pub_date = item.findtext("pubDate", "")
            # Clean up date
            if pub_date:
                pub_date = pub_date.split("+")[0].strip()
                pub_date = pub_date.replace("GMT", "").strip()

            result += f"{i}. {title}"
            if source:
                result += f" — {source}"
            result += "\n"

        result += "\nSource: Google News"
        return result

    except Exception as e:
        return f"📰 News fetch nahi ho paya: {str(e)[:100]}"


def extract_stock_from_text(text: str) -> str:
    """Extract stock name/symbol from query."""
    lower = text.lower()
    for alias in STOCK_ALIASES:
        if alias in lower:
            return alias
    # Try to find a ticker-like word (all caps, 2-5 chars)
    tickers = re.findall(r'\b([A-Z]{2,5})\b', text)
    if tickers:
        return tickers[0]
    return ""


def extract_news_topic(text: str) -> str:
    """Extract news topic from query."""
    lower = text.lower()
    # Remove common filler words
    for filler in ["latest", "aaj ka", "aaj ki", "today", "news", "headlines",
                    "kya hai", "batao", "dikhao", "bata", "show", "get", "khabar", "samachar"]:
        lower = lower.replace(filler, "")
    topic = lower.strip()
    return topic if len(topic) > 1 else "india"


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

    # Stock / market patterns
    stock_patterns = [
        r"(?:stock|share|price|rate)\s*(?:of|ka|ki)?\s*(?:kya hai|bata|check|show)?",
        r"(?:kya|kitna|kitni|what)\s*(?:hai|is)?\s*(?:price|rate|stock|share)",
        r"(?:sensex|nifty|market)\s*(?:kya hai|kitna|check|status|today|aaj)?",
        r"\b(?:reliance|tcs|infosys|hdfc|sbi|icici|wipro|adani|tata|bajaj|maruti|airtel)\b",
        r"\b(?:apple|google|microsoft|amazon|tesla|meta|nvidia)\b\s*(?:stock|share|price)?",
    ]
    for pat in stock_patterns:
        if re.search(pat, lower):
            return "stock"

    # News patterns
    news_patterns = [
        r"(?:news|khabar|samachar|headlines?)\s*(?:bata|dikha|kya hai|show|today|aaj)?",
        r"(?:aaj|today|latest|top)\s*(?:ka|ki|ke)?\s*(?:news|khabar|samachar|headlines?)",
        r"(?:kya ho raha|what.s happening|kya chal raha)",
    ]
    for pat in news_patterns:
        if re.search(pat, lower):
            return "news"

    return None


def extract_city_from_text(text: str) -> str:
    """Extract city name from weather query. Default: Gurgaon (user's location)."""
    lower = text.lower()

    # Try regex: "weather in <city>", "mausam <city>", "<city> ka mausam"
    m = re.search(r"(?:weather|mausam|forecast|temperature)\s+(?:in|of|for|ka|ki)\s+([a-zA-Z\s]+)", lower)
    if m:
        city = m.group(1).strip().rstrip("?.,!")
        if len(city) > 1:
            return city.title()

    m = re.search(r"([a-zA-Z\s]+?)\s+(?:ka|ki|me|mein|mai)\s+(?:weather|mausam|temperature)", lower)
    if m:
        city = m.group(1).strip().rstrip("?.,!")
        if len(city) > 1:
            return city.title()

    # Known cities list
    cities = [
        "delhi", "new delhi", "mumbai", "bangalore", "bengaluru", "chennai",
        "kolkata", "hyderabad", "pune", "jaipur", "lucknow", "ahmedabad",
        "noida", "gurgaon", "gurugram", "chandigarh", "bhopal", "indore",
        "patna", "ranchi", "shimla", "manali", "goa", "varanasi", "agra",
        "surat", "nagpur", "vadodara", "coimbatore", "kochi", "visakhapatnam",
        "new york", "london", "dubai", "tokyo", "singapore", "paris",
        "san francisco", "los angeles", "chicago", "toronto", "sydney",
        "beijing", "shanghai", "bangkok", "hong kong", "seoul",
    ]
    for city in cities:
        if city in lower:
            return city.title()

    # Check for "weather in <unknown city>" pattern — pass through as-is
    m2 = re.search(r"(?:weather|mausam|forecast)\s+(?:in|of|for)\s+([a-zA-Z][a-zA-Z\s]{1,30})", lower)
    if m2:
        extracted = m2.group(1).strip().rstrip("?.,!")
        if len(extracted) > 1:
            return extracted.title()

    return "auto:ip"  # WeatherAPI.com auto-detects location from IP


def extract_forecast_type(text: str) -> str:
    """Detect if user wants current, today, or multi-day forecast."""
    lower = text.lower()
    if any(w in lower for w in ["week", "7 day", "next week", "hafte", "weekly", "agle hafte"]):
        return "week"
    if any(w in lower for w in ["tomorrow", "kal", "agle din", "next day"]):
        return "tomorrow"
    if any(w in lower for w in ["forecast", "prediction", "aage", "upcoming"]):
        return "forecast"
    return "current"
