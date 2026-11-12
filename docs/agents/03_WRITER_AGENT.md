# ✍️ 03: Writer Agent (`writer-001`)

## 📌 Overview
The **Writer Agent** produces professional written content across various formats, including technical essays, blog posts, formal business emails, video scripts, proofreading reports, and concise summaries. It interfaces with the unified LLM engine (cloud or local fallback).

* **Agent ID:** `writer-001`
* **Canonical Name:** Writer Agent
* **Category:** `writer`
* **Aliases:** `writer`, `writer-001`
* **Implementation File:** [`core_ai/src/ai_assistant/agents/writer/writer_agent.py`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/writer/writer_agent.py)
* **Base Class:** [`BaseAgent`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/base_agent.py)

---

## ⚙️ Trigger Keywords & Intent Matching
The agent automatically accepts tasks containing:
`write`, `draft`, `essay`, `article`, `blog`, `summarize`, `summary`, `proofread`, `script`, `content`, `story`, `rewrite`, `copyedit`.

---

## 🛠️ Declared Capabilities & Methods

| Capability | Internal Method | Description | Primary Engine |
| :--- | :--- | :--- | :--- |
| `write_article` | `execute(task)` | Generates long-form structured articles with headings, introduction, and conclusion. | Unified LLM (Gemini / OpenAI / Local) |
| `summarize_text` | `execute(task)` | Condenses lengthy input texts or previous agent outputs into concise executive bullet points. | Unified LLM / Heuristic Fallback |
| `draft_email` | `execute(task)` | Formulates polite, professional email drafts tailored to specific recipients and goals. | Unified LLM |
| `proofread` | `execute(task)` | Identifies spelling, grammatical, and stylistic flaws and generates an edited version. | Unified LLM |
| `creative_writing` | `execute(task)` | Creates narrative fiction, creative copy, storytelling, or speech scripts. | Unified LLM |

---

## 📥 Input Parameter Schema (`task.params`)

```json
{
  "topic": "The Impact of Local LLMs on Enterprise Privacy",
  "type": "article | email | summary | script | proofread",
  "tone": "professional | casual | academic | persuasive",
  "length": 600,
  "source_text": "Text to summarize or proofread...",
  "filename": "Enterprise_LLM_Whitepaper.md"
}
```

---

## 📤 Output Return Schema (`TaskResult`)

```python
TaskResult(
    success=True,
    output_path="D:/Projects/Ai_Assistant/outputs/Enterprise_LLM_Whitepaper.md",
    artifacts=["D:/Projects/Ai_Assistant/outputs/Enterprise_LLM_Whitepaper.md"],
    data={
        "content": "Full generated text markdown...",
        "summary": "First 240 characters...",
        "output": "Full generated text markdown...",
        "type": "article",
        "used_llm": True,
        "message": "Writing task completed (article)."
    }
)
```

---

## 🛡️ Error Handling & Fallback Strategy
* **Zero-Failure Offline Fallback:** If internet access is lost or cloud LLM quotas are exhausted, `_generate_fallback_content()` generates a clean, deterministic structured draft based on template outlines rather than crashing.
* **Upstream Data Ingestion:** If `source_text` is omitted for a summary task, `_extract_upstream_text()` automatically pulls output from upstream chained research tasks.
* **Deterministic Mock Mode:** Supports `config['mock_mode'] = True` or `params['mock'] = True` for high-speed automated unit testing without consuming API tokens.

---

## 🚀 Execution Examples

### 1. Python Direct Invocation
```python
from ai_assistant.agents.loader import get_global_registry
from ai_assistant.agents.models import Task

registry = get_global_registry()
agent = registry.get_agent("writer-001")

task = Task(
    task_id="write_01",
    description="Draft an email proposing an AI partnership",
    params={
        "type": "email",
        "topic": "Partnership Proposal for AI Assistant",
        "tone": "professional"
    }
)
result = await agent.execute(task)
print(result.data["content"])
```

### 2. REST API Invocation
```http
POST /api/agents/tasks
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>

{
  "agent_id": "writer-001",
  "description": "Write a 500-word article on edge AI processing",
  "params": {
    "type": "article",
    "tone": "technical",
    "length": 500
  }
}
```
