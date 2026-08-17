"""
Show detailed training data for task/command recognition
"""
import sqlite3

print("="*80)
print(" "*15 + "DETAILED TRAINING DATASETS FOR TASKS & COMMANDS")
print("="*80)

# 1. Command Sequences Data
print("\n📊 1. COMMAND SEQUENCES DATABASE")
print("-"*80)
conn = sqlite3.connect('F:/bn/assitant/data/command_sequences.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM command_sequences")
seq_count = c.fetchone()[0]
print(f"Total Sequences: {seq_count}")

if seq_count > 0:
    c.execute("SELECT * FROM command_sequences LIMIT 5")
    print("\nSample Command Sequences:")
    for row in c.fetchall():
        print(f"  - {row}")

c.execute("SELECT COUNT(*) FROM predictions")
pred_count = c.fetchone()[0]
print(f"\nPredictions Made: {pred_count}")
conn.close()

# 2. Smart Commands Data
print("\n\n📊 2. SMART COMMANDS DATABASE")
print("-"*80)
conn = sqlite3.connect('F:/bn/assitant/data/smart_commands.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM command_usage")
usage_count = c.fetchone()[0]
print(f"Command Usage Records: {usage_count}")

if usage_count > 0:
    c.execute("SELECT * FROM command_usage LIMIT 5")
    print("\nSample Command Usage:")
    for row in c.fetchall():
        print(f"  - {row[:5]}...")  # First 5 fields

conn.close()

# 3. Historical RAG - User Interactions
print("\n\n📊 3. HISTORICAL RAG (User Interactions)")
print("-"*80)
conn = sqlite3.connect('F:/bn/assitant/data/historical_rag.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM interactions")
int_count = c.fetchone()[0]
print(f"Total Interactions: {int_count}")

if int_count > 0:
    c.execute("SELECT query, response, success_score FROM interactions ORDER BY timestamp DESC LIMIT 5")
    print("\nRecent User Queries & Responses:")
    for i, (query, response, score) in enumerate(c.fetchall(), 1):
        print(f"  {i}. Query: {query[:60]}...")
        print(f"     Response: {response[:60]}...")
        print(f"     Success: {score}\n")

conn.close()

# 4. Feedback Learning
print("\n📊 4. FEEDBACK LEARNING (418 Examples)")
print("-"*80)
conn = sqlite3.connect('F:/bn/assitant/data/feedback_learning.db')
c = conn.cursor()

c.execute("SELECT feedback_type, COUNT(*) FROM feedback GROUP BY feedback_type")
feedback_types = c.fetchall()
print("Feedback by Type:")
for ftype, count in feedback_types:
    print(f"  {ftype}: {count} examples")

c.execute("SELECT prompt, response, feedback_value FROM feedback WHERE feedback_type='thumbs_up' LIMIT 3")
print("\nPositive Examples (Thumbs Up):")
for i, (prompt, response, value) in enumerate(c.fetchall(), 1):
    print(f"  {i}. Prompt: {prompt[:50]}...")
    print(f"     Response: {response[:50]}...")

conn.close()

# 5. Enhanced Learning - Behavior Patterns
print("\n\n📊 5. ENHANCED LEARNING - BEHAVIOR PATTERNS")
print("-"*80)
conn = sqlite3.connect('F:/bn/assitant/data/enhanced_learning.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM behavior_patterns")
pattern_count = c.fetchone()[0]
print(f"Behavior Patterns: {pattern_count}")

c.execute("SELECT context, action, success_rate FROM behavior_patterns")
print("\nLearned Patterns:")
for context, action, success_rate in c.fetchall():
    print(f"  Context: {context[:60]}...")
    print(f"  Action: {action}")
    print(f"  Success Rate: {success_rate*100:.1f}%\n")

# Skills learned
c.execute("SELECT name, category, proficiency, usage_count FROM skills")
print("Skills Learned:")
for name, category, prof, usage in c.fetchall():
    print(f"  - {name} ({category}): Proficiency {prof*100:.1f}%, Used {usage} times")

conn.close()

# 6. Conversation AI
print("\n\n📊 6. CONVERSATION AI - USER PATTERNS")
print("-"*80)
conn = sqlite3.connect('F:/bn/assitant/data/conversation_ai.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM conversations")
conv_count = c.fetchone()[0]
print(f"Conversations: {conv_count}")

c.execute("SELECT topic, started_at FROM conversations ORDER BY last_activity DESC LIMIT 5")
print("\nRecent Conversation Topics:")
for i, (topic, started) in enumerate(c.fetchall(), 1):
    print(f"  {i}. {topic} ({started})")

c.execute("SELECT COUNT(*) FROM mood_history")
mood_count = c.fetchone()[0]
print(f"\nMood History Records: {mood_count}")

conn.close()

# Summary
print("\n\n" + "="*80)
print("🎯 SUMMARY: DATASETS AVAILABLE FOR TRAINING")
print("="*80)

datasets = [
    ("Historical RAG Interactions", int_count, "User queries → AI responses with success scores"),
    ("Feedback Learning", 418, "Thumbs up/down on AI responses + preference pairs"),
    ("Behavior Patterns", 3, "Context → Action mappings with success rates"),
    ("Skills Database", 3, "Learned skills with proficiency levels"),
    ("Knowledge Graph", 27, "Concept nodes + 21 relationships"),
    ("Conversations", 19, "Full conversation history with topics"),
    ("Mood History", 11, "User mood tracking for context"),
]

print("\n✅ USABLE FOR TASK/COMMAND TRAINING:")
for name, count, description in datasets:
    print(f"\n  📁 {name}: {count} records")
    print(f"     Use: {description}")

print("\n\n💡 RECOMMENDED APPROACH:")
print("="*80)
print("""
1. **Use Historical RAG Interactions** for:
   - Training on actual user queries
   - Learning successful response patterns
   - Building query → action mappings

2. **Use Feedback Learning** for:
   - Identifying good vs bad responses
   - Learning user preferences
   - RLHF (Reinforcement Learning from Human Feedback)

3. **Use Behavior Patterns** for:
   - Predicting user actions from context
   - Learning time-based patterns
   - Skill-based action prediction

4. **Use Knowledge Graph** for:
   - Understanding topic relationships
   - Context-aware task execution
   - Semantic understanding

TOTAL TRAINING EXAMPLES: 575+
""")
print("="*80)
