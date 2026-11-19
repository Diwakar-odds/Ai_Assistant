"""
Tool schemas for function calling. Define available tools and their JSON schemas.
"""
tool_schemas = [
    {
        "name": "open_application",
        "description": "Open an application by name.",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Name of the application to open."}
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "search_google",
        "description": "Open Google in the user's web browser for a query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "web_search",
        "description": "Search the live web headlessly for real-time information, gold/crypto/stock prices, weather, sports scores, and latest news.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query or factual question."},
                "max_results": {"type": "integer", "description": "Maximum number of results to return (default 5)."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "play_music",
        "description": "Play music by song or artist name.",
        "parameters": {
            "type": "object",
            "properties": {
                "song": {"type": "string", "description": "Song or artist name."}
            },
            "required": ["song"]
        }
    }
]
