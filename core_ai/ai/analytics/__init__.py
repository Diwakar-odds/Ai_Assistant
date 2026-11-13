"""
AI Analytics Sub-package
Provides anomaly detection, behavior/conversation clustering, usage patterns, explainability, and workflow recommendation.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .usage_pattern_analyzer import UsagePatternAnalyzer
    from .behavior_clustering import BehaviorClusterer
    from .conversation_clustering import ConversationClusterer
    from .anomaly_detection import AnomalyDetector
    from .explainability import ExplainabilityEngine
    from .workflow_recommender import WorkflowRecommender
    from .workflow_scheduler import WorkflowScheduler

def __getattr__(name):
    if name == "UsagePatternAnalyzer":
        from . import usage_pattern_analyzer
        return getattr(usage_pattern_analyzer, name)
    elif name == "BehaviorClusterer":
        from . import behavior_clustering
        return getattr(behavior_clustering, name)
    elif name == "ConversationClusterer":
        from . import conversation_clustering
        return getattr(conversation_clustering, name)
    elif name == "AnomalyDetector":
        from . import anomaly_detection
        return getattr(anomaly_detection, name)
    elif name == "ExplainabilityEngine":
        from . import explainability
        return getattr(explainability, name)
    elif name == "WorkflowRecommender":
        from . import workflow_recommender
        return getattr(workflow_recommender, name)
    elif name == "WorkflowScheduler":
        from . import workflow_scheduler
        return getattr(workflow_scheduler, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "UsagePatternAnalyzer",
    "BehaviorClusterer",
    "ConversationClusterer",
    "AnomalyDetector",
    "ExplainabilityEngine",
    "WorkflowRecommender",
    "WorkflowScheduler",
]

