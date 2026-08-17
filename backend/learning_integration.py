"""
Learning Systems Integration for Flask Backend
Provides helper functions to integrate learning_api with modern_web_backend.py
"""

try:
    from learning_api import (
        get_active_learner, get_explainability, get_behavior_clusterer,
        get_conversation_clusterer, get_llm_bandit, get_model_compressor,
        get_workflow_scheduler, get_contrastive_learner, get_self_supervised,
        get_causal_inference, get_query_cache, get_command_sequences,
        get_historical_rag, get_command_predictor, get_anomaly_detector,
        get_knowledge_graph, get_ppo_agent, get_maml_learner,
        get_federated_server, get_gnn, get_domain_embeddings,
        get_smart_commands, get_adaptive_voice, get_workflow_recommender,
        get_context_generator
    )
    LEARNING_SYSTEMS_AVAILABLE = True
except ImportError as e:
    LEARNING_SYSTEMS_AVAILABLE = False
    print(f"âš ï¸ Learning systems not available: {e}")


def get_learning_stats():
    """Get stats from all learning systems"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        return {"error": "Learning systems not available"}
    
    stats = {}
    systems = {
        'active_learning': get_active_learner,
        'explainability': get_explainability,
        'behavior_clustering': get_behavior_clusterer,
        'conversation_clustering': get_conversation_clusterer,
        'llm_bandit': get_llm_bandit,
        'model_compression': get_model_compressor,
        'workflow_scheduler': get_workflow_scheduler,
        'contrastive_learning': get_contrastive_learner,
        'self_supervised': get_self_supervised,
        'causal_inference': get_causal_inference,
        'query_cache': get_query_cache,
        'command_sequences': get_command_sequences,
        'historical_rag': get_historical_rag,
        'command_predictor': get_command_predictor,
        'anomaly_detection': get_anomaly_detector,
        'knowledge_graph': get_knowledge_graph,
        'ppo_agent': get_ppo_agent,
        'maml_learner': get_maml_learner,
        'federated_server': get_federated_server,
        'gnn': get_gnn,
        'domain_embeddings': get_domain_embeddings,
        'smart_commands': get_smart_commands,
        'adaptive_voice': get_adaptive_voice,
        'workflow_recommender': get_workflow_recommender,
        'context_generator': get_context_generator
    }
    
    for name, getter in systems.items():
        try:
            system = getter()
            if system and hasattr(system, 'get_stats'):
                stats[name] = system.get_stats()
            else:
                stats[name] = {"error": "System not initialized or missing get_stats()"}
        except Exception as e:
            stats[name] = {"error": str(e)}
    
    return stats

