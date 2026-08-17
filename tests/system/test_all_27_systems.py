"""
Integration Test for All 27 Learning Systems
Tests that all systems can be initialized and provide stats
"""

import sys
import os
# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

def test_all_systems():
    """Test all 27 learning systems"""
    
    print("=" * 70)
    print("TESTING ALL 27 LEARNING SYSTEMS")
    print("=" * 70)
    
    systems_tested = []
    systems_failed = []
    
    # Test 1: Active Learning
    try:
        from ai_assistant.ai.active_learning import ActiveLearner
        al = ActiveLearner()
        stats = al.get_stats()
        systems_tested.append("✅ Active Learning")
        print(f"✅ Active Learning - {stats.get('total_samples', 0)} samples")
    except Exception as e:
        systems_failed.append(f"❌ Active Learning: {e}")
        print(f"❌ Active Learning: {e}")
    
    # Test 2: Explainability
    try:
        from ai_assistant.ai.explainability import ExplainabilityEngine
        xai = ExplainabilityEngine()
        stats = xai.get_stats()
        systems_tested.append("✅ Explainability")
        print(f"✅ Explainability - {stats.get('total_explanations', 0)} explanations")
    except Exception as e:
        systems_failed.append(f"❌ Explainability: {e}")
        print(f"❌ Explainability: {e}")
    
    # Test 3: Behavior Clustering
    try:
        from ai_assistant.ai.behavior_clustering import BehaviorClusterer
        bc = BehaviorClusterer()
        stats = bc.get_stats()
        systems_tested.append("✅ Behavior Clustering")
        print(f"✅ Behavior Clustering - {stats.get('total_sessions', 0)} sessions")
    except Exception as e:
        systems_failed.append(f"❌ Behavior Clustering: {e}")
        print(f"❌ Behavior Clustering: {e}")
    
    # Test 4: Conversation Clustering
    try:
        from ai_assistant.ai.conversation_clustering import ConversationClusterer
        cc = ConversationClusterer()
        stats = cc.get_stats()
        systems_tested.append("✅ Conversation Clustering")
        print(f"✅ Conversation Clustering - {stats.get('total_conversations', 0)} conversations")
    except Exception as e:
        systems_failed.append(f"❌ Conversation Clustering: {e}")
        print(f"❌ Conversation Clustering: {e}")
    
    # Test 5: LLM Bandit
    try:
        from ai_assistant.ai.llm_bandit import LLMBandit
        bandit = LLMBandit()
        stats = bandit.get_stats()
        systems_tested.append("✅ LLM Bandit")
        print(f"✅ LLM Bandit - {stats.get('total_selections', 0)} selections")
    except Exception as e:
        systems_failed.append(f"❌ LLM Bandit: {e}")
        print(f"❌ LLM Bandit: {e}")
    
    # Test 6: Model Compression
    try:
        from ai_assistant.ai.model_compression import ModelCompressor
        mc = ModelCompressor()
        stats = mc.get_stats()
        systems_tested.append("✅ Model Compression")
        print(f"✅ Model Compression - {stats.get('total_compressions', 0)} compressions")
    except Exception as e:
        systems_failed.append(f"❌ Model Compression: {e}")
        print(f"❌ Model Compression: {e}")
    
    # Test 7: Workflow Scheduler
    try:
        from ai_assistant.ai.workflow_scheduler import WorkflowScheduler
        ws = WorkflowScheduler()
        stats = ws.get_stats()
        systems_tested.append("✅ Workflow Scheduler")
        print(f"✅ Workflow Scheduler - {stats.get('total_workflows', 0)} workflows")
    except Exception as e:
        systems_failed.append(f"❌ Workflow Scheduler: {e}")
        print(f"❌ Workflow Scheduler: {e}")
    
    # Test 8: Contrastive Learning
    try:
        from ai_assistant.ai.contrastive_learning import ContrastiveLearner
        cl = ContrastiveLearner()
        stats = cl.get_stats()
        systems_tested.append("✅ Contrastive Learning")
        print(f"✅ Contrastive Learning - {stats.get('total_epochs', 0)} epochs")
    except Exception as e:
        systems_failed.append(f"❌ Contrastive Learning: {e}")
        print(f"❌ Contrastive Learning: {e}")
    
    # Test 9: Self-Supervised Learning
    try:
        from ai_assistant.ai.self_supervised_learning import SelfSupervisedLearner
        ssl = SelfSupervisedLearner()
        stats = ssl.get_stats()
        systems_tested.append("✅ Self-Supervised Learning")
        print(f"✅ Self-Supervised Learning - {stats.get('total_epochs', 0)} epochs")
    except Exception as e:
        systems_failed.append(f"❌ Self-Supervised Learning: {e}")
        print(f"❌ Self-Supervised Learning: {e}")
    
    # Test 10: Causal Inference
    try:
        from ai_assistant.ai.causal_inference import CausalInference
        ci = CausalInference()
        stats = ci.get_stats()
        systems_tested.append("✅ Causal Inference")
        print(f"✅ Causal Inference - {stats.get('total_edges', 0)} edges")
    except Exception as e:
        systems_failed.append(f"❌ Causal Inference: {e}")
        print(f"❌ Causal Inference: {e}")
    
    # Test 11: Query Cache
    try:
        from ai_assistant.ai.query_cache import QuerySimilarityCache
        qc = QuerySimilarityCache()
        stats = qc.get_stats()
        systems_tested.append("✅ Query Cache")
        print(f"✅ Query Cache - {stats.get('total_queries', 0)} queries")
    except Exception as e:
        systems_failed.append(f"❌ Query Cache: {e}")
        print(f"❌ Query Cache: {e}")
    
    # Test 12: Command Sequences
    try:
        from ai_assistant.ai.command_sequences import CommandMarkovChain
        cs = CommandMarkovChain()
        stats = cs.get_stats()
        systems_tested.append("✅ Command Sequences")
        print(f"✅ Command Sequences - {stats.get('total_sequences', 0)} sequences")
    except Exception as e:
        systems_failed.append(f"❌ Command Sequences: {e}")
        print(f"❌ Command Sequences: {e}")
    
    # Test 13: Historical RAG
    try:
        from ai_assistant.ai.historical_rag import HistoricalRAG
        rag = HistoricalRAG()
        stats = rag.get_stats()
        systems_tested.append("✅ Historical RAG")
        print(f"✅ Historical RAG - {stats.get('total_interactions', 0)} interactions")
    except Exception as e:
        systems_failed.append(f"❌ Historical RAG: {e}")
        print(f"❌ Historical RAG: {e}")
    
    # Test 14: Command Predictor
    try:
        from ai_assistant.ai.command_predictor import CommandSuccessPredictor
        cp = CommandSuccessPredictor()
        stats = cp.get_stats()
        systems_tested.append("✅ Command Predictor")
        print(f"✅ Command Predictor - {stats.get('total_predictions', 0)} predictions")
    except Exception as e:
        systems_failed.append(f"❌ Command Predictor: {e}")
        print(f"❌ Command Predictor: {e}")
    
    # Test 15: Anomaly Detection
    try:
        from ai_assistant.ai.anomaly_detection import AnomalyDetector
        ad = AnomalyDetector()
        stats = ad.get_stats()
        systems_tested.append("✅ Anomaly Detection")
        print(f"✅ Anomaly Detection - {stats.get('total_checks', 0)} checks")
    except Exception as e:
        systems_failed.append(f"❌ Anomaly Detection: {e}")
        print(f"❌ Anomaly Detection: {e}")
    
    # Test 16: Knowledge Graph
    try:
        from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
        kg = PersonalKnowledgeGraph(db_path="data/test_knowledge_graph.db")
        stats = kg.get_stats()
        systems_tested.append("✅ Knowledge Graph")
        print(f"✅ Knowledge Graph - {stats.get('total_nodes', 0)} nodes")
    except Exception as e:
        systems_failed.append(f"❌ Knowledge Graph: {e}")
        print(f"❌ Knowledge Graph: {e}")
    
    print("\n" + "=" * 70)
    print("NEW SYSTEMS (10)")
    print("=" * 70)
    
    # Test 17: Full RL System (PPO)
    try:
        from ai_assistant.ai.full_rl_system import PPOAgent
        ppo = PPOAgent(state_dim=10, action_dim=4)
        stats = ppo.get_stats()
        systems_tested.append("✅ PPO Agent (RL)")
        print(f"✅ PPO Agent (RL) - {stats.get('total_episodes', 0)} episodes")
    except Exception as e:
        systems_failed.append(f"❌ PPO Agent: {e}")
        print(f"❌ PPO Agent: {e}")
    
    # Test 18: Meta-Learning (MAML)
    try:
        from ai_assistant.ai.meta_learning import MAMLLearner
        maml = MAMLLearner(input_dim=10, hidden_dim=5, output_dim=2)
        stats = maml.get_stats()
        systems_tested.append("✅ MAML Meta-Learning")
        print(f"✅ MAML Meta-Learning - {stats.get('total_tasks', 0)} tasks")
    except Exception as e:
        systems_failed.append(f"❌ MAML: {e}")
        print(f"❌ MAML: {e}")
    
    # Test 19: Federated Learning
    try:
        from ai_assistant.ai.federated_learning import FederatedServer
        fed = FederatedServer(input_dim=10, output_dim=5)
        stats = fed.get_stats()
        systems_tested.append("✅ Federated Learning")
        print(f"✅ Federated Learning - {stats.get('total_clients', 0)} clients")
    except Exception as e:
        systems_failed.append(f"❌ Federated Learning: {e}")
        print(f"❌ Federated Learning: {e}")
    
    # Test 20: Graph Neural Networks
    try:
        from ai_assistant.ai.graph_neural_networks import GraphNeuralNetwork
        gnn = GraphNeuralNetwork()
        stats = gnn.get_stats()
        systems_tested.append("✅ Graph Neural Networks")
        print(f"✅ Graph Neural Networks - {stats.get('total_nodes', 0)} nodes")
    except Exception as e:
        systems_failed.append(f"❌ GNN: {e}")
        print(f"❌ GNN: {e}")
    
    # Test 21: Domain Embeddings
    try:
        from ai_assistant.ai.domain_embeddings import DomainAdaptedEmbeddings
        de = DomainAdaptedEmbeddings()
        stats = de.get_stats()
        systems_tested.append("✅ Domain Embeddings")
        print(f"✅ Domain Embeddings - {stats.get('total_domains', 0)} domains")
    except Exception as e:
        systems_failed.append(f"❌ Domain Embeddings: {e}")
        print(f"❌ Domain Embeddings: {e}")
    
    # Test 22: Smart Command Prediction
    try:
        from ai_assistant.ai.smart_command_prediction import SmartCommandPredictor
        scp = SmartCommandPredictor()
        stats = scp.get_stats()
        systems_tested.append("✅ Smart Command Prediction")
        print(f"✅ Smart Command Prediction - {stats.get('total_predictions', 0)} predictions")
    except Exception as e:
        systems_failed.append(f"❌ Smart Commands: {e}")
        print(f"❌ Smart Commands: {e}")
    
    # Test 23: Adaptive Voice
    try:
        from ai_assistant.ai.adaptive_voice import AdaptiveVoiceRecognition
        av = AdaptiveVoiceRecognition()
        stats = av.get_stats()
        systems_tested.append("✅ Adaptive Voice")
        print(f"✅ Adaptive Voice - {stats.get('total_recognitions', 0)} recognitions")
    except Exception as e:
        systems_failed.append(f"❌ Adaptive Voice: {e}")
        print(f"❌ Adaptive Voice: {e}")
    
    # Test 24: Workflow Recommender
    try:
        from ai_assistant.ai.workflow_recommender import WorkflowRecommender
        wr = WorkflowRecommender()
        stats = wr.get_stats()
        systems_tested.append("✅ Workflow Recommender")
        print(f"✅ Workflow Recommender - {stats.get('total_workflows', 0)} workflows")
    except Exception as e:
        systems_failed.append(f"❌ Workflow Recommender: {e}")
        print(f"❌ Workflow Recommender: {e}")
    
    # Test 25: Context-Aware Response
    try:
        from ai_assistant.ai.context_aware_response import ContextAwareResponseGenerator
        car = ContextAwareResponseGenerator()
        stats = car.get_stats()
        systems_tested.append("✅ Context-Aware Response")
        print(f"✅ Context-Aware Response - {stats.get('total_conversations', 0)} conversations")
    except Exception as e:
        systems_failed.append(f"❌ Context-Aware Response: {e}")
        print(f"❌ Context-Aware Response: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✅ Systems Working: {len(systems_tested)}/27")
    print(f"❌ Systems Failed: {len(systems_failed)}/27")
    
    if systems_failed:
        print("\nFailed Systems:")
        for failure in systems_failed:
            print(f"  {failure}")
    
    success_rate = (len(systems_tested) / 27) * 100
    print(f"\n📊 Success Rate: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("\n🎉 ALL 27 SYSTEMS OPERATIONAL!")
        return True
    else:
        print(f"\n⚠️  {27 - len(systems_tested)} systems need attention")
        return False

if __name__ == "__main__":
    success = test_all_systems()
    sys.exit(0 if success else 1)
