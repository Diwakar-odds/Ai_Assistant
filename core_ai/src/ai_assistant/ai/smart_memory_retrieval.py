# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Smart Memory Retrieval
Searches memory to answer user questions from past conversations
"""

import sqlite3
import re
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta

class SmartMemoryRetrieval:
    """Intelligently retrieve information from learned conversations"""
    
    def __init__(self, db_path: str = "data/core/memory.db"):
        self.db_path = Path(db_path)
    
    def answer_from_memory(self, question: str) -> Optional[str]:
        """
        Try to answer a question from memory
        
        Args:
            question: User's question
            
        Returns:
            Answer if found, None otherwise
        """
        question_lower = question.lower()
        
        # Extract key information patterns
        patterns = {
            'date': self._extract_date_query,
            'app_usage': self._extract_app_query,
            'event': self._extract_event_query,
            'general': self._search_general_memory
        }
        
        # Try each pattern
        for pattern_name, pattern_func in patterns.items():
            result = pattern_func(question_lower)
            if result:
                return result
        
        return None
    
    def _extract_date_query(self, question: str) -> Optional[str]:
        """Extract date-related information (exams, appointments, etc.)"""
        # Patterns for date queries
        date_patterns = [
            r'when.*exam',
            r'exam.*date',
            r'when.*test',
            r'when.*appointment',
            r'when.*meeting',
        ]
        
        if any(re.search(pattern, question) for pattern in date_patterns):
            return self._search_for_dates(question)
        
        return None
    
    def _search_for_dates(self, question: str) -> Optional[str]:
        """Search memory for date-related information"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Search for exam/test/appointment mentions
            keywords = ['exam', 'test', 'appointment', 'meeting', 'deadline', 'due']
            
            for keyword in keywords:
                if keyword in question:
                    cursor.execute("""
                        SELECT content, timestamp, importance_level 
                        FROM enhanced_memory 
                        WHERE LOWER(content) LIKE ? 
                        ORDER BY importance_level DESC, timestamp DESC
                        LIMIT 5
                    """, (f'%{keyword}%',))
                    
                    results = cursor.fetchall()
                    if results:
                        # Extract dates from content
                        for content, timestamp, importance in results:
                            dates = self._extract_dates_from_text(content)
                            if dates:
                                conn.close()
                                return f"Based on our previous conversation: {dates[0]}"
            
            conn.close()
        except Exception as e:
            logger.error(f"Error searching for dates: {e}")
        
        return None
    
    def _extract_dates_from_text(self, text: str) -> List[str]:
        """Extract date mentions from text"""
        date_patterns = [
            r'\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*',
            r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}',
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'on\s+the\s+\d{1,2}(?:st|nd|rd|th)?',
        ]
        
        dates = []
        text_lower = text.lower()
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text_lower)
            dates.extend(matches)
        
        return dates
    
    def _extract_app_query(self, question: str) -> Optional[str]:
        """Extract app usage information"""
        app_patterns = [
            r'what.*app.*use',
            r'which.*application',
            r'prefer.*app',
        ]
        
        if any(re.search(pattern, question) for pattern in app_patterns):
            return self._search_app_usage()
        
        return None
    
    def _search_app_usage(self) -> Optional[str]:
        """Search for app usage patterns"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Find commonly used apps
            apps = ['notepad', 'sticky', 'chrome', 'excel', 'word', 'calculator', 'spotify']
            
            cursor.execute("""
                SELECT content 
                FROM enhanced_memory 
                WHERE """ + " OR ".join([f"LOWER(content) LIKE '%{app}%'" for app in apps]) + """
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            
            results = cursor.fetchall()
            conn.close()
            
            if results:
                # Count app mentions
                app_counts = {}
                for (content,) in results:
                    for app in apps:
                        if app in content.lower():
                            app_counts[app] = app_counts.get(app, 0) + 1
                
                if app_counts:
                    most_used = sorted(app_counts.items(), key=lambda x: x[1], reverse=True)
                    app_list = ", ".join([f"{app} ({count} times)" for app, count in most_used[:3]])
                    return f"Based on your history, you commonly use: {app_list}"
        except Exception as e:
            logger.error(f"Error searching app usage: {e}")
        
        return None
    
    def _extract_event_query(self, question: str) -> Optional[str]:
        """Extract event-related information"""
        event_patterns = [
            r'what.*today',
            r'what.*tomorrow',
            r'what.*next week',
            r'upcoming',
        ]
        
        if any(re.search(pattern, question) for pattern in event_patterns):
            return self._search_events(question)
        
        return None
    
    def _search_events(self, question: str) -> Optional[str]:
        """Search for upcoming events"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Get recent high-importance conversations
            cursor.execute("""
                SELECT content, timestamp 
                FROM enhanced_memory 
                WHERE importance_level >= 4 
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            
            results = cursor.fetchall()
            conn.close()
            
            if results:
                events = []
                for content, timestamp in results:
                    if any(word in content.lower() for word in ['exam', 'meeting', 'appointment', 'deadline']):
                        events.append(content[:100])
                
                if events:
                    return f"Upcoming events from your history:\\n" + "\\n".join(f"- {e}" for e in events[:3])
        except Exception as e:
            logger.error(f"Error searching events: {e}")
        
        return None
    
    def _search_general_memory(self, question: str) -> Optional[str]:
        """General memory search based on semantic vector embeddings (RAG)"""
        try:
            from ai_assistant.ai.memory import semantic_search_memory
            
            # Use the new vector-based search
            result = semantic_search_memory(question, limit=2, threshold=0.25)
            
            # If the result is one of the fallback "Not found" messages, return None
            if result.startswith("No "):
                return None
                
            return result
            
        except Exception as e:
            logger.error(f"Error in general semantic search: {e}")
            return None


# Integration function
def enhance_response_with_memory(user_message: str, ai_response: str) -> str:
    """
    Enhance AI response by checking memory first
    
    Args:
        user_message: User's message/question
        ai_response: AI's generated response
        
    Returns:
        Enhanced response with memory information if available
    """
    # Check if it's a question
    if '?' not in user_message:
        return ai_response
    
    # Try to answer from memory
    retriever = SmartMemoryRetrieval()
    memory_answer = retriever.answer_from_memory(user_message)
    
    if memory_answer:
        return memory_answer
    
    # Return original response if no memory found
    return ai_response


# Test function
if __name__ == "__main__":
    retriever = SmartMemoryRetrieval()
    
    test_questions = [
        "when is my exam?",
        "what apps do I use?",
        "when is my test?",
    ]
    
    logger.debug("Testing Smart Memory Retrieval:")
    print("="*60)
    
    for question in test_questions:
        print(f"\\nQ: {question}")
        answer = retriever.answer_from_memory(question)
        print(f"A: {answer or 'No information found in memory'}")
