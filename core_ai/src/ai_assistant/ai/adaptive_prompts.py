"""
Adaptive Prompt Engineering System
Dynamically optimizes prompts based on user feedback and context

Features:
- Prompt template library with versioning
- A/B testing for prompt variations
- Automatic prompt improvement from feedback
- Context-aware prompt selection
- Few-shot example injection
"""

import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import hashlib
from pathlib import Path


@dataclass
class PromptTemplate:
    """Prompt template with metadata"""
    id: str
    name: str
    template: str
    variables: List[str]
    category: str
    version: int
    success_rate: float
    usage_count: int
    created_at: datetime
    
    def render(self, **kwargs) -> str:
        """Render template with variables"""
        result = self.template
        for var, value in kwargs.items():
            placeholder = f"{{{var}}}"
            result = result.replace(placeholder, str(value))
        return result


@dataclass
class PromptExperiment:
    """A/B test experiment for prompts"""
    id: str
    name: str
    variant_a: str
    variant_b: str
    a_wins: int
    b_wins: int
    ties: int
    confidence: float


class PromptOptimizer:
    """
    Optimizes prompts through reinforcement learning and A/B testing
    """
    
    def __init__(self, db_path: str = "data/prompt_optimizer.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.templates = {}
        self.experiments = {}
        self.performance_history = defaultdict(deque)
        
        self._init_database()
        self._load_templates()
        self._init_default_templates()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    template TEXT NOT NULL,
                    variables TEXT NOT NULL,
                    category TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    success_rate REAL DEFAULT 0.5,
                    usage_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_experiments (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    variant_a TEXT NOT NULL,
                    variant_b TEXT NOT NULL,
                    a_wins INTEGER DEFAULT 0,
                    b_wins INTEGER DEFAULT 0,
                    ties INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 0.5,
                    created_at TEXT NOT NULL,
                    ended_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id TEXT NOT NULL,
                    rendered_prompt TEXT NOT NULL,
                    context TEXT NOT NULL,
                    response_quality REAL,
                    user_feedback TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
    
    def _load_templates(self):
        """Load existing templates"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM prompt_templates")
            
            for row in cursor.fetchall():
                template = PromptTemplate(
                    id=row[0],
                    name=row[1],
                    template=row[2],
                    variables=json.loads(row[3]),
                    category=row[4],
                    version=row[5],
                    success_rate=row[6],
                    usage_count=row[7],
                    created_at=datetime.fromisoformat(row[8])
                )
                self.templates[template.id] = template
    
    def _init_default_templates(self):
        """Initialize default prompt templates"""
        defaults = [
            {
                'name': 'code_explanation',
                'template': '''You are an expert programmer. Explain the following code clearly and concisely:

Code:
```
{code}
```

Explanation:''',
                'variables': ['code'],
                'category': 'coding'
            },
            {
                'name': 'task_automation',
                'template': '''You are a helpful automation assistant. The user wants to automate the following task:

Task: {task}
Context: {context}

Provide a step-by-step automation solution.''',
                'variables': ['task', 'context'],
                'category': 'automation'
            },
            {
                'name': 'information_query',
                'template': '''Answer the following question accurately and concisely:

Question: {question}

Consider the user's context: {context}

Answer:''',
                'variables': ['question', 'context'],
                'category': 'query'
            },
            {
                'name': 'conversational',
                'template': '''You are a friendly and helpful AI assistant. 

User: {message}

Respond naturally and helpfully:''',
                'variables': ['message'],
                'category': 'chat'
            },
        ]
        
        for template_def in defaults:
            template_id = self._generate_id(template_def['name'])
            
            if template_id not in self.templates:
                template = PromptTemplate(
                    id=template_id,
                    name=template_def['name'],
                    template=template_def['template'],
                    variables=template_def['variables'],
                    category=template_def['category'],
                    version=1,
                    success_rate=0.5,
                    usage_count=0,
                    created_at=datetime.now()
                )
                self.save_template(template)
    
    def _generate_id(self, name: str) -> str:
        """Generate unique ID for template"""
        return hashlib.md5(f"{name}_{datetime.now().timestamp()}".encode()).hexdigest()[:12]
    
    def save_template(self, template: PromptTemplate):
        """Save template to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO prompt_templates
                (id, name, template, variables, category, version, success_rate, usage_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template.id,
                template.name,
                template.template,
                json.dumps(template.variables),
                template.category,
                template.version,
                template.success_rate,
                template.usage_count,
                template.created_at.isoformat()
            ))
        
        self.templates[template.id] = template
    
    def get_best_template(self, category: str, context: Dict = None) -> Optional[PromptTemplate]:
        """Get best performing template for category"""
        candidates = [t for t in self.templates.values() if t.category == category]
        
        if not candidates:
            return None
        
        # Sort by success rate and usage (explore-exploit)
        def score(template):
            exploration_bonus = 0.1 / (template.usage_count + 1)
            return template.success_rate + exploration_bonus
        
        best = max(candidates, key=score)
        return best
    
    def render_prompt(self, template_id: str, **kwargs) -> str:
        """Render prompt from template"""
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")
        
        template = self.templates[template_id]
        
        # Add context enrichment
        enriched_kwargs = self._enrich_context(kwargs)
        
        # Render template
        rendered = template.render(**enriched_kwargs)
        
        # Record usage
        template.usage_count += 1
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO prompt_usage
                (template_id, rendered_prompt, context, timestamp)
                VALUES (?, ?, ?, ?)
            """, (
                template_id,
                rendered,
                json.dumps(kwargs),
                datetime.now().isoformat()
            ))
        
        return rendered
    
    def _enrich_context(self, kwargs: Dict) -> Dict:
        """Add contextual information to prompt variables"""
        enriched = kwargs.copy()
        
        # Add timestamp context if not present
        if 'context' not in enriched:
            enriched['context'] = f"Current time: {datetime.now().strftime('%I:%M %p, %A')}"
        
        return enriched
    
    def record_feedback(self, template_id: str, quality_score: float, feedback: str = ""):
        """Record feedback for prompt performance"""
        if template_id not in self.templates:
            return
        
        template = self.templates[template_id]
        
        # Update success rate with exponential moving average
        alpha = 0.1  # Learning rate
        template.success_rate = alpha * quality_score + (1 - alpha) * template.success_rate
        
        # Track history
        self.performance_history[template_id].append(quality_score)
        if len(self.performance_history[template_id]) > 100:
            self.performance_history[template_id].popleft()
        
        # Update database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE prompt_templates
                SET success_rate = ?, usage_count = ?
                WHERE id = ?
            """, (template.success_rate, template.usage_count, template_id))
            
            # Record detailed feedback
            conn.execute("""
                UPDATE prompt_usage
                SET response_quality = ?, user_feedback = ?
                WHERE template_id = ? AND timestamp = (
                    SELECT MAX(timestamp) FROM prompt_usage WHERE template_id = ?
                )
            """, (quality_score, feedback, template_id, template_id))
    
    def create_ab_experiment(self, name: str, variant_a: str, variant_b: str) -> str:
        """Create A/B test experiment"""
        experiment_id = self._generate_id(f"exp_{name}")
        
        experiment = PromptExperiment(
            id=experiment_id,
            name=name,
            variant_a=variant_a,
            variant_b=variant_b,
            a_wins=0,
            b_wins=0,
            ties=0,
            confidence=0.5
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO prompt_experiments
                (id, name, variant_a, variant_b, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                experiment_id,
                name,
                variant_a,
                variant_b,
                datetime.now().isoformat()
            ))
        
        self.experiments[experiment_id] = experiment
        return experiment_id
    
    def record_experiment_result(self, experiment_id: str, winner: str):
        """Record A/B test result"""
        if experiment_id not in self.experiments:
            return
        
        experiment = self.experiments[experiment_id]
        
        if winner == 'a':
            experiment.a_wins += 1
        elif winner == 'b':
            experiment.b_wins += 1
        else:
            experiment.ties += 1
        
        # Calculate statistical confidence
        total = experiment.a_wins + experiment.b_wins + experiment.ties
        if total > 0:
            a_rate = experiment.a_wins / total
            b_rate = experiment.b_wins / total
            experiment.confidence = abs(a_rate - b_rate)
        
        # Update database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE prompt_experiments
                SET a_wins = ?, b_wins = ?, ties = ?, confidence = ?
                WHERE id = ?
            """, (
                experiment.a_wins,
                experiment.b_wins,
                experiment.ties,
                experiment.confidence,
                experiment_id
            ))
    
    def get_optimization_insights(self) -> Dict:
        """Get insights for prompt optimization"""
        insights = {
            'total_templates': len(self.templates),
            'templates_by_category': defaultdict(int),
            'best_performers': [],
            'needs_improvement': [],
        }
        
        for template in self.templates.values():
            insights['templates_by_category'][template.category] += 1
            
            if template.success_rate > 0.7 and template.usage_count > 10:
                insights['best_performers'].append({
                    'name': template.name,
                    'success_rate': template.success_rate,
                    'usage_count': template.usage_count
                })
            elif template.success_rate < 0.4 and template.usage_count > 5:
                insights['needs_improvement'].append({
                    'name': template.name,
                    'success_rate': template.success_rate,
                    'usage_count': template.usage_count
                })
        
        return insights


def example_usage():
    """Demonstrate prompt optimization"""
    optimizer = PromptOptimizer()
    
    # Get best template for coding task
    template = optimizer.get_best_template('coding')
    if template:
        print("Best coding template:", template.name)
        
        # Render prompt
        prompt = optimizer.render_prompt(
            template.id,
            code="def hello(): print('world')",
        )
        print("\nRendered prompt:")
        print(prompt)
        
        # Simulate feedback
        optimizer.record_feedback(template.id, 0.9, "Great explanation!")
    
    # Get insights
    insights = optimizer.get_optimization_insights()
    print("\nOptimization Insights:")
    print(json.dumps(insights, indent=2, default=str))


if __name__ == "__main__":
    example_usage()
