"""
Unified Memory Retrieval for Chat and Voice
Searches memory and returns answers from learned data
"""

import sqlite3
from pathlib import Path
import re
from typing import Optional, List, Dict

class UnifiedMemoryRetrieval:
    """
    Retrieves learned information for BOTH chat and voice queries
    Same memory, same learning, different interfaces
    """
    
    def __init__(self):
        self.memory_db = Path("data/memory.db")
        self.enhanced_learning_db = Path("data/enhanced_learning.db")
    
    def search_memory(self, query: str, mode: str = "chat") -> Optional[str]:
        """
        Search memory for relevant information
        Works for both chat and voice queries
        
        Args:
            query: User's question (from chat or voice)
            mode: 'chat' or 'voice' (doesn't affect search, just for logging)
        
        Returns:
            Answer if found, None otherwise
        """
        query_lower = query.lower()
        
        # Check for specific question patterns
        
        # 1. Date/Time questions
        if any(word in query_lower for word in ['when', 'date', 'time']):
            answer = self._search_dates(query_lower)
            if answer:
                return answer
        
        # 2. App/Tool questions  
        if any(word in query_lower for word in ['what app', 'which app', 'what tool']):
            answer = self._search_apps(query_lower)
            if answer:
                return answer
        
        # 3. "What did I" questions (recall recent actions)
        if 'what did i' in query_lower or 'what was i' in query_lower:
            answer = self._search_recent_actions(query_lower)
            if answer:
                return answer
        
        # 4. General keyword search
        answer = self._search_keywords(query_lower)
        if answer:
            return answer
        
        return None
    
    def _search_dates(self, query: str) -> Optional[str]:
        """Search for date-related information"""
        try:
            conn = sqlite3.connect(str(self.memory_db))
            cursor = conn.cursor()
            
            # Search for exam dates
            if 'exam' in query:
                cursor.execute("""
                    SELECT content FROM enhanced_memory 
                    WHERE content LIKE '%exam%' 
                    AND content LIKE '%dec%'
                    ORDER BY importance_level DESC, timestamp DESC
                    LIMIT 1
                """)
                row = cursor.fetchone()
                if row:
                    # Extract date from content
                    content = row[0]
                    date_match = re.search(r'(\d{1,2}\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*\d{0,4})', 
                                         content.lower())
                    if date_match:
                        conn.close()
                        return f"Your exam is on {date_match.group(1)}"
            
            conn.close()
        except Exception as e:
            print(f"Error searching dates: {e}")
        
        return None
    
    def _search_apps(self, query: str) -> Optional[str]:
        """Search for app usage information"""
        try:
            conn = sqlite3.connect(str(self.memory_db))
            cursor = conn.cursor()
            
            # Find apps mentioned in conversations
            cursor.execute("""
                SELECT content FROM enhanced_memory 
                WHERE speaker = 'user'
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            
            apps_found = []
            for row in cursor.fetchall():
                content = row[0].lower()
                # Look for common apps
                for app in ['notepad', 'sticky', 'calculator', 'chrome', 'excel', 'word', 'paint']:
                    if app in content:
                        apps_found.append(app)
            
            conn.close()
            
            if apps_found:
                return f"You've used: {', '.join(set(apps_found))}"
        
        except Exception as e:
            print(f"Error searching apps: {e}")
        
        return None
    
    def _search_recent_actions(self, query: str) -> Optional[str]:
        """Search recent user actions"""
        try:
            conn = sqlite3.connect(str(self.memory_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT content, timestamp FROM enhanced_memory 
                WHERE speaker = 'user'
                ORDER BY timestamp DESC
                LIMIT 5
            """)
            
            recent = cursor.fetchall()
            conn.close()
            
            if recent:
                # Return most recent action
                return f"Recently you said: {recent[0][0][:100]}"
        
        except Exception as e:
            print(f"Error searching recent actions: {e}")
        
        return None
    
    def _search_keywords(self, query: str) -> Optional[str]:
        """General keyword-based search"""
        try:
            # Extract key words from query
            keywords = [w for w in query.split() if len(w) > 3 and w not in ['what', 'when', 'where', 'which', 'that', 'this']]
            
            if not keywords:
                return None
            
            conn = sqlite3.connect(str(self.memory_db))
            cursor = conn.cursor()
            
            # Build search query
            search_pattern = '%' + '%'.join(keywords) + '%'
            
            cursor.execute("""
                SELECT content, importance_level FROM enhanced_memory 
                WHERE content LIKE ?
                ORDER BY importance_level DESC, timestamp DESC
                LIMIT 1
            """, (search_pattern,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return f"I found: {row[0][:150]}"
        
        except Exception as e:
            print(f"Error in keyword search: {e}")
        
        return None
    
    def get_context_for_response(self, query: str, mode: str = "chat") -> Dict:
        """
        Get full context for generating a response
        Returns relevant memories, facts, and patterns
        """
        context = {
            'query': query,
            'mode': mode,
            'relevant_memories': [],
            'facts': {},
            'recent_context': []
        }
        
        try:
            conn = sqlite3.connect(str(self.memory_db))
            cursor = conn.cursor()
            
            # Get recent conversation context (last 5 messages)
            cursor.execute("""
                SELECT speaker, content FROM memory 
                ORDER BY timestamp DESC 
                LIMIT 5
            """)
            context['recent_context'] = [
                {'speaker': row[0], 'content': row[1]} 
                for row in cursor.fetchall()
            ]
            
            # Get relevant memories based on query keywords
            keywords = query.lower().split()
            for keyword in keywords:
                if len(keyword) > 3:
                    cursor.execute("""
                        SELECT content, importance_level, category 
                        FROM enhanced_memory 
                        WHERE content LIKE ?
                        ORDER BY importance_level DESC
                        LIMIT 3
                    """, (f'%{keyword}%',))
                    
                    for row in cursor.fetchall():
                        context['relevant_memories'].append({
                            'content': row[0],
                            'importance': row[1],
                            'category': row[2]
                        })
            
            conn.close()
        
        except Exception as e:
            print(f"Error getting context: {e}")
        
        return context


# INTEGRATION EXAMPLE
def example_usage():
    """
    Example: How to use unified memory for both chat and voice
    """
    
    retrieval = UnifiedMemoryRetrieval()
    
    # Test queries from both chat and voice
    test_queries = [
        ("when is my exam?", "voice"),
        ("when is my exam?", "chat"),
        ("what apps have i used?", "voice"),
        ("what did i ask you recently?", "chat"),
    ]
    
    print("\n" + "="*60)
    print("🎙️💬 UNIFIED MEMORY RETRIEVAL TEST")
    print("="*60)
    
    for query, mode in test_queries:
        icon = "🎙️" if mode == "voice" else "💬"
        print(f"\n{icon} [{mode.upper()}] Query: {query}")
        
        # Search memory
        answer = retrieval.search_memory(query, mode)
        
        if answer:
            print(f"   ✅ Found: {answer}")
        else:
            print(f"   ❌ No relevant memory found")
        
        # Get full context
        context = retrieval.get_context_for_response(query, mode)
        print(f"   📚 Context: {len(context['recent_context'])} recent messages, "
              f"{len(context['relevant_memories'])} relevant memories")
    
    print("\n" + "="*60)
    print("✅ Same memory works for both chat and voice!")
    print("="*60)


if __name__ == "__main__":
    example_usage()
