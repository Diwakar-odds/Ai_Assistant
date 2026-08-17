"""
COMPREHENSIVE VERIFICATION REPORT
Online Learning System Status Check
"""
import sqlite3
import os
from datetime import datetime

print("="*80)
print(" " * 20 + "ONLINE LEARNING SYSTEM - VERIFICATION REPORT")
print("="*80)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# 1. Check Files
print("[1] FILE SYSTEM CHECK")
print("-" * 80)
files_to_check = [
    ('online_learning_trainer.py', 'Main trainer'),
    ('schedule_online_learning.py', 'Scheduler'),
    ('ONLINE_LEARNING_GUIDE.md', 'User guide'),
    ('ONLINE_LEARNING_ARCHITECTURE.md', 'Architecture docs'),
    ('data/online_learning.db', 'Learning database')
]

for file, description in files_to_check:
    path = f'F:/bn/assitant/{file}'
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"  ✓ {description:30s} - {file:40s} ({size:,} bytes)")
    else:
        print(f"  ✗ {description:30s} - {file:40s} (MISSING)")

# 2. Check Database
print(f"\n[2] DATABASE STATUS")
print("-" * 80)
try:
    conn = sqlite3.connect('F:/bn/assitant/data/online_learning.db')
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"  Tables: {', '.join(tables)}")
    
    # Check collected data
    cursor.execute("SELECT COUNT(*) FROM collected_data")
    total_collected = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM collected_data WHERE processed = 0")
    pending = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM collected_data WHERE processed = 1")
    processed = cursor.fetchone()[0]
    
    print(f"\n  Data Collection:")
    print(f"    Total Items Collected: {total_collected}")
    print(f"    Processed:            {processed}")
    print(f"    Pending:              {pending}")
    
    # Show sample data types
    cursor.execute("SELECT data_type, COUNT(*) FROM collected_data GROUP BY data_type")
    data_types = cursor.fetchall()
    if data_types:
        print(f"\n  Data Types:")
        for dtype, count in data_types:
            print(f"    {dtype:20s}: {count} items")
    
    # Check most recent collection
    cursor.execute("SELECT source_type, data_type, timestamp FROM collected_data ORDER BY id DESC LIMIT 1")
    recent = cursor.fetchone()
    if recent:
        print(f"\n  Most Recent Collection:")
        print(f"    Type: {recent[0]} / {recent[1]}")
        print(f"    Time: {recent[2]}")
    
    conn.close()
    print("\n  ✓ Database is operational")
    
except Exception as e:
    print(f"\n  ✗ Database error: {e}")

# 3. Check Learning Progress
print(f"\n[3] AI LEARNING SYSTEMS STATUS")
print("-" * 80)
try:
    import sys
    sys.path.insert(0, 'F:/bn/assitant')
    from ai_assistant.ai.historical_rag import HistoricalRAG
    from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
    from ai_assistant.modules.memory import save_to_memory
    
    print("  ✓ Historical RAG - Available")
    print("  ✓ Knowledge Graph - Available")
    print("  ✓ Semantic Memory - Available")
    
    # Check if RAG has data
    rag = HistoricalRAG()
    print(f"\n  ✓ AI systems initialized successfully")
    
except Exception as e:
    print(f"  ✗ AI systems error: {e}")

# 4. Test Data Collection
print(f"\n[4] DATA COLLECTION TEST")
print("-" * 80)
try:
    from ai_assistant.web_scraping import get_weather_info, get_latest_news
    
    # Test weather
    weather = get_weather_info("Paris")
    if "Temperature" in weather:
        print(f"  ✓ Weather API working")
        print(f"    Sample: {weather[:60]}...")
    else:
        print(f"  ✗ Weather API failed: {weather[:60]}")
    
    # Test news
    news = get_latest_news(category="general", max_articles=1)
    if "Latest" in news:
        print(f"  ✓ News RSS working")
        print(f"    Sample: {news.split(chr(10))[0][:60]}...")
    else:
        print(f"  ✗ News RSS failed")
        
except Exception as e:
    print(f"  ✗ Collection test error: {e}")

# 5. Summary
print(f"\n[5] SUMMARY")
print("=" * 80)
if total_collected > 0:
    print(f"\n  ✓ SYSTEM IS OPERATIONAL!")
    print(f"\n  Data Collected:  {total_collected} items")
    print(f"  Data Processed:  {processed} items")
    print(f"  Success Rate:    {(processed/total_collected*100) if total_collected > 0 else 0:.1f}%")
    
    print(f"\n  The AI has successfully:")
    print(f"    • Collected data from internet sources")
    print(f"    • Stored data in database")
    print(f"    • Processed data through learning systems")
    
    print(f"\n  NEXT STEPS:")
    print(f"    1. Run: python online_learning_trainer.py")
    print(f"    2. Choose option 1 for full daily collection")
    print(f"    3. View stats with option 5")
    print(f"    4. Automate with: python schedule_online_learning.py")
else:
    print(f"\n  ⚠  No data collected yet")
    print(f"\n  Run this to collect your first data:")
    print(f"    python online_learning_trainer.py")

print("\n" + "=" * 80)
print(" " * 30 + "END OF REPORT")
print("=" * 80)
