"""
Enhanced Learning & Memory System for YourDaddy Assistant

This module implements behavioral learning, skill acquisition, predictive actions,
and personal knowledge graph capabilities.
"""

import json
import sqlite3
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, Counter
import pickle
import os
from dataclasses import dataclass
import networkx as nx
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ADVANCED_FEATURES_AVAILABLE = True

@dataclass
class Skill:
    """Represents a learned skill"""
    name: str
    category: str
    proficiency: float
    last_used: datetime
    usage_count: int
    success_rate: float
    learning_speed: float

@dataclass
class BehaviorPattern:
    """Represents a learned behavior pattern"""
    pattern_id: str
    context: Dict[str, Any]
    action: str
    frequency: int
    success_rate: float
    last_occurrence: datetime
    confidence: float

@dataclass
class KnowledgeNode:
    """Node in the personal knowledge graph"""
    node_id: str
    content: str
    node_type: str  # person, place, event, concept, skill
    metadata: Dict[str, Any]
    created_at: datetime
    last_accessed: datetime
    importance_score: float

class EnhancedLearningSystem:
    """Main learning system coordinating all learning components"""
    
    def __init__(self, db_path: str = "enhanced_learning.db"):
        self.db_path = db_path
        self.behavioral_learner = BehavioralLearner(db_path)
        self.skill_manager = SkillAcquisitionManager(db_path)
        self.predictor = PredictiveActionEngine(db_path)
        self.knowledge_graph = PersonalKnowledgeGraph(db_path)
        
        self.init_database()
    
    def init_database(self):
        """Initialize the learning database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Behavioral patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS behavior_patterns (
                pattern_id TEXT PRIMARY KEY,
                context TEXT NOT NULL,
                action TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                success_rate REAL DEFAULT 1.0,
                last_occurrence TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confidence REAL DEFAULT 0.5
            )
        ''')
        
        # Skills table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skills (
                name TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                proficiency REAL DEFAULT 0.0,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 1.0,
                learning_speed REAL DEFAULT 0.1
            )
        ''')
        
        # Knowledge graph nodes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_nodes (
                node_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                node_type TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                importance_score REAL DEFAULT 0.5
            )
        ''')
        
        # Knowledge graph edges
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_edges (
                edge_id TEXT PRIMARY KEY,
                source_node TEXT NOT NULL,
                target_node TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_node) REFERENCES knowledge_nodes (node_id),
                FOREIGN KEY (target_node) REFERENCES knowledge_nodes (node_id)
            )
        ''')
        
        # Predictions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                prediction_id TEXT PRIMARY KEY,
                predicted_action TEXT NOT NULL,
                context TEXT NOT NULL,
                confidence REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                actual_outcome TEXT,
                was_correct INTEGER
            )
        ''')
        
        # Learning sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_sessions (
                session_id TEXT PRIMARY KEY,
                session_type TEXT NOT NULL,
                data TEXT NOT NULL,
                insights TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def learn_from_interaction(self, context: Dict[str, Any], action: str, outcome: str):
        """Learn from user interactions"""
        # Update behavioral patterns
        self.behavioral_learner.record_behavior(context, action, outcome == "success")
        
        # Update skills if applicable
        if "skill" in context:
            self.skill_manager.update_skill_usage(context["skill"], outcome == "success")
        
        # Update knowledge graph
        self.knowledge_graph.update_from_interaction(context, action, outcome)
        
        # Generate predictions for future
        self.predictor.update_predictions(context, action, outcome)
    
    def get_predictions(self, current_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get predictions for current context"""
        return self.predictor.predict_actions(current_context)
    
    def get_skill_recommendations(self) -> List[str]:
        """Get skill learning recommendations"""
        return self.skill_manager.get_skill_recommendations()
    
    def get_knowledge_insights(self) -> Dict[str, Any]:
        """Get insights from knowledge graph"""
        return self.knowledge_graph.generate_insights()

class BehavioralLearner:
    """Learns from user behavior patterns"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.min_pattern_frequency = 3
        self.min_confidence_threshold = 0.7
    
    def record_behavior(self, context: Dict[str, Any], action: str, success: bool):
        """Record a behavior instance"""
        pattern_id = self._generate_pattern_id(context, action)
        context_str = json.dumps(context, sort_keys=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if pattern exists
        cursor.execute(
            "SELECT frequency, success_rate FROM behavior_patterns WHERE pattern_id = ?",
            (pattern_id,)
        )
        result = cursor.fetchone()
        
        if result:
            frequency, old_success_rate = result
            new_frequency = frequency + 1
            new_success_rate = (old_success_rate * frequency + (1 if success else 0)) / new_frequency
            
            cursor.execute('''
                UPDATE behavior_patterns 
                SET frequency = ?, success_rate = ?, last_occurrence = CURRENT_TIMESTAMP,
                    confidence = MIN(1.0, frequency * 0.1)
                WHERE pattern_id = ?
            ''', (new_frequency, new_success_rate, pattern_id))
        else:
            cursor.execute('''
                INSERT INTO behavior_patterns 
                (pattern_id, context, action, frequency, success_rate, confidence)
                VALUES (?, ?, ?, 1, ?, 0.1)
            ''', (pattern_id, context_str, action, 1.0 if success else 0.0))
        
        conn.commit()
        conn.close()
    
    def _generate_pattern_id(self, context: Dict[str, Any], action: str) -> str:
        """Generate a unique pattern ID from context and action"""
        # Extract key context features
        key_features = []
        if "time_of_day" in context:
            hour = int(context["time_of_day"].split(":")[0])
            if hour < 12:
                key_features.append("morning")
            elif hour < 17:
                key_features.append("afternoon")
            else:
                key_features.append("evening")
        
        if "day_of_week" in context:
            key_features.append(context["day_of_week"])
        
        if "location" in context:
            key_features.append(context["location"])
        
        if "mood" in context:
            key_features.append(context["mood"])
        
        # Create pattern ID
        pattern_base = "_".join(key_features) + "_" + action.lower().replace(" ", "_")
        return f"pattern_{hash(pattern_base) % 10000:04d}"
    
    def get_behavior_patterns(self, min_confidence: float = 0.5) -> List[BehaviorPattern]:
        """Get learned behavior patterns above confidence threshold"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT pattern_id, context, action, frequency, success_rate, 
                   last_occurrence, confidence
            FROM behavior_patterns 
            WHERE confidence >= ? AND frequency >= ?
            ORDER BY confidence DESC
        ''', (min_confidence, self.min_pattern_frequency))
        
        patterns = []
        for row in cursor.fetchall():
            pattern = BehaviorPattern(
                pattern_id=row[0],
                context=json.loads(row[1]),
                action=row[2],
                frequency=row[3],
                success_rate=row[4],
                last_occurrence=datetime.fromisoformat(row[5]),
                confidence=row[6]
            )
            patterns.append(pattern)
        
        conn.close()
        return patterns

class SkillAcquisitionManager:
    """Manages skill learning and development"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.skill_categories = [
            "communication", "productivity", "entertainment", "technical",
            "creative", "analytical", "social", "physical"
        ]
    
    def update_skill_usage(self, skill_name: str, success: bool, category: str = "general"):
        """Update skill usage statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if skill exists
        cursor.execute("SELECT * FROM skills WHERE name = ?", (skill_name,))
        result = cursor.fetchone()
        
        if result:
            # Update existing skill
            usage_count = result[4] + 1
            old_success_rate = result[5]
            new_success_rate = (old_success_rate * (usage_count - 1) + (1 if success else 0)) / usage_count
            
            # Adjust proficiency based on success
            proficiency_change = 0.1 if success else -0.05
            new_proficiency = max(0, min(1, result[2] + proficiency_change))
            
            cursor.execute('''
                UPDATE skills 
                SET proficiency = ?, last_used = CURRENT_TIMESTAMP, usage_count = ?, success_rate = ?
                WHERE name = ?
            ''', (new_proficiency, usage_count, new_success_rate, skill_name))
        else:
            # Create new skill
            initial_proficiency = 0.1 if success else 0.05
            cursor.execute('''
                INSERT INTO skills (name, category, proficiency, usage_count, success_rate)
                VALUES (?, ?, ?, 1, ?)
            ''', (skill_name, category, initial_proficiency, 1.0 if success else 0.0))
        
        conn.commit()
        conn.close()
    
    def get_skills_by_category(self, category: str = None) -> List[Skill]:
        """Get skills, optionally filtered by category"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if category:
            cursor.execute("SELECT * FROM skills WHERE category = ? ORDER BY proficiency DESC", (category,))
        else:
            cursor.execute("SELECT * FROM skills ORDER BY proficiency DESC")
        
        skills = []
        for row in cursor.fetchall():
            skill = Skill(
                name=row[0],
                category=row[1],
                proficiency=row[2],
                last_used=datetime.fromisoformat(row[3]),
                usage_count=row[4],
                success_rate=row[5],
                learning_speed=row[6]
            )
            skills.append(skill)
        
        conn.close()
        return skills
    
    def get_skill_recommendations(self) -> List[str]:
        """Get recommendations for skills to develop"""
        skills = self.get_skills_by_category()
        
        # Find skills with low proficiency but high usage
        recommendations = []
        for skill in skills:
            if skill.proficiency < 0.5 and skill.usage_count > 5:
                recommendations.append(f"Focus on improving '{skill.name}' - used {skill.usage_count} times but only {skill.proficiency:.1%} proficient")
        
        # Suggest new skill categories if user is advanced in current ones
        advanced_categories = set()
        for skill in skills:
            if skill.proficiency > 0.8:
                advanced_categories.add(skill.category)
        
        for category in self.skill_categories:
            if category not in advanced_categories:
                recommendations.append(f"Consider exploring '{category}' skills")
        
        return recommendations[:5]  # Return top 5 recommendations

class PredictiveActionEngine:
    """Predicts likely user actions based on context"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.context_vectorizer = TfidfVectorizer(max_features=100)
        self.prediction_model = None
    
    def predict_actions(self, current_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Predict likely actions for current context"""
        # Get historical patterns
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT action, confidence, success_rate
            FROM behavior_patterns
            WHERE confidence > 0.5
            ORDER BY confidence DESC, success_rate DESC
            LIMIT 10
        ''')
        
        patterns = cursor.fetchall()
        conn.close()
        
        # Generate predictions
        predictions = []
        for action, confidence, success_rate in patterns:
            prediction_confidence = self._calculate_context_similarity(current_context, action)
            if prediction_confidence > 0.3:
                predictions.append({
                    "action": action,
                    "confidence": prediction_confidence,
                    "success_probability": success_rate,
                    "reasoning": f"Based on {confidence:.1%} confident pattern with {success_rate:.1%} success rate"
                })
        
        return sorted(predictions, key=lambda x: x["confidence"], reverse=True)[:5]
    
    def _calculate_context_similarity(self, current_context: Dict[str, Any], action: str) -> float:
        """Calculate similarity between current context and historical patterns"""
        # Simple similarity based on time and context keywords
        now = datetime.now()
        hour = now.hour
        day_of_week = now.strftime("%A")
        
        # Time-based similarity
        time_score = 1.0
        if "morning" in action and 6 <= hour < 12:
            time_score = 1.0
        elif "afternoon" in action and 12 <= hour < 17:
            time_score = 1.0
        elif "evening" in action and 17 <= hour <= 23:
            time_score = 1.0
        else:
            time_score = 0.5
        
        # Context keyword similarity
        context_score = 0.5
        for key, value in current_context.items():
            if str(value).lower() in action.lower():
                context_score += 0.2
        
        return min(1.0, (time_score + context_score) / 2)
    
    def update_predictions(self, context: Dict[str, Any], action: str, outcome: str):
        """Update prediction accuracy"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        prediction_id = f"pred_{hash(str(context) + action) % 10000:04d}"
        
        cursor.execute('''
            INSERT OR REPLACE INTO predictions 
            (prediction_id, predicted_action, context, confidence, actual_outcome, was_correct)
            VALUES (?, ?, ?, 0.8, ?, ?)
        ''', (prediction_id, action, json.dumps(context), outcome, 1 if outcome == "success" else 0))
        
        conn.commit()
        conn.close()

class PersonalKnowledgeGraph:
    """Manages personal knowledge graph and relationships"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.graph = nx.DiGraph()
        self.load_graph()
    
    def load_graph(self):
        """Load knowledge graph from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load nodes
        cursor.execute("SELECT node_id, content, node_type, importance_score FROM knowledge_nodes")
        for node_id, content, node_type, importance in cursor.fetchall():
            self.graph.add_node(node_id, content=content, type=node_type, importance=importance)
        
        # Load edges
        cursor.execute("SELECT source_node, target_node, relationship_type, strength FROM knowledge_edges")
        for source, target, rel_type, strength in cursor.fetchall():
            if self.graph.has_node(source) and self.graph.has_node(target):
                self.graph.add_edge(source, target, relationship=rel_type, weight=strength)
        
        conn.close()
    
    def add_knowledge_node(self, content: str, node_type: str, metadata: Dict[str, Any] = None) -> str:
        """Add a new knowledge node"""
        node_id = f"{node_type}_{hash(content) % 10000:04d}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO knowledge_nodes 
            (node_id, content, node_type, metadata, importance_score)
            VALUES (?, ?, ?, ?, 0.5)
        ''', (node_id, content, node_type, json.dumps(metadata or {})))
        
        conn.commit()
        conn.close()
        
        self.graph.add_node(node_id, content=content, type=node_type, importance=0.5)
        return node_id
    
    def add_relationship(self, source_id: str, target_id: str, relationship_type: str, strength: float = 1.0):
        """Add a relationship between nodes"""
        edge_id = f"edge_{hash(source_id + target_id + relationship_type) % 10000:04d}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO knowledge_edges 
            (edge_id, source_node, target_node, relationship_type, strength)
            VALUES (?, ?, ?, ?, ?)
        ''', (edge_id, source_id, target_id, relationship_type, strength))
        
        conn.commit()
        conn.close()
        
        if self.graph.has_node(source_id) and self.graph.has_node(target_id):
            self.graph.add_edge(source_id, target_id, relationship=relationship_type, weight=strength)
    
    def update_from_interaction(self, context: Dict[str, Any], action: str, outcome: str):
        """Update knowledge graph from interaction"""
        # Create nodes for key entities
        for key, value in context.items():
            if key in ["location", "person", "topic", "skill"]:
                node_id = self.add_knowledge_node(str(value), key, {"context": context})
                
                # Connect to action
                action_node = self.add_knowledge_node(action, "action", {"outcome": outcome})
                self.add_relationship(node_id, action_node, "triggered", 1.0 if outcome == "success" else 0.5)
    
    def find_related_concepts(self, concept: str, max_depth: int = 2) -> List[str]:
        """Find concepts related to given concept"""
        related = []
        
        # Find node containing concept
        concept_node = None
        for node_id, data in self.graph.nodes(data=True):
            if concept.lower() in data.get('content', '').lower():
                concept_node = node_id
                break
        
        if concept_node:
            # Use BFS to find related nodes
            visited = set()
            queue = [(concept_node, 0)]
            
            while queue:
                node, depth = queue.pop(0)
                if node in visited or depth > max_depth:
                    continue
                
                visited.add(node)
                if depth > 0:  # Don't include the original concept
                    related.append(self.graph.nodes[node]['content'])
                
                # Add neighbors
                for neighbor in self.graph.neighbors(node):
                    if neighbor not in visited:
                        queue.append((neighbor, depth + 1))
        
        return related[:10]  # Return top 10 related concepts
    
    def generate_insights(self) -> Dict[str, Any]:
        """Generate insights from the knowledge graph"""
        insights = {
            "total_nodes": self.graph.number_of_nodes(),
            "total_relationships": self.graph.number_of_edges(),
            "most_connected": [],
            "knowledge_clusters": [],
            "learning_paths": []
        }
        
        if self.graph.number_of_nodes() > 0:
            # Most connected nodes
            degree_centrality = nx.degree_centrality(self.graph)
            most_connected = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
            for node_id, centrality in most_connected:
                insights["most_connected"].append({
                    "concept": self.graph.nodes[node_id]['content'],
                    "connections": int(centrality * self.graph.number_of_nodes())
                })
            
            # Find clusters using community detection
            if self.graph.number_of_edges() > 0:
                try:
                    # Convert to undirected for community detection
                    undirected = self.graph.to_undirected()
                    communities = nx.community.greedy_modularity_communities(undirected)
                    
                    for i, community in enumerate(communities[:5]):
                        cluster_concepts = [self.graph.nodes[node]['content'] for node in list(community)[:3]]
                        insights["knowledge_clusters"].append({
                            "cluster_id": i + 1,
                            "concepts": cluster_concepts
                        })
                except:
                    pass  # Handle cases where community detection fails
        
        return insights
    
    def visualize_graph(self, output_path: str = "knowledge_graph.png"):
        """Create a visualization of the knowledge graph"""
        if self.graph.number_of_nodes() == 0:
            return False
        
        plt.figure(figsize=(12, 8))
        
        # Create layout
        pos = nx.spring_layout(self.graph, k=1, iterations=50)
        
        # Color nodes by type
        node_colors = []
        for node in self.graph.nodes():
            node_type = self.graph.nodes[node].get('type', 'unknown')
            if node_type == 'person':
                node_colors.append('lightblue')
            elif node_type == 'location':
                node_colors.append('lightgreen')
            elif node_type == 'skill':
                node_colors.append('orange')
            elif node_type == 'action':
                node_colors.append('lightcoral')
            else:
                node_colors.append('lightgray')
        
        # Draw graph
        nx.draw(self.graph, pos, 
                node_color=node_colors,
                node_size=500,
                font_size=8,
                font_weight='bold',
                with_labels=False,
                edge_color='gray',
                arrows=True)
        
        # Add labels
        labels = {node: self.graph.nodes[node]['content'][:15] + ('...' if len(self.graph.nodes[node]['content']) > 15 else '') 
                 for node in self.graph.nodes()}
        nx.draw_networkx_labels(self.graph, pos, labels, font_size=6)
        
        plt.title("Personal Knowledge Graph")
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return True

def main():
    """Example usage of the Enhanced Learning System"""
    learning_system = EnhancedLearningSystem()
    
    # Example interaction
    context = {
        "time_of_day": "09:30",
        "day_of_week": "Monday",
        "location": "office",
        "mood": "focused",
        "skill": "email_management"
    }
    
    # Learn from interaction
    learning_system.learn_from_interaction(context, "check_email", "success")
    
    # Get predictions
    predictions = learning_system.get_predictions(context)
    print("Predictions:", predictions)
    
    # Get skill recommendations
    recommendations = learning_system.get_skill_recommendations()
    print("Skill recommendations:", recommendations)
    
    # Get knowledge insights
    insights = learning_system.get_knowledge_insights()
    print("Knowledge insights:", insights)

if __name__ == "__main__":
    main()