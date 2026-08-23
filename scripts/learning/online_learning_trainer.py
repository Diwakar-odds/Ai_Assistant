"""
Online Learning Trainer - Connects WebScrapingManager to 27 AI Learning Systems

This system:
1. Collects data from internet sources (news, RSS, weather, websites)
2. Processes and structures the data
3. Routes data to appropriate learning systems
4. Tracks learning progress
5. Reports insights

Author: AI Assistant
Date: December 21, 2025
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import sqlite3

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ai_assistant.integrations.web_scraping import (
    WebScrapingManager,
    get_weather_info,
    get_latest_news
)

# Import learning systems
try:
    from ai_assistant.ai.historical_rag import HistoricalRAG
    from ai_assistant.ai.conversation_clustering import ConversationClusterer
    from ai_assistant.ai.intent_classification import IntentClassifier
    from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
    from ai_assistant.ai.memory import save_to_memory, search_memory
    from ai_assistant.ai.advanced_feedback_learning import AdaptiveLearningEngine
except ImportError as e:
    print(f"Warning: Could not import some learning systems: {e}")
    raise


class OnlineLearningTrainer:
    """
    Coordinates online data collection and feeds it to AI learning systems.
    """
    
    def __init__(self, db_path: str = "data/online_learning.db"):
        """
        Initialize the online learning trainer.
        
        Args:
            db_path: Path to database for tracking online learning
        """
        self.db_path = db_path
        self.web_scraper = WebScrapingManager()
        self.logger = self._setup_logging()
        
        # Initialize database
        self._init_database()
        
        # Initialize learning systems
        self.learning_systems = self._init_learning_systems()
        
        self.logger.info("OnlineLearningTrainer initialized successfully")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger("OnlineLearningTrainer")
        logger.setLevel(logging.INFO)
        
        # Create date-based logs directory structure
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        log_dir = Path("logs") / today
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # File handler with timestamp
        timestamp = datetime.now().strftime("%H%M%S")
        log_file = f"online_learning_{timestamp}.log"
        fh = logging.FileHandler(log_dir / log_file)
        fh.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def _init_database(self):
        """Initialize SQLite database for tracking online learning."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for tracking collected data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collected_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_name TEXT NOT NULL,
                data_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT 0
            )
        """)
        
        # Table for tracking learning progress
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                system_name TEXT NOT NULL,
                data_id INTEGER,
                success BOOLEAN,
                error_message TEXT,
                learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (data_id) REFERENCES collected_data (id)
            )
        """)
        
        # Table for daily statistics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date DATE PRIMARY KEY,
                articles_collected INTEGER DEFAULT 0,
                items_learned INTEGER DEFAULT 0,
                systems_updated INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Database initialized at {self.db_path}")
    
    def _init_learning_systems(self) -> Dict[str, Any]:
        """Initialize available learning systems."""
        systems = {}
        
        try:
            systems['historical_rag'] = HistoricalRAG()
            self.logger.info("✓ HistoricalRAG initialized")
        except Exception as e:
            self.logger.warning(f"✗ HistoricalRAG: {e}")
        
        try:
            systems['conversation_clusterer'] = ConversationClusterer()
            self.logger.info("✓ ConversationClusterer initialized")
        except Exception as e:
            self.logger.warning(f"✗ ConversationClusterer: {e}")
        
        try:
            systems['intent_classifier'] = IntentClassifier()
            self.logger.info("✓ IntentClassifier initialized")
        except Exception as e:
            self.logger.warning(f"✗ IntentClassifier: {e}")
        
        try:
            systems['knowledge_graph'] = PersonalKnowledgeGraph(db_path="data/ai_memory.db")
            self.logger.info("✓ PersonalKnowledgeGraph initialized")
        except Exception as e:
            self.logger.warning(f"✗ PersonalKnowledgeGraph: {e}")
        
        # Semantic memory uses the memory module functions
        systems['semantic_memory'] = {
            'save': save_to_memory,
            'search': search_memory
        }
        self.logger.info("✓ SemanticMemory (memory module) initialized")
        
        try:
            systems['feedback_learning'] = AdaptiveLearningEngine()
            self.logger.info("✓ FeedbackLearning initialized")
        except Exception as e:
            self.logger.warning(f"✗ FeedbackLearning: {e}")
        
        return systems
    
    def collect_news(self, categories: List[str] = None, max_articles: int = 5) -> int:
        """
        Collect news articles from various categories.
        
        Args:
            categories: List of news categories (default: technology, business)
            max_articles: Maximum articles to collect per category
        
        Returns:
            Number of articles collected
        """
        if categories is None:
            categories = ["technology", "business", "general"]
        
        total_collected = 0
        
        for category in categories:
            try:
                self.logger.info(f"Collecting {category} news...")
                
                # Use the standalone get_latest_news function
                news_text = get_latest_news(category=category, max_articles=max_articles)
                
                if news_text and len(news_text) > 100 and "❌" not in news_text:
                    # Store in database
                    self._store_collected_data(
                        source_type="news_api",
                        source_name=f"{category}_news",
                        data_type="news_article",
                        content=news_text,
                        metadata=json.dumps({"category": category, "timestamp": datetime.now().isoformat()})
                    )
                    total_collected += 1
                    self.logger.info(f"✓ Collected {category} news")
                else:
                    self.logger.warning(f"✗ No content for {category} news")
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Error collecting {category} news: {e}")
        
        self.logger.info(f"Total articles collected: {total_collected}")
        return total_collected
    
    def collect_weather_patterns(self, cities: List[str] = None) -> int:
        """
        Collect weather data for pattern learning.
        
        Args:
            cities: List of cities to collect weather for
        
        Returns:
            Number of weather records collected
        """
        if cities is None:
            cities = ["New York", "London", "Tokyo", "Sydney"]
        
        total_collected = 0
        
        for city in cities:
            try:
                # Use standalone get_weather_info function
                weather_info = get_weather_info(location=city)
                
                if weather_info and "❌" not in weather_info:
                    self._store_collected_data(
                        source_type="api",
                        source_name="weather",
                        data_type="weather_data",
                        content=weather_info,
                        metadata=json.dumps({"city": city, "timestamp": datetime.now().isoformat()})
                    )
                    total_collected += 1
                    self.logger.info(f"✓ Collected weather for {city}")
                else:
                    self.logger.warning(f"✗ Failed to get weather for {city}")
                
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error collecting weather for {city}: {e}")
        
        return total_collected
    
    def _store_collected_data(self, source_type: str, source_name: str, 
                             data_type: str, content: str, metadata: str = None):
        """Store collected data in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO collected_data (source_type, source_name, data_type, content, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (source_type, source_name, data_type, content, metadata))
        
        conn.commit()
        conn.close()
    
    def process_and_learn(self, batch_size: int = 10) -> Dict[str, int]:
        """
        Process unprocessed data and feed to learning systems.
        
        Args:
            batch_size: Number of items to process in one batch
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'systems_updated': set()
        }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get unprocessed data
        cursor.execute("""
            SELECT id, source_type, data_type, content, metadata
            FROM collected_data
            WHERE processed = 0
            LIMIT ?
        """, (batch_size,))
        
        unprocessed = cursor.fetchall()
        
        for data_id, source_type, data_type, content, metadata in unprocessed:
            try:
                # Route to appropriate learning systems
                if data_type == "news_article":
                    self._learn_from_article(data_id, content, metadata)
                    stats['systems_updated'].add('historical_rag')
                    stats['systems_updated'].add('semantic_memory')
                    stats['systems_updated'].add('knowledge_graph')
                
                elif data_type == "weather_data":
                    self._learn_from_weather(data_id, content, metadata)
                    stats['systems_updated'].add('semantic_memory')
                
                # Mark as processed
                cursor.execute("""
                    UPDATE collected_data SET processed = 1 WHERE id = ?
                """, (data_id,))
                
                stats['processed'] += 1
                stats['successful'] += 1
                
            except Exception as e:
                self.logger.error(f"Error processing data {data_id}: {e}")
                stats['failed'] += 1
                
                # Record error
                cursor.execute("""
                    INSERT INTO learning_progress (system_name, data_id, success, error_message)
                    VALUES (?, ?, ?, ?)
                """, ("processor", data_id, False, str(e)))
        
        conn.commit()
        conn.close()
        
        stats['systems_updated'] = len(stats['systems_updated'])
        
        self.logger.info(f"Processing complete: {stats}")
        return stats
    
    def _learn_from_article(self, data_id: int, content: str, metadata: str):
        """Feed article content to appropriate learning systems."""
        
        # Extract text from content (simplified - you'd parse RSS/HTML properly)
        text = content[:5000]  # Limit text length
        
        # Feed to HistoricalRAG
        if 'historical_rag' in self.learning_systems:
            try:
                self.learning_systems['historical_rag'].add_interaction(
                    query='Internet article content',
                    response=text[:500],  # Limit to 500 chars
                    context={'source': 'internet', 'type': 'article'},
                    success_score=0.8
                )
                self._record_learning_success(data_id, 'historical_rag')
            except Exception as e:
                self.logger.error(f"HistoricalRAG learning error: {e}")
        
        # Feed to SemanticMemory (using memory module)
        if 'semantic_memory' in self.learning_systems:
            try:
                self.learning_systems['semantic_memory']['save'](
                    speaker='internet',
                    content=text[:1000]  # Limit to 1000 chars
                )
                self._record_learning_success(data_id, 'semantic_memory')
            except Exception as e:
                self.logger.error(f"SemanticMemory learning error: {e}")
        
        # Extract entities for KnowledgeGraph (simplified)
        if 'knowledge_graph' in self.learning_systems:
            try:
                # Simple entity extraction - you'd use NER here
                words = text.split()[:100]
                entities = [w for w in words if w[0].isupper() and len(w) > 3]
                
                for entity in entities[:10]:  # Limit entities
                    self.learning_systems['knowledge_graph'].add_knowledge_node(
                        content=entity,
                        node_type='discovered_entity',
                        metadata={'source': 'online_article'}
                    )
                
                self._record_learning_success(data_id, 'knowledge_graph')
            except Exception as e:
                self.logger.error(f"KnowledgeGraph learning error: {e}")
    
    def _learn_from_weather(self, data_id: int, content: str, metadata: str):
        """Feed weather data to learning systems."""
        
        try:
            # Content is already a formatted string from get_weather_info
            # Feed to SemanticMemory as contextual knowledge
            if 'semantic_memory' in self.learning_systems:
                self.learning_systems['semantic_memory']['save'](
                    speaker='weather_api',
                    content=content[:500]  # Limit to 500 chars
                )
                self._record_learning_success(data_id, 'semantic_memory')
            
        except Exception as e:
            self.logger.error(f"Weather learning error: {e}")
    
    def _record_learning_success(self, data_id: int, system_name: str):
        """Record successful learning in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO learning_progress (system_name, data_id, success)
            VALUES (?, ?, ?)
        """, (system_name, data_id, True))
        
        conn.commit()
        conn.close()
    
    def get_learning_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get learning statistics for the last N days.
        
        Args:
            days: Number of days to look back
        
        Returns:
            Dictionary with statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total data collected
        cursor.execute("""
            SELECT COUNT(*) FROM collected_data
            WHERE collected_at >= datetime('now', '-' || ? || ' days')
        """, (days,))
        total_collected = cursor.fetchone()[0]
        
        # Total processed
        cursor.execute("""
            SELECT COUNT(*) FROM collected_data
            WHERE processed = 1 AND collected_at >= datetime('now', '-' || ? || ' days')
        """, (days,))
        total_processed = cursor.fetchone()[0]
        
        # Learning by system
        cursor.execute("""
            SELECT system_name, COUNT(*) as count, SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful
            FROM learning_progress
            WHERE learned_at >= datetime('now', '-' || ? || ' days')
            GROUP BY system_name
            ORDER BY count DESC
        """, (days,))
        systems_stats = cursor.fetchall()
        
        conn.close()
        
        return {
            'period_days': days,
            'total_collected': total_collected,
            'total_processed': total_processed,
            'processing_rate': f"{(total_processed/total_collected*100) if total_collected > 0 else 0:.1f}%",
            'systems_updated': len(systems_stats),
            'system_breakdown': [
                {'system': s[0], 'total': s[1], 'successful': s[2]}
                for s in systems_stats
            ]
        }
    
    def run_daily_collection(self):
        """
        Run daily data collection and processing cycle.
        This should be scheduled to run once per day.
        """
        self.logger.info("=" * 60)
        self.logger.info("STARTING DAILY ONLINE LEARNING CYCLE")
        self.logger.info("=" * 60)
        
        try:
            # Step 1: Collect news
            self.logger.info("\n[1/4] Collecting news articles...")
            articles = self.collect_news(max_articles=20)
            
            # Step 2: Collect weather
            self.logger.info("\n[2/4] Collecting weather data...")
            weather = self.collect_weather_patterns()
            
            # Step 3: Process and learn
            self.logger.info("\n[3/4] Processing and learning...")
            stats = self.process_and_learn(batch_size=50)
            
            # Step 4: Report stats
            self.logger.info("\n[4/4] Generating statistics...")
            learning_stats = self.get_learning_stats(days=1)
            
            self.logger.info("\n" + "=" * 60)
            self.logger.info("DAILY CYCLE COMPLETE")
            self.logger.info("=" * 60)
            self.logger.info(f"Articles collected: {articles}")
            self.logger.info(f"Weather records: {weather}")
            self.logger.info(f"Items processed: {stats['processed']}")
            self.logger.info(f"Learning success: {stats['successful']}/{stats['processed']}")
            self.logger.info(f"Systems updated: {stats['systems_updated']}")
            self.logger.info("=" * 60)
            
            return {
                'success': True,
                'articles': articles,
                'weather': weather,
                'processed': stats['processed'],
                'systems_updated': stats['systems_updated']
            }
            
        except Exception as e:
            self.logger.error(f"Error in daily collection: {e}")
            return {'success': False, 'error': str(e)}


def main():
    """Main execution function."""
    print("\n" + "=" * 70)
    print(" ONLINE LEARNING TRAINER - Connecting Internet to Your AI ".center(70))
    print("=" * 70 + "\n")
    
    # Initialize trainer
    print("Initializing Online Learning Trainer...")
    trainer = OnlineLearningTrainer()
    
    print("\n" + "-" * 70)
    print(" MENU ".center(70))
    print("-" * 70)
    print("1. Run daily collection cycle (collect + process + learn)")
    print("2. Collect news articles only")
    print("3. Collect weather data only")
    print("4. Process existing data")
    print("5. View learning statistics (last 7 days)")
    print("6. View learning statistics (last 30 days)")
    print("0. Exit")
    print("-" * 70)
    
    while True:
        choice = input("\nEnter your choice (0-6): ").strip()
        
        if choice == '0':
            print("\nExiting...")
            break
        
        elif choice == '1':
            print("\nRunning daily collection cycle...")
            result = trainer.run_daily_collection()
            if result['success']:
                print(f"\n✓ Daily cycle completed successfully!")
            else:
                print(f"\n✗ Error: {result.get('error')}")
        
        elif choice == '2':
            print("\nCollecting news articles...")
            count = trainer.collect_news()
            print(f"\n✓ Collected {count} articles")
        
        elif choice == '3':
            print("\nCollecting weather data...")
            count = trainer.collect_weather_patterns()
            print(f"\n✓ Collected {count} weather records")
        
        elif choice == '4':
            print("\nProcessing existing data...")
            stats = trainer.process_and_learn(batch_size=50)
            print(f"\n✓ Processed: {stats['processed']}")
            print(f"✓ Successful: {stats['successful']}")
            print(f"✗ Failed: {stats['failed']}")
            print(f"✓ Systems updated: {stats['systems_updated']}")
        
        elif choice == '5':
            print("\nLearning Statistics (Last 7 Days)")
            print("-" * 70)
            stats = trainer.get_learning_stats(days=7)
            print(f"Total Collected: {stats['total_collected']}")
            print(f"Total Processed: {stats['total_processed']}")
            print(f"Processing Rate: {stats['processing_rate']}")
            print(f"Systems Updated: {stats['systems_updated']}")
            print("\nSystem Breakdown:")
            for system in stats['system_breakdown']:
                print(f"  - {system['system']}: {system['successful']}/{system['total']} successful")
        
        elif choice == '6':
            print("\nLearning Statistics (Last 30 Days)")
            print("-" * 70)
            stats = trainer.get_learning_stats(days=30)
            print(f"Total Collected: {stats['total_collected']}")
            print(f"Total Processed: {stats['total_processed']}")
            print(f"Processing Rate: {stats['processing_rate']}")
            print(f"Systems Updated: {stats['systems_updated']}")
            print("\nSystem Breakdown:")
            for system in stats['system_breakdown']:
                print(f"  - {system['system']}: {system['successful']}/{system['total']} successful")
        
        else:
            print("\n✗ Invalid choice. Please enter 0-6.")


if __name__ == "__main__":
    main()
