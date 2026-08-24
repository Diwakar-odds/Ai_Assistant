"""
Federated Learning System
Privacy-preserving distributed learning across devices
"""

import numpy as np
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import logging
import hashlib

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class ClientUpdate:
    """Update from a federated learning client"""
    client_id: str
    round_number: int
    model_update: Dict[str, np.ndarray]
    num_samples: int
    loss: float
    timestamp: str


@dataclass
class FederatedRound:
    """Single round of federated learning"""
    round_number: int
    num_clients: int
    aggregated_loss: float
    convergence_delta: float
    timestamp: str


if TORCH_AVAILABLE:
    class FederatedModel(nn.Module):
        """Simple model for federated learning"""
        
        def __init__(self, input_dim: int, output_dim: int, hidden_dim: int = 64):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, output_dim)
            )
        
        def forward(self, x):
            return self.net(x)


class FederatedClient:
    """
    Client in federated learning system
    Trains on local data without sharing raw data
    """
    
    def __init__(self, 
                 client_id: str,
                 input_dim: int,
                 output_dim: int,
                 local_data: Optional[List] = None):
        
        self.client_id = client_id
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.local_data = local_data or []
        
        if TORCH_AVAILABLE:
            self.local_model = FederatedModel(input_dim, output_dim)
            self.optimizer = torch.optim.SGD(self.local_model.parameters(), lr=0.01)
        else:
            # Fallback: simple weight averaging
            self.local_weights = np.random.randn(output_dim, input_dim) * 0.01
        
        logger.info(f"Client {client_id} initialized with {len(self.local_data)} samples")
    
    def set_model_parameters(self, parameters: Dict[str, np.ndarray]):
        """Update local model with global parameters"""
        if TORCH_AVAILABLE:
            state_dict = {}
            for name, param in parameters.items():
                state_dict[name] = torch.FloatTensor(param)
            self.local_model.load_state_dict(state_dict, strict=False)
        else:
            if 'weights' in parameters:
                self.local_weights = parameters['weights']
    
    def train_local_model(self, num_epochs: int = 1) -> ClientUpdate:
        """Train model on local data"""
        if len(self.local_data) == 0:
            return self._empty_update()
        
        if not TORCH_AVAILABLE:
            return self._simple_train(num_epochs)
        
        self.local_model.train()
        total_loss = 0
        
        for epoch in range(num_epochs):
            for x, y in self.local_data:
                x_tensor = torch.FloatTensor(x).unsqueeze(0)
                y_tensor = torch.FloatTensor(y).unsqueeze(0)
                
                # Forward pass
                pred = self.local_model(x_tensor)
                loss = nn.functional.mse_loss(pred, y_tensor)
                
                # Backward pass
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                
                total_loss += loss.item()
        
        avg_loss = total_loss / (len(self.local_data) * num_epochs)
        
        # Get model updates
        model_update = {}
        for name, param in self.local_model.named_parameters():
            model_update[name] = param.data.cpu().numpy()
        
        return ClientUpdate(
            client_id=self.client_id,
            round_number=0,  # Set by server
            model_update=model_update,
            num_samples=len(self.local_data),
            loss=avg_loss,
            timestamp=datetime.now().isoformat()
        )
    
    def _simple_train(self, num_epochs: int) -> ClientUpdate:
        """Simplified training for fallback"""
        for epoch in range(num_epochs):
            for x, y in self.local_data:
                pred = np.dot(self.local_weights, x)
                error = y - pred
                self.local_weights += 0.01 * np.outer(error, x)
        
        return ClientUpdate(
            client_id=self.client_id,
            round_number=0,
            model_update={'weights': self.local_weights},
            num_samples=len(self.local_data),
            loss=0.0,
            timestamp=datetime.now().isoformat()
        )
    
    def _empty_update(self) -> ClientUpdate:
        """Return empty update when no data"""
        return ClientUpdate(
            client_id=self.client_id,
            round_number=0,
            model_update={},
            num_samples=0,
            loss=0.0,
            timestamp=datetime.now().isoformat()
        )
    
    def add_local_data(self, data: List[Tuple[np.ndarray, np.ndarray]]):
        """Add more data to client's local dataset"""
        self.local_data.extend(data)


class FederatedServer:
    """
    Central server coordinating federated learning
    Aggregates client updates without accessing raw data
    """
    
    def __init__(self,
                 input_dim: int,
                 output_dim: int,
                 aggregation_strategy: str = 'fedavg',
                 db_path: str = "data/federated_learning.db"):
        
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.aggregation_strategy = aggregation_strategy
        self.db_path = db_path
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        if TORCH_AVAILABLE:
            self.global_model = FederatedModel(input_dim, output_dim)
        else:
            self.global_weights = np.random.randn(output_dim, input_dim) * 0.01
        
        self.clients = {}
        self.round_number = 0
        self.round_history = []
        
        logger.info(f"Federated Server initialized: {aggregation_strategy}")
    
    def _init_database(self):
        """Initialize database for federated learning"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    client_id TEXT PRIMARY KEY,
                    registered_at TEXT,
                    total_samples INTEGER,
                    total_updates INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rounds (
                    round_number INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    num_clients INTEGER,
                    aggregated_loss REAL,
                    convergence_delta REAL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS client_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    round_number INTEGER,
                    client_id TEXT,
                    timestamp TEXT,
                    num_samples INTEGER,
                    loss REAL,
                    FOREIGN KEY (round_number) REFERENCES rounds(round_number),
                    FOREIGN KEY (client_id) REFERENCES clients(client_id)
                )
            """)
    
    def register_client(self, client: FederatedClient):
        """Register a new client"""
        self.clients[client.client_id] = client
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO clients (client_id, registered_at, total_samples, total_updates)
                VALUES (?, ?, ?, ?)
            """, (
                client.client_id,
                datetime.now().isoformat(),
                len(client.local_data),
                0
            ))
        
        logger.info(f"Client {client.client_id} registered")
    
    def get_global_parameters(self) -> Dict[str, np.ndarray]:
        """Get current global model parameters"""
        if TORCH_AVAILABLE:
            params = {}
            for name, param in self.global_model.named_parameters():
                params[name] = param.data.cpu().numpy()
            return params
        else:
            return {'weights': self.global_weights}
    
    def federated_averaging(self, client_updates: List[ClientUpdate]) -> Dict[str, np.ndarray]:
        """
        FedAvg: Aggregate client updates weighted by number of samples
        """
        if len(client_updates) == 0:
            return self.get_global_parameters()
        
        total_samples = sum(update.num_samples for update in client_updates)
        
        if not TORCH_AVAILABLE:
            # Simple averaging
            weighted_sum = np.zeros_like(self.global_weights)
            for update in client_updates:
                if 'weights' in update.model_update:
                    weight = update.num_samples / total_samples
                    weighted_sum += weight * update.model_update['weights']
            return {'weights': weighted_sum}
        
        # Average all parameters
        aggregated = {}
        
        # Get parameter names from first update
        param_names = list(client_updates[0].model_update.keys())
        
        for param_name in param_names:
            weighted_sum = np.zeros_like(client_updates[0].model_update[param_name])
            
            for update in client_updates:
                if param_name in update.model_update:
                    weight = update.num_samples / total_samples
                    weighted_sum += weight * update.model_update[param_name]
            
            aggregated[param_name] = weighted_sum
        
        return aggregated
    
    def federated_round(self, 
                       participating_clients: Optional[List[str]] = None,
                       local_epochs: int = 1) -> FederatedRound:
        """
        Execute one round of federated learning
        """
        self.round_number += 1
        
        # Select clients
        if participating_clients is None:
            participating_clients = list(self.clients.keys())
        
        # Distribute global model to clients
        global_params = self.get_global_parameters()
        for client_id in participating_clients:
            if client_id in self.clients:
                self.clients[client_id].set_model_parameters(global_params)
        
        # Collect client updates
        client_updates = []
        for client_id in participating_clients:
            if client_id in self.clients:
                update = self.clients[client_id].train_local_model(local_epochs)
                update.round_number = self.round_number
                client_updates.append(update)
                
                # Save update to database
                self._save_client_update(update)
        
        # Aggregate updates
        if self.aggregation_strategy == 'fedavg':
            aggregated_params = self.federated_averaging(client_updates)
        else:
            aggregated_params = self.federated_averaging(client_updates)  # Default
        
        # Update global model
        old_params = self.get_global_parameters()
        
        if TORCH_AVAILABLE:
            state_dict = {}
            for name, param in aggregated_params.items():
                state_dict[name] = torch.FloatTensor(param)
            self.global_model.load_state_dict(state_dict, strict=False)
        else:
            self.global_weights = aggregated_params['weights']
        
        # Compute convergence metrics
        convergence_delta = self._compute_convergence_delta(old_params, aggregated_params)
        avg_loss = np.mean([update.loss for update in client_updates])
        
        # Create round summary
        round_summary = FederatedRound(
            round_number=self.round_number,
            num_clients=len(client_updates),
            aggregated_loss=avg_loss,
            convergence_delta=convergence_delta,
            timestamp=datetime.now().isoformat()
        )
        
        self._save_round(round_summary)
        self.round_history.append(round_summary)
        
        logger.info(f"Round {self.round_number}: Loss={avg_loss:.4f}, Delta={convergence_delta:.6f}")
        
        return round_summary
    
    def _compute_convergence_delta(self, 
                                   old_params: Dict[str, np.ndarray],
                                   new_params: Dict[str, np.ndarray]) -> float:
        """Compute parameter change between rounds"""
        total_delta = 0
        count = 0
        
        for key in old_params:
            if key in new_params:
                delta = np.linalg.norm(new_params[key] - old_params[key])
                total_delta += delta
                count += 1
        
        return total_delta / max(count, 1)
    
    def _save_client_update(self, update: ClientUpdate):
        """Save client update to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO client_updates 
                (round_number, client_id, timestamp, num_samples, loss)
                VALUES (?, ?, ?, ?, ?)
            """, (
                update.round_number,
                update.client_id,
                update.timestamp,
                update.num_samples,
                update.loss
            ))
            
            # Update client stats
            conn.execute("""
                UPDATE clients 
                SET total_updates = total_updates + 1
                WHERE client_id = ?
            """, (update.client_id,))
    
    def _save_round(self, round_summary: FederatedRound):
        """Save round summary to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO rounds 
                (round_number, timestamp, num_clients, aggregated_loss, convergence_delta)
                VALUES (?, ?, ?, ?, ?)
            """, (
                round_summary.round_number,
                round_summary.timestamp,
                round_summary.num_clients,
                round_summary.aggregated_loss,
                round_summary.convergence_delta
            ))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get federated learning statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM clients")
            total_clients = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM rounds")
            total_rounds = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(aggregated_loss) FROM rounds")
            avg_loss = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(convergence_delta) FROM rounds")
            avg_delta = cursor.fetchone()[0]
        
        return {
            'total_clients': total_clients,
            'total_rounds': total_rounds,
            'avg_loss': float(avg_loss) if avg_loss else 0,
            'avg_convergence_delta': float(avg_delta) if avg_delta else 0,
            'current_round': self.round_number,
            'torch_available': TORCH_AVAILABLE
        }


class SecureAggregation:
    """
    Secure aggregation for differential privacy
    Adds noise to protect individual client contributions
    """
    
    def __init__(self, noise_scale: float = 0.1, clipping_norm: float = 1.0):
        self.noise_scale = noise_scale
        self.clipping_norm = clipping_norm
    
    def clip_update(self, update: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Clip update to bounded norm"""
        clipped = {}
        for key, value in update.items():
            norm = np.linalg.norm(value)
            if norm > self.clipping_norm:
                clipped[key] = value * (self.clipping_norm / norm)
            else:
                clipped[key] = value
        return clipped
    
    def add_noise(self, aggregated: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Add Gaussian noise for differential privacy"""
        noisy = {}
        for key, value in aggregated.items():
            noise = np.random.normal(0, self.noise_scale, value.shape)
            noisy[key] = value + noise
        return noisy
    
    def secure_aggregate(self, 
                        updates: List[Dict[str, np.ndarray]],
                        weights: Optional[List[float]] = None) -> Dict[str, np.ndarray]:
        """Securely aggregate updates with differential privacy"""
        if weights is None:
            weights = [1.0 / len(updates)] * len(updates)
        
        # Clip each update
        clipped_updates = [self.clip_update(u) for u in updates]
        
        # Weighted average
        aggregated = {}
        param_names = list(clipped_updates[0].keys())
        
        for param_name in param_names:
            weighted_sum = np.zeros_like(clipped_updates[0][param_name])
            for update, weight in zip(clipped_updates, weights):
                weighted_sum += weight * update[param_name]
            aggregated[param_name] = weighted_sum
        
        # Add noise
        noisy_aggregated = self.add_noise(aggregated)
        
        return noisy_aggregated


# Example usage
def example_federated_learning():
    """Example of federated learning with multiple clients"""
    
    # Create server
    server = FederatedServer(input_dim=10, output_dim=5)
    
    # Create clients with different local data
    for i in range(5):
        # Each client has different local data distribution
        local_data = [(np.random.randn(10), np.random.randn(5)) for _ in range(20)]
        client = FederatedClient(f"client_{i}", 10, 5, local_data)
        server.register_client(client)
    
    # Run federated learning rounds
    for round_num in range(10):
        round_summary = server.federated_round(local_epochs=2)
        logger.info(f"Round {round_num}: {round_summary}")
    
    return server
