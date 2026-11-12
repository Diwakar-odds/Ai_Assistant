# 🧠 14: Autonomous Learning Agent (`autonomous-001`)

## 📌 Overview
The **Autonomous Learning Agent** enables long-term adaptive memory, user preference tracking, behavior reflection, and autonomous skill generation. It observes conversations and workflow executions, routes memory entities to the `LearningDataRouter` and SQLite Personal Knowledge Graph, reflects on recurring patterns, and synthesizes reusable agent skills from observed user instructions.

* **Agent ID:** `autonomous-001`
* **Canonical Name:** Autonomous Learning Agent
* **Category:** `core`
* **Aliases:** `autonomous`, `autonomous-001`
* **Implementation File:** [`core_ai/src/ai_assistant/agents/core/autonomous_agent.py`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/core/autonomous_agent.py)
* **Base Class:** [`BaseAgent`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/base_agent.py)

---

## ⚙️ Trigger Keywords & Intent Matching
The agent automatically accepts tasks containing:
`remember`, `learn`, `reflect`, `what did i say`, `my preferences`, `save this`, `propose skill`, `skill`, `memorize`, `recall`.

---

## 🛠️ Declared Capabilities & Methods

| Capability | Internal Method | Description | Primary Engine |
| :--- | :--- | :--- | :--- |
| `memory_persistence` | `execute(task)` | Saves facts, preferences, or conversation turns to the long-term knowledge store. | `LearningDataRouter` / Memory DB |
| `behavior_learning` | `execute(task)` | Analyzes user correction patterns and updates behavioral weights. | Knowledge Graph Edge Weights |
| `reflection` | `_reflect(task)` | Evaluates recent interactions and summarizes accumulated user knowledge. | Unified LLM Reflection Prompt |
| `skill_generation` | `_generate_skill(task)` | Synthesizes a new reusable workflow or skill definition from repetitive tasks. | Skill Generator / DSL Builder |

---

## 📥 Input Parameter Schema (`task.params`)

```json
{
  "content": "User prefers concise Python code without type hints for quick prototypes.",
  "category": "preference | command | personal | workflow",
  "importance": 5,
  "speaker": "user",
  "workflow_history": [
    "User searched for stock prices",
    "User created an Excel sheet with stock prices",
    "User emailed the sheet to accounting"
  ]
}
```

---

## 📤 Output Return Schema (`TaskResult`)

```python
TaskResult(
    success=True,
    output_path=None,
    data={
        "status": "persisted",
        "memory_entry": {
            "timestamp": "2026-11-12T09:00:00Z",
            "content": "User prefers concise Python code...",
            "category": "preference",
            "importance": 5
        },
        "total_active_memories": 142,
        "knowledge_graph_updated": True,
        "message": "Memory explicitly saved to Knowledge Graph and memory store."
    }
)
```

---

## 🛡️ Error Handling & Fallback Strategy
* **Decoupled Router Architecture:** If `LearningDataRouter` fails to import or the SQLite database is temporarily locked, the agent gracefully falls back to an in-memory session memory buffer (`self._memories.append(entry)`), ensuring conversation flow is never broken.
* **Safe Skill Generation:** Autonomous skills proposed by this agent are marked as `draft` status and require user confirmation before being registered into the live tool dispatcher.

---

## 🚀 Execution Examples

### 1. Python Direct Invocation
```python
from ai_assistant.agents.loader import get_global_registry
from ai_assistant.agents.models import Task

registry = get_global_registry()
agent = registry.get_agent("autonomous-001")

task = Task(
    task_id="learn_pref_01",
    description="Remember that my preferred video editing software is DaVinci Resolve",
    params={
        "content": "Preferred video editing software: DaVinci Resolve",
        "category": "preference",
        "importance": 5
    }
)
result = await agent.execute(task)
print(result.data["message"])
```

### 2. REST API Invocation
```http
POST /api/agents/tasks
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>

{
  "agent_id": "autonomous-001",
  "description": "Reflect on what you have learned about my work habits",
  "params": {
    "action": "reflect"
  }
}
```
