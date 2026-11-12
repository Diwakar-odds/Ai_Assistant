# 🔍 02: Research Agent (`research-001`)

## 📌 Overview
The **Research Agent** is dedicated to real-time information retrieval, web searching, Wikipedia summary extraction, and direct webpage content scraping. It is designed to run asynchronously without stalling the backend event loop.

* **Agent ID:** `research-001`
* **Canonical Name:** Research Agent
* **Category:** `research`
* **Aliases:** `research`, `research-001`
* **Implementation File:** [`core_ai/src/ai_assistant/agents/research/research_agent.py`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/research/research_agent.py)
* **Base Class:** [`BaseAgent`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/base_agent.py)

---

## ⚙️ Trigger Keywords & Intent Matching
The agent automatically accepts tasks containing:
`research`, `search`, `find`, `lookup`, `wikipedia`, `scrape`, `investigate`, `google`, `facts`, `extract`.

---

## 🛠️ Declared Capabilities & Methods

| Capability | Internal Method | Description | Primary Engine |
| :--- | :--- | :--- | :--- |
| `web_search` | `_web_search(task)` | Executes web searches via DuckDuckGo HTML parser with User-Agent rotation. | DuckDuckGo HTML & BeautifulSoup |
| `wikipedia_summary` | `_search_wikipedia(task)` | Queries the official MediaWiki OpenSearch and Summary APIs for verified factual summaries. | Wikipedia REST API |
| `scrape_url` | `_scrape_url(task)` | Fetches a target URL, strips navigation/boilerplate, and extracts article text. | `requests` + `BeautifulSoup` |
| `research_topic` | `_web_search(task)` | Aggregates search results into a clean, markdown-formatted bibliography. | Multi-result aggregator |

---

## 📥 Input Parameter Schema (`task.params`)

```json
{
  "query": "Latest breakthroughs in autonomous agent architectures",
  "num_results": 5,
  "url": "https://example.com/article",
  "extract_text_only": true
}
```

---

## 📤 Output Return Schema (`TaskResult`)

```python
TaskResult(
    success=True,
    output_path=None,
    data={
        "query": "Quantum Computing",
        "results": [
            {
                "title": "Quantum Computing - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Quantum_computing",
                "description": "Quantum computing is a rapidly-emerging technology..."
            }
        ],
        "sources": ["https://en.wikipedia.org/wiki/Quantum_computing"],
        "summary": "Found 5 results for Quantum Computing",
        "output": "Markdown formatted summary with links..."
    }
)
```

---

## 🛡️ Error Handling & Fallback Strategy
* **Rate-Limit Resilience:** Network queries use a strict 10-second timeout (`requests.get(..., timeout=10)`).
* **HTML Sanitization:** Raw HTML is stripped of `<script>`, `<style>`, and navigation boilerplate before text extraction to protect tokens and memory.
* **Safe Fallback:** If search endpoints return empty or are throttled, the agent returns structured error metadata rather than unhandled network exceptions.

---

## 🚀 Execution Examples

### 1. Python Direct Invocation
```python
from ai_assistant.agents.loader import get_global_registry
from ai_assistant.agents.models import Task

registry = get_global_registry()
agent = registry.get_agent("research-001")

task = Task(
    task_id="res_01",
    description="Wikipedia search for Alan Turing",
    params={"query": "Alan Turing", "num_results": 3}
)
result = await agent.execute(task)
print(result.data["output"])
```

### 2. REST API Invocation
```http
POST /api/agents/tasks
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>

{
  "agent_id": "research-001",
  "description": "Find news about Python 3.13 release",
  "params": {
    "query": "Python 3.13 release date features",
    "num_results": 5
  }
}
```
