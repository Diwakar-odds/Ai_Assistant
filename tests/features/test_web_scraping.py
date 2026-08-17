"""
Unit tests for Web Scraping Module

Tests for:
- get_weather_info()
- get_weather_forecast()
- get_latest_news()
- search_web()
- get_stock_price()
- get_crypto_price()
- scrape_website_content()
- get_trending_topics()
- monitor_rss_feeds()
"""

import unittest
import os
import sys
from unittest.mock import patch, Mock, MagicMock
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.web_scraping import (
    get_weather_info,
    get_weather_forecast,
    get_latest_news,
    search_web,
    get_stock_price,
    get_crypto_price,
    scrape_website_content,
    get_trending_topics,
    monitor_rss_feeds,
    get_product_price
)


class TestWeatherFunctions(unittest.TestCase):
    """Test suite for weather-related functions"""
    
    @patch('modules.web_scraping.requests.get')
    def test_get_weather_info_with_api_key(self, mock_get):
        """Test weather info retrieval with API key"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'main': {
                'temp': 20,
                'feels_like': 18,
                'humidity': 65
            },
            'weather': [{'description': 'Clear sky'}],
            'wind': {'speed': 5.5}
        }
        mock_get.return_value = mock_response
        
        result = get_weather_info("London", api_key="test_key")
        
        self.assertIn("Weather", result)
        self.assertIn("London", result)
        self.assertIn("20", result)
    
    @patch('modules.web_scraping.requests.get')
    def test_get_weather_info_without_api_key(self, mock_get):
        """Test weather info retrieval without API key (free service)"""
        # Mock successful response from wttr.in
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'current_condition': [{
                'temp_C': '22',
                'FeelsLikeC': '20',
                'humidity': '70',
                'weatherDesc': [{'value': 'Sunny'}],
                'windspeedKmph': '10'
            }]
        }
        mock_get.return_value = mock_response
        
        result = get_weather_info("Paris")
        
        self.assertIn("Weather", result)
        self.assertIn("Paris", result)
        self.assertIn("22", result)
    
    @patch('modules.web_scraping.requests.get')
    def test_get_weather_info_error(self, mock_get):
        """Test weather info with API error"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = get_weather_info("InvalidCity")
        
        self.assertIn("Could not get weather", result)
    
    @patch('modules.web_scraping.requests.get')
    def test_get_weather_forecast(self, mock_get):
        """Test weather forecast retrieval"""
        # Mock forecast response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'weather': [
                {
                    'date': '2024-01-01',
                    'maxtempC': '25',
                    'mintempC': '15',
                    'hourly': [{'weatherDesc': [{'value': 'Partly cloudy'}]}]
                },
                {
                    'date': '2024-01-02',
                    'maxtempC': '23',
                    'mintempC': '14',
                    'hourly': [{'weatherDesc': [{'value': 'Rainy'}]}]
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = get_weather_forecast("Tokyo", days=2)
        
        self.assertIn("Forecast", result)
        self.assertIn("Tokyo", result)
        self.assertIn("25", result)


class TestNewsFunctions(unittest.TestCase):
    """Test suite for news-related functions"""
    
    @patch('modules.web_scraping.feedparser.parse')
    def test_get_latest_news_basic(self, mock_parse):
        """Test news retrieval"""
        # Mock RSS feed response
        mock_feed = MagicMock()
        mock_feed.feed.title = "Test News Source"
        mock_feed.entries = [
            {
                'title': 'Breaking News 1',
                'summary': 'Summary of news 1',
                'link': 'http://example.com/1',
                'published': 'Mon, 01 Jan 2024 12:00:00 GMT'
            },
            {
                'title': 'Breaking News 2',
                'summary': 'Summary of news 2',
                'link': 'http://example.com/2',
                'published': 'Mon, 01 Jan 2024 13:00:00 GMT'
            }
        ]
        mock_parse.return_value = mock_feed
        
        result = get_latest_news(category="general", max_articles=2)
        
        self.assertIn("Latest", result)
        self.assertIn("News", result)
    
    @patch('modules.web_scraping.feedparser.parse')
    def test_get_latest_news_technology(self, mock_parse):
        """Test technology news retrieval"""
        mock_feed = MagicMock()
        mock_feed.feed.title = "Tech News"
        mock_feed.entries = [
            {
                'title': 'New AI Breakthrough',
                'summary': 'AI advances',
                'link': 'http://tech.com/ai',
                'published': 'Mon, 01 Jan 2024 12:00:00 GMT'
            }
        ]
        mock_parse.return_value = mock_feed
        
        result = get_latest_news(category="technology")
        
        self.assertIn("News", result)
    
    @patch('modules.web_scraping.feedparser.parse')
    def test_get_latest_news_no_results(self, mock_parse):
        """Test news retrieval with no results"""
        mock_feed = MagicMock()
        mock_feed.entries = []
        mock_parse.return_value = mock_feed
        
        result = get_latest_news()
        
        self.assertIn("Could not retrieve", result)


class TestWebSearchFunctions(unittest.TestCase):
    """Test suite for web search functions"""
    
    @patch('modules.web_scraping.requests.get')
    def test_search_web_basic(self, mock_get):
        """Test basic web search"""
        # Mock search results page
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <div class="result">
            <a class="result__a" href="http://example.com">Example Result</a>
            <a class="result__snippet">This is a sample result</a>
        </div>
        '''
        mock_get.return_value = mock_response
        
        result = search_web("test query", num_results=1)
        
        self.assertIn("Search Results", result)
        self.assertIn("test query", result)
    
    @patch('modules.web_scraping.requests.get')
    def test_search_web_error(self, mock_get):
        """Test web search with error"""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response
        
        result = search_web("test")
        
        self.assertIn("unavailable", result)
    
    @patch('modules.web_scraping.requests.get')
    def test_search_web_no_results(self, mock_get):
        """Test web search with no results"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<html><body>No results</body></html>'
        mock_get.return_value = mock_response
        
        result = search_web("nonexistent query")
        
        self.assertIn("No search results", result)


class TestFinancialFunctions(unittest.TestCase):
    """Test suite for financial data functions"""
    
    @patch('modules.web_scraping.requests.get')
    def test_get_stock_price_success(self, mock_get):
        """Test stock price retrieval"""
        # Mock Yahoo Finance API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'chart': {
                'result': [{
                    'meta': {
                        'regularMarketPrice': 150.50,
                        'previousClose': 148.00,
                        'currency': 'USD'
                    }
                }]
            }
        }
        mock_get.return_value = mock_response
        
        result = get_stock_price("AAPL")
        
        self.assertIn("Stock Info", result)
        self.assertIn("AAPL", result)
        self.assertIn("150.50", result)
    
    @patch('modules.web_scraping.requests.get')
    def test_get_stock_price_invalid_symbol(self, mock_get):
        """Test stock price with invalid symbol"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'chart': {'result': None}}
        mock_get.return_value = mock_response
        
        result = get_stock_price("INVALID")
        
        self.assertIn("No data found", result)
    
    @patch('modules.web_scraping.requests.get')
    def test_get_crypto_price_success(self, mock_get):
        """Test cryptocurrency price retrieval"""
        # Mock CoinGecko API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'bitcoin': {
                'usd': 45000.00,
                'usd_24h_change': 2.5
            }
        }
        mock_get.return_value = mock_response
        
        result = get_crypto_price("bitcoin")
        
        self.assertIn("Crypto Info", result)
        self.assertIn("45,000", result)
        self.assertIn("2.5", result)
    
    @patch('modules.web_scraping.requests.get')
    def test_get_crypto_price_invalid(self, mock_get):
        """Test crypto price with invalid symbol"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response
        
        result = get_crypto_price("invalid_crypto")
        
        self.assertIn("not found", result)


class TestWebScrapingFunctions(unittest.TestCase):
    """Test suite for web scraping functions"""
    
    @patch('modules.web_scraping.requests.get')
    def test_scrape_website_content_success(self, mock_get):
        """Test website content scraping"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <head><title>Test Page</title></head>
            <body>
                <p>This is test content</p>
                <meta name="description" content="Test description">
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        result = scrape_website_content("http://example.com", extract_text=True)
        
        self.assertIn("Website Content", result)
        self.assertIn("Test Page", result)
    
    @patch('modules.web_scraping.requests.get')
    def test_scrape_website_content_error(self, mock_get):
        """Test website scraping with error"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = scrape_website_content("http://example.com")
        
        self.assertIn("Could not access", result)
    
    @patch('modules.web_scraping.requests.get')
    def test_scrape_website_metadata_only(self, mock_get):
        """Test scraping metadata without full text"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '''
        <html>
            <head>
                <title>Test</title>
                <meta name="description" content="Description">
            </head>
            <body>
                <img src="img1.png">
                <a href="link1">Link</a>
            </body>
        </html>
        '''
        mock_get.return_value = mock_response
        
        result = scrape_website_content("http://example.com", extract_text=False)
        
        self.assertIn("Website Content", result)
        self.assertIn("Page Stats", result)


class TestTrendingFunctions(unittest.TestCase):
    """Test suite for trending topics functions"""
    
    @patch('modules.web_scraping.requests.get')
    def test_get_trending_reddit(self, mock_get):
        """Test getting trending topics from Reddit"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'children': [
                    {
                        'data': {
                            'title': 'Trending Post 1',
                            'subreddit': 'programming',
                            'score': 5000,
                            'num_comments': 200
                        }
                    },
                    {
                        'data': {
                            'title': 'Trending Post 2',
                            'subreddit': 'technology',
                            'score': 4000,
                            'num_comments': 150
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        result = get_trending_topics("reddit")
        
        self.assertIn("Trending on Reddit", result)
        self.assertIn("Trending Post", result)
    
    @patch('modules.web_scraping.requests.get')
    def test_get_trending_github(self, mock_get):
        """Test getting trending topics from GitHub"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'items': [
                {
                    'full_name': 'user/repo1',
                    'description': 'Awesome project',
                    'stargazers_count': 10000,
                    'language': 'Python'
                },
                {
                    'full_name': 'user/repo2',
                    'description': 'Another project',
                    'stargazers_count': 5000,
                    'language': 'JavaScript'
                }
            ]
        }
        mock_get.return_value = mock_response
        
        result = get_trending_topics("github")
        
        self.assertIn("Trending on GitHub", result)
        self.assertIn("user/repo", result)
    
    def test_get_trending_general(self):
        """Test getting general trending topics"""
        result = get_trending_topics("general")
        
        self.assertIn("General Trending", result)
        self.assertIn("Trending Topics", result)


class TestRSSFunctions(unittest.TestCase):
    """Test suite for RSS monitoring functions"""
    
    @patch('modules.web_scraping.feedparser.parse')
    def test_monitor_rss_feeds_success(self, mock_parse):
        """Test monitoring RSS feeds"""
        mock_feed = MagicMock()
        mock_feed.feed.title = "Test Feed"
        mock_feed.entries = [
            {
                'title': 'Article 1',
                'link': 'http://example.com/1',
                'published': 'Mon, 01 Jan 2024 12:00:00 GMT'
            },
            {
                'title': 'Article 2',
                'link': 'http://example.com/2',
                'published': 'Mon, 01 Jan 2024 13:00:00 GMT'
            }
        ]
        mock_parse.return_value = mock_feed
        
        feed_urls = ['http://example.com/rss']
        result = monitor_rss_feeds(feed_urls, max_items=2)
        
        self.assertIn("RSS Feed Monitor", result)
        self.assertIn("Article", result)
    
    @patch('modules.web_scraping.feedparser.parse')
    def test_monitor_rss_feeds_no_items(self, mock_parse):
        """Test RSS monitoring with no items"""
        mock_feed = MagicMock()
        mock_feed.entries = []
        mock_parse.return_value = mock_feed
        
        result = monitor_rss_feeds(['http://example.com/rss'])
        
        self.assertIn("Could not retrieve", result)


class TestProductPriceFunctions(unittest.TestCase):
    """Test suite for product price functions"""
    
    def test_get_product_price_basic(self):
        """Test product price tracking (demonstration)"""
        result = get_product_price("laptop", marketplace="amazon")
        
        # This is a demonstration function
        self.assertIn("Price Search", result)
        self.assertIn("laptop", result)
        self.assertIn("API", result)


class TestWebScrapingEdgeCases(unittest.TestCase):
    """Test suite for edge cases and error handling"""
    
    @patch('modules.web_scraping.requests.get')
    def test_network_timeout(self, mock_get):
        """Test handling of network timeout"""
        mock_get.side_effect = Exception("Connection timeout")
        
        result = get_weather_info("London")
        
        self.assertIn("error", result.lower())
    
    @patch('modules.web_scraping.requests.get')
    def test_invalid_json_response(self, mock_get):
        """Test handling of invalid JSON response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        
        result = get_stock_price("AAPL")
        
        self.assertIn("error", result.lower())
    
    @patch('modules.web_scraping.requests.get')
    def test_html_parsing_error(self, mock_get):
        """Test handling of HTML parsing errors"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Invalid HTML <<>>"
        mock_get.return_value = mock_response
        
        result = scrape_website_content("http://example.com")
        
        # Should not crash
        self.assertIn("Website Content", result)


def suite():
    """Create test suite"""
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestWeatherFunctions))
    test_suite.addTest(unittest.makeSuite(TestNewsFunctions))
    test_suite.addTest(unittest.makeSuite(TestWebSearchFunctions))
    test_suite.addTest(unittest.makeSuite(TestFinancialFunctions))
    test_suite.addTest(unittest.makeSuite(TestWebScrapingFunctions))
    test_suite.addTest(unittest.makeSuite(TestTrendingFunctions))
    test_suite.addTest(unittest.makeSuite(TestRSSFunctions))
    test_suite.addTest(unittest.makeSuite(TestProductPriceFunctions))
    test_suite.addTest(unittest.makeSuite(TestWebScrapingEdgeCases))
    return test_suite


if __name__ == '__main__':
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
