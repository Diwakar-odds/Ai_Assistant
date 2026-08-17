"""
Usage Pattern Analyzer for Fine-Tuning
Analyzes command history to create personalized training datasets

Features:
- Pattern extraction from conversation history
- Common task identification
- Training data generation for fine-tuning
- Preference learning from feedback
- Domain-specific knowledge extraction
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import logging
import re

logger = logging.getLogger(__name__)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available - clustering disabled")


class UsagePatternAnalyzer:
    """Analyzes usage patterns for personalized fine-tuning"""
    
    def __init__(self, data_dir: str = "data"):
        """Initialize analyzer"""
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "conversation_history.db"
        self.feedback_db_path = self.data_dir / "feedback.db"
        
        # Analysis results
        self.patterns = {
            'common_commands': [],
            'frequent_topics': [],
            'time_patterns': {},
            'app_usage': {},
            'command_sequences': [],
            'preferences': {},
            'training_data': []
        }
    
    def analyze_all(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Run complete analysis
        
        Args:
            days_back: Number of days to analyze
            
        Returns:
            Analysis results dictionary
        """
        logger.info(f"📊 Analyzing usage patterns (last {days_back} days)...")
        
        # Analyze different aspects
        self.patterns['common_commands'] = self._analyze_common_commands(days_back)
        self.patterns['frequent_topics'] = self._analyze_topics(days_back)
        self.patterns['time_patterns'] = self._analyze_time_patterns(days_back)
        self.patterns['app_usage'] = self._analyze_app_usage(days_back)
        self.patterns['command_sequences'] = self._analyze_sequences(days_back)
        self.patterns['preferences'] = self._analyze_preferences(days_back)
        
        # Generate training data
        self.patterns['training_data'] = self._generate_training_data(days_back)
        
        logger.info(f"✅ Analysis complete!")
        return self.patterns
    
    def _get_conversations(self, days_back: int) -> List[Dict]:
        """Get conversations from database"""
        if not self.db_path.exists():
            logger.warning(f"Database not found: {self.db_path}")
            return []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get conversations from last N days
            cutoff = datetime.now() - timedelta(days=days_back)
            
            cursor.execute("""
                SELECT timestamp, user_input, assistant_response, success
                FROM conversations
                WHERE datetime(timestamp) >= datetime(?)
                ORDER BY timestamp ASC
            """, (cutoff.isoformat(),))
            
            conversations = []
            for row in cursor.fetchall():
                conversations.append({
                    'timestamp': row[0],
                    'user_input': row[1],
                    'response': row[2],
                    'success': bool(row[3])
                })
            
            conn.close()
            logger.info(f"Found {len(conversations)} conversations")
            return conversations
        
        except Exception as e:
            logger.error(f"Error reading conversations: {e}")
            return []
    
    def _analyze_common_commands(self, days_back: int) -> List[Dict]:
        """Identify most common command patterns"""
        conversations = self._get_conversations(days_back)
        
        # Extract command types
        command_counter = Counter()
        
        for conv in conversations:
            user_input = conv['user_input'].lower()
            
            # Categorize by intent
            if any(word in user_input for word in ['open', 'launch', 'start', 'run']):
                command_counter['app_launch'] += 1
            elif any(word in user_input for word in ['search', 'find', 'look for']):
                command_counter['search'] += 1
            elif any(word in user_input for word in ['play', 'music', 'song']):
                command_counter['music'] += 1
            elif any(word in user_input for word in ['weather', 'temperature']):
                command_counter['weather'] += 1
            elif any(word in user_input for word in ['email', 'message', 'send']):
                command_counter['communication'] += 1
            elif any(word in user_input for word in ['calculate', 'what is']):
                command_counter['calculation'] += 1
            elif any(word in user_input for word in ['remind', 'reminder', 'schedule']):
                command_counter['reminder'] += 1
            else:
                command_counter['other'] += 1
        
        # Get top commands
        top_commands = [
            {'command_type': cmd, 'count': count, 'percentage': (count / len(conversations)) * 100}
            for cmd, count in command_counter.most_common(10)
        ]
        
        return top_commands
    
    def _analyze_topics(self, days_back: int) -> List[Dict]:
        """Extract frequent topics using TF-IDF"""
        conversations = self._get_conversations(days_back)
        
        if not conversations or not SKLEARN_AVAILABLE:
            return []
        
        # Combine user inputs
        texts = [conv['user_input'] for conv in conversations]
        
        try:
            # TF-IDF vectorization
            vectorizer = TfidfVectorizer(
                max_features=20,
                stop_words='english',
                ngram_range=(1, 2)
            )
            tfidf_matrix = vectorizer.fit_transform(texts)
            
            # Get top terms
            feature_names = vectorizer.get_feature_names_out()
            scores = tfidf_matrix.sum(axis=0).A1
            
            topics = [
                {'topic': feature_names[i], 'score': float(scores[i])}
                for i in scores.argsort()[-20:][::-1]
            ]
            
            return topics
        
        except Exception as e:
            logger.error(f"Topic analysis failed: {e}")
            return []
    
    def _analyze_time_patterns(self, days_back: int) -> Dict[str, Any]:
        """Analyze usage by time of day and day of week"""
        conversations = self._get_conversations(days_back)
        
        hour_counts = defaultdict(int)
        day_counts = defaultdict(int)
        
        for conv in conversations:
            try:
                dt = datetime.fromisoformat(conv['timestamp'])
                hour_counts[dt.hour] += 1
                day_counts[dt.strftime('%A')] += 1
            except:
                continue
        
        # Find peak hours
        peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else 12
        peak_day = max(day_counts.items(), key=lambda x: x[1])[0] if day_counts else 'Monday'
        
        return {
            'peak_hour': peak_hour,
            'peak_day': peak_day,
            'hourly_distribution': dict(hour_counts),
            'daily_distribution': dict(day_counts),
            'most_active_time': f"{peak_hour}:00 on {peak_day}s"
        }
    
    def _analyze_app_usage(self, days_back: int) -> Dict[str, Any]:
        """Analyze which apps are used most"""
        conversations = self._get_conversations(days_back)
        
        app_counter = Counter()
        
        for conv in conversations:
            user_input = conv['user_input'].lower()
            
            # Extract app names (simple pattern matching)
            if 'spotify' in user_input:
                app_counter['Spotify'] += 1
            elif 'chrome' in user_input or 'browser' in user_input:
                app_counter['Chrome'] += 1
            elif 'vscode' in user_input or 'code' in user_input:
                app_counter['VSCode'] += 1
            elif 'excel' in user_input:
                app_counter['Excel'] += 1
            elif 'word' in user_input:
                app_counter['Word'] += 1
            elif 'outlook' in user_input or 'email' in user_input:
                app_counter['Outlook'] += 1
        
        top_apps = dict(app_counter.most_common(10))
        
        return {
            'top_apps': top_apps,
            'total_app_commands': sum(app_counter.values()),
            'unique_apps': len(app_counter)
        }
    
    def _analyze_sequences(self, days_back: int) -> List[Dict]:
        """Identify common command sequences (workflows)"""
        conversations = self._get_conversations(days_back)
        
        # Look for sequences within 5 minutes
        sequences = []
        current_sequence = []
        last_time = None
        
        for conv in conversations:
            try:
                conv_time = datetime.fromisoformat(conv['timestamp'])
                
                if last_time and (conv_time - last_time).seconds > 300:  # 5 min gap
                    if len(current_sequence) >= 2:
                        sequences.append(current_sequence.copy())
                    current_sequence = []
                
                current_sequence.append(conv['user_input'][:50])  # Truncate
                last_time = conv_time
            except:
                continue
        
        # Find common sequences
        sequence_counter = Counter()
        for seq in sequences:
            if len(seq) >= 2:
                key = " → ".join(seq[:3])  # First 3 commands
                sequence_counter[key] += 1
        
        common_sequences = [
            {'sequence': seq, 'count': count}
            for seq, count in sequence_counter.most_common(5)
        ]
        
        return common_sequences
    
    def _analyze_preferences(self, days_back: int) -> Dict[str, Any]:
        """Analyze user preferences from feedback"""
        if not self.feedback_db_path.exists():
            return {}
        
        try:
            conn = sqlite3.connect(self.feedback_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT rating, feedback_text
                FROM feedback
                WHERE datetime(timestamp) >= datetime(?)
            """, ((datetime.now() - timedelta(days=days_back)).isoformat(),))
            
            ratings = []
            feedback_texts = []
            
            for row in cursor.fetchall():
                if row[0]:
                    ratings.append(row[0])
                if row[1]:
                    feedback_texts.append(row[1])
            
            conn.close()
            
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            
            return {
                'average_rating': round(avg_rating, 2),
                'total_feedback_count': len(ratings),
                'positive_feedback': len([r for r in ratings if r >= 4]),
                'negative_feedback': len([r for r in ratings if r <= 2]),
                'sample_feedback': feedback_texts[:5]
            }
        
        except Exception as e:
            logger.error(f"Error analyzing preferences: {e}")
            return {}
    
    def _generate_training_data(self, days_back: int) -> List[Dict]:
        """
        Generate training data in fine-tuning format
        
        Returns list of training examples in the format:
        {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
        """
        conversations = self._get_conversations(days_back)
        
        training_data = []
        
        for conv in conversations:
            # Only include successful interactions
            if conv.get('success', False) and conv.get('response'):
                example = {
                    "messages": [
                        {"role": "user", "content": conv['user_input']},
                        {"role": "assistant", "content": conv['response']}
                    ],
                    "metadata": {
                        "timestamp": conv['timestamp'],
                        "success": conv['success']
                    }
                }
                training_data.append(example)
        
        return training_data
    
    def export_for_finetuning(self, output_path: str, format: str = "openai") -> str:
        """
        Export training data for fine-tuning
        
        Args:
            output_path: Where to save the file
            format: "openai" for JSONL or "huggingface" for JSON
            
        Returns:
            Path to exported file
        """
        if not self.patterns['training_data']:
            logger.warning("No training data available. Run analyze_all() first.")
            return ""
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "openai":
            # OpenAI JSONL format
            with open(output_file, 'w', encoding='utf-8') as f:
                for example in self.patterns['training_data']:
                    # Remove metadata for fine-tuning
                    training_example = {"messages": example['messages']}
                    f.write(json.dumps(training_example) + '\n')
        
        elif format == "huggingface":
            # HuggingFace JSON format
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.patterns['training_data'], f, indent=2)
        
        logger.info(f"✅ Exported {len(self.patterns['training_data'])} examples to {output_file}")
        return str(output_file)
    
    def generate_report(self, output_path: str = None) -> str:
        """Generate human-readable analysis report"""
        report = []
        report.append("=" * 80)
        report.append("USAGE PATTERN ANALYSIS REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Common Commands
        report.append("📊 Most Common Commands:")
        for cmd in self.patterns.get('common_commands', [])[:5]:
            report.append(f"  • {cmd['command_type']}: {cmd['count']} times ({cmd['percentage']:.1f}%)")
        report.append("")
        
        # Topics
        if self.patterns.get('frequent_topics'):
            report.append("🔍 Frequent Topics:")
            for topic in self.patterns['frequent_topics'][:5]:
                report.append(f"  • {topic['topic']}")
            report.append("")
        
        # Time Patterns
        time_p = self.patterns.get('time_patterns', {})
        if time_p:
            report.append("⏰ Usage Patterns:")
            report.append(f"  • Most active time: {time_p.get('most_active_time', 'N/A')}")
            report.append(f"  • Peak hour: {time_p.get('peak_hour', 0)}:00")
            report.append(f"  • Peak day: {time_p.get('peak_day', 'N/A')}")
            report.append("")
        
        # App Usage
        app_usage = self.patterns.get('app_usage', {})
        if app_usage.get('top_apps'):
            report.append("📱 Top Applications:")
            for app, count in list(app_usage['top_apps'].items())[:5]:
                report.append(f"  • {app}: {count} times")
            report.append("")
        
        # Sequences
        sequences = self.patterns.get('command_sequences', [])
        if sequences:
            report.append("🔄 Common Workflows:")
            for seq in sequences[:3]:
                report.append(f"  • {seq['sequence']} ({seq['count']}x)")
            report.append("")
        
        # Preferences
        prefs = self.patterns.get('preferences', {})
        if prefs:
            report.append("⭐ User Satisfaction:")
            report.append(f"  • Average rating: {prefs.get('average_rating', 0):.1f}/5.0")
            report.append(f"  • Positive feedback: {prefs.get('positive_feedback', 0)}")
            report.append(f"  • Negative feedback: {prefs.get('negative_feedback', 0)}")
            report.append("")
        
        # Training Data
        training_count = len(self.patterns.get('training_data', []))
        report.append(f"💾 Training Data: {training_count} examples ready for fine-tuning")
        report.append("")
        report.append("=" * 80)
        
        report_text = '\n'.join(report)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            logger.info(f"✅ Report saved to {output_path}")
        
        return report_text


if __name__ == "__main__":
    # Demo analysis
    print("📊 Running Usage Pattern Analysis...\n")
    
    analyzer = UsagePatternAnalyzer()
    results = analyzer.analyze_all(days_back=30)
    
    # Generate report
    report = analyzer.generate_report()
    print(report)
    
    # Export training data
    if results['training_data']:
        output_file = analyzer.export_for_finetuning(
            "data/training/finetuning_data.jsonl",
            format="openai"
        )
        print(f"\n✅ Training data exported to: {output_file}")
