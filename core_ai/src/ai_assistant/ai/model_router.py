# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Intelligent Model Router
Routes queries to appropriate LLM based on complexity, cost, and context

Features:
- Query complexity analysis
- Cost optimization
- Performance tracking
- Fallback handling
- Multi-model support
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model capability tiers"""
    FAST = "fast"          # Quick, cheap models (Gemini Flash)
    STANDARD = "standard"  # Balanced models (GPT-3.5)
    ADVANCED = "advanced"  # Powerful models (GPT-4, Gemini Pro)
    SPECIALIST = "specialist"  # Domain-specific models


@dataclass
class ModelConfig:
    """Configuration for a model"""
    name: str
    tier: ModelTier
    max_tokens: int
    cost_per_1k_tokens: float
    avg_latency_ms: float
    capabilities: List[str]
    priority: int = 0  # Higher = preferred


@dataclass
class QueryAnalysis:
    """Analysis of a query"""
    complexity_score: float  # 0-1
    requires_reasoning: bool
    requires_creativity: bool
    requires_coding: bool
    requires_math: bool
    requires_multimodal: bool
    token_estimate: int
    recommended_tier: ModelTier
    confidence: float


class IntelligentModelRouter:
    """Routes queries to optimal model based on analysis"""
    
    def __init__(self):
        """Initialize router"""
        self.models = self._initialize_models()
        self.stats = {
            'total_queries': 0,
            'by_tier': {tier.value: 0 for tier in ModelTier},
            'total_cost': 0.0,
            'total_latency_ms': 0.0
        }
        
        # Complexity keywords
        self.complexity_indicators = {
            'high': ['complex', 'detailed', 'comprehensive', 'analyze', 'compare',
                    'evaluate', 'explain why', 'reasoning', 'multi-step', 'creative'],
            'medium': ['describe', 'summarize', 'how does', 'what are', 'list'],
            'low': ['what is', 'who is', 'when', 'where', 'define', 'yes or no']
        }
        
        # Capability keywords
        self.capability_keywords = {
            'coding': ['code', 'program', 'function', 'class', 'debug', 'implement',
                      'python', 'javascript', 'api', 'sql', 'algorithm'],
            'math': ['calculate', 'equation', 'formula', 'math', 'compute',
                    'percentage', 'probability', 'statistics'],
            'reasoning': ['why', 'explain', 'reason', 'cause', 'analyze', 'compare',
                         'evaluate', 'assess', 'determine'],
            'creativity': ['creative', 'story', 'poem', 'imagine', 'design',
                          'brainstorm', 'generate ideas', 'invent']
        }
    
    def _initialize_models(self) -> List[ModelConfig]:
        """Initialize available models"""
        return [
            # Fast tier
            ModelConfig(
                name="gemini-2.0-flash-exp",
                tier=ModelTier.FAST,
                max_tokens=8192,
                cost_per_1k_tokens=0.0001,
                avg_latency_ms=500,
                capabilities=['general', 'multimodal', 'coding'],
                priority=10
            ),
            
            # Standard tier
            ModelConfig(
                name="gpt-3.5-turbo",
                tier=ModelTier.STANDARD,
                max_tokens=4096,
                cost_per_1k_tokens=0.002,
                avg_latency_ms=1000,
                capabilities=['general', 'coding', 'reasoning'],
                priority=5
            ),
            
            # Advanced tier
            ModelConfig(
                name="gpt-4-turbo",
                tier=ModelTier.ADVANCED,
                max_tokens=8192,
                cost_per_1k_tokens=0.03,
                avg_latency_ms=3000,
                capabilities=['general', 'coding', 'reasoning', 'creativity', 'math'],
                priority=1
            ),
            
            ModelConfig(
                name="gemini-2.0-pro",
                tier=ModelTier.ADVANCED,
                max_tokens=32768,
                cost_per_1k_tokens=0.0025,
                avg_latency_ms=2000,
                capabilities=['general', 'multimodal', 'reasoning', 'coding'],
                priority=2
            ),
        ]
    
    def analyze_query(self, query: str, context: Dict[str, Any] = None) -> QueryAnalysis:
        """
        Analyze query to determine complexity and requirements
        
        Args:
            query: User query
            context: Optional context (conversation history, etc.)
            
        Returns:
            QueryAnalysis with recommendations
        """
        query_lower = query.lower()
        
        # Estimate tokens (rough: 1 token ≈ 4 chars)
        token_estimate = len(query) // 4 + 100  # Add buffer for response
        
        # Check capabilities
        requires_coding = any(kw in query_lower for kw in self.capability_keywords['coding'])
        requires_math = any(kw in query_lower for kw in self.capability_keywords['math'])
        requires_reasoning = any(kw in query_lower for kw in self.capability_keywords['reasoning'])
        requires_creativity = any(kw in query_lower for kw in self.capability_keywords['creativity'])
        requires_multimodal = context.get('has_image', False) if context else False
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity(query_lower)
        
        # Adjust complexity based on requirements
        if requires_reasoning or requires_creativity:
            complexity_score = max(complexity_score, 0.6)
        if requires_math:
            complexity_score = max(complexity_score, 0.5)
        if requires_coding and len(query.split()) > 20:
            complexity_score = max(complexity_score, 0.5)
        
        # Determine recommended tier
        if complexity_score >= 0.7 or requires_creativity:
            recommended_tier = ModelTier.ADVANCED
            confidence = 0.9
        elif complexity_score >= 0.4 or requires_coding or requires_math:
            recommended_tier = ModelTier.STANDARD
            confidence = 0.8
        else:
            recommended_tier = ModelTier.FAST
            confidence = 0.85
        
        # Multimodal requires specific models
        if requires_multimodal:
            recommended_tier = ModelTier.ADVANCED  # Gemini Pro for images
            confidence = 0.95
        
        return QueryAnalysis(
            complexity_score=complexity_score,
            requires_reasoning=requires_reasoning,
            requires_creativity=requires_creativity,
            requires_coding=requires_coding,
            requires_math=requires_math,
            requires_multimodal=requires_multimodal,
            token_estimate=token_estimate,
            recommended_tier=recommended_tier,
            confidence=confidence
        )
    
    def _calculate_complexity(self, query: str) -> float:
        """Calculate query complexity score (0-1)"""
        score = 0.3  # Base score
        
        # Length indicator
        word_count = len(query.split())
        if word_count > 50:
            score += 0.3
        elif word_count > 20:
            score += 0.2
        elif word_count > 10:
            score += 0.1
        
        # Complexity keywords
        high_count = sum(1 for kw in self.complexity_indicators['high'] if kw in query)
        medium_count = sum(1 for kw in self.complexity_indicators['medium'] if kw in query)
        low_count = sum(1 for kw in self.complexity_indicators['low'] if kw in query)
        
        score += min(high_count * 0.2, 0.4)
        score += min(medium_count * 0.1, 0.2)
        score -= min(low_count * 0.1, 0.2)
        
        # Question marks (multiple = more complex)
        question_marks = query.count('?')
        if question_marks > 1:
            score += 0.15
        
        # Contains code blocks
        if '```' in query or 'def ' in query or 'class ' in query:
            score += 0.2
        
        return min(max(score, 0.0), 1.0)
    
    def route(self, query: str, context: Dict[str, Any] = None,
              override_tier: ModelTier = None) -> Tuple[ModelConfig, QueryAnalysis]:
        """
        Route query to best model
        
        Args:
            query: User query
            context: Optional context
            override_tier: Force specific tier (for testing/preferences)
            
        Returns:
            Tuple of (selected model, query analysis)
        """
        # Analyze query
        analysis = self.analyze_query(query, context)
        
        # Use override or recommendation
        target_tier = override_tier or analysis.recommended_tier
        
        # Get models for tier
        tier_models = [m for m in self.models if m.tier == target_tier]
        
        if not tier_models:
            logger.warning(f"No models for tier {target_tier}, using fallback")
            tier_models = self.models
        
        # Sort by priority (higher first)
        tier_models.sort(key=lambda m: m.priority, reverse=True)
        
        # Select best model
        selected = tier_models[0]
        
        # Check if multimodal needed
        if analysis.requires_multimodal:
            multimodal_models = [m for m in tier_models if 'multimodal' in m.capabilities]
            if multimodal_models:
                selected = multimodal_models[0]
        
        # Update stats
        self.stats['total_queries'] += 1
        self.stats['by_tier'][selected.tier.value] += 1
        
        logger.info(f"🎯 Routed to {selected.name} (tier={selected.tier.value}, "
                   f"complexity={analysis.complexity_score:.2f})")
        
        return selected, analysis
    
    def record_usage(self, model: ModelConfig, tokens_used: int, latency_ms: float):
        """
        Record model usage for stats
        
        Args:
            model: Model that was used
            tokens_used: Number of tokens
            latency_ms: Response latency in milliseconds
        """
        cost = (tokens_used / 1000) * model.cost_per_1k_tokens
        self.stats['total_cost'] += cost
        self.stats['total_latency_ms'] += latency_ms
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        total = max(self.stats['total_queries'], 1)
        
        return {
            'total_queries': self.stats['total_queries'],
            'tier_distribution': {
                tier: {
                    'count': count,
                    'percentage': round((count / total) * 100, 2)
                }
                for tier, count in self.stats['by_tier'].items()
            },
            'total_cost_usd': round(self.stats['total_cost'], 4),
            'avg_latency_ms': round(self.stats['total_latency_ms'] / total, 2),
            'estimated_savings': self._calculate_savings()
        }
    
    def _calculate_savings(self) -> Dict[str, Any]:
        """Calculate cost savings from routing vs always using GPT-4"""
        gpt4_cost_per_1k = 0.03
        total_tokens = self.stats['total_queries'] * 500  # Estimate
        
        gpt4_cost = (total_tokens / 1000) * gpt4_cost_per_1k
        actual_cost = self.stats['total_cost']
        savings = gpt4_cost - actual_cost
        
        return {
            'if_all_gpt4_usd': round(gpt4_cost, 4),
            'actual_cost_usd': round(actual_cost, 4),
            'saved_usd': round(savings, 4),
            'savings_percentage': round((savings / max(gpt4_cost, 0.01)) * 100, 2)
        }
    
    def recommend_model(self, 
                       tier: ModelTier = None,
                       capability: str = None,
                       max_latency_ms: float = None,
                       max_cost_per_1k: float = None) -> Optional[ModelConfig]:
        """
        Recommend model based on constraints
        
        Args:
            tier: Specific tier
            capability: Required capability
            max_latency_ms: Maximum acceptable latency
            max_cost_per_1k: Maximum cost per 1k tokens
            
        Returns:
            Best matching model or None
        """
        candidates = self.models
        
        # Filter by tier
        if tier:
            candidates = [m for m in candidates if m.tier == tier]
        
        # Filter by capability
        if capability:
            candidates = [m for m in candidates if capability in m.capabilities]
        
        # Filter by latency
        if max_latency_ms:
            candidates = [m for m in candidates if m.avg_latency_ms <= max_latency_ms]
        
        # Filter by cost
        if max_cost_per_1k:
            candidates = [m for m in candidates if m.cost_per_1k_tokens <= max_cost_per_1k]
        
        if not candidates:
            return None
        
        # Sort by priority
        candidates.sort(key=lambda m: m.priority, reverse=True)
        return candidates[0]


# Global router instance
_model_router = None

def get_model_router() -> IntelligentModelRouter:
    """Get global router instance"""
    global _model_router
    if _model_router is None:
        _model_router = IntelligentModelRouter()
    return _model_router


if __name__ == "__main__":
    # Test the router
    logger.debug("Testing Intelligent Model Router...\n")
    
    router = IntelligentModelRouter()
    
    test_queries = [
        "What is the capital of France?",
        "Write a Python function to sort a list using quicksort algorithm",
        "Explain the philosophical implications of quantum entanglement",
        "Calculate 25% of 840",
        "Write a creative short story about a robot learning to love"
    ]
    
    for query in test_queries:
        print(f"Query: {query}")
        model, analysis = router.route(query)
        print(f"  → Model: {model.name}")
        print(f"  → Tier: {model.tier.value}")
        print(f"  → Complexity: {analysis.complexity_score:.2f}")
        print(f"  → Requirements: coding={analysis.requires_coding}, "
              f"reasoning={analysis.requires_reasoning}, "
              f"creativity={analysis.requires_creativity}")
        print()
    
    print("\nRouter Stats:")
    stats = router.get_stats()
    print(f"Total queries: {stats['total_queries']}")
    print(f"Tier distribution: {stats['tier_distribution']}")
    print(f"Estimated savings: {stats['estimated_savings']}")
