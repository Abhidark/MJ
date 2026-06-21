"""
Mercury Module -- Finance
Fetches cryptocurrency prices, currency conversion rates, and financial data.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from modules.base_module import BaseModule

try:
    import httpx
except ImportError:
    httpx = None


class MercuryModule(BaseModule):
    name = "mercury"
    display_name = "Mercury"
    icon = "\U0001f4b0"  # money bag
    description = "Finance tools -- crypto prices, currency conversion, and market data"
    version = "1.0"
    category = "utility"
    enabled = True

    KEYWORDS = [
        r"\bprice\b", r"\bstock\b", r"\bcrypto\b", r"\bbitcoin\b", r"\bethereum\b",
        r"\bcurrency\b", r"\bconvert\b", r"\brupees?\b", r"\bdollar\b", r"\beur\b",
        r"\binr\b", r"\busd\b", r"\bmarket\b", r"\bcoin\b", r"\brate\b",
        r"\bkitna\b.*\b(dollar|rupee|paisa)\b", r"\bexchange\s+rate\b",
        r"\bsolana\b", r"\bdoge\b", r"\bbnb\b", r"\bxrp\b",
    ]

    CRYPTO_MAP = {
        "bitcoin": "bitcoin", "btc": "bitcoin",
        "ethereum": "ethereum", "eth": "ethereum",
        "solana": "solana", "sol": "solana",
        "dogecoin": "dogecoin", "doge": "dogecoin",
        "bnb": "binancecoin", "binance": "binancecoin",
        "xrp": "ripple", "ripple": "ripple",
        "cardano": "cardano", "ada": "cardano",
        "polkadot": "polkadot", "dot": "polkadot",
        "polygon": "matic-network", "matic": "matic-network",
        "litecoin": "litecoin", "ltc": "litecoin",
    }

    CURRENCY_SYMBOLS = {
        "inr": "INR", "rupee": "INR", "rupees": "INR",
        "usd": "USD", "dollar": "USD", "dollars": "USD",
        "eur": "EUR", "euro": "EUR", "euros": "EUR",
        "gbp": "GBP", "pound": "GBP", "pounds": "GBP",
        "jpy": "JPY", "yen": "JPY",
        "cad": "CAD", "aud": "AUD", "cny": "CNY",
    }

    def __init__(self):
        self.default_currency = "INR"

    def can_handle(self, text: str, intent: str, context: dict) -> float:
        text_lower = text.lower()
        for pattern in self.KEYWORDS:
            if re.search(pattern, text_lower):
                return 0.85
        if intent in ("crypto_price", "currency_convert", "finance", "stock_price"):
            return 0.9
        return 0.0

    def _detect_crypto(self, text: str) -> str | None:
        text_lower = text.lower()
        for keyword, coin_id in self.CRYPTO_MAP.items():
            if keyword in text_lower:
                return coin_id
        return None

    def _detect_currencies(self, text: str) -> tuple[str | None, str | None]:
        text_lower = text.lower()
        found = []
        for keyword, code in self.CURRENCY_SYMBOLS.items():
            if keyword in text_lower and code not in found:
                found.append(code)
        if len(found) >= 2:
            return found[0], found[1]
        elif len(found) == 1:
            return found[0], self.default_currency if found[0] != self.default_currency else "USD"
        return None, None

    def _detect_amount(self, text: str) -> float:
        match = re.search(r"(\d+(?:,\d{3})*(?:\.\d+)?)", text.replace(",", ""))
        if match:
            return float(match.group(1))
        return 1.0

    def execute(self, text: str, context: dict) -> dict:
        return {
            "response": "Mercury requires async execution for API calls. Use execute_async.",
            "data": None,
            "action": "needs_async",
        }

    async def execute_async(self, text: str, context: dict) -> dict:
        if httpx is None:
            return {
                "response": "httpx is not installed. Run: pip install httpx",
                "data": None,
                "action": "error",
            }

        crypto = self._detect_crypto(text)
        if crypto:
            return await self._fetch_crypto_price(crypto)

        from_curr, to_curr = self._detect_currencies(text)
        if from_curr and to_curr:
            amount = self._detect_amount(text)
            return await self._convert_currency(amount, from_curr, to_curr)

        # Default: show top crypto prices
        return await self._fetch_top_crypto()

    async def _fetch_crypto_price(self, coin_id: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                url = (
                    f"https://api.coingecko.com/api/v3/simple/price"
                    f"?ids={coin_id}&vs_currencies=usd,inr,eur&include_24hr_change=true"
                )
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            if coin_id not in data:
                return {
                    "response": f"Could not find data for '{coin_id}'.",
                    "data": None,
                    "action": "not_found",
                }

            info = data[coin_id]
            usd = info.get("usd", "N/A")
            inr = info.get("inr", "N/A")
            eur = info.get("eur", "N/A")
            change = info.get("usd_24h_change", 0)
            trend = "\U0001f4c8" if change >= 0 else "\U0001f4c9"
            change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"

            response = (
                f"{trend} **{coin_id.replace('-', ' ').title()}** Price:\n\n"
                f"  USD: ${usd:,.2f}\n"
                f"  INR: ₹{inr:,.2f}\n"
                f"  EUR: €{eur:,.2f}\n"
                f"  24h Change: {change_str}"
            )
            return {"response": response, "data": info, "action": "crypto_price"}

        except Exception as e:
            return {
                "response": f"Failed to fetch crypto price: {str(e)}",
                "data": {"error": str(e)},
                "action": "error",
            }

    async def _convert_currency(self, amount: float, from_curr: str, to_curr: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                url = f"https://api.exchangerate-api.com/v4/latest/{from_curr}"
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            rate = data["rates"].get(to_curr)
            if rate is None:
                return {
                    "response": f"Currency '{to_curr}' not supported.",
                    "data": None,
                    "action": "not_found",
                }

            converted = amount * rate
            response = (
                f"\U0001f4b1 **Currency Conversion:**\n\n"
                f"  {amount:,.2f} {from_curr} = **{converted:,.2f} {to_curr}**\n"
                f"  Rate: 1 {from_curr} = {rate:.4f} {to_curr}"
            )
            return {"response": response, "data": {"amount": amount, "from": from_curr, "to": to_curr, "rate": rate, "result": converted}, "action": "currency_convert"}

        except Exception as e:
            return {
                "response": f"Failed to convert currency: {str(e)}",
                "data": {"error": str(e)},
                "action": "error",
            }

    async def _fetch_top_crypto(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                url = (
                    "https://api.coingecko.com/api/v3/simple/price"
                    "?ids=bitcoin,ethereum,solana,dogecoin,ripple"
                    f"&vs_currencies={self.default_currency.lower()}&include_24hr_change=true"
                )
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            curr = self.default_currency.lower()
            lines = ["\U0001f4b0 **Top Crypto Prices:**\n"]
            for coin_id, info in data.items():
                price = info.get(curr, "N/A")
                change = info.get(f"{curr}_24h_change", 0)
                trend = "\U0001f7e2" if change >= 0 else "\U0001f534"
                change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
                lines.append(f"  {trend} {coin_id.title()}: {price:,.2f} {self.default_currency} ({change_str})")

            return {"response": "\n".join(lines), "data": data, "action": "top_crypto"}

        except Exception as e:
            return {
                "response": f"Failed to fetch market data: {str(e)}",
                "data": {"error": str(e)},
                "action": "error",
            }

    def get_system_prompt_addition(self) -> str:
        return (
            "You can fetch real-time crypto prices and convert currencies. "
            "When the user asks about prices or conversion, use the Mercury module."
        )

    def get_context_for_llm(self, text: str, context: dict) -> str:
        crypto = self._detect_crypto(text)
        if crypto:
            return f"[Mercury] User asking about {crypto} price."
        from_curr, to_curr = self._detect_currencies(text)
        if from_curr:
            return f"[Mercury] Currency conversion: {from_curr} -> {to_curr}"
        return "[Mercury] Finance query detected."

    def get_settings(self) -> dict:
        return {
            "enabled": self.enabled,
            "default_currency": self.default_currency,
        }

    def update_settings(self, settings: dict):
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "default_currency" in settings:
            if settings["default_currency"] in ("INR", "USD", "EUR"):
                self.default_currency = settings["default_currency"]

    def get_settings_schema(self) -> list:
        return [
            {"key": "enabled", "label": "Enabled", "type": "toggle", "value": self.enabled},
            {
                "key": "default_currency", "label": "Default Currency",
                "type": "select", "value": self.default_currency,
                "options": [
                    {"label": "INR (₹)", "value": "INR"},
                    {"label": "USD ($)", "value": "USD"},
                    {"label": "EUR (€)", "value": "EUR"},
                ],
            },
        ]
