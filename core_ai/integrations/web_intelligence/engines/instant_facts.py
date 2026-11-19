"""
Specialized Instant Facts Connector for high-frequency queries:
- Weather (wttr.in format=j1)
- Stocks (Yahoo Finance API)
- Crypto (CoinGecko API)
Returns SearchResult objects with live data for instant grounding.
"""

import logging
import re
from typing import List, Optional
import requests

from ..models import SearchResult

logger = logging.getLogger(__name__)


class InstantFactsConnector:
    """Handles fast domain-specific queries without parsing messy web pages."""

    def __init__(self, timeout: float = 2.5):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def check_and_fetch(self, query: str) -> Optional[List[SearchResult]]:
        """If query matches a specialized domain, fetch and return live facts."""
        q_lower = query.lower()

        # 1. Weather
        if any(w in q_lower for w in ["weather", "mausam", "temperature", "forecast"]):
            return self._fetch_weather(query)

        # 2. Crypto
        if any(c in q_lower for c in ["bitcoin", "ethereum", "solana", "crypto", "btc", "eth"]):
            return self._fetch_crypto(query)

        # 3. Stock
        if any(s in q_lower for s in ["stock", "share price", "nasdaq", "nifty", "sensex"]):
            return self._fetch_stock(query)

        return None

    def _fetch_weather(self, query: str) -> Optional[List[SearchResult]]:
        """Fetch weather using wttr.in JSON API."""
        try:
            # Extract city name if present
            city = "Delhi"  # default
            m = re.search(r"\b(?:in|of|for|me|mein)\s+([a-zA-Z\s]+)", query, re.IGNORECASE)
            if m:
                extracted = m.group(1).strip()
                # filter out words like "today", "aaj"
                words = [w for w in extracted.split() if w.lower() not in ["today", "aaj", "current", "now", "kya", "hai", "batao"]]
                if words:
                    city = " ".join(words)

            url = f"https://wttr.in/{city}?format=j1"
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                current = data["current_condition"][0]
                temp_c = current.get("temp_C", "")
                feels_like = current.get("FeelsLikeC", "")
                desc = current.get("weatherDesc", [{}])[0].get("value", "")
                humidity = current.get("humidity", "")
                wind = current.get("windspeedKmph", "")

                snippet = (
                    f"Live Weather for {city.title()}: Temperature: {temp_c}°C (Feels like {feels_like}°C), "
                    f"Conditions: {desc}, Humidity: {humidity}%, Wind: {wind} km/h."
                )
                return [
                    SearchResult(
                        title=f"Live Weather: {city.title()}",
                        url=f"https://wttr.in/{city}",
                        snippet=snippet,
                        source="Live Weather API (wttr.in)",
                    )
                ]
        except Exception as exc:
            logger.debug(f"Instant weather fetch failed: {exc}")
        return None

    def _fetch_crypto(self, query: str) -> Optional[List[SearchResult]]:
        """Fetch cryptocurrency price using CoinGecko free API."""
        try:
            coin = "bitcoin"
            if "ethereum" in query.lower() or "eth" in query.lower():
                coin = "ethereum"
            elif "solana" in query.lower() or "sol" in query.lower():
                coin = "solana"

            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd,inr&include_24hr_change=true"
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if coin in data:
                    usd = data[coin].get("usd")
                    inr = data[coin].get("inr")
                    chg = data[coin].get("usd_24h_change", 0.0)
                    chg_sign = "+" if chg > 0 else ""

                    snippet = (
                        f"Current {coin.title()} Price: ${usd:,.2f} USD (₹{inr:,.2f} INR). "
                        f"24h Change: {chg_sign}{chg:.2f}%."
                    )
                    return [
                        SearchResult(
                            title=f"Live Crypto Price: {coin.title()}",
                            url=f"https://www.coingecko.com/en/coins/{coin}",
                            snippet=snippet,
                            source="CoinGecko API",
                        )
                    ]
        except Exception as exc:
            logger.debug(f"Instant crypto fetch failed: {exc}")
        return None

    def _fetch_stock(self, query: str) -> Optional[List[SearchResult]]:
        """Fetch stock chart price using Yahoo Finance."""
        try:
            # Simple symbol extraction
            symbol = None
            m = re.search(r"\b([A-Z]{2,6}|AAPL|GOOGL|MSFT|TSLA|NVDA|AMZN|META)\b", query)
            if m:
                symbol = m.group(1).upper()

            if not symbol:
                return None

            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if "chart" in data and data["chart"].get("result"):
                    meta = data["chart"]["result"][0]["meta"]
                    price = meta.get("regularMarketPrice")
                    prev = meta.get("previousClose")
                    currency = meta.get("currency", "USD")
                    diff = (price - prev) if (price and prev) else 0
                    pct = (diff / prev * 100) if prev else 0
                    sign = "+" if diff > 0 else ""

                    snippet = (
                        f"Current {symbol} Stock Price: {price:.2f} {currency} "
                        f"({sign}{diff:.2f}, {sign}{pct:.2f}%). Previous close: {prev:.2f} {currency}."
                    )
                    return [
                        SearchResult(
                            title=f"Live Stock Price: {symbol}",
                            url=f"https://finance.yahoo.com/quote/{symbol}",
                            snippet=snippet,
                            source="Yahoo Finance",
                        )
                    ]
        except Exception as exc:
            logger.debug(f"Instant stock fetch failed: {exc}")
        return None
