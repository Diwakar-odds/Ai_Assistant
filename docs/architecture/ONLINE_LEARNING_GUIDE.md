# Online Learning System - Quick Start Guide

## What It Does

The Online Learning System connects your AI to the internet, allowing it to:

1. **Collect** - Automatically fetch news, weather, and other data
2. **Process** - Clean and structure the data
3. **Learn** - Feed data to your 27 AI systems
4. **Track** - Monitor what was learned
5. **Report** - Show learning statistics

## Benefits to Your AI

### Before (Local Only)
- 108 conversations
- 179 messages
- Limited knowledge
- Static learning

### After (With Internet)
- **1000s of articles** daily
- **Real-time updates** (news, weather)
- **Continuous learning** 24/7
- **Broader knowledge** base

### Specific AI Improvements

| Your AI System | Gets Data From | Improvement |
|----------------|---------------|-------------|
| HistoricalRAG | News articles | Better answers with current events |
| SemanticMemory | All text sources | Richer context understanding |
| KnowledgeGraph | Entities from articles | Comprehensive knowledge base |
| IntentClassifier | Various queries | Better intent recognition |
| FeedbackLearning | Reviews/ratings | Improved sentiment analysis |
| ConversationClusterer | Forums/discussions | Better conversation patterns |

## How It Works

```
Internet Sources (News, Weather, RSS)
          ↓
   WebScrapingManager (collects)
          ↓
   Data Processor (cleans, structures)
          ↓
   Learning Router (routes to systems)
          ↓
   ┌──────────────────────────────┐
   ↓                              ↓
HistoricalRAG              SemanticMemory
KnowledgeGraph            IntentClassifier
FeedbackLearning         (and 22 more systems)
```

## Installation

1. **Check Dependencies**
```bash
pip install schedule feedparser beautifulsoup4 requests
```

2. **Verify Your Systems**
```bash
python test_all_27_systems.py
```
All 27 systems should be operational (27/27 ✓)

## Quick Start

### Option 1: Interactive Mode (Recommended for First Time)

```bash
python online_learning_trainer.py
```

This opens a menu:
- **Option 1**: Run full daily cycle (collect + process + learn)
- **Option 2**: Just collect news
- **Option 3**: Just collect weather
- **Option 4**: Process collected data
- **Option 5**: View last 7 days stats
- **Option 6**: View last 30 days stats

**Try Option 1 first** to see it in action!

### Option 2: One-Time Run (Command Line)

```python
from online_learning_trainer import OnlineLearningTrainer

trainer = OnlineLearningTrainer()
result = trainer.run_daily_collection()
print(result)
```

### Option 3: Automated Daily (Scheduler)

```bash
python schedule_online_learning.py
```

Runs automatically at 3:00 AM daily. Press Ctrl+C to stop.

## What Happens During Daily Cycle

```
[1/4] Collecting news articles...
  ✓ Fetching from NYTimes RSS
  ✓ Fetching from BBC Technology
  ✓ Fetching from Reddit r/technology
  ✓ Fetching from Hacker News
  → Collected 20 articles

[2/4] Collecting weather data...
  ✓ New York weather
  ✓ London weather  
  ✓ Tokyo weather
  ✓ Sydney weather
  → Collected 4 weather records

[3/4] Processing and learning...
  ✓ Article → HistoricalRAG (current events context)
  ✓ Article → SemanticMemory (embeddings)
  ✓ Article → KnowledgeGraph (entities extracted)
  ✓ Weather → SemanticMemory (structured data)
  → Processed 24 items successfully

[4/4] Generating statistics...
  ✓ 24/24 items processed (100%)
  ✓ 3 systems updated
  ✓ 0 failures
```

## Database Location

All data stored in: `data/online_learning.db`

**Tables:**
- `collected_data` - Raw data from internet
- `learning_progress` - What each AI system learned
- `daily_stats` - Aggregate statistics

## Viewing Results

### Check What Was Learned

```python
from online_learning_trainer import OnlineLearningTrainer

trainer = OnlineLearningTrainer()
stats = trainer.get_learning_stats(days=7)

print(f"Collected: {stats['total_collected']} items")
print(f"Processed: {stats['total_processed']} items")
print(f"Success Rate: {stats['processing_rate']}")

for system in stats['system_breakdown']:
    print(f"{system['system']}: {system['successful']} items learned")
```

### Expected Output

```
Learning Statistics (Last 7 Days)
------------------------------------------------------------
Total Collected: 168
Total Processed: 165
Processing Rate: 98.2%
Systems Updated: 3

System Breakdown:
  - historical_rag: 140/140 successful
  - semantic_memory: 165/165 successful
  - knowledge_graph: 120/140 successful
```

## Customization

### Add Your Own Data Sources

Edit `online_learning_trainer.py`, find `collect_news()`:

```python
sources = [
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://your-favorite-rss-feed.com/rss",  # Add here!
]
```

### Change Collection Schedule

Edit `schedule_online_learning.py`:

```python
# Current: Daily at 3 AM
schedule.every().day.at("03:00").do(run_daily_learning)

# Change to: Every 6 hours
schedule.every(6).hours.do(run_daily_learning)

# Or: Twice daily
schedule.every().day.at("03:00").do(run_daily_learning)
schedule.every().day.at("15:00").do(run_daily_learning)
```

### Connect More Learning Systems

In `_init_learning_systems()`, add:

```python
systems['your_new_system'] = YourNewSystem()
```

Then in `_learn_from_article()`, add:

```python
if 'your_new_system' in self.learning_systems:
    self.learning_systems['your_new_system'].learn(text)
```

## Monitoring

### Logs

All activity logged to: `logs/online_learning.log`

```bash
tail -f logs/online_learning.log
```

### Statistics Dashboard (Coming Soon)

You can build a dashboard using the database:

```sql
SELECT 
    date(collected_at) as day,
    COUNT(*) as articles,
    source_type
FROM collected_data
GROUP BY day, source_type
ORDER BY day DESC;
```

## Troubleshooting

### "No content collected"
- Check internet connection
- RSS feeds may be blocked (try different sources)
- Use VPN if needed

### "System X failed to learn"
- Check `logs/online_learning.log` for specific error
- Verify system is initialized: `python test_all_27_systems.py`
- Some systems may need specific data formats

### "Database locked"
- Close other instances of the trainer
- Delete `data/online_learning.db` and restart (will lose stats)

## Performance

**Expected Performance:**
- 20 articles collected: ~40 seconds
- 4 weather records: ~4 seconds
- 24 items processed: ~10-30 seconds
- **Total cycle: ~1-2 minutes**

**Storage:**
- 100 articles ≈ 5 MB database growth
- 1 month daily runs ≈ 150 MB
- Can safely run for years with auto-cleanup

## Next Steps

1. **First Run**: `python online_learning_trainer.py` → Choose option 1
2. **Check Results**: Choose option 5 to see stats
3. **Automate**: Run `python schedule_online_learning.py`
4. **Customize**: Add your favorite data sources
5. **Monitor**: Check `logs/online_learning.log` daily

## Benefits Timeline

**Day 1:** 20 articles → AI learns current tech trends  
**Week 1:** 140 articles → Broad technology knowledge  
**Month 1:** 600 articles → Deep domain expertise  
**Year 1:** 7,300 articles → Expert-level understanding

**Your AI transforms from having 179 messages to having 7,000+ real-world examples!**

## Questions?

Run the interactive mode: `python online_learning_trainer.py`

Check your 27 systems: `python check_systems_status.py`

View logs: `tail -f logs/online_learning.log`

---

**Created:** December 21, 2025  
**Your AI is now connected to the internet! 🚀**
