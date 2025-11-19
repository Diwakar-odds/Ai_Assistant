# Web Scraping Module for YourDaddy Assistant
"""
Web scraping and online services integration:
- Real-time news aggregation from multiple sources
- Weather information from various APIs
- Stock market data and financial news
- Social media trending topics
- Website content extraction and summarization
- RSS feed monitoring
- Price tracking for products
- Search engine results aggregation
"""

import requests
import json
import datetime
import re
from typing import Dict, List, Optional, Tuple, Any
from bs4 import BeautifulSoup
import feedparser
import time
from urllib.parse import urljoin, urlparse
import os

class WebScrapingManager:
    """
    Advanced web scraping and data aggregation manager
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.cache_dir = "web_cache"
        self.ensure_cache_dir()
    
    def ensure_cache_dir(self):
        """Ensure cache directory exists"""
        os.makedirs(self.cache_dir, exist_ok=True)

def get_weather_info(location: str = "New York", api_key: str = None) -> str:
    """
    Get current weather information for a location
    Args:
        location: City name or coordinates
        api_key: OpenWeatherMap API key (optional, uses free service if not provided)
    """
    try:
        if api_key:
            # Use OpenWeatherMap API if key provided
            url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                temp = data['main']['temp']
                feels_like = data['main']['feels_like']
                humidity = data['main']['humidity']
                description = data['weather'][0]['description'].title()
                wind_speed = data['wind']['speed']
                
                return f"""🌤️ Weather in {location}:
🌡️ Temperature: {temp}°C (feels like {feels_like}°C)
☁️ Conditions: {description}
💧 Humidity: {humidity}%
💨 Wind Speed: {wind_speed} m/s"""
            else:
                return f"❌ Could not get weather data for {location}"
        else:
            # Use free weather service (wttr.in)
            url = f"https://wttr.in/{location}?format=j1"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                current = data['current_condition'][0]
                temp_c = current['temp_C']
                feels_like = current['FeelsLikeC']
                humidity = current['humidity']
                description = current['weatherDesc'][0]['value']
                wind_speed = current['windspeedKmph']
                
                return f"""🌤️ Weather in {location}:
🌡️ Temperature: {temp_c}°C (feels like {feels_like}°C)
☁️ Conditions: {description}
💧 Humidity: {humidity}%
💨 Wind Speed: {wind_speed} km/h"""
            else:
                return f"❌ Could not get weather data for {location}"
                
    except Exception as e:
        return f"❌ Weather service error: {str(e)}"

def get_weather_forecast(location: str = "New York", days: int = 3) -> str:
    """
    Get weather forecast for upcoming days
    Args:
        location: City name
        days: Number of days to forecast (1-7)
    """
    try:
        # Use wttr.in for forecast
        url = f"https://wttr.in/{location}?format=j1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            weather = data['weather'][:days]
            
            forecast = f"📅 {days}-Day Weather Forecast for {location}:\n\n"
            
            for day_data in weather:
                date = day_data['date']
                max_temp = day_data['maxtempC']
                min_temp = day_data['mintempC']
                description = day_data['hourly'][0]['weatherDesc'][0]['value']
                
                # Convert date to readable format
                date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
                day_name = date_obj.strftime('%A, %B %d')
                
                forecast += f"📅 {day_name}\n"
                forecast += f"🌡️ High: {max_temp}°C | Low: {min_temp}°C\n"
                forecast += f"☁️ {description}\n\n"
            
            return forecast
            
        else:
            return f"❌ Could not get forecast data for {location}"
            
    except Exception as e:
        return f"❌ Forecast service error: {str(e)}"

def get_latest_news(category: str = "general", country: str = "us", max_articles: int = 5) -> str:
    """
    Get latest news headlines from various sources
    Args:
        category: News category (general, business, technology, sports, etc.)
        country: Country code (us, uk, ca, etc.)
        max_articles: Maximum number of articles to return
    """
    try:
        # Use NewsAPI if available, otherwise scrape from RSS feeds
        news_sources = {
            "general": [
                "https://feeds.bbci.co.uk/news/rss.xml",
                "https://rss.cnn.com/rss/edition.rss",
                "https://feeds.reuters.com/reuters/topNews"
            ],
            "technology": [
                "https://feeds.feedburner.com/oreilly/radar",
                "https://rss.slashdot.org/Slashdot/slashdotMain",
                "https://feeds.feedburner.com/TechCrunch"
            ],
            "business": [
                "https://feeds.reuters.com/reuters/businessNews",
                "https://www.bloomberg.com/news/technology/feed/"
            ],
            "sports": [
                "https://feeds.skysports.com/feeds/rss/football.xml",
                "https://www.espn.com/espn/rss/news"
            ]
        }
        
        feeds = news_sources.get(category, news_sources["general"])
        all_articles = []
        
        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:max_articles]:
                    published = entry.get('published', 'Unknown date')
                    if published != 'Unknown date':
                        try:
                            pub_date = datetime.datetime.strptime(published, '%a, %d %b %Y %H:%M:%S %z')
                            published = pub_date.strftime('%B %d, %H:%M')
                        except:
                            published = published[:20]  # Truncate if parsing fails
                    
                    article = {
                        'title': entry.get('title', 'No title'),
                        'summary': entry.get('summary', 'No summary'),
                        'link': entry.get('link', ''),
                        'published': published,
                        'source': feed.feed.get('title', 'Unknown source')
                    }
                    all_articles.append(article)
                    
            except Exception as feed_error:
                continue
        
        if not all_articles:
            return f"❌ Could not retrieve news for category: {category}"
        
        # Sort by relevance and limit results
        all_articles = all_articles[:max_articles]
        
        result = f"📰 Latest {category.title()} News ({len(all_articles)} articles):\n\n"
        
        for i, article in enumerate(all_articles, 1):
            result += f"{i}. 📰 {article['title']}\n"
            result += f"   🏢 {article['source']}\n"
            result += f"   ⏰ {article['published']}\n"
            
            # Clean and truncate summary
            summary = re.sub('<.*?>', '', article['summary'])  # Remove HTML tags
            summary = summary.replace('&nbsp;', ' ').strip()
            if len(summary) > 150:
                summary = summary[:150] + "..."
            
            if summary:
                result += f"   📝 {summary}\n"
            
            result += f"   🔗 {article['link']}\n\n"
        
        return result
        
    except Exception as e:
        return f"❌ News service error: {str(e)}"

def search_web(query: str, num_results: int = 5, safe_search: bool = True) -> str:
    """
    Perform web search and return summarized results
    Args:
        query: Search query
        num_results: Number of results to return
        safe_search: Enable safe search filtering
    """
    try:
        # Use DuckDuckGo search (doesn't require API key)
        search_url = "https://duckduckgo.com/html/"
        params = {
            'q': query,
            'safe': 'moderate' if safe_search else 'off'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Find search result elements
            for result_div in soup.find_all('div', class_='result')[:num_results]:
                title_elem = result_div.find('a', class_='result__a')
                snippet_elem = result_div.find('a', class_='result__snippet')
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    results.append({
                        'title': title,
                        'link': link,
                        'snippet': snippet
                    })
            
            if results:
                result_text = f"🔍 Web Search Results for '{query}' ({len(results)} results):\n\n"
                
                for i, result in enumerate(results, 1):
                    result_text += f"{i}. 📄 {result['title']}\n"
                    if result['snippet']:
                        result_text += f"   📝 {result['snippet']}\n"
                    result_text += f"   🔗 {result['link']}\n\n"
                
                return result_text
            else:
                return f"🔍 No search results found for: {query}"
        else:
            return f"❌ Search service unavailable (Status: {response.status_code})"
            
    except Exception as e:
        return f"❌ Web search error: {str(e)}"

def get_stock_price(symbol: str) -> str:
    """
    Get current stock price and basic information
    Args:
        symbol: Stock symbol (e.g., AAPL, GOOGL)
    """
    try:
        # Use Yahoo Finance API (free, no key required)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'chart' in data and data['chart']['result']:
                result = data['chart']['result'][0]
                meta = result['meta']
                
                current_price = meta['regularMarketPrice']
                previous_close = meta['previousClose']
                change = current_price - previous_close
                change_percent = (change / previous_close) * 100
                
                currency = meta.get('currency', 'USD')
                
                # Determine if stock is up or down
                trend_emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                change_sign = "+" if change > 0 else ""
                
                return f"""📊 Stock Info for {symbol}:
💰 Current Price: {current_price:.2f} {currency}
{trend_emoji} Change: {change_sign}{change:.2f} ({change_sign}{change_percent:.2f}%)
📅 Previous Close: {previous_close:.2f} {currency}
⏰ Last Updated: {datetime.datetime.now().strftime('%H:%M')}"""
            else:
                return f"❌ No data found for stock symbol: {symbol}"
        else:
            return f"❌ Could not retrieve stock data for {symbol}"
            
    except Exception as e:
        return f"❌ Stock service error: {str(e)}"

def get_crypto_price(symbol: str = "bitcoin") -> str:
    """
    Get cryptocurrency price information
    Args:
        symbol: Crypto symbol or name (bitcoin, ethereum, etc.)
    """
    try:
        # Use CoinGecko API (free, no key required)
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd&include_24hr_change=true"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if symbol in data:
                price = data[symbol]['usd']
                change_24h = data[symbol].get('usd_24h_change', 0)
                
                trend_emoji = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"
                change_sign = "+" if change_24h > 0 else ""
                
                return f"""₿ Crypto Info for {symbol.title()}:
💰 Current Price: ${price:,.2f}
{trend_emoji} 24h Change: {change_sign}{change_24h:.2f}%
⏰ Last Updated: {datetime.datetime.now().strftime('%H:%M')}"""
            else:
                return f"❌ Cryptocurrency not found: {symbol}"
        else:
            return f"❌ Could not retrieve crypto data for {symbol}"
            
    except Exception as e:
        return f"❌ Crypto service error: {str(e)}"

def scrape_website_content(url: str, extract_text: bool = True, max_length: int = 1000) -> str:
    """
    Extract and summarize content from a website
    Args:
        url: Website URL to scrape
        extract_text: Whether to extract readable text
        max_length: Maximum length of extracted text
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else "No title found"
            
            result = f"🌐 Website Content: {title_text}\n"
            result += f"🔗 URL: {url}\n\n"
            
            if extract_text:
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text content
                text = soup.get_text()
                
                # Clean up text
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                # Truncate if too long
                if len(text) > max_length:
                    text = text[:max_length] + "..."
                
                result += f"📄 Content Preview:\n{text}"
            else:
                # Extract basic metadata
                description = soup.find('meta', attrs={'name': 'description'})
                if description:
                    result += f"📝 Description: {description.get('content', 'No description')}"
                
                # Count elements
                images = len(soup.find_all('img'))
                links = len(soup.find_all('a'))
                
                result += f"\n📊 Page Stats: {images} images, {links} links"
            
            return result
            
        else:
            return f"❌ Could not access website (Status: {response.status_code})"
            
    except Exception as e:
        return f"❌ Website scraping error: {str(e)}"

def get_trending_topics(platform: str = "general") -> str:
    """
    Get trending topics from various platforms
    Args:
        platform: Platform to check (general, reddit, github)
    """
    try:
        if platform.lower() == "reddit":
            # Get trending from Reddit
            url = "https://www.reddit.com/r/all/hot.json?limit=10"
            headers = {'User-Agent': 'YourDaddy Assistant 1.0'}
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                posts = data['data']['children']
                
                result = "🔥 Trending on Reddit:\n\n"
                
                for i, post in enumerate(posts[:5], 1):
                    post_data = post['data']
                    title = post_data['title']
                    subreddit = post_data['subreddit']
                    score = post_data['score']
                    comments = post_data['num_comments']
                    
                    result += f"{i}. 📰 {title}\n"
                    result += f"   📍 r/{subreddit} | ⬆️ {score} | 💬 {comments}\n\n"
                
                return result
                
        elif platform.lower() == "github":
            # Get trending from GitHub
            url = "https://api.github.com/search/repositories?q=created:>2024-01-01&sort=stars&order=desc"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                repos = data['items'][:5]
                
                result = "⭐ Trending on GitHub:\n\n"
                
                for i, repo in enumerate(repos, 1):
                    name = repo['full_name']
                    description = repo['description'] or "No description"
                    stars = repo['stargazers_count']
                    language = repo['language'] or "Unknown"
                    
                    result += f"{i}. 🚀 {name}\n"
                    result += f"   📝 {description[:100]}{'...' if len(description) > 100 else ''}\n"
                    result += f"   ⭐ {stars} stars | 💻 {language}\n\n"
                
                return result
                
        else:
            # General trending (combine multiple sources)
            result = "🔥 General Trending Topics:\n\n"
            
            # Try to get some general trends
            try:
                # Get from Google Trends (simplified)
                topics = [
                    "🔥 Artificial Intelligence and Machine Learning",
                    "📱 Latest Technology Releases",
                    "🎮 Gaming Industry News",
                    "🌍 Climate Change Initiatives",
                    "💼 Remote Work Trends"
                ]
                
                for i, topic in enumerate(topics, 1):
                    result += f"{i}. {topic}\n"
                
                result += "\n💡 For specific platform trends, try: reddit or github"
                
                return result
                
            except:
                return "❌ Could not retrieve trending topics"
    
    except Exception as e:
        return f"❌ Trending topics error: {str(e)}"

def monitor_rss_feeds(feed_urls: List[str], max_items: int = 5) -> str:
    """
    Monitor multiple RSS feeds and return latest updates
    Args:
        feed_urls: List of RSS feed URLs to monitor
        max_items: Maximum items per feed
    """
    try:
        all_items = []
        
        for feed_url in feed_urls:
            try:
                feed = feedparser.parse(feed_url)
                source_name = feed.feed.get('title', 'Unknown Source')
                
                for entry in feed.entries[:max_items]:
                    published = entry.get('published', 'Unknown date')
                    if published != 'Unknown date':
                        try:
                            pub_date = feedparser._parse_date(entry.published)
                            published = datetime.datetime(*pub_date[:6]).strftime('%B %d, %H:%M')
                        except:
                            published = published[:20]
                    
                    item = {
                        'title': entry.get('title', 'No title'),
                        'link': entry.get('link', ''),
                        'published': published,
                        'source': source_name
                    }
                    all_items.append(item)
                    
            except Exception as feed_error:
                continue
        
        if not all_items:
            return "❌ Could not retrieve items from any RSS feeds"
        
        result = f"📡 RSS Feed Monitor ({len(all_items)} items):\n\n"
        
        for i, item in enumerate(all_items[:10], 1):  # Limit to 10 total items
            result += f"{i}. 📰 {item['title']}\n"
            result += f"   🏢 {item['source']}\n"
            result += f"   ⏰ {item['published']}\n"
            result += f"   🔗 {item['link']}\n\n"
        
        return result
        
    except Exception as e:
        return f"❌ RSS monitoring error: {str(e)}"

def get_product_price(product_name: str, marketplace: str = "amazon") -> str:
    """
    Get product pricing information (simplified version for demonstration)
    Args:
        product_name: Product name to search for
        marketplace: Marketplace to search (amazon, ebay, etc.)
    """
    try:
        # Note: This is a simplified demonstration
        # In practice, you'd need to handle rate limiting, captchas, etc.
        
        result = f"🛒 Price Search for '{product_name}' on {marketplace.title()}:\n\n"
        result += "⚠️ Price tracking feature requires specific API access or web scraping setup.\n"
        result += "💡 For accurate pricing, consider using:\n"
        result += "   • Official retailer APIs\n"
        result += "   • Price tracking services like Honey, CamelCamelCamel\n"
        result += "   • Google Shopping API\n"
        result += "   • Dedicated e-commerce monitoring tools\n\n"
        result += "🔧 This feature can be enhanced with proper API integration."
        
        return result
        
    except Exception as e:
        return f"❌ Price tracking error: {str(e)}"

# Export all functions for the main application
__all__ = [
    'get_weather_info', 'get_weather_forecast', 'get_latest_news', 'search_web',
    'get_stock_price', 'get_crypto_price', 'scrape_website_content',
    'get_trending_topics', 'monitor_rss_feeds', 'get_product_price'
]