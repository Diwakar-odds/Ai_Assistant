import logging
import json
import re
from typing import Dict, Any, List, Optional
from ai_assistant.ai.llm_provider import UnifiedChatInterface
from ai_assistant.ai.user_dna import UserDNA
from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
from ai_assistant.core.database_config import get_db_path_str

logger = logging.getLogger(__name__)

class FactExtractor:
    """
    LLM-powered fact extraction pipeline that runs on conversation turns.
    Extracts people, projects, dates, and commitments and stores them
    in the PersonalKnowledgeGraph.
    """
    
    def __init__(self, user_dna: Optional[UserDNA] = None, pkg: Optional[PersonalKnowledgeGraph] = None):
        self.user_dna = user_dna or UserDNA()
        self.pkg = pkg or PersonalKnowledgeGraph(get_db_path_str('personal_knowledge'))
        self.llm = UnifiedChatInterface()
        
        # Override the system prompt for extraction
        self.llm.reset()
        self.llm.add_system_message(
            "You are an expert information extraction system. "
            "Your task is to analyze user text and extract entities and relationships. "
            "Output ONLY valid JSON in the exact format requested, with no markdown formatting or extra text."
        )

    def extract_from_turn(self, user_text: str, assistant_response: str = "") -> Dict[str, Any]:
        """
        Analyze the conversation turn to extract structured facts.
        Populates both UserDNA (for simple preferences) and PersonalKnowledgeGraph (for relations).
        """
        logger.info(f"Extracting facts from text: {user_text[:50]}...")
        
        # 1. Fallback regex extraction (fast, deterministic)
        found_in_dna = self.user_dna.extract_facts_from_text(user_text)
        
        # 2. LLM-based deep extraction
        prompt = f"""
        Analyze the following text from the user. Extract any mentioned people, projects, deadlines, commitments, or facts.
        
        User: {user_text}
        
        Return a JSON object with the following structure (leave arrays empty if none found):
        {{
            "relationships": [
                {{"entity1": "User", "relation": "working_on", "entity2": "Project X"}},
                {{"entity1": "User", "relation": "meeting_with", "entity2": "John"}},
                {{"entity1": "User", "relation": "likes", "entity2": "Coffee"}}
            ]
        }}
        """
        
        try:
            response = self.llm.chat(prompt, stream=False)
            
            # Clean up potential markdown formatting in response
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
                
            data = json.loads(clean_response)
            
            relationships = data.get("relationships", [])
            extracted_count = len(relationships)
            
            for rel in relationships:
                e1 = rel.get("entity1")
                r = rel.get("relation")
                e2 = rel.get("entity2")
                
                if e1 and r and e2:
                    e1_id = self.pkg.add_knowledge_node(e1, "entity", {"source": "fact_extractor", "context": user_text})
                    e2_id = self.pkg.add_knowledge_node(e2, "entity", {"source": "fact_extractor", "context": user_text})
                    self.pkg.add_relationship(e1_id, e2_id, r)
                    logger.debug(f"Fact Extractor added triple: {e1} -> {r} -> {e2}")
            
            if extracted_count > 0:
                logger.info(f"Successfully extracted {extracted_count} relationships via LLM.")
                
            return {
                "success": True,
                "regex_facts_found": found_in_dna,
                "llm_relations_found": extracted_count
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Fact Extractor: {e}. Raw response: {response}")
            return {"success": False, "error": "JSON Parse Error"}
        except Exception as e:
            logger.error(f"Error in Fact Extractor: {e}")
            return {"success": False, "error": str(e)}

    def batch_process_history(self, chat_history: List[Dict[str, str]]):
        """Process an entire historical chat transcript."""
        for message in chat_history:
            if message.get("role") == "user":
                self.extract_from_turn(message.get("content", ""))
