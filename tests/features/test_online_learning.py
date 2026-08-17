"""
Quick test script for online learning system
"""
import sys
sys.path.insert(0, 'F:/bn/assitant')

print("=" * 70)
print("TESTING ONLINE LEARNING SYSTEM")
print("=" * 70)

# Test 1: Import all required modules
print("\n[1/5] Testing imports...")
try:
    from ai_assistant.web_scraping import WebScrapingManager
    print("  ✓ WebScrapingManager imported")
    
    from ai_assistant.ai.historical_rag import HistoricalRAG
    print("  ✓ HistoricalRAG imported")
    
    from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
    print("  ✓ PersonalKnowledgeGraph imported")
    
    from ai_assistant.modules.memory import save_to_memory, search_memory
    print("  ✓ Memory module imported")
    
    from online_learning_trainer import OnlineLearningTrainer
    print("  ✓ OnlineLearningTrainer imported")
    
    print("  ✓ All imports successful!")
except Exception as e:
    print(f"  ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Initialize the trainer
print("\n[2/5] Initializing OnlineLearningTrainer...")
try:
    trainer = OnlineLearningTrainer()
    print("  ✓ Trainer initialized successfully")
    print(f"  ✓ Learning systems loaded: {len(trainer.learning_systems)}")
    for system_name in trainer.learning_systems.keys():
        print(f"    - {system_name}")
except Exception as e:
    print(f"  ✗ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Collect news data
print("\n[3/5] Collecting news from internet...")
try:
    num_articles = trainer.collect_news(max_articles=5)
    print(f"  ✓ Collected {num_articles} articles")
except Exception as e:
    print(f"  ✗ News collection failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Collect weather data
print("\n[4/5] Collecting weather data...")
try:
    num_weather = trainer.collect_weather_patterns(cities=['London', 'New York'])
    print(f"  ✓ Collected {num_weather} weather records")
except Exception as e:
    print(f"  ✗ Weather collection failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Process and learn from collected data
print("\n[5/5] Processing data and feeding to AI learning systems...")
try:
    stats = trainer.process_and_learn(batch_size=20)
    print(f"  ✓ Processed {stats['processed']} items")
    print(f"  ✓ Successfully learned: {stats['successful']}")
    print(f"  ✓ Failed: {stats['failed']}")
    print(f"  ✓ Systems updated: {', '.join(stats['systems_updated'])}")
except Exception as e:
    print(f"  ✗ Processing failed: {e}")
    import traceback
    traceback.print_exc()

# Final Statistics
print("\n" + "=" * 70)
print("LEARNING STATISTICS")
print("=" * 70)
try:
    overall_stats = trainer.get_learning_stats(days=1)
    print(f"Total Collected: {overall_stats['total_collected']}")
    print(f"Total Processed: {overall_stats['total_processed']}")
    print(f"Processing Rate: {overall_stats['processing_rate']}")
    print(f"Systems Updated: {overall_stats['systems_updated']}")
    
    if overall_stats['system_breakdown']:
        print("\nSystem Breakdown:")
        for system in overall_stats['system_breakdown']:
            print(f"  - {system['system']}: {system['successful']}/{system['total']} successful")
except Exception as e:
    print(f"Error getting stats: {e}")

print("\n" + "=" * 70)
print("TEST COMPLETE!")
print("=" * 70)
print("\nNext steps:")
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")
print(f"1. Check logs/{today}/online_learning_*.log for detailed logs")
print("2. Check data/online_learning.db for collected data")
print("3. Run 'python online_learning_trainer.py' for interactive mode")
print("4. Run 'python schedule_online_learning.py' for automated daily learning")
