import logging
import requests
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class RealTimeAPIManager:
    """
    Manages connections to external real-time data sources.
    Uses free APIs and services that do not require API keys for basic functionality.
    """
    def __init__(self):
        pass

    def get_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch current weather using Open-Meteo (No API Key required)."""
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            if "current_weather" in data:
                cw = data["current_weather"]
                return {
                    "temperature": cw.get("temperature"),
                    "windspeed": cw.get("windspeed"),
                    "is_day": cw.get("is_day") == 1,
                    "raw": cw
                }
            return {"error": "Weather data unavailable."}
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return {"error": str(e)}

    def get_stock_price(self, symbol: str) -> Dict[str, Any]:
        """Fetch current stock price using yfinance."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            data = ticker.fast_info
            return {
                "symbol": symbol,
                "current_price": data.last_price,
                "currency": ticker.info.get("currency", "USD") if hasattr(ticker, "info") else "USD"
            }
        except Exception as e:
            logger.error(f"Stock API error for {symbol}: {e}")
            return {"error": str(e)}

    def get_top_news(self, category: str = "technology") -> List[Dict[str, str]]:
        """Fetch latest news using RSS feeds (feedparser)."""
        try:
            import feedparser
            # Map categories to free RSS feeds
            feeds = {
                "technology": "http://feeds.bbci.co.uk/news/technology/rss.xml",
                "world": "http://feeds.bbci.co.uk/news/world/rss.xml",
                "business": "http://feeds.bbci.co.uk/news/business/rss.xml"
            }
            url = feeds.get(category.lower(), feeds["world"])
            feed = feedparser.parse(url)
            
            results = []
            for entry in feed.entries[:5]:  # Top 5 news
                results.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.get("summary", "")
                })
            return results
        except Exception as e:
            logger.error(f"News API error: {e}")
            return []
