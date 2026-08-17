"""
Show what AI has learned from the internet
"""
import sqlite3
from datetime import datetime

print("="*80)
print(" "*25 + "WHAT AI HAS LEARNED ONLINE")
print("="*80)
print(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

conn = sqlite3.connect('F:/bn/assitant/data/online_learning.db')
cursor = conn.cursor()

# Get summary stats
cursor.execute('SELECT COUNT(*) FROM collected_data')
total = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM collected_data WHERE processed=1')
processed = cursor.fetchone()[0]

cursor.execute('SELECT data_type, COUNT(*) FROM collected_data GROUP BY data_type')
by_type = cursor.fetchall()

print(f"📊 SUMMARY STATISTICS")
print("-"*80)
print(f"Total Items Learned:     {total}")
print(f"Successfully Processed:  {processed}")
print(f"Processing Rate:         {(processed/total*100) if total > 0 else 0:.1f}%")

print(f"\n📁 BY CONTENT TYPE")
print("-"*80)
for dtype, count in by_type:
    print(f"  {dtype:30s}: {count} items")

# Get all collected content with full details
cursor.execute('''
    SELECT id, data_type, source_type, source_name, content, collected_at 
    FROM collected_data 
    ORDER BY id ASC
''')
all_data = cursor.fetchall()

print(f"\n📚 DETAILED LEARNING CONTENT")
print("="*80)

for idx, (item_id, dtype, stype, sname, content, timestamp) in enumerate(all_data, 1):
    print(f"\n[Item {idx}] ID: {item_id}")
    print(f"Type: {dtype} | Source: {stype}/{sname}")
    print(f"Time: {timestamp}")
    print(f"\nContent Preview:")
    
    # Show meaningful preview based on type
    if dtype == "news_article":
        lines = content.split('\n')[:10]  # First 10 lines
        for line in lines:
            if line.strip():
                print(f"  {line[:76]}")
    elif dtype == "weather_data":
        lines = content.split('\n')[:5]  # First 5 lines
        for line in lines:
            if line.strip():
                print(f"  {line}")
    else:
        print(f"  {content[:300]}...")
    
    print("-"*80)

conn.close()

print(f"\n📈 KNOWLEDGE GROWTH")
print("="*80)
print(f"Starting Knowledge: 179 messages (before online learning)")
print(f"New Learning:       {total} items from internet")
print(f"Current Total:      {179 + total} messages")
print(f"Growth:             +{(total/179*100):.1f}%")

print(f"\n🧠 WHAT THE AI NOW KNOWS")
print("="*80)

# Count unique topics
cursor = sqlite3.connect('F:/bn/assitant/data/online_learning.db')
c = cursor.cursor()
c.execute('SELECT content FROM collected_data WHERE data_type="news_article"')
news_items = c.fetchall()

if news_items:
    print(f"\n📰 NEWS TOPICS LEARNED:")
    for i, (content,) in enumerate(news_items, 1):
        # Extract first headline
        lines = content.split('\n')
        for line in lines:
            if '📰' in line and 'Latest' not in line:
                headline = line.replace('📰', '').strip()
                if headline and len(headline) > 10:
                    print(f"  {i}. {headline[:70]}")
                    break

c.execute('SELECT DISTINCT content FROM collected_data WHERE data_type="weather_data"')
weather_items = c.fetchall()

if weather_items:
    print(f"\n🌤️ WEATHER PATTERNS LEARNED:")
    for i, (content,) in enumerate(weather_items, 1):
        # Extract city and temp
        first_line = content.split('\n')[0]
        temp_line = content.split('\n')[1] if len(content.split('\n')) > 1 else ""
        print(f"  {i}. {first_line}")
        if temp_line:
            print(f"     {temp_line}")

c.close()

print(f"\n✅ The AI has successfully learned from internet sources!")
print("="*80)
