"""
Full Reinforcement Learning System (PPO/A3C)
Deep RL with policy gradients for complex decision making
"""

import numpy as np
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from collections import deque
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

# Try to import PyTorch, fall back to numpy if unavailable
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim
    from torch.distributions import Categorical
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available, using simplified RL implementation")


@dataclass
class Experience:
    """Single experience tuple for RL"""
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool
    log_prob: Optional[float] = None
    value: Optional[float] = None


@dataclass
class Episode:
    """Complete episode trajectory"""
    states: List[np.ndarray]
    actions: List[int]
    rewards: List[float]
    log_probs: List[float]
    values: List[float]
    total_reward: float
    length: int


if TORCH_AVAILABLE:
    class ActorCriticNetwork(nn.Module):
        """
        Actor-Critic neural network for PPO
        Actor outputs action probabilities, Critic outputs state value
        """
        def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 128):
            super().__init__()
            
            # Shared layers
            self.shared = nn.Sequential(
                nn.Linear(state_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU()
            )
            
            # Actor head (policy)
            self.actor = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.ReLU(),
                nn.Linear(hidden_dim // 2, action_dim),
                nn.Softmax(dim=-1)
            )
            
            # Critic head (value function)
            self.critic = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.ReLU(),
                nn.Linear(hidden_dim // 2, 1)
            )
        
        def forward(self, state):
            """Forward pass through network"""
            shared_features = self.shared(state)
            action_probs = self.actor(shared_features)
            state_value = self.critic(shared_features)
            return action_probs, state_value
        
        def act(self, state):
            """Select action based on current policy"""
            action_probs, state_value = self.forward(state)
            dist = Categorical(action_probs)
            action = dist.sample()
            log_prob = dist.log_prob(action)
            return action.item(), log_prob.item(), state_value.item()
        
        def evaluate(self, states, actions):
            """Evaluate actions taken in given states"""
            action_probs, state_values = self.forward(states)
            dist = Categorical(action_probs)
            action_log_probs = dist.log_prob(actions)
            dist_entropy = dist.entropy()
            return action_log_probs, state_values.squeeze(), dist_entropy


class PPOAgent:
    """
    Proximal Policy Optimization agent
    State-of-the-art policy gradient method with clipped objective
    """
    
    def __init__(self, 
                 state_dim: int,
                 action_dim: int,
                 hidden_dim: int = 128,
                 lr: float = 3e-4,
                 gamma: float = 0.99,
                 epsilon_clip: float = 0.2,
                 k_epochs: int = 4,
                 db_path: str = "data/rl_ppo.db"):
        
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon_clip = epsilon_clip
        self.k_epochs = k_epochs
        self.db_path = db_path
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        if TORCH_AVAILABLE:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.policy = ActorCriticNetwork(state_dim, action_dim, hidden_dim).to(self.device)
            self.optimizer = optim.Adam(self.policy.parameters(), lr=lr)
            self.policy_old = ActorCriticNetwork(state_dim, action_dim, hidden_dim).to(self.device)
            self.policy_old.load_state_dict(self.policy.state_dict())
            self.mse_loss = nn.MSELoss()
        else:
            # Fallback to simple table-based policy
            self.q_table = {}
            self.action_counts = {}
        
        self.memory = []
        self.episode_rewards = deque(maxlen=100)
        
        logger.info(f"PPO Agent initialized: {state_dim}D state, {action_dim} actions")
    
    def _init_database(self):
        """Initialize SQLite database for experience storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    total_reward REAL,
                    length INTEGER,
                    avg_value REAL,
                    policy_loss REAL,
                    value_loss REAL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_id INTEGER,
                    step INTEGER,
                    state TEXT,
                    action INTEGER,
                    reward REAL,
                    next_state TEXT,
                    done INTEGER,
                    FOREIGN KEY (episode_id) REFERENCES episodes(id)
                )
            """)
    
    def select_action(self, state: np.ndarray) -> Tuple[int, float, float]:
        """
        Select action using current policy
        Returns: (action, log_prob, state_value)
        """
        if TORCH_AVAILABLE:
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            with torch.no_grad():
                action, log_prob, value = self.policy_old.act(state_tensor)
            return action, log_prob, value
        else:
            # Simple epsilon-greedy for fallback
            state_key = tuple(np.round(state, 2))
            if state_key not in self.q_table:
                self.q_table[state_key] = np.zeros(self.action_dim)
            
            if np.random.random() < 0.1:  # exploration
                action = np.random.randint(self.action_dim)
            else:
                action = np.argmax(self.q_table[state_key])
            
            return action, 0.0, 0.0
    
    def store_transition(self, state, action, reward, next_state, done, log_prob=None, value=None):
        """Store experience in memory"""
        experience = Experience(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done,
            log_prob=log_prob,
            value=value
        )
        self.memory.append(experience)
    
    def compute_returns(self, rewards: List[float], dones: List[bool]) -> List[float]:
        """Compute discounted returns"""
        returns = []
        R = 0
        for reward, done in zip(reversed(rewards), reversed(dones)):
            if done:
                R = 0
            R = reward + self.gamma * R
            returns.insert(0, R)
        return returns
    
    def update(self):
        """Update policy using PPO algorithm"""
        if len(self.memory) == 0:
            return {}
        
        if not TORCH_AVAILABLE:
            # Simple Q-learning update for fallback
            for exp in self.memory:
                state_key = tuple(np.round(exp.state, 2))
                next_state_key = tuple(np.round(exp.next_state, 2))
                
                if state_key not in self.q_table:
                    self.q_table[state_key] = np.zeros(self.action_dim)
                if next_state_key not in self.q_table:
                    self.q_table[next_state_key] = np.zeros(self.action_dim)
                
                # Q-learning update
                lr = 0.1
                target = exp.reward + self.gamma * np.max(self.q_table[next_state_key]) * (1 - exp.done)
                self.q_table[state_key][exp.action] += lr * (target - self.q_table[state_key][exp.action])
            
            self.memory.clear()
            return {'policy_loss': 0, 'value_loss': 0, 'entropy': 0}
        
        # Convert memory to tensors
        states = torch.FloatTensor(np.array([exp.state for exp in self.memory])).to(self.device)
        actions = torch.LongTensor([exp.action for exp in self.memory]).to(self.device)
        old_log_probs = torch.FloatTensor([exp.log_prob for exp in self.memory]).to(self.device)
        
        # Compute returns and advantages
        rewards = [exp.reward for exp in self.memory]
        dones = [exp.done for exp in self.memory]
        returns = self.compute_returns(rewards, dones)
        returns = torch.FloatTensor(returns).to(self.device)
        
        # Normalize returns
        returns = (returns - returns.mean()) / (returns.std() + 1e-8)
        
        # PPO update for k epochs
        total_policy_loss = 0
        total_value_loss = 0
        total_entropy = 0
        
        for _ in range(self.k_epochs):
            # Evaluate actions
            log_probs, state_values, entropy = self.policy.evaluate(states, actions)
            
            # Compute advantages
            advantages = returns - state_values.detach()
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
            
            # Compute PPO loss
            ratios = torch.exp(log_probs - old_log_probs.detach())
            surr1 = ratios * advantages
            surr2 = torch.clamp(ratios, 1 - self.epsilon_clip, 1 + self.epsilon_clip) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()
            
            # Compute value loss
            value_loss = self.mse_loss(state_values, returns)
            
            # Total loss with entropy bonus
            loss = policy_loss + 0.5 * value_loss - 0.01 * entropy.mean()
            
            # Backpropagation
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.policy.parameters(), 0.5)
            self.optimizer.step()
            
            total_policy_loss += policy_loss.item()
            total_value_loss += value_loss.item()
            total_entropy += entropy.mean().item()
        
        # Update old policy
        self.policy_old.load_state_dict(self.policy.state_dict())
        
        # Clear memory
        self.memory.clear()
        
        return {
            'policy_loss': total_policy_loss / self.k_epochs,
            'value_loss': total_value_loss / self.k_epochs,
            'entropy': total_entropy / self.k_epochs
        }
    
    def save_episode(self, episode: Episode):
        """Save episode to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO episodes (timestamp, total_reward, length, avg_value)
                VALUES (?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                episode.total_reward,
                episode.length,
                np.mean(episode.values) if episode.values else 0
            ))
            episode_id = cursor.lastrowid
            
            # Save experiences
            for i, (state, action, reward, log_prob) in enumerate(zip(
                episode.states, episode.actions, episode.rewards, episode.log_probs
            )):
                next_state = episode.states[i + 1] if i + 1 < len(episode.states) else state
                done = 1 if i == len(episode.states) - 1 else 0
                
                cursor.execute("""
                    INSERT INTO experiences (episode_id, step, state, action, reward, next_state, done)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    episode_id,
                    i,
                    json.dumps(state.tolist()),
                    action,
                    reward,
                    json.dumps(next_state.tolist()),
                    done
                ))
        
        self.episode_rewards.append(episode.total_reward)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM episodes")
            total_episodes = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(total_reward), AVG(length) FROM episodes")
            avg_reward, avg_length = cursor.fetchone()
        
        return {
            'total_episodes': total_episodes,
            'avg_reward': float(avg_reward) if avg_reward else 0,
            'avg_length': float(avg_length) if avg_length else 0,
            'recent_avg_reward': float(np.mean(self.episode_rewards)) if self.episode_rewards else 0,
            'memory_size': len(self.memory),
            'torch_available': TORCH_AVAILABLE
        }


class A3CWorker:
    """
    Asynchronous Advantage Actor-Critic Worker
    For parallel training across multiple environments
    """
    
    def __init__(self, 
                 worker_id: int,
                 global_network: Optional['ActorCriticNetwork'],
                 state_dim: int,
                 action_dim: int,
                 gamma: float = 0.99):
        
        self.worker_id = worker_id
        self.gamma = gamma
        
        if TORCH_AVAILABLE and global_network is not None:
            self.local_network = ActorCriticNetwork(state_dim, action_dim)
            self.local_network.load_state_dict(global_network.state_dict())
            self.global_network = global_network
        else:
            self.local_network = None
            self.global_network = None
        
        self.episode_count = 0
        self.step_count = 0
        
        logger.info(f"A3C Worker {worker_id} initialized")
    
    def sync_with_global(self):
        """Synchronize local network with global network"""
        if self.local_network and self.global_network:
            self.local_network.load_state_dict(self.global_network.state_dict())
    
    def compute_gradient(self, trajectory: List[Experience]) -> Dict[str, Any]:
        """Compute gradients from trajectory"""
        if not TORCH_AVAILABLE or not self.local_network:
            return {}
        
        states = torch.FloatTensor(np.array([exp.state for exp in trajectory]))
        actions = torch.LongTensor([exp.action for exp in trajectory])
        rewards = [exp.reward for exp in trajectory]
        
        # Compute returns
        returns = []
        R = 0
        for reward in reversed(rewards):
            R = reward + self.gamma * R
            returns.insert(0, R)
        returns = torch.FloatTensor(returns)
        
        # Forward pass
        action_probs, values = self.local_network(states)
        values = values.squeeze()
        
        # Compute advantages
        advantages = returns - values.detach()
        
        # Policy loss
        dist = Categorical(action_probs)
        log_probs = dist.log_prob(actions)
        policy_loss = -(log_probs * advantages).mean()
        
        # Value loss
        value_loss = F.mse_loss(values, returns)
        
        # Entropy bonus
        entropy = dist.entropy().mean()
        
        # Total loss
        loss = policy_loss + 0.5 * value_loss - 0.01 * entropy
        
        return {
            'loss': loss,
            'policy_loss': policy_loss.item(),
            'value_loss': value_loss.item(),
            'entropy': entropy.item()
        }


class RLEnvironmentWrapper:
    """
    Wrapper for converting assistant tasks into RL environments
    Maps commands/queries to states and actions
    """
    
    def __init__(self, state_dim: int = 10, action_dim: int = 5):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.current_state = np.zeros(state_dim)
        self.step_count = 0
        self.max_steps = 100
    
    def reset(self) -> np.ndarray:
        """Reset environment to initial state"""
        self.current_state = np.random.randn(self.state_dim) * 0.1
        self.step_count = 0
        return self.current_state.copy()
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Take action in environment
        Returns: (next_state, reward, done, info)
        """
        self.step_count += 1
        
        # Simulate state transition
        self.current_state += np.random.randn(self.state_dim) * 0.1
        self.current_state = np.clip(self.current_state, -3, 3)
        
        # Compute reward (example: prefer certain actions)
        reward = -np.abs(action - 2) + np.random.randn() * 0.1  # Prefer action 2
        
        # Check if done
        done = self.step_count >= self.max_steps
        
        info = {'step': self.step_count}
        
        return self.current_state.copy(), reward, done, info
    
    def encode_command(self, command: str) -> np.ndarray:
        """Encode text command into state vector"""
        # Simple hash-based encoding
        state = np.zeros(self.state_dim)
        for i, char in enumerate(command[:self.state_dim]):
            state[i] = ord(char) / 255.0
        return state
    
    def decode_action(self, action: int) -> str:
        """Decode action to command"""
        actions_map = {
            0: "search",
            1: "open",
            2: "close",
            3: "execute",
            4: "wait"
        }
        return actions_map.get(action, "unknown")


# Example usage and training function
def train_ppo_agent(num_episodes: int = 100, steps_per_episode: int = 50):
    """Train PPO agent on environment"""
    env = RLEnvironmentWrapper(state_dim=10, action_dim=5)
    agent = PPOAgent(state_dim=10, action_dim=5)
    
    for episode in range(num_episodes):
        state = env.reset()
        episode_reward = 0
        
        states, actions, rewards, log_probs, values = [], [], [], [], []
        
        for step in range(steps_per_episode):
            action, log_prob, value = agent.select_action(state)
            next_state, reward, done, _ = env.step(action)
            
            agent.store_transition(state, action, reward, next_state, done, log_prob, value)
            
            states.append(state)
            actions.append(action)
            rewards.append(reward)
            log_probs.append(log_prob)
            values.append(value)
            
            episode_reward += reward
            state = next_state
            
            if done:
                break
        
        # Update policy
        losses = agent.update()
        
        # Save episode
        ep = Episode(
            states=states,
            actions=actions,
            rewards=rewards,
            log_probs=log_probs,
            values=values,
            total_reward=episode_reward,
            length=len(states)
        )
        agent.save_episode(ep)
        
        if episode % 10 == 0:
            logger.info(f"Episode {episode}: Reward={episode_reward:.2f}, Losses={losses}")
    
    return agent
