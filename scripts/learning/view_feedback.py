#!/usr/bin/env python3
"""
View User Feedback Log
Displays thumbs up/down feedback from users to help the AI learn
"""

import json
from pathlib import Path
from datetime import datetime

def view_feedback():
    """Display all user feedback with statistics"""
    feedback_file = Path('user_data/feedback_log.json')
    
    if not feedback_file.exists():
        print("📭 No feedback recorded yet.")
        print("\n💡 Tip: Use thumbs up/down buttons in the chat interface to provide feedback!")
        return
    
    try:
        with open(feedback_file, 'r', encoding='utf-8') as f:
            feedback_data = json.load(f)
        
        if not feedback_data:
            print("📭 No feedback recorded yet.")
            return
        
        # Statistics
        total = len(feedback_data)
        thumbs_up = sum(1 for f in feedback_data if f.get('feedback') == 'up')
        thumbs_down = sum(1 for f in feedback_data if f.get('feedback') == 'down')
        neutral = sum(1 for f in feedback_data if f.get('feedback') is None)
        
        print("=" * 70)
        print("📊 USER FEEDBACK STATISTICS")
        print("=" * 70)
        print(f"\n📈 Total Feedback: {total}")
        print(f"👍 Positive: {thumbs_up} ({thumbs_up/total*100:.1f}%)")
        print(f"👎 Negative: {thumbs_down} ({thumbs_down/total*100:.1f}%)")
        print(f"🔄 Removed: {neutral} ({neutral/total*100:.1f}%)")
        
        # Satisfaction score
        if thumbs_up + thumbs_down > 0:
            satisfaction = thumbs_up / (thumbs_up + thumbs_down) * 100
            print(f"\n⭐ Satisfaction Score: {satisfaction:.1f}%")
        
        print("\n" + "=" * 70)
        print("📝 RECENT FEEDBACK (Last 10)")
        print("=" * 70)
        
        # Show last 10 feedback entries
        for i, entry in enumerate(reversed(feedback_data[-10:]), 1):
            timestamp = entry.get('timestamp', 'Unknown')
            feedback = entry.get('feedback')
            message = entry.get('message', '')[:100]  # First 100 chars
            
            # Format timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                time_str = timestamp
            
            # Feedback icon
            if feedback == 'up':
                icon = '👍 GOOD'
                color = '\033[92m'  # Green
            elif feedback == 'down':
                icon = '👎 POOR'
                color = '\033[91m'  # Red
            else:
                icon = '🔄 REMOVED'
                color = '\033[93m'  # Yellow
            
            reset = '\033[0m'
            
            print(f"\n{i}. {color}{icon}{reset} - {time_str}")
            print(f"   Message: {message}...")
        
        print("\n" + "=" * 70)
        
        # Learning insights
        print("\n💡 LEARNING INSIGHTS:")
        if thumbs_down > thumbs_up * 0.3:  # More than 30% negative
            print("   ⚠️  High negative feedback - Review responses for improvement areas")
        elif thumbs_up > total * 0.7:  # More than 70% positive
            print("   ✅ Excellent performance - AI is learning well!")
        else:
            print("   📈 Good progress - Continue providing feedback to improve")
        
        print("\n📌 Tip: Feedback helps the AI:")
        print("   • Learn your communication preferences")
        print("   • Improve response quality")
        print("   • Understand what works and what doesn't")
        print("   • Adapt to your workflow patterns\n")
        
    except json.JSONDecodeError:
        print("❌ Error: Feedback log file is corrupted")
    except Exception as e:
        print(f"❌ Error reading feedback: {e}")

if __name__ == "__main__":
    view_feedback()
