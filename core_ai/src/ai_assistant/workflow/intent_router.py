import os
import re
from typing import List, Optional, Tuple
from semantic_router import Route, RouteLayer
from semantic_router.encoders import HuggingFaceEncoder

class IntentRouter:
    """
    Semantic Router for advanced intent classification.
    Uses local embeddings to map user queries to actionable routes.
    """
    
    def __init__(self, threshold: float = 0.75):
        self.encoder = HuggingFaceEncoder(name="sentence-transformers/all-MiniLM-L6-v2")
        self.routes = self._define_routes()
        self.layer = RouteLayer(encoder=self.encoder, routes=self.routes)
        self.threshold = threshold
        print("✅ Semantic Router initialized with local encoder")

    def _define_routes(self) -> List[Route]:
        """Define the semantic routes for the system."""
        
        # 1. Vision Route (Screenshots, Seeing)
        vision_route = Route(
            name="vision",
            utterances=[
                "look at this",
                "what is on my screen",
                "screen dekho",
                "take a screenshot",
                "capture the screen",
                "read this text",
                "tell me what you see",
                "kya hai ye screen par",
                "scan this image",
                "check taskbar",
                "describe the current window",
                "ankhein khol ke dekho"
            ]
        )
        
        # 2. Open App Route
        open_route = Route(
            name="open",
            utterances=[
                "open google chrome",
                "launch spotify",
                "start notepad",
                "run calculator",
                "chrome khol do",
                "vscode chalu karo",
                "open the browser",
                "launch the application"
            ]
        )
        
        # 3. Close App Route
        close_route = Route(
            name="close",
            utterances=[
                "close this window",
                "quit chrome",
                "exit spotify",
                "kill the process",
                "band karo ise",
                "stop the application",
                "shut it down"
            ]
        )
        
        # 4. Search Route
        search_route = Route(
            name="search",
            utterances=[
                "search for recent AI news",
                "google who is the president",
                "find a recipe for pasta",
                "look up quantum computing",
                "dhund ke batao",
                "internet pe search karo",
                "khoj karo iski"
            ]
        )
        
        # 5. Play/Media Route (YouTube/Spotify)
        play_route = Route(
            name="play",
            utterances=[
                "play some music",
                "put on a song",
                "search for techburner on youtube",
                "play lo-fi beats",
                "gana bajao",
                "kuch chalao",
                "watch a video",
                "baja do kuch"
            ]
        )

        return [vision_route, open_route, close_route, search_route, play_route]

    def determine_intent(self, query: str) -> Tuple[Optional[str], float]:
        """
        Determine the intent of a query.
        Returns: (route_name, confidence_score)
        """
        try:
            # Semantic Router returns a simplified object or string?
            # Creating a mock wrapper for now as version differences vary
            # In 0.0.23, routing is simple.
            
            # Use the layer to route
            result = self.layer(query)
            
            if result.name and result.score and result.score >= self.threshold:
                return result.name, result.score
            
            return None, 0.0
            
        except Exception as e:
            print(f"Routing Error: {e}")
            return None, 0.0
