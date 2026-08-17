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
        "description": "Search Google for a query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."}
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
