"""
Tests for online learning system
"""
import sys
import os
import pytest

# Add proper paths
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, os.path.join(project_root, 'core_ai', 'src'))
sys.path.insert(0, os.path.join(project_root, 'scripts', 'learning'))

def test_imports():
    """Verify that all required modules can be imported."""
    try:
        from ai_assistant.integrations.web_scraping import WebScrapingManager
        from ai_assistant.ai.historical_rag import HistoricalRAG
        from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
        from ai_assistant.ai.memory import save_to_memory, search_memory
        from online_learning_trainer import OnlineLearningTrainer
    except Exception as e:
        pytest.fail(f"Import failed: {e}")

@pytest.mark.skip(reason="Requires internet connection and takes significant time")
def test_initialize_and_run_trainer():
    """Test the initialization and execution of OnlineLearningTrainer."""
    from online_learning_trainer import OnlineLearningTrainer
    trainer = OnlineLearningTrainer()
    assert len(trainer.learning_systems) > 0
    
    # Test data collection
    num_articles = trainer.collect_news(max_articles=1)
    assert num_articles >= 0
    
    num_weather = trainer.collect_weather_patterns(cities=['London'])
    assert num_weather >= 0
    
    stats = trainer.process_and_learn(batch_size=5)
    assert 'processed' in stats
    
    overall_stats = trainer.get_learning_stats(days=1)
    assert 'total_collected' in overall_stats
