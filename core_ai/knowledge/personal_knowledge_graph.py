import logging
from typing import Dict, Any, List, Optional
from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
from ai_assistant.core.database_config import get_db_path_str

logger = logging.getLogger(__name__)

class KnowledgeGraphInterface:
    """
    Clean interface for the Executive Brain to query the Personal Knowledge Graph.
    Provides context resolution for commands.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KnowledgeGraphInterface, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if not self._initialized:
            db_path = get_db_path_str('personal_knowledge')
            self.pkg = PersonalKnowledgeGraph(db_path)
            self._initialized = True
            
    def get_context_for_command(self, command: str) -> str:
        """
        Analyze a command, extract potential entities, and return relevant context from the graph.
        For example, if command is "Message Diwakar", it will look up "Diwakar" and return relations.
        """
        words = command.lower().split()
        context_pieces = []
        
        # Super naive entity extraction for demonstration
        # In a real system, we'd use NLP NER. Here we just try to find matches in the FTS.
        # Let's extract words > 3 chars
        keywords = [w for w in words if len(w) > 3 and w not in ['open', 'start', 'play', 'send', 'message', 'what', 'who', 'where']]
        
        for keyword in keywords:
            # Query the graph for this keyword
            results = self.pkg._search_fts(keyword, limit=2)
            for res in results:
                content = res.get('content', '')
                if content and content.lower() != keyword:
                    context_pieces.append(f"- Known fact: {content}")
                    
                node_id = res.get('node_id')
                if node_id:
                    # Get relations
                    relations = self.pkg.related_to(node_id, limit=3)
                    for rel in relations:
                        target = rel.get('target', '')
                        rel_type = rel.get('relationship', '')
                        if target and rel_type:
                            context_pieces.append(f"- {content} is {rel_type} {target}")
                            
        if context_pieces:
            unique_pieces = list(set(context_pieces))
            return "Knowledge Graph Context:\n" + "\n".join(unique_pieces)
        return ""
        
def get_knowledge_graph() -> KnowledgeGraphInterface:
    return KnowledgeGraphInterface()
