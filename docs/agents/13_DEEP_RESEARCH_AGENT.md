# 🔬 13: Deep Research Agent (`deep-research-001`)

## 📌 Overview
The **Deep Research Agent** is a multi-step investigation engine. Given an open-ended or complex topic, it breaks the prompt down into sub-queries, executes parallel asynchronous web searches, scrapes and sanitizes multiple sources, analyzes findings, and employs an LLM to synthesize an exhaustive, citation-backed markdown research whitepaper.

* **Agent ID:** `deep-research-001`
* **Canonical Name:** Deep Research Agent
* **Category:** `research`
* **Aliases:** `deep_research`, `deep-research`, `deep-research-001`
* **Implementation File:** [`core_ai/src/ai_assistant/agents/research/deep_research_agent.py`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/research/deep_research_agent.py)
* **Base Class:** [`BaseAgent`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/base_agent.py)

---

## ⚙️ Trigger Keywords & Intent Matching
The agent automatically accepts tasks containing:
`deep research`, `synthesize`, `comprehensive analysis`, `market research`, `in-depth`, `multi-source`, `literature survey`.

---

## 🛠️ Declared Capabilities & Methods

| Capability | Internal Method | Description | Primary Engine |
| :--- | :--- | :--- | :--- |
| `deep_research` | `execute(task)` | Complete end-to-end investigation, query expansion, concurrent scraping, and report synthesis. | Pipeline Orchestrator |
| `multi_source_scrape` | `_parallel_search_and_scrape(queries)` | Executes parallel async DuckDuckGo queries and scrapes target articles simultaneously. | `asyncio.gather` + `requests` |
| `social_synthesis` | `_synthesize_results(topic, raw_data)` | Correlates cross-source claims, identifies contradictions, and synthesizes final report. | Unified LLM (Gemini / OpenAI) |

---

## 📥 Input Parameter Schema (`task.params`)

```json
{
  "query": "Quantum Key Distribution algorithms and post-quantum cryptography standards",
  "max_queries": 3,
  "sources_per_query": 3,
  "output_path": "D:/Projects/Ai_Assistant/outputs/QKD_Research_Report.md"
}
```

---

## 📤 Output Return Schema (`TaskResult`)

```python
TaskResult(
    success=True,
    output_path="D:/Projects/Ai_Assistant/outputs/deep_research_a1b2c3d4.md",
    artifacts=["D:/Projects/Ai_Assistant/outputs/deep_research_a1b2c3d4.md"],
    data={
        "synthesis": "# Quantum Key Distribution Research...\n\n### 1. Executive Summary...",
        "summary": "First 600 characters of the whitepaper...",
        "raw_data_count": 8,
        "sources": [
            "https://en.wikipedia.org/wiki/Quantum_key_distribution",
            "https://csrc.nist.gov/projects/post-quantum-cryptography"
        ],
        "message": "Deep research completed across 8 source(s)."
    },
    metadata={
        "used_llm": True,
        "queries": [
            "quantum key distribution algorithms",
            "post-quantum cryptography standards nist",
            "qkd practical implementations"
        ]
    }
)
```

---

## 🛡️ Error Handling & Fallback Strategy
* **Parallel Asynchronous Scraping:** Queries and web scraping are dispatched in parallel using `asyncio.to_thread` and `asyncio.gather(..., return_exceptions=True)`, ensuring that one slow website never blocks the rest of the research pipeline.
* **Deterministic Synthesis Fallback:** If LLM access is interrupted, `_synthesize_results()` compiles an organized, well-formatted bibliography and extracted snippet report directly from the collected website text.

---

## 🚀 Execution Examples

### 1. Python Direct Invocation
```python
from ai_assistant.agents.loader import get_global_registry
from ai_assistant.agents.models import Task

registry = get_global_registry()
agent = registry.get_agent("deep-research-001")

task = Task(
    task_id="deep_res_01",
    description="Deep research on the state of Solid State Batteries in 2026",
    params={"query": "Solid State Batteries automotive commercialization 2026"}
)
result = await agent.execute(task)
print(result.output_path)
```

### 2. REST API Invocation
```http
POST /api/agents/tasks
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>

{
  "agent_id": "deep-research-001",
  "description": "Comprehensive market research on edge AI hardware",
  "params": {
    "query": "Edge AI NPUs comparison Apple Google Qualcomm Intel"
  }
}
```
