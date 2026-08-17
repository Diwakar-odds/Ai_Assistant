# 🚀 Complete API Documentation - All 27 Learning Systems

## API Base URL
```
http://localhost:8000/api/learning
```

## Overview
**Total Endpoints**: 65+  
**Total Systems**: 27  
**Response Format**: JSON

---

## 1. Global Endpoints

### GET `/stats/all`
Get statistics from all 27 learning systems

**Response**:
```json
{
  "success": true,
  "timestamp": "2025-12-18T10:30:00",
  "systems": {
    "active_learning": {...},
    "ppo_agent": {...},
    ...
  },
  "total_systems": 27
}
```

---

## 2. Reinforcement Learning (PPO/A3C)

### POST `/rl/train`
Train PPO agent with experience

**Request**:
```json
{
  "state": [0.1, 0.2, ...],
  "action": 5,
  "reward": 1.5
}
```

### POST `/rl/select-action`
Select action using policy

**Request**: `List[float]` (state vector)

**Response**:
```json
{
  "success": true,
  "action": 3,
  "state": [...]
}
```

### GET `/rl/stats`
Get PPO statistics

---

## 3. Meta-Learning (MAML)

### POST `/meta/register-task`
Register new meta-learning task

**Request**:
```json
{
  "task_name": "user_preference_learning",
  "task_type": "classification",
  "support_data": [{...}, ...],
  "query_data": [{...}, ...]
}
```

### POST `/meta/adapt`
Quick adaptation to task (few-shot)

**Request**: Same as register-task

**Response**:
```json
{
  "success": true,
  "task_name": "user_preference_learning",
  "adaptation_loss": 0.345
}
```

### GET `/meta/stats`
Get meta-learning statistics

---

## 4. Federated Learning

### POST `/federated/register-client`
Register federated learning client

**Request**:
```json
{
  "client_id": "device_001",
  "model_params": {},
  "num_samples": 1000
}
```

### POST `/federated/train-round`
Perform training round with client updates

**Request**: `List[FederatedClientRequest]`

**Response**:
```json
{
  "success": true,
  "round_number": 5,
  "num_clients": 3,
  "global_params_size": 1024
}
```

### GET `/federated/stats`
Get federated learning statistics

---

## 5. Graph Neural Networks (GNN)

### POST `/gnn/add-node`
Add node to knowledge graph

**Request**:
```json
{
  "node_id": "user_123",
  "node_type": "user",
  "features": [0.1, 0.2, ...]
}
```

### POST `/gnn/add-edge`
Add edge between nodes

**Request**:
```json
{
  "source": "user_123",
  "target": "item_456",
  "edge_type": "interacts_with"
}
```

### POST `/gnn/train`
Train GNN model

**Query Params**: `epochs=10`

### POST `/gnn/predict-link`
Predict link probability

**Query Params**: `source=user_123&target=item_456`

**Response**:
```json
{
  "success": true,
  "link_probability": 0.87
}
```

### GET `/gnn/stats`
Get GNN statistics

---

## 6. Domain-Adapted Embeddings

### POST `/domain/register`
Register new domain

**Request**:
```json
{
  "domain_name": "medical",
  "examples": ["patient diagnosis", "treatment plan", ...]
}
```

### POST `/domain/train`
Train domain adapter

**Query Params**: `domain_name=medical&epochs=5`

### POST `/domain/embed`
Get embedding for text

**Query Params**: `text=patient%20condition&domain=medical`

**Response**:
```json
{
  "success": true,
  "embedding": [0.1, 0.2, ...],
  "dimension": 384
}
```

### POST `/domain/detect`
Auto-detect domain

**Query Params**: `text=user%20input`

**Response**:
```json
{
  "detected_domain": "medical"
}
```

### GET `/domain/stats`
Get domain statistics

---

## 7. Smart Command Prediction

### POST `/smart-commands/predict`
Predict next commands

**Request**:
```json
{
  "user_id": "user_123",
  "recent_commands": ["open file", "edit text"],
  "context": {"time": "morning"}
}
```

**Response**:
```json
{
  "success": true,
  "predictions": [
    {"command": "save file", "score": 0.85},
    {"command": "close window", "score": 0.62}
  ]
}
```

### POST `/smart-commands/autocomplete`
Autocomplete command

**Query Params**: `user_id=user_123&partial=ope`

**Response**:
```json
{
  "suggestions": ["open file", "open folder", "open recent"]
}
```

### POST `/smart-commands/log`
Log command usage

**Query Params**: `user_id=user_123&command=open%20file`

### GET `/smart-commands/stats`
Get prediction statistics

---

## 8. Adaptive Voice Recognition

### POST `/adaptive-voice/log`
Log recognition result

**Request**:
```json
{
  "user_id": "user_123",
  "text": "open the file",
  "confidence": 0.92,
  "was_correct": true
}
```

### POST `/adaptive-voice/correct`
Apply correction

**Query Params**: `user_id=user_123&recognized=open%20file&correct=open%20folder`

### GET `/adaptive-voice/suggestions`
Get correction suggestions

**Query Params**: `user_id=user_123&text=open%20fle`

**Response**:
```json
{
  "suggestions": ["open file", "open folder"]
}
```

### GET `/adaptive-voice/stats`
Get voice adaptation statistics

---

## 9. Workflow Recommender

### POST `/workflow/register`
Register workflow

**Query Params**: `name=backup&steps=[...]&description=...`

### POST `/workflow/recommend`
Get workflow recommendations

**Request**:
```json
{
  "user_id": "user_123",
  "current_tasks": ["task1", "task2"],
  "context": {"urgency": "high"}
}
```

**Response**:
```json
{
  "recommendations": [
    {
      "workflow": "quick_backup",
      "score": 0.89,
      "time_estimate": 120
    }
  ]
}
```

### POST `/workflow/automation`
Identify automation opportunities

**Query Params**: `user_id=user_123`

**Response**:
```json
{
  "opportunities": [
    {
      "pattern": "daily_backup",
      "frequency": 30,
      "time_saved": 600
    }
  ],
  "count": 5
}
```

### POST `/workflow/log-execution`
Log workflow execution

**Query Params**: `user_id=user_123&workflow_name=backup&duration=120&success=true`

### GET `/workflow/stats`
Get workflow statistics

---

## 10. Context-Aware Response Generation

### POST `/context/generate`
Generate intelligent response

**Request**:
```json
{
  "user_id": "user_123",
  "query": "How do I backup my files?",
  "context": {"recent_activity": "file_editing"}
}
```

**Response**:
```json
{
  "success": true,
  "response": "Based on your recent file editing, I recommend...",
  "user_id": "user_123"
}
```

### POST `/context/feedback`
Provide response feedback

**Query Params**: `user_id=user_123&response_id=resp_456&rating=5&feedback=helpful`

### GET `/context/conversation-history`
Get conversation history

**Query Params**: `user_id=user_123&limit=50`

**Response**:
```json
{
  "history": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "timestamp": "..."}
  ],
  "count": 50
}
```

### GET `/context/stats`
Get response generation statistics

---

## 11. Active Learning (Existing)

### POST `/active/add-sample`
Add unlabeled sample

### POST `/active/select-samples`
Select samples for labeling (uncertainty sampling)

### POST `/active/provide-label`
Provide label for sample

### GET `/active/stats`
Get active learning statistics

---

## 12. Explainability (XAI) (Existing)

### POST `/explainability/explain`
Get SHAP explanations

### POST `/explainability/attention`
Visualize attention weights

### POST `/explainability/counterfactual`
Generate counterfactual explanations

### GET `/explainability/stats`
Get XAI statistics

---

## 13. Behavior Clustering (Existing)

### POST `/behavior-clustering/add-session`
Add user session

### POST `/behavior-clustering/cluster`
Perform clustering

### GET `/behavior-clustering/stats`
Get clustering statistics

---

## 14. Conversation Clustering (Existing)

### POST `/conversation-clustering/add-conversation`
Add conversation

### POST `/conversation-clustering/cluster`
Cluster conversations

### GET `/conversation-clustering/stats`
Get conversation clustering statistics

---

## 15. LLM Bandit Selection (Existing)

### POST `/llm/select`
Select best LLM using Thompson Sampling

### POST `/llm/reward`
Update rewards

### GET `/llm/stats`
Get LLM selection statistics

---

## 16. Model Compression (Existing)

### POST `/compression/quantize`
Quantize model

### POST `/compression/prune`
Prune model parameters

### POST `/compression/distill`
Knowledge distillation

### GET `/compression/stats`
Get compression statistics

---

## 17. Workflow Scheduling (Existing)

### POST `/workflow/schedule`
Schedule workflow tasks

### GET `/workflow/status`
Get scheduling status

---

## 18. Contrastive Learning (Existing)

### POST `/contrastive/train`
Train with contrastive loss

### POST `/contrastive/embed`
Get contrastive embeddings

### GET `/contrastive/stats`
Get contrastive learning statistics

---

## 19. Self-Supervised Learning (Existing)

### POST `/self-supervised/train`
Self-supervised training

### POST `/self-supervised/predict`
Masked prediction

### GET `/self-supervised/stats`
Get self-supervised statistics

---

## 20. Causal Inference (Existing)

### POST `/causal/add-edge`
Add causal edge

### POST `/causal/intervene`
Perform intervention

### POST `/causal/counterfactual`
Counterfactual query

### GET `/causal/graph`
Export causal graph

### GET `/causal/stats`
Get causal inference statistics

---

## 21. Query Cache (Existing)

### POST `/query-cache/check`
Check cache for similar query

### POST `/query-cache/add`
Add query result to cache

### GET `/query-cache/stats`
Get cache statistics

---

## 22. Command Sequences (Existing)

### POST `/command-sequences/add`
Add command sequence

### POST `/command-sequences/predict`
Predict next command

### GET `/command-sequences/stats`
Get sequence statistics

---

## 23. Historical RAG (Existing)

### POST `/historical-rag/query`
Query with historical context

### POST `/historical-rag/add`
Add to historical context

### GET `/historical-rag/stats`
Get RAG statistics

---

## 24. Command Predictor (Existing)

### POST `/command-predictor/predict`
Predict command success

### POST `/command-predictor/feedback`
Provide success feedback

### GET `/command-predictor/stats`
Get predictor statistics

---

## 25. Anomaly Detection (Existing)

### POST `/anomaly/train`
Train anomaly detector

### POST `/anomaly/detect`
Detect anomalies

### GET `/anomaly/stats`
Get anomaly detection statistics

---

## 26-27. Knowledge Graph (Existing)

### GET `/knowledge-graph/export`
Export graph for visualization

### GET `/knowledge-graph/stats`
Get knowledge graph statistics

---

## Error Handling

All endpoints return consistent error format:

```json
{
  "detail": "Error message",
  "status_code": 500
}
```

**Common Status Codes**:
- `200` - Success
- `400` - Bad request
- `500` - Server error
- `503` - Service unavailable (systems not loaded)

---

## Usage Examples

### Python Client
```python
import requests

# Get all stats
response = requests.get("http://localhost:8000/api/learning/stats/all")
stats = response.json()

# Train RL agent
response = requests.post(
    "http://localhost:8000/api/learning/rl/train",
    json={"state": [0.1, 0.2], "action": 5, "reward": 1.5}
)

# Generate context-aware response
response = requests.post(
    "http://localhost:8000/api/learning/context/generate",
    json={"user_id": "user_123", "query": "Help me backup files"}
)
```

### JavaScript Client
```javascript
// Get smart command predictions
const response = await fetch('http://localhost:8000/api/learning/smart-commands/predict', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    user_id: 'user_123',
    recent_commands: ['open file', 'edit'],
    context: {}
  })
});
const predictions = await response.json();
```

---

## Testing

Start API server:
```bash
cd f:/bn/assitant
uvicorn ai_assistant.services.learning_api:router --reload --port 8000
```

Test endpoint:
```bash
curl http://localhost:8000/api/learning/stats/all
```

---

**Total Systems**: 27  
**Total Endpoints**: 65+  
**Status**: Production Ready ✅

*Last Updated*: December 18, 2025
