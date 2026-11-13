"""
AI Learning Sub-package
Provides active, contrastive, reinforcement, federated, and meta-learning systems.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .active_learning import ActiveLearner
    from .advanced_feedback_learning import FeedbackType, ResponseQuality, FeedbackEntry
    from .auto_learning_router import LearningDataRouter
    from .causal_inference import CausalInference
    from .contrastive_learning import ContrastiveLearner
    from .enhanced_learning import Skill, BehaviorPattern, KnowledgeNode
    from .full_rl_system import Experience, Episode, PPOAgent
    from .meta_learning import Task, MetaLearningResult, MAMLLearner
    from .model_compression import ModelCompressor
    from .multimodal_learning import MultiModalProfile, ModalityInteraction, CrossModalEmbedder
    from .qlora_trainer import TrainingConfig, QLoRATrainer
    from .self_supervised_learning import SelfSupervisedLearner

def __getattr__(name):
    if name == "ActiveLearner":
        from . import active_learning
        return getattr(active_learning, name)
    elif name in ("FeedbackType", "ResponseQuality", "FeedbackEntry"):
        from . import advanced_feedback_learning
        return getattr(advanced_feedback_learning, name)
    elif name == "LearningDataRouter":
        from . import auto_learning_router
        return getattr(auto_learning_router, name)
    elif name == "CausalInference":
        from . import causal_inference
        return getattr(causal_inference, name)
    elif name == "ContrastiveLearner":
        from . import contrastive_learning
        return getattr(contrastive_learning, name)
    elif name in ("Skill", "BehaviorPattern", "KnowledgeNode"):
        from . import enhanced_learning
        return getattr(enhanced_learning, name)
    elif name in ("Experience", "Episode", "PPOAgent"):
        from . import full_rl_system
        return getattr(full_rl_system, name)
    elif name in ("Task", "MetaLearningResult", "MAMLLearner"):
        from . import meta_learning
        return getattr(meta_learning, name)
    elif name == "ModelCompressor":
        from . import model_compression
        return getattr(model_compression, name)
    elif name in ("MultiModalProfile", "ModalityInteraction", "CrossModalEmbedder"):
        from . import multimodal_learning
        return getattr(multimodal_learning, name)
    elif name in ("TrainingConfig", "QLoRATrainer"):
        from . import qlora_trainer
        return getattr(qlora_trainer, name)
    elif name == "SelfSupervisedLearner":
        from . import self_supervised_learning
        return getattr(self_supervised_learning, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "ActiveLearner",
    "FeedbackType",
    "ResponseQuality",
    "FeedbackEntry",
    "LearningDataRouter",
    "CausalInference",
    "ContrastiveLearner",
    "Skill",
    "BehaviorPattern",
    "KnowledgeNode",
    "Experience",
    "Episode",
    "PPOAgent",
    "Task",
    "MetaLearningResult",
    "MAMLLearner",
    "ModelCompressor",
    "MultiModalProfile",
    "ModalityInteraction",
    "CrossModalEmbedder",
    "TrainingConfig",
    "QLoRATrainer",
    "SelfSupervisedLearner",
]

