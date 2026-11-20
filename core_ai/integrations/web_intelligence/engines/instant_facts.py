"""
Specialized Instant Facts Connector for high-frequency real-time domains:
- Weather (Open-Meteo with Geocoding, fallback to wttr.in)
- Currency Conversion (Frankfurter ECB reference rates, fallback to open.er-api)
- Metals / Commodities (Gold-API spot XAU/XAG + derived Indian INR per 10g/1kg)
- Crypto (CoinGecko keyless multi-currency API)
- Stocks (Yahoo Finance chart API)

Returns SearchResult objects with verified live data in <300ms without messy web scraping.
"""

from datetime import datetime
import logging
import re
from typing import Any, Dict, List, Optional
import requests

from ..models import SearchResult

logger = logging.getLogger(__name__)

_WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Slight rain showers",
    81: "Moderate rain showers", 82: "Violent rain showers", 95: "Thunderstorm",
    96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
}

_CCY_MAP = {
    "dollar": "USD", "dollars": "USD", "usd": "USD", "$": "USD",
    "euro": "EUR", "euros": "EUR", "eur": "EUR", "€": "EUR",
    "pound": "GBP", "pounds": "GBP", "gbp": "GBP", "£": "GBP",
    "rupee": "INR", "rupees": "INR", "inr": "INR", "₹": "INR",
    "yen": "JPY", "jpy": "JPY", "¥": "JPY",
    "dirham": "AED", "aed": "AED",
    "cad": "CAD", "aud": "AUD", "cny": "CNY"
}

_CRYPTO_MAP = {
    "bitcoin": "bitcoin", "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "solana": "solana", "sol": "solana",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "ripple": "ripple", "xrp": "ripple",
    "binancecoin": "binancecoin", "bnb": "binancecoin"
}

_OZ_TO_GRAMS = 31.1034768


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

        # 1. Currency Conversion (e.g. "100 usd to inr", "dollar ka rate", "euro in rupees")
        if any(c in q_lower for c in ["usd", "inr", "eur", "gbp", "dollar", "euro", "pound", "rupee"]) and any(
            t in q_lower for t in ["to", "in", "rate", "price", "convert", "kitna", "bhav", "value"]
        ):
            res = self._fetch_currency(query)
            if res:
                return res

        # 2. Metals (Gold / Silver live spot and retail calculation)
        if any(w in q_lower for w in ["gold", "silver", "sona", "sone", "chandi", "chaandi", "xau", "xag"]):
            if any(p in q_lower for p in ["price", "rate", "bhav", "daam", "kitna", "cost", "spot", "today", "aaj"]):
                res = self._fetch_metals(query)
                if res:
                    return res

        # 3. Weather
        if any(w in q_lower for w in ["weather", "mausam", "temperature", "tapman", "forecast", "barish", "rain"]):
            res = self._fetch_weather(query)
            if res:
                return res

        # 4. Crypto
        if any(c in q_lower for c in ["bitcoin", "ethereum", "solana", "crypto", "btc", "eth", "doge", "xrp"]):
            res = self._fetch_crypto(query)
            if res:
                return res

        # 5. Stock
        if any(s in q_lower for s in ["stock", "share price", "nasdaq", "nifty", "sensex"]):
            res = self._fetch_stock(query)
            if res:
                return res

        return None

    def _fetch_weather(self, query: str) -> Optional[List[SearchResult]]:
        """Fetch weather using Open-Meteo with geocoding, fallback to wttr.in."""
        # 1. Extract location
        city = "Delhi"
        m = re.search(r"\b(?:in|of|for|me|mein|ka|ki|ke)\s+([a-zA-Z\s]+)", query, re.IGNORECASE)
        if m:
            extracted = m.group(1).strip()
            words = [
                w for w in extracted.split()
                if w.lower() not in ["today", "aaj", "current", "now", "kya", "hai", "batao", "kaisa", "kaisi", "weather", "mausam"]
            ]
            if words:
                city = " ".join(words)

        # 2. Try Open-Meteo High-Availability API
        try:
            geo_url = "https://geocoding-api.open-meteo.com/v1/search"
            geo_resp = self.session.get(geo_url, params={"name": city, "count": 1, "language": "en", "format": "json"}, timeout=self.timeout)
            if geo_resp.status_code == 200:
                geo_data = geo_resp.json()
                results = geo_data.get("results")
                if results and len(results) > 0:
                    hit = results[0]
                    lat, lon = hit["latitude"], hit["longitude"]
                    place_name = ", ".join(x for x in [hit.get("name"), hit.get("admin1"), hit.get("country")] if x)

                    fc_url = "https://api.open-meteo.com/v1/forecast"
                    fc_params = {
                        "latitude": lat,
                        "longitude": lon,
                        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
                        "forecast_days": 2,
                        "timezone": "auto"
                    }
                    fc_resp = self.session.get(fc_url, params=fc_params, timeout=self.timeout)
                    if fc_resp.status_code == 200:
                        fc_data = fc_resp.json()
                        cur = fc_data.get("current", {})
                        daily = fc_data.get("daily", {})

                        temp = cur.get("temperature_2m", "?")
                        feels = cur.get("apparent_temperature", temp)
                        humidity = cur.get("relative_humidity_2m", "?")
                        wind = cur.get("wind_speed_10m", "?")
                        cond = _WMO_CODES.get(cur.get("weather_code", 0), "Clear")

                        today_max = daily.get("temperature_2m_max", [temp])[0]
                        today_min = daily.get("temperature_2m_min", [temp])[0]
                        rain_prob = daily.get("precipitation_probability_max", [0])[0]

                        snippet = (
                            f"Live Weather for {place_name}: {temp}°C (Feels like {feels}°C), {cond}. "
                            f"Humidity: {humidity}%, Wind: {wind} km/h. "
                            f"Today's Range: High {today_max}°C / Low {today_min}°C, Rain chance: {rain_prob}%."
                        )
                        return [
                            SearchResult(
                                title=f"Live Weather: {place_name}",
                                url=f"https://open-meteo.com/en/weather?latitude={lat}&longitude={lon}",
                                snippet=snippet,
                                source="Open-Meteo High-Resolution Forecast",
                            )
                        ]
        except Exception as exc:
            logger.debug(f"Open-Meteo fetch error, trying wttr.in fallback: {exc}")

        # Fallback to wttr.in
        try:
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
            logger.debug(f"Instant weather fallback failed: {exc}")
        return None

    def _fetch_currency(self, query: str) -> Optional[List[SearchResult]]:
        """Fetch live foreign exchange rates using Frankfurter (ECB) or open.er-api."""
        try:
            q_clean = query.lower()
            found_codes = []
            for token, code in _CCY_MAP.items():
                if re.search(rf"\b{re.escape(token)}\b", q_clean):
                    if code not in found_codes:
                        found_codes.append(code)

            if not found_codes:
                return None

            base = found_codes[0]
            quote = found_codes[1] if len(found_codes) > 1 else ("INR" if base != "INR" else "USD")

            # Extract amount if present, e.g. "100 usd to inr"
            amount = 1.0
            num_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:usd|eur|gbp|dollar|euro|pound|inr|rupee|aed|cad|aud)?\b", q_clean)
            if num_match:
                try:
                    amount = float(num_match.group(1))
                except ValueError:
                    amount = 1.0

            rate = None
            date_str = datetime.now().strftime("%Y-%m-%d")

            # Try Frankfurter (European Central Bank Reference Rate)
            try:
                url = f"https://api.frankfurter.dev/v1/latest?base={base}&symbols={quote}"
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    d = resp.json()
                    rate = float(d["rates"][quote])
                    date_str = d.get("date", date_str)
            except Exception:
                rate = None

            # Fallback to open.er-api
            if rate is None:
                url = f"https://open.er-api.com/v6/latest/{base}"
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    d = resp.json()
                    rates = d.get("rates", {})
                    if quote in rates:
                        rate = float(rates[quote])

            if rate is not None:
                converted = amount * rate
                snippet = (
                    f"Live Currency Rate ({date_str}): {amount:g} {base} = {converted:,.2f} {quote} "
                    f"(1 {base} = {rate:,.4f} {quote}). Mid-market reference rate."
                )
                return [
                    SearchResult(
                        title=f"Exchange Rate: {base}/{quote}",
                        url=f"https://www.frankfurter.app/",
                        snippet=snippet,
                        source="European Central Bank (Frankfurter FX)",
                    )
                ]
        except Exception as exc:
            logger.debug(f"Instant currency fetch failed: {exc}")
        return None

    def _fetch_metals(self, query: str) -> Optional[List[SearchResult]]:
        """Fetch spot gold/silver prices and derive Indian INR rate per 10g / 1kg."""
        try:
            q_clean = query.lower()
            sym = "XAU" if any(w in q_clean for w in ["gold", "sona", "sone", "xau"]) else "XAG"
            metal_name = "Gold" if sym == "XAU" else "Silver"

            url = f"https://api.gold-api.com/price/{sym}"
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                price_usd = float(data.get("price") or data.get("priceUsd") or 0.0)
                if price_usd <= 0:
                    return None

                as_of = data.get("updatedAtReadable") or datetime.now().strftime("%Y-%m-%d %H:%M")

                # Get USD/INR rate to provide Indian benchmark
                usd_inr = 85.0  # safe default fallback
                try:
                    fx_resp = self.session.get("https://api.frankfurter.dev/v1/latest?base=USD&symbols=INR", timeout=1.5)
                    if fx_resp.status_code == 200:
                        usd_inr = float(fx_resp.json()["rates"]["INR"])
                except Exception:
                    pass

                if sym == "XAU":
                    # Gold: convert per troy oz (31.1035g) to per 10 grams in INR
                    inr_per_10g = (price_usd / _OZ_TO_GRAMS) * 10 * usd_inr
                    snippet = (
                        f"Live {metal_name} Spot Price: ${price_usd:,.2f} USD per troy ounce (as of {as_of}). "
                        f"Direct conversion at USD/INR {usd_inr:.2f}: ~₹{inr_per_10g:,.0f} per 10 grams (24 Karat spot). "
                        f"Note: Indian retail MCX jeweller rates include import duty, state GST, and making charges."
                    )
                else:
                    # Silver: convert per troy oz to per 1 kg in INR
                    inr_per_1kg = (price_usd / _OZ_TO_GRAMS) * 1000 * usd_inr
                    snippet = (
                        f"Live {metal_name} Spot Price: ${price_usd:,.2f} USD per troy ounce (as of {as_of}). "
                        f"Direct conversion at USD/INR {usd_inr:.2f}: ~₹{inr_per_1kg:,.0f} per 1 kg silver spot. "
                        f"Note: Local retail rates differ by state taxes and refiner premiums."
                    )

                return [
                    SearchResult(
                        title=f"Live {metal_name} Price Benchmark",
                        url="https://gold-api.com",
                        snippet=snippet,
                        source=f"Live Spot Benchmark (gold-api.com & ECB FX)",
                    )
                ]
        except Exception as exc:
            logger.debug(f"Instant metals fetch failed: {exc}")
        return None

    def _fetch_crypto(self, query: str) -> Optional[List[SearchResult]]:
        """Fetch cryptocurrency price using CoinGecko free API."""
        try:
            q_clean = query.lower()
            coin_id = "bitcoin"
            for token, cid in _CRYPTO_MAP.items():
                if token in q_clean:
                    coin_id = cid
                    break

            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd,inr&include_24hr_change=true"
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                if coin_id in data:
                    usd = data[coin_id].get("usd", 0.0)
                    inr = data[coin_id].get("inr", 0.0)
                    chg = data[coin_id].get("usd_24h_change", 0.0)
                    chg_sign = "+" if chg > 0 else ""

                    snippet = (
                        f"Current {coin_id.title()} Price: ${usd:,.2f} USD (₹{inr:,.2f} INR). "
                        f"24h Change: {chg_sign}{chg:.2f}%."
                    )
                    return [
                        SearchResult(
                            title=f"Live Crypto Price: {coin_id.title()}",
                            url=f"https://www.coingecko.com/en/coins/{coin_id}",
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
