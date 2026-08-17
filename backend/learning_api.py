"""
Advanced Learning Systems API Endpoints
FastAPI endpoints for all 16 learning systems
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime
import json

# Import learning systems
try:
    from ai_assistant.ai.active_learning import ActiveLearner
    from ai_assistant.ai.explainability import ExplainabilityEngine
    from ai_assistant.ai.behavior_clustering import BehaviorClusterer
    from ai_assistant.ai.conversation_clustering import ConversationClusterer
    from ai_assistant.ai.llm_bandit import LLMBandit
    from ai_assistant.ai.model_compression import ModelCompressor
    from ai_assistant.ai.workflow_scheduler import WorkflowScheduler
    from ai_assistant.ai.contrastive_learning import ContrastiveLearner
    from ai_assistant.ai.self_supervised_learning import SelfSupervisedLearner
    from ai_assistant.ai.causal_inference import CausalInference
    from ai_assistant.ai.query_cache import QuerySimilarityCache
    from ai_assistant.ai.command_sequences import CommandMarkovChain
    from ai_assistant.ai.historical_rag import HistoricalRAG
    from ai_assistant.ai.command_predictor import CommandSuccessPredictor
    from ai_assistant.ai.anomaly_detection import AnomalyDetector
    from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
    from ai_assistant.ai.full_rl_system import PPOAgent, RLEnvironmentWrapper
    from ai_assistant.ai.meta_learning import MAMLLearner
    from ai_assistant.ai.federated_learning import FederatedServer, FederatedClient
    from ai_assistant.ai.graph_neural_networks import GraphNeuralNetwork
    from ai_assistant.ai.domain_embeddings import DomainAdaptedEmbeddings
    from ai_assistant.ai.smart_command_prediction import SmartCommandPredictor
    from ai_assistant.ai.adaptive_voice import AdaptiveVoiceRecognition
    from ai_assistant.ai.workflow_recommender import WorkflowRecommender
    from ai_assistant.ai.context_aware_response import ContextAwareResponseGenerator
    LEARNING_SYSTEMS_AVAILABLE = True
except ImportError as e:
    print(f"Learning systems import error: {e}")
    LEARNING_SYSTEMS_AVAILABLE = False

# Initialize systems (lazy loading)
_active_learner = None
_explainability = None
_behavior_clusterer = None
_conversation_clusterer = None
_llm_bandit = None
_model_compressor = None
_workflow_scheduler = None
_contrastive_learner = None
_self_supervised = None
_causal_inference = None
_query_cache = None
_command_sequences = None
_historical_rag = None
_command_predictor = None
_anomaly_detector = None
_knowledge_graph = None
_ppo_agent = None
_maml_learner = None
_federated_server = None
_gnn = None
_domain_embeddings = None
_smart_commands = None
_adaptive_voice = None
_workflow_recommender = None
_context_generator = None

router = APIRouter(prefix="/api/learning", tags=["learning"])

# Pydantic models
class SampleData(BaseModel):
    sample_data: Dict
    features: List[float]

class LabelRequest(BaseModel):
    sample_id: int
    label: int
    labeled_by: str = "user"

class ExplainRequest(BaseModel):
    prediction_id: str
    features: List[float]
    prediction: int

class SessionData(BaseModel):
    user_id: str
    session_id: str
    session_data: Dict

class ConversationData(BaseModel):
    conversation_id: str
    user_id: str
    messages: List[Dict]

class TaskRequest(BaseModel):
    task_type: str
    text: str
    requirements: List[str] = []
    budget: Optional[str] = None

class WorkflowRequest(BaseModel):
    task_ids: List[str]
    resources: Optional[Dict] = None

class CausalEdge(BaseModel):
    cause: str
    effect: str
    strength: float
    confidence: float = 0.8

class InterventionRequest(BaseModel):
    variable: str
    value: float

# New Systems Models
class RLStateAction(BaseModel):
    state: List[float]
    action: Optional[int] = None
    reward: Optional[float] = None

class MetaTaskRequest(BaseModel):
    task_name: str
    task_type: str
    support_data: List[Dict]
    query_data: Optional[List[Dict]] = None

class FederatedClientRequest(BaseModel):
    client_id: str
    model_params: Dict
    num_samples: int

class GNNNodeRequest(BaseModel):
    node_id: str
    node_type: str
    features: Optional[List[float]] = None

class GNNEdgeRequest(BaseModel):
    source: str
    target: str
    edge_type: str

class DomainRequest(BaseModel):
    domain_name: str
    examples: List[str]

class CommandContext(BaseModel):
    user_id: str
    recent_commands: List[str]
    context: Optional[Dict] = None

class VoiceRecognition(BaseModel):
    user_id: str
    text: str
    confidence: float
    was_correct: Optional[bool] = None

class WorkflowContext(BaseModel):
    user_id: str
    current_tasks: List[str]
    context: Dict

class ContextRequest(BaseModel):
    user_id: str
    query: str
    context: Optional[Dict] = None

# Helper functions
def get_active_learner():
    global _active_learner
    if _active_learner is None:
        _active_learner = ActiveLearner()
    return _active_learner

def get_explainability():
    global _explainability
    if _explainability is None:
        _explainability = ExplainabilityEngine()
    return _explainability

def get_behavior_clusterer():
    global _behavior_clusterer
    if _behavior_clusterer is None:
        _behavior_clusterer = BehaviorClusterer()
    return _behavior_clusterer

def get_conversation_clusterer():
    global _conversation_clusterer
    if _conversation_clusterer is None:
        _conversation_clusterer = ConversationClusterer()
    return _conversation_clusterer

def get_llm_bandit():
    global _llm_bandit
    if _llm_bandit is None:
        _llm_bandit = LLMBandit()
    return _llm_bandit

def get_model_compressor():
    global _model_compressor
    if _model_compressor is None:
        _model_compressor = ModelCompressor()
    return _model_compressor

def get_workflow_scheduler():
    global _workflow_scheduler
    if _workflow_scheduler is None:
        _workflow_scheduler = WorkflowScheduler()
    return _workflow_scheduler

def get_contrastive_learner():
    global _contrastive_learner
    if _contrastive_learner is None:
        _contrastive_learner = ContrastiveLearner()
    return _contrastive_learner

def get_self_supervised():
    global _self_supervised
    if _self_supervised is None:
        _self_supervised = SelfSupervisedLearner()
    return _self_supervised

def get_causal_inference():
    global _causal_inference
    if _causal_inference is None:
        _causal_inference = CausalInference()
    return _causal_inference

def get_query_cache():
    global _query_cache
    if _query_cache is None:
        _query_cache = QuerySimilarityCache()
    return _query_cache

def get_command_sequences():
    global _command_sequences
    if _command_sequences is None:
        _command_sequences = CommandMarkovChain()
    return _command_sequences

def get_historical_rag():
    global _historical_rag
    if _historical_rag is None:
        _historical_rag = HistoricalRAG()
    return _historical_rag

def get_command_predictor():
    global _command_predictor
    if _command_predictor is None:
        _command_predictor = CommandSuccessPredictor()
    return _command_predictor

def get_anomaly_detector():
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = AnomalyDetector()
    return _anomaly_detector

def get_knowledge_graph():
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = PersonalKnowledgeGraph()
    return _knowledge_graph

def get_ppo_agent():
    global _ppo_agent
    if _ppo_agent is None:
        _ppo_agent = PPOAgent(state_dim=128, action_dim=32)
    return _ppo_agent

def get_maml_learner():
    global _maml_learner
    if _maml_learner is None:
        _maml_learner = MAMLLearner(input_dim=128, hidden_dim=64, output_dim=32)
    return _maml_learner

def get_federated_server():
    global _federated_server
    if _federated_server is None:
        _federated_server = FederatedServer()
    return _federated_server

def get_gnn():
    global _gnn
    if _gnn is None:
        _gnn = GraphNeuralNetwork()
    return _gnn

def get_domain_embeddings():
    global _domain_embeddings
    if _domain_embeddings is None:
        _domain_embeddings = DomainAdaptedEmbeddings()
    return _domain_embeddings

def get_smart_commands():
    global _smart_commands
    if _smart_commands is None:
        _smart_commands = SmartCommandPredictor()
    return _smart_commands

def get_adaptive_voice():
    global _adaptive_voice
    if _adaptive_voice is None:
        _adaptive_voice = AdaptiveVoiceRecognition()
    return _adaptive_voice

def get_workflow_recommender():
    global _workflow_recommender
    if _workflow_recommender is None:
        _workflow_recommender = WorkflowRecommender()
    return _workflow_recommender

def get_context_generator():
    global _context_generator
    if _context_generator is None:
        _context_generator = ContextAwareResponseGenerator()
    return _context_generator

# Active Learning endpoints
@router.post("/active/add-sample")
async def add_unlabeled_sample(data: SampleData):
    """Add unlabeled sample for active learning"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    learner = get_active_learner()
    sample_id = learner.add_unlabeled_sample(data.sample_data, data.features)
    
    return {
        "success": True,
        "sample_id": sample_id,
        "timestamp": datetime.now().isoformat()
    }

@router.post("/active/select-samples")
async def select_samples_to_label(strategy: str = "uncertainty", num_samples: int = 10):
    """Select most informative samples for labeling"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    learner = get_active_learner()
    selected = learner.select_samples_to_label(strategy, num_samples)
    
    return {
        "success": True,
        "selected_samples": selected,
        "count": len(selected)
    }

@router.get("/active/next-to-label")
async def get_next_to_label(batch_size: int = 1):
    """Get next samples from labeling queue"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    learner = get_active_learner()
    next_batch = learner.get_next_to_label(batch_size)
    
    return {
        "success": True,
        "samples": next_batch,
        "count": len(next_batch)
    }

@router.post("/active/provide-label")
async def provide_label(data: LabelRequest):
    """Provide label for a sample"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    learner = get_active_learner()
    learner.provide_label(data.sample_id, data.label, data.labeled_by)
    
    return {
        "success": True,
        "message": "Label recorded"
    }

@router.get("/active/stats")
async def get_active_learning_stats():
    """Get active learning statistics"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    learner = get_active_learner()
    stats = learner.get_stats()
    
    return stats

# Explainability endpoints
@router.post("/explain/prediction")
async def explain_prediction(data: ExplainRequest):
    """Generate explanation for a prediction"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    engine = get_explainability()
    
    import numpy as np
    features_array = np.array(data.features)
    
    explanation = engine.explain_prediction(
        data.prediction_id,
        features_array,
        data.prediction
    )
    
    return explanation

@router.get("/explain/feature-importance")
async def get_feature_importance_summary():
    """Get aggregate feature importance"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    engine = get_explainability()
    summary = engine.get_feature_importance_summary()
    
    return {
        "success": True,
        "feature_importance": summary
    }

# Behavior Clustering endpoints
@router.post("/behavior/add-session")
async def add_session(data: SessionData):
    """Add user session for clustering"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    clusterer = get_behavior_clusterer()
    session_id = clusterer.add_session(data.user_id, data.session_id, data.session_data)
    
    return {
        "success": True,
        "session_id": session_id
    }

@router.post("/behavior/cluster")
async def cluster_sessions():
    """Cluster all sessions"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    clusterer = get_behavior_clusterer()
    clusterer.cluster_sessions()
    
    return {
        "success": True,
        "message": "Sessions clustered"
    }

@router.get("/behavior/classify-user/{user_id}")
async def classify_user(user_id: str):
    """Classify user based on behavior"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    clusterer = get_behavior_clusterer()
    classification = clusterer.classify_user(user_id)
    
    return classification

@router.get("/behavior/insights")
async def get_cluster_insights():
    """Get insights about behavior clusters"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    clusterer = get_behavior_clusterer()
    insights = clusterer.get_cluster_insights()
    
    return {
        "success": True,
        "insights": insights
    }

# Conversation Clustering endpoints
@router.post("/conversation/add")
async def add_conversation(data: ConversationData):
    """Add conversation for clustering"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    clusterer = get_conversation_clusterer()
    conv_id = clusterer.add_conversation(data.conversation_id, data.user_id, data.messages)
    
    return {
        "success": True,
        "id": conv_id
    }

@router.post("/conversation/cluster")
async def cluster_conversations():
    """Cluster conversations"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    clusterer = get_conversation_clusterer()
    clusterer.cluster_conversations()
    
    return {
        "success": True,
        "message": "Conversations clustered"
    }

@router.get("/conversation/similar")
async def find_similar_conversations(query: str, top_k: int = 5):
    """Find similar conversations"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    clusterer = get_conversation_clusterer()
    similar = clusterer.find_similar_conversations(query, top_k)
    
    return {
        "success": True,
        "similar": similar
    }

# LLM Bandit endpoints
@router.post("/llm/select")
async def select_llm(task: TaskRequest):
    """Select best LLM for task"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    bandit = get_llm_bandit()
    selection = bandit.select_llm(task.dict())
    
    return selection

@router.get("/llm/performance")
async def get_llm_performance():
    """Get LLM performance summary"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    bandit = get_llm_bandit()
    summary = bandit.get_performance_summary()
    
    return {
        "success": True,
        "performance": summary
    }

# Workflow Scheduler endpoints
@router.post("/workflow/schedule")
async def schedule_workflow(data: WorkflowRequest):
    """Generate workflow schedule"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    scheduler = get_workflow_scheduler()
    schedule = scheduler.schedule_workflow(data.task_ids, data.resources)
    
    return {
        "success": True,
        "schedule": schedule
    }

@router.get("/workflow/stats")
async def get_workflow_stats():
    """Get workflow statistics"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    scheduler = get_workflow_scheduler()
    stats = scheduler.get_stats()
    
    return stats

# Causal Inference endpoints
@router.post("/causal/add-edge")
async def add_causal_edge(edge: CausalEdge):
    """Add causal edge to graph"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    causal = get_causal_inference()
    causal.add_causal_edge(edge.cause, edge.effect, edge.strength, edge.confidence)
    
    return {
        "success": True,
        "message": "Causal edge added"
    }

@router.post("/causal/intervene")
async def do_intervention(data: InterventionRequest):
    """Simulate intervention"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    causal = get_causal_inference()
    result = causal.do_intervention(data.variable, data.value)
    
    return result

@router.get("/causal/stats")
async def get_causal_stats():
    """Get causal inference statistics"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    causal = get_causal_inference()
    stats = causal.get_stats()
    
    return stats

# Knowledge Graph endpoints
@router.get("/knowledge-graph/visualize")
async def visualize_knowledge_graph():
    """Get knowledge graph visualization data"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    kg = get_knowledge_graph()
    
    # Export graph data for visualization
    import networkx as nx
    graph_data = nx.node_link_data(kg.graph)
    
    return {
        "success": True,
        "graph": graph_data,
        "num_nodes": kg.graph.number_of_nodes(),
        "num_edges": kg.graph.number_of_edges()
    }

@router.get("/knowledge-graph/stats")
async def get_knowledge_graph_stats():
    """Get knowledge graph statistics"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    kg = get_knowledge_graph()
    
    return {
        "success": True,
        "num_nodes": kg.graph.number_of_nodes(),
        "num_edges": kg.graph.number_of_edges(),
        "timestamp": datetime.now().isoformat()
    }

# Unified dashboard endpoint
@router.get("/dashboard")
async def get_learning_dashboard():
    """Get unified learning systems dashboard"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        return {
            "success": False,
            "message": "Learning systems not available"
        }
    
    dashboard = {
        "timestamp": datetime.now().isoformat(),
        "systems": {}
    }
    
    # Collect stats from all systems
    try:
        dashboard["systems"]["active_learning"] = get_active_learner().get_stats()
    except Exception:
        pass
    
    try:
        dashboard["systems"]["behavior_clustering"] = get_behavior_clusterer().get_stats()
    except Exception:
        pass
    
    try:
        dashboard["systems"]["conversation_clustering"] = get_conversation_clusterer().get_stats()
    except Exception:
        pass
    
    try:
        dashboard["systems"]["llm_bandit"] = get_llm_bandit().get_stats()
    except Exception:
        pass
    
    try:
        dashboard["systems"]["workflow_scheduler"] = get_workflow_scheduler().get_stats()
    except Exception:
        pass
    
    try:
        dashboard["systems"]["causal_inference"] = get_causal_inference().get_stats()
    except Exception:
        pass
    
    return dashboard

# ==================== KNOWLEDGE GRAPH VISUALIZATION ====================

@router.get("/knowledge-graph/export")
async def export_knowledge_graph():
    """Export knowledge graph as JSON for visualization (D3.js, vis.js compatible)"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        kg = get_knowledge_graph()
        graph_data = kg.export_graph_data()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "graph": graph_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge-graph/stats")
async def knowledge_graph_stats():
    """Get knowledge graph statistics"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        kg = get_knowledge_graph()
        stats = kg.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== NEW SYSTEMS (ALL 10) ====================

@router.get("/stats/all")
async def get_all_stats():
    """Get stats from all 27 learning systems"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        return {"success": False, "message": "Learning systems not available"}
    
    all_stats = {}
    
    # All 27 systems
    systems = [
        # Original 16 systems
        ("active_learning", lambda: get_active_learner().get_stats()),
        ("explainability", lambda: get_explainability().get_stats()),
        ("behavior_clustering", lambda: get_behavior_clusterer().get_stats()),
        ("conversation_clustering", lambda: get_conversation_clusterer().get_stats()),
        ("llm_bandit", lambda: get_llm_bandit().get_stats()),
        ("model_compression", lambda: get_model_compressor().get_stats()),
        ("workflow_scheduler", lambda: get_workflow_scheduler().get_stats()),
        ("contrastive_learning", lambda: get_contrastive_learner().get_stats()),
        ("self_supervised", lambda: get_self_supervised().get_stats()),
        ("causal_inference", lambda: get_causal_inference().get_stats()),
        ("query_cache", lambda: get_query_cache().get_stats()),
        ("command_sequences", lambda: get_command_sequences().get_stats()),
        ("historical_rag", lambda: get_historical_rag().get_stats()),
        ("command_predictor", lambda: get_command_predictor().get_stats()),
        ("anomaly_detection", lambda: get_anomaly_detector().get_stats()),
        ("knowledge_graph", lambda: get_knowledge_graph().get_stats()),
        # 10 new systems
        ("ppo_agent", lambda: get_ppo_agent().get_stats()),
        ("maml_learner", lambda: get_maml_learner().get_stats()),
        ("federated_server", lambda: get_federated_server().get_stats()),
        ("gnn", lambda: get_gnn().get_stats()),
        ("domain_embeddings", lambda: get_domain_embeddings().get_stats()),
        ("smart_commands", lambda: get_smart_commands().get_stats()),
        ("adaptive_voice", lambda: get_adaptive_voice().get_stats()),
        ("workflow_recommender", lambda: get_workflow_recommender().get_stats()),
        ("context_generator", lambda: get_context_generator().get_stats()),
    ]
    
    for name, getter in systems:
        try:
            all_stats[name] = getter()
        except Exception as e:
            all_stats[name] = {"error": str(e)}
    
    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "systems": all_stats,
        "total_systems": len(all_stats)
    }
# NEW SYSTEMS ENDPOINTS - To be appended to learning_api.py

# ==================== REINFORCEMENT LEARNING (PPO) ====================

@router.post("/rl/train")
async def train_rl_agent(data: RLStateAction):
    """Train PPO agent with state-action-reward experience"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        agent = get_ppo_agent()
        agent.store_experience(data.state, data.action, data.reward, data.state, False)
        
        # Train if enough experiences
        metrics = agent.train()
        
        return {
            "success": True,
            "message": "Experience stored and training performed",
            "metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rl/select-action")
async def select_rl_action(state: List[float]):
    """Select action using PPO policy"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        agent = get_ppo_agent()
        action = agent.select_action(state)
        
        return {
            "success": True,
            "action": int(action),
            "state": state
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rl/stats")
async def get_rl_stats():
    """Get PPO agent statistics"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        agent = get_ppo_agent()
        stats = agent.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== META-LEARNING (MAML) ====================

@router.post("/meta/register-task")
async def register_meta_task(task: MetaTaskRequest):
    """Register new meta-learning task"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        learner = get_maml_learner()
        learner.register_task(task.task_name, task.support_data, task.query_data or [])
        
        return {
            "success": True,
            "message": f"Task '{task.task_name}' registered",
            "task_name": task.task_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/meta/adapt")
async def adapt_meta_model(task: MetaTaskRequest):
    """Quickly adapt to new task using MAML"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        learner = get_maml_learner()
        loss = learner.adapt_to_task(task.task_name, task.support_data)
        
        return {
            "success": True,
            "message": "Model adapted to task",
            "task_name": task.task_name,
            "adaptation_loss": float(loss)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/meta/stats")
async def get_meta_stats():
    """Get meta-learning statistics"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        learner = get_maml_learner()
        stats = learner.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== FEDERATED LEARNING ====================

@router.post("/federated/register-client")
async def register_federated_client(client: FederatedClientRequest):
    """Register new federated learning client"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        server = get_federated_server()
        server.register_client(client.client_id)
        
        return {
            "success": True,
            "message": f"Client '{client.client_id}' registered",
            "client_id": client.client_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/federated/train-round")
async def federated_training_round(updates: List[FederatedClientRequest]):
    """Perform federated training round with client updates"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        server = get_federated_server()
        
        # Submit client updates
        for update in updates:
            server.submit_client_update(
                update.client_id,
                update.model_params,
                update.num_samples
            )
        
        # Aggregate
        global_params = server.aggregate_updates()
        
        return {
            "success": True,
            "message": "Training round completed",
            "round_number": server.current_round,
            "num_clients": len(updates),
            "global_params_size": len(global_params)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/federated/stats")
async def get_federated_stats():
    """Get federated learning statistics"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        server = get_federated_server()
        stats = server.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== GRAPH NEURAL NETWORKS ====================

@router.post("/gnn/add-node")
async def add_gnn_node(node: GNNNodeRequest):
    """Add node to graph"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        gnn = get_gnn()
        gnn.add_node(node.node_id, node.node_type, node.features)
        
        return {
            "success": True,
            "message": f"Node '{node.node_id}' added",
            "node_id": node.node_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gnn/add-edge")
async def add_gnn_edge(edge: GNNEdgeRequest):
    """Add edge to graph"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        gnn = get_gnn()
        gnn.add_edge(edge.source, edge.target, edge.edge_type)
        
        return {
            "success": True,
            "message": f"Edge added: {edge.source} -> {edge.target}",
            "edge_type": edge.edge_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gnn/train")
async def train_gnn(epochs: int = 10):
    """Train GNN model"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        gnn = get_gnn()
        loss = gnn.train(epochs=epochs)
        
        return {
            "success": True,
            "message": "GNN training completed",
            "final_loss": float(loss),
            "epochs": epochs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gnn/predict-link")
async def predict_gnn_link(source: str, target: str):
    """Predict probability of link between two nodes"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        gnn = get_gnn()
        probability = gnn.predict_link(source, target)
        
        return {
            "success": True,
            "source": source,
            "target": target,
            "link_probability": float(probability)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gnn/stats")
async def get_gnn_stats():
    """Get GNN statistics"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        gnn = get_gnn()
        stats = gnn.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DOMAIN-ADAPTED EMBEDDINGS ====================

@router.post("/domain/register")
async def register_domain(domain: DomainRequest):
    """Register new domain with examples"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        embeddings = get_domain_embeddings()
        embeddings.register_domain(domain.domain_name, domain.examples)
        
        return {
            "success": True,
            "message": f"Domain '{domain.domain_name}' registered",
            "num_examples": len(domain.examples)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/domain/train")
async def train_domain(domain_name: str, epochs: int = 5):
    """Train domain-specific adapter"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        embeddings = get_domain_embeddings()
        loss = embeddings.train_domain(domain_name, epochs=epochs)
        
        return {
            "success": True,
            "message": f"Domain '{domain_name}' adapter trained",
            "final_loss": float(loss),
            "epochs": epochs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/domain/embed")
async def embed_text(text: str, domain: Optional[str] = None):
    """Get embedding for text (optionally domain-adapted)"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        embeddings = get_domain_embeddings()
        embedding = embeddings.get_embedding(text, domain)
        
        return {
            "success": True,
            "text": text,
            "domain": domain,
            "embedding": embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding),
            "dimension": len(embedding)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/domain/detect")
async def detect_domain(text: str):
    """Detect most likely domain for text"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        embeddings = get_domain_embeddings()
        domain = embeddings.detect_domain(text)
        
        return {
            "success": True,
            "text": text,
            "detected_domain": domain
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/domain/stats")
async def get_domain_stats():
    """Get domain embeddings statistics"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        embeddings = get_domain_embeddings()
        stats = embeddings.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SMART COMMAND PREDICTION ====================

@router.post("/smart-commands/predict")
async def predict_commands(context: CommandContext):
    """Predict next likely commands"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        predictor = get_smart_commands()
        predictions = predictor.predict_next_commands(
            context.user_id,
            context.recent_commands,
            context.context
        )
        
        return {
            "success": True,
            "predictions": predictions,
            "user_id": context.user_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/smart-commands/autocomplete")
async def autocomplete_command(user_id: str, partial: str):
    """Get command autocomplete suggestions"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        predictor = get_smart_commands()
        suggestions = predictor.autocomplete_command(user_id, partial)
        
        return {
            "success": True,
            "partial": partial,
            "suggestions": suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/smart-commands/log")
async def log_command_usage(user_id: str, command: str, context: Optional[Dict] = None):
    """Log command usage for learning"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        predictor = get_smart_commands()
        predictor.log_command_usage(user_id, command, context)
        
        return {
            "success": True,
            "message": "Command usage logged"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/smart-commands/stats")
async def get_smart_commands_stats():
    """Get smart command prediction statistics"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        predictor = get_smart_commands()
        stats = predictor.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ADAPTIVE VOICE RECOGNITION ====================

@router.post("/adaptive-voice/log")
async def log_voice_recognition(recognition: VoiceRecognition):
    """Log voice recognition result"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        voice = get_adaptive_voice()
        voice.log_recognition(
            recognition.user_id,
            recognition.text,
            recognition.confidence,
            recognition.was_correct
        )
        
        return {
            "success": True,
            "message": "Recognition logged"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/adaptive-voice/correct")
async def apply_voice_correction(user_id: str, recognized: str, correct: str):
    """Apply correction to learn from mistakes"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        voice = get_adaptive_voice()
        voice.apply_correction(user_id, recognized, correct)
        
        return {
            "success": True,
            "message": "Correction applied",
            "recognized": recognized,
            "correct": correct
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/adaptive-voice/suggestions")
async def get_voice_suggestions(user_id: str, text: str):
    """Get correction suggestions for recognized text"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        voice = get_adaptive_voice()
        suggestions = voice.suggest_corrections(user_id, text)
        
        return {
            "success": True,
            "text": text,
            "suggestions": suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/adaptive-voice/stats")
async def get_adaptive_voice_stats():
    """Get adaptive voice recognition statistics"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        voice = get_adaptive_voice()
        stats = voice.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WORKFLOW RECOMMENDER ====================

@router.post("/workflow/register")
async def register_workflow(name: str, steps: List[str], description: str = ""):
    """Register new workflow"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        recommender = get_workflow_recommender()
        recommender.register_workflow(name, steps, description)
        
        return {
            "success": True,
            "message": f"Workflow '{name}' registered",
            "num_steps": len(steps)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workflow/recommend")
async def recommend_workflow(context: WorkflowContext):
    """Get workflow recommendations based on context"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        recommender = get_workflow_recommender()
        recommendations = recommender.recommend_workflow(
            context.user_id,
            context.current_tasks,
            context.context
        )
        
        return {
            "success": True,
            "recommendations": recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workflow/automation")
async def identify_automation(user_id: str):
    """Identify automation opportunities"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        recommender = get_workflow_recommender()
        opportunities = recommender.identify_automation_opportunities(user_id)
        
        return {
            "success": True,
            "opportunities": opportunities,
            "count": len(opportunities)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workflow/log-execution")
async def log_workflow_execution(
    user_id: str,
    workflow_name: str,
    duration: float,
    success: bool
):
    """Log workflow execution"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        recommender = get_workflow_recommender()
        recommender.log_execution(user_id, workflow_name, duration, success)
        
        return {
            "success": True,
            "message": "Execution logged"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflow/stats")
async def get_workflow_stats():
    """Get workflow recommender statistics"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        recommender = get_workflow_recommender()
        stats = recommender.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CONTEXT-AWARE RESPONSE ====================

@router.post("/context/generate")
async def generate_context_response(request: ContextRequest):
    """Generate context-aware response"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        generator = get_context_generator()
        response = generator.generate_response(
            request.user_id,
            request.query,
            request.context
        )
        
        return {
            "success": True,
            "response": response,
            "user_id": request.user_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/context/feedback")
async def provide_context_feedback(
    user_id: str,
    response_id: str,
    rating: int,
    feedback: Optional[str] = None
):
    """Provide feedback on generated response"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        generator = get_context_generator()
        generator.log_feedback(user_id, response_id, rating, feedback)
        
        return {
            "success": True,
            "message": "Feedback recorded",
            "response_id": response_id,
            "rating": rating
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/context/conversation-history")
async def get_conversation_history(user_id: str, limit: int = 50):
    """Get recent conversation history"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        generator = get_context_generator()
        history = generator.get_conversation_history(user_id, limit)
        
        return {
            "success": True,
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/context/stats")
async def get_context_stats():
    """Get context-aware response statistics"""
    if not LEARNING_SYSTEMS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Learning systems not available")
    
    try:
        generator = get_context_generator()
        stats = generator.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
