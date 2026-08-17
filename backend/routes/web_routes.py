from flask import Blueprint, jsonify, request, send_from_directory, render_template, Response, stream_with_context
import os, json, sys, time, datetime
from .common import logger, api_logger, jwt_required, create_access_token, get_jwt_identity, verify_jwt_in_request

web_bp = Blueprint('web', __name__)
@web_bp.route('/api/web/weather', methods=['GET'])
def api_get_weather():
    """Get weather information for a location"""
    try:
        from ai_assistant.integrations.web_scraping import get_weather_info
        
        location = request.args.get('location', 'New York')
        api_key = request.args.get('api_key')
        
        result = get_weather_info(location, api_key)
        
        return jsonify({
            "success": True,
            "weather": result,
            "location": location,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route('/api/web/news', methods=['GET'])
def api_get_news():
    """Get latest news headlines"""
    try:
        from ai_assistant.integrations.web_scraping import get_latest_news
        
        category = request.args.get('category', 'general')
        country = request.args.get('country', 'us')
        max_articles = int(request.args.get('max_articles', 5))
        
        result = get_latest_news(category, country, max_articles)
        
        return jsonify({
            "success": True,
            "news": result,
            "category": category,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"News API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route('/api/web/stock', methods=['GET'])
def api_get_stock():
    """Get stock price information"""
    try:
        from ai_assistant.integrations.web_scraping import get_stock_price
        
        symbol = request.args.get('symbol', 'AAPL')
        
        result = get_stock_price(symbol)
        
        return jsonify({
            "success": True,
            "stock_info": result,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Stock API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route('/api/web/crypto', methods=['GET'])
def api_get_crypto():
    """Get cryptocurrency price information"""
    try:
        from ai_assistant.integrations.web_scraping import get_crypto_price
        
        symbol = request.args.get('symbol', 'bitcoin')
        
        result = get_crypto_price(symbol)
        
        return jsonify({
            "success": True,
            "crypto_info": result,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Crypto API error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route('/api/web/scrape', methods=['POST'])
@jwt_required()
def api_scrape_website():
    """Scrape website content"""
    try:
        from ai_assistant.integrations.web_scraping import scrape_website_content
        
        data = request.get_json()
        url = data.get('url')
        extract_text = data.get('extract_text', True)
        max_length = data.get('max_length', 1000)
        
        if not url:
            return jsonify({"success": False, "error": "URL required"}), 400
        
        result = scrape_website_content(url, extract_text, max_length)
        
        return jsonify({
            "success": True,
            "content": result,
            "url": url,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Web scraping error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@web_bp.route('/api/web/trending', methods=['GET'])
def api_get_trending():
    """Get trending topics from various platforms"""
    try:
        from ai_assistant.integrations.web_scraping import get_trending_topics
        
        platform = request.args.get('platform', 'general')
        
        result = get_trending_topics(platform)
        
        return jsonify({
            "success": True,
            "trending": result,
            "platform": platform,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Trending topics error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500