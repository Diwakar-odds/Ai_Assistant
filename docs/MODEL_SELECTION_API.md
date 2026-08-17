# Model Selection & Settings API

## 🎯 New Model Selection Endpoints

All endpoints are now available in the backend for users to choose their preferred AI models.

---

## 📡 API Endpoints

### 1. Get Available Models
**GET** `/api/models/available`

Get list of all available models with their providers and capabilities.

**Response:**
```json
{
  "success": true,
  "models": [
    {
      "id": "gemini-2.0-flash-exp",
      "name": "Gemini 2.0 Flash",
      "provider": "Google",
      "tier": "fast",
      "max_tokens": 8192,
      "cost_per_1k_tokens": 0.0001,
      "avg_latency_ms": 500,
      "capabilities": ["general", "multimodal", "coding"],
      "priority": 10,
      "description": "Fast, cost-effective model for general queries"
    },
    {
      "id": "gpt-3.5-turbo",
      "name": "GPT-3.5 Turbo",
      "provider": "OpenAI",
      "tier": "standard",
      "max_tokens": 4096,
      "cost_per_1k_tokens": 0.002,
      "avg_latency_ms": 1000,
      "capabilities": ["general", "coding", "reasoning"],
      "priority": 5,
      "description": "Balanced model for medium complexity tasks"
    },
    {
      "id": "gpt-4-turbo",
      "name": "GPT-4 Turbo",
      "provider": "OpenAI",
      "tier": "advanced",
      "max_tokens": 8192,
      "cost_per_1k_tokens": 0.03,
      "avg_latency_ms": 3000,
      "capabilities": ["general", "coding", "reasoning", "creativity", "math"],
      "priority": 1,
      "description": "Most capable model for complex tasks"
    }
  ],
  "by_provider": {
    "Google": [...],
    "OpenAI": [...],
    "Anthropic": [...]
  },
  "total_models": 5,
  "providers": ["Google", "OpenAI", "Anthropic"],
  "timestamp": "2026-01-12T..."
}
```

---

### 2. Get Model Preference
**GET** `/api/models/preference`

Get the user's current model preference.

**Response:**
```json
{
  "success": true,
  "preference": {
    "preferred_model": "gemini-2.0-flash-exp",
    "auto_route": true,
    "fallback_model": "gpt-3.5-turbo",
    "max_cost_per_query": 0.01,
    "updated_at": "2026-01-12T..."
  },
  "user": "john_doe",
  "timestamp": "2026-01-12T..."
}
```

---

### 3. Set Model Preference
**POST** `/api/models/preference`

Set the user's preferred model.

**Request:**
```json
{
  "preferred_model": "gpt-4-turbo",
  "auto_route": false,
  "fallback_model": "gpt-3.5-turbo",
  "max_cost_per_query": 0.05
}
```

**Response:**
```json
{
  "success": true,
  "preference": {
    "preferred_model": "gpt-4-turbo",
    "auto_route": false,
    "fallback_model": "gpt-3.5-turbo",
    "max_cost_per_query": 0.05,
    "updated_at": "2026-01-12T..."
  },
  "message": "Model preference saved: gpt-4-turbo",
  "timestamp": "2026-01-12T..."
}
```

**Parameters:**
- `preferred_model` (required): Model ID to use by default
- `auto_route` (optional, default: true): Whether to use intelligent routing
- `fallback_model` (optional): Model to use if preferred is unavailable
- `max_cost_per_query` (optional, default: 0.01): Maximum cost limit per query

---

### 4. Get Model Statistics
**GET** `/api/models/stats`

Get usage statistics for each model.

**Response:**
```json
{
  "success": true,
  "stats": {
    "routing": {
      "total_queries": 500,
      "tier_distribution": {
        "fast": {"count": 300, "percentage": 60},
        "standard": {"count": 150, "percentage": 30},
        "advanced": {"count": 50, "percentage": 10}
      },
      "total_cost_usd": 0.125,
      "estimated_savings": {
        "if_all_gpt4_usd": 1.50,
        "actual_cost_usd": 0.125,
        "saved_usd": 1.375,
        "savings_percentage": 91.7
      }
    }
  },
  "user": "john_doe",
  "timestamp": "2026-01-12T..."
}
```

---

### 5. Compare Models
**POST** `/api/models/compare`

Compare multiple models side by side.

**Request:**
```json
{
  "model_ids": ["gemini-2.0-flash-exp", "gpt-4-turbo", "claude-3-sonnet"]
}
```

**Response:**
```json
{
  "success": true,
  "comparison": [
    {
      "id": "gemini-2.0-flash-exp",
      "name": "Gemini 2.0 Flash",
      "tier": "fast",
      "cost_per_1k_tokens": 0.0001,
      "max_tokens": 8192,
      "avg_latency_ms": 500,
      "capabilities": ["general", "multimodal", "coding"]
    },
    {
      "id": "gpt-4-turbo",
      "name": "GPT-4 Turbo",
      "tier": "advanced",
      "cost_per_1k_tokens": 0.03,
      "max_tokens": 8192,
      "avg_latency_ms": 3000,
      "capabilities": ["general", "coding", "reasoning", "creativity", "math"]
    }
  ],
  "model_count": 2,
  "timestamp": "2026-01-12T..."
}
```

---

### 6. Get Providers
**GET** `/api/models/providers`

Get list of all available LLM providers.

**Response:**
```json
{
  "success": true,
  "providers": [
    {
      "id": "google",
      "name": "Google",
      "description": "Google Gemini models",
      "models": ["gemini-2.0-flash-exp", "gemini-2.0-pro", "gemini-1.5-pro"],
      "features": ["multimodal", "fast", "cost-effective"],
      "api_key_required": true,
      "status": "active"
    },
    {
      "id": "openai",
      "name": "OpenAI",
      "description": "GPT models from OpenAI",
      "models": ["gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o"],
      "features": ["versatile", "powerful", "coding"],
      "api_key_required": true,
      "status": "active"
    },
    {
      "id": "anthropic",
      "name": "Anthropic",
      "description": "Claude models",
      "models": ["claude-3-sonnet", "claude-3-opus", "claude-3-haiku"],
      "features": ["safe", "reasoning", "long-context"],
      "api_key_required": true,
      "status": "active"
    }
  ],
  "total_providers": 3,
  "timestamp": "2026-01-12T..."
}
```

---

## 💡 Frontend Integration Examples

### React/JavaScript Example

```javascript
// Settings Component
import React, { useState, useEffect } from 'react';

function ModelSettings() {
  const [models, setModels] = useState([]);
  const [preference, setPreference] = useState(null);
  const [selectedModel, setSelectedModel] = useState('');

  // Load available models
  useEffect(() => {
    fetch('/api/models/available')
      .then(r => r.json())
      .then(data => {
        setModels(data.models);
      });

    // Load current preference
    fetch('/api/models/preference')
      .then(r => r.json())
      .then(data => {
        setPreference(data.preference);
        setSelectedModel(data.preference.preferred_model);
      });
  }, []);

  // Save preference
  const handleSave = async () => {
    const response = await fetch('/api/models/preference', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        preferred_model: selectedModel,
        auto_route: true
      })
    });

    const data = await response.json();
    if (data.success) {
      alert('Model preference saved!');
    }
  };

  return (
    <div className="model-settings">
      <h2>AI Model Settings</h2>
      
      <div className="model-selector">
        <label>Choose your preferred model:</label>
        <select 
          value={selectedModel} 
          onChange={(e) => setSelectedModel(e.target.value)}
        >
          {models.map(model => (
            <optgroup key={model.provider} label={model.provider}>
              <option value={model.id}>
                {model.name} - ${model.cost_per_1k_tokens}/1K tokens
              </option>
            </optgroup>
          ))}
        </select>
      </div>

      <div className="model-grid">
        {models.map(model => (
          <div 
            key={model.id} 
            className={`model-card ${selectedModel === model.id ? 'selected' : ''}`}
            onClick={() => setSelectedModel(model.id)}
          >
            <h3>{model.name}</h3>
            <p className="provider">{model.provider}</p>
            <p className="description">{model.description}</p>
            
            <div className="specs">
              <span className="tier">{model.tier}</span>
              <span className="cost">${model.cost_per_1k_tokens}/1K</span>
              <span className="latency">{model.avg_latency_ms}ms</span>
            </div>

            <div className="capabilities">
              {model.capabilities.map(cap => (
                <span key={cap} className="badge">{cap}</span>
              ))}
            </div>
          </div>
        ))}
      </div>

      <button onClick={handleSave}>Save Preference</button>
    </div>
  );
}
```

### Grouped by Provider Example

```javascript
function ModelsByProvider() {
  const [modelsByProvider, setModelsByProvider] = useState({});

  useEffect(() => {
    fetch('/api/models/available')
      .then(r => r.json())
      .then(data => {
        setModelsByProvider(data.by_provider);
      });
  }, []);

  return (
    <div className="providers">
      {Object.entries(modelsByProvider).map(([provider, models]) => (
        <div key={provider} className="provider-section">
          <h2>{provider}</h2>
          <div className="models-list">
            {models.map(model => (
              <div key={model.id} className="model-item">
                <h3>{model.name}</h3>
                <p>Cost: ${model.cost_per_1k_tokens}/1K tokens</p>
                <p>Speed: {model.avg_latency_ms}ms</p>
                <button onClick={() => selectModel(model.id)}>
                  Use This Model
                </button>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## 🎨 Example CSS Styles

```css
.model-settings {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin: 20px 0;
}

.model-card {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.model-card:hover {
  border-color: #2196F3;
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.model-card.selected {
  border-color: #4CAF50;
  background: #f1f8f4;
}

.provider {
  color: #666;
  font-size: 0.9em;
  margin: 5px 0;
}

.specs {
  display: flex;
  gap: 10px;
  margin: 10px 0;
}

.tier {
  background: #2196F3;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8em;
}

.cost {
  background: #FF9800;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8em;
}

.latency {
  background: #9C27B0;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8em;
}

.capabilities {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 10px;
}

.badge {
  background: #E0E0E0;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75em;
}
```

---

## 📊 Model Comparison View

```javascript
function ModelComparison() {
  const [comparison, setComparison] = useState([]);

  const compareModels = async () => {
    const response = await fetch('/api/models/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model_ids: ['gemini-2.0-flash-exp', 'gpt-3.5-turbo', 'gpt-4-turbo']
      })
    });

    const data = await response.json();
    setComparison(data.comparison);
  };

  return (
    <div>
      <button onClick={compareModels}>Compare Models</button>
      
      <table className="comparison-table">
        <thead>
          <tr>
            <th>Model</th>
            <th>Tier</th>
            <th>Cost/1K</th>
            <th>Max Tokens</th>
            <th>Latency</th>
            <th>Capabilities</th>
          </tr>
        </thead>
        <tbody>
          {comparison.map(model => (
            <tr key={model.id}>
              <td>{model.name}</td>
              <td>{model.tier}</td>
              <td>${model.cost_per_1k_tokens}</td>
              <td>{model.max_tokens}</td>
              <td>{model.avg_latency_ms}ms</td>
              <td>{model.capabilities.join(', ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## ✅ Complete Implementation Checklist

- [x] API endpoint to list all models
- [x] API endpoint to get/set user preference
- [x] API endpoint to get model statistics
- [x] API endpoint to compare models
- [x] API endpoint to list providers
- [x] Models grouped by provider
- [x] Tier-based categorization
- [x] Cost and performance metrics
- [x] Capability tagging
- [x] User preference persistence
- [x] Auto-routing option
- [x] Fallback model support

---

## 🎯 Quick Test

```bash
# Get available models
curl http://localhost:5000/api/models/available

# Get providers
curl http://localhost:5000/api/models/providers

# Set preference
curl -X POST http://localhost:5000/api/models/preference \
  -H "Content-Type: application/json" \
  -d '{"preferred_model": "gpt-4-turbo", "auto_route": false}'

# Get preference
curl http://localhost:5000/api/models/preference

# Compare models
curl -X POST http://localhost:5000/api/models/compare \
  -H "Content-Type: application/json" \
  -d '{"model_ids": ["gemini-2.0-flash-exp", "gpt-4-turbo"]}'
```

---

**All model selection features are now integrated and ready to use! Users can choose any model from any provider through the settings menu.** 🎉
