"""
Graph Neural Networks for Knowledge Graph Reasoning
GCN/GAT for graph-based learning and reasoning
"""

import numpy as np
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False


if TORCH_AVAILABLE:
    class GraphConvLayer(nn.Module):
        """Single Graph Convolutional Layer (GCN)"""
        
        def __init__(self, in_features: int, out_features: int):
            super().__init__()
            self.linear = nn.Linear(in_features, out_features)
        
        def forward(self, x, adj):
            """
            x: Node features [num_nodes, in_features]
            adj: Adjacency matrix [num_nodes, num_nodes]
            """
            # Message passing: aggregate neighbor features
            support = self.linear(x)
            output = torch.mm(adj, support)
            return output
    
    
    class GraphAttentionLayer(nn.Module):
        """Graph Attention Layer (GAT)"""
        
        def __init__(self, in_features: int, out_features: int, num_heads: int = 4):
            super().__init__()
            self.num_heads = num_heads
            self.out_features = out_features
            
            # Multi-head attention
            self.W = nn.Linear(in_features, out_features * num_heads)
            self.a = nn.Parameter(torch.zeros(size=(2 * out_features, 1)))
            nn.init.xavier_uniform_(self.a.data)
            
            self.leakyrelu = nn.LeakyReLU(0.2)
        
        def forward(self, x, adj):
            """Apply graph attention"""
            h = self.W(x)  # [num_nodes, out_features * num_heads]
            num_nodes = h.size(0)
            
            # Attention mechanism
            a_input = self._prepare_attentional_mechanism_input(h)
            e = self.leakyrelu(torch.matmul(a_input, self.a).squeeze(2))
            
            # Mask attention to neighbors only
            zero_vec = -9e15 * torch.ones_like(e)
            attention = torch.where(adj > 0, e, zero_vec)
            attention = F.softmax(attention, dim=1)
            
            # Apply attention
            h_prime = torch.matmul(attention, h)
            
            return h_prime
        
        def _prepare_attentional_mechanism_input(self, h):
            """Prepare input for attention computation"""
            num_nodes = h.size(0)
            h_repeated = h.repeat(num_nodes, 1, 1)
            h_repeated_T = h.repeat(1, num_nodes).view(num_nodes, num_nodes, -1)
            a_input = torch.cat([h_repeated, h_repeated_T], dim=-1)
            return a_input
    
    
    class GNNModel(nn.Module):
        """Complete GNN model with multiple layers"""
        
        def __init__(self, 
                     input_dim: int, 
                     hidden_dim: int, 
                     output_dim: int,
                     num_layers: int = 2,
                     use_attention: bool = False):
            super().__init__()
            
            self.use_attention = use_attention
            self.layers = nn.ModuleList()
            
            # First layer
            if use_attention:
                self.layers.append(GraphAttentionLayer(input_dim, hidden_dim))
            else:
                self.layers.append(GraphConvLayer(input_dim, hidden_dim))
            
            # Hidden layers
            for _ in range(num_layers - 2):
                if use_attention:
                    self.layers.append(GraphAttentionLayer(hidden_dim, hidden_dim))
                else:
                    self.layers.append(GraphConvLayer(hidden_dim, hidden_dim))
            
            # Output layer
            if use_attention:
                self.layers.append(GraphAttentionLayer(hidden_dim, output_dim))
            else:
                self.layers.append(GraphConvLayer(hidden_dim, output_dim))
        
        def forward(self, x, adj):
            """Forward pass through GNN"""
            for i, layer in enumerate(self.layers):
                x = layer(x, adj)
                if i < len(self.layers) - 1:  # No activation on last layer
                    x = F.relu(x)
            return x


class GraphNeuralNetwork:
    """
    Graph Neural Network system for knowledge graph reasoning
    """
    
    def __init__(self,
                 node_feature_dim: int = 64,
                 hidden_dim: int = 128,
                 output_dim: int = 32,
                 use_attention: bool = True,
                 db_path: str = "data/gnn.db"):
        
        self.node_feature_dim = node_feature_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.db_path = db_path
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Initialize node embeddings for all cases
        self.node_embeddings = {}
        
        if TORCH_AVAILABLE:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = GNNModel(
                node_feature_dim, 
                hidden_dim, 
                output_dim,
                use_attention=use_attention
            ).to(self.device)
            self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        else:
            # Fallback: simple message passing (node_embeddings already initialized)
            pass
        
        if NETWORKX_AVAILABLE:
            self.graph = nx.DiGraph()
        else:
            self.adjacency = {}
        
        self.node_features = {}
        self.trained = False
        
        logger.info(f"GNN initialized: {node_feature_dim}D features, attention={use_attention}")
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    node_id TEXT PRIMARY KEY,
                    features TEXT,
                    embedding TEXT,
                    node_type TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_edges (
                    source TEXT,
                    target TEXT,
                    edge_type TEXT,
                    weight REAL,
                    PRIMARY KEY (source, target, edge_type)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    num_epochs INTEGER,
                    final_loss REAL,
                    num_nodes INTEGER,
                    num_edges INTEGER
                )
            """)
    
    def add_node(self, node_id: str, features: np.ndarray, node_type: str = "entity"):
        """Add node to graph"""
        self.node_features[node_id] = features
        
        if NETWORKX_AVAILABLE:
            self.graph.add_node(node_id, features=features, node_type=node_type)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO graph_nodes (node_id, features, node_type)
                VALUES (?, ?, ?)
            """, (node_id, json.dumps(features.tolist()), node_type))
    
    def add_edge(self, source: str, target: str, edge_type: str = "relates_to", weight: float = 1.0):
        """Add edge to graph"""
        if NETWORKX_AVAILABLE:
            self.graph.add_edge(source, target, edge_type=edge_type, weight=weight)
        else:
            if source not in self.adjacency:
                self.adjacency[source] = []
            self.adjacency[source].append((target, edge_type, weight))
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO graph_edges (source, target, edge_type, weight)
                VALUES (?, ?, ?, ?)
            """, (source, target, edge_type, weight))
    
    def get_adjacency_matrix(self) -> Tuple[np.ndarray, List[str]]:
        """Get adjacency matrix and node list"""
        if NETWORKX_AVAILABLE:
            nodes = list(self.graph.nodes())
            adj_matrix = nx.adjacency_matrix(self.graph, nodelist=nodes).todense()
            return np.array(adj_matrix, dtype=np.float32), nodes
        else:
            nodes = list(self.node_features.keys())
            n = len(nodes)
            adj_matrix = np.zeros((n, n), dtype=np.float32)
            
            node_to_idx = {node: i for i, node in enumerate(nodes)}
            for source, neighbors in self.adjacency.items():
                if source in node_to_idx:
                    for target, _, weight in neighbors:
                        if target in node_to_idx:
                            adj_matrix[node_to_idx[source], node_to_idx[target]] = weight
            
            return adj_matrix, nodes
    
    def get_feature_matrix(self, nodes: List[str]) -> np.ndarray:
        """Get node feature matrix"""
        features = []
        for node in nodes:
            if node in self.node_features:
                features.append(self.node_features[node])
            else:
                features.append(np.zeros(self.node_feature_dim))
        return np.array(features, dtype=np.float32)
    
    def train(self, num_epochs: int = 100, task: str = "node_classification"):
        """Train GNN model"""
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not available, skipping training")
            return
        
        # Get graph data
        adj_matrix, nodes = self.get_adjacency_matrix()
        feature_matrix = self.get_feature_matrix(nodes)
        
        if len(nodes) == 0:
            logger.warning("No nodes in graph, skipping training")
            return
        
        # Convert to tensors
        adj_tensor = torch.FloatTensor(adj_matrix).to(self.device)
        features_tensor = torch.FloatTensor(feature_matrix).to(self.device)
        
        # Normalize adjacency matrix (add self-loops and normalize)
        adj_tensor = adj_tensor + torch.eye(adj_tensor.size(0)).to(self.device)
        degree = torch.sum(adj_tensor, dim=1)
        degree_inv_sqrt = torch.pow(degree, -0.5)
        degree_inv_sqrt[torch.isinf(degree_inv_sqrt)] = 0
        norm_adj = degree_inv_sqrt.unsqueeze(1) * adj_tensor * degree_inv_sqrt.unsqueeze(0)
        
        self.model.train()
        
        for epoch in range(num_epochs):
            # Forward pass
            embeddings = self.model(features_tensor, norm_adj)
            
            # Self-supervised loss: reconstruct adjacency
            reconstructed_adj = torch.mm(embeddings, embeddings.t())
            reconstructed_adj = torch.sigmoid(reconstructed_adj)
            
            loss = F.binary_cross_entropy(reconstructed_adj, adj_tensor)
            
            # Backward pass
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
            
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}: Loss={loss.item():.4f}")
        
        # Save embeddings
        self.model.eval()
        with torch.no_grad():
            final_embeddings = self.model(features_tensor, norm_adj)
            for i, node in enumerate(nodes):
                embedding = final_embeddings[i].cpu().numpy()
                self.node_embeddings[node] = embedding
                
                # Update database
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        UPDATE graph_nodes SET embedding = ? WHERE node_id = ?
                    """, (json.dumps(embedding.tolist()), node))
        
        # Save training run
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO training_runs (timestamp, num_epochs, final_loss, num_nodes, num_edges)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                num_epochs,
                loss.item(),
                len(nodes),
                len(self.graph.edges()) if NETWORKX_AVAILABLE else 0
            ))
        
        self.trained = True
        logger.info(f"Training complete: {len(nodes)} nodes, loss={loss.item():.4f}")
    
    def get_node_embedding(self, node_id: str) -> Optional[np.ndarray]:
        """Get learned embedding for a node"""
        return self.node_embeddings.get(node_id)
    
    def predict_link(self, source: str, target: str) -> float:
        """Predict likelihood of link between two nodes"""
        if source not in self.node_embeddings or target not in self.node_embeddings:
            return 0.0
        
        source_emb = self.node_embeddings[source]
        target_emb = self.node_embeddings[target]
        
        # Cosine similarity
        similarity = np.dot(source_emb, target_emb) / (
            np.linalg.norm(source_emb) * np.linalg.norm(target_emb) + 1e-8
        )
        
        return float(similarity)
    
    def find_similar_nodes(self, node_id: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Find most similar nodes based on embeddings"""
        if node_id not in self.node_embeddings:
            return []
        
        query_emb = self.node_embeddings[node_id]
        similarities = []
        
        for other_id, other_emb in self.node_embeddings.items():
            if other_id != node_id:
                sim = np.dot(query_emb, other_emb) / (
                    np.linalg.norm(query_emb) * np.linalg.norm(other_emb) + 1e-8
                )
                similarities.append((other_id, float(sim)))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get GNN statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM graph_nodes")
            num_nodes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM graph_edges")
            num_edges = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM training_runs")
            training_runs = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(final_loss) FROM training_runs")
            avg_loss = cursor.fetchone()[0]
        
        return {
            'num_nodes': num_nodes,
            'num_edges': num_edges,
            'training_runs': training_runs,
            'avg_loss': float(avg_loss) if avg_loss else 0,
            'trained': self.trained,
            'num_embeddings': len(self.node_embeddings),
            'torch_available': TORCH_AVAILABLE,
            'networkx_available': NETWORKX_AVAILABLE
        }
