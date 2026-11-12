# 🌐 09: Web Agent (`web-001`)

## 📌 Overview
The **Web Agent** navigates websites, extracts dynamic page content, inspects HTML forms, monitors website status, and executes browser interactions. It features a lightweight, high-speed HTTP + BeautifulSoup mode for read-heavy scraping, as well as an interactive Selenium-driven BrowserAutomation mode for form filling and clicks.

* **Agent ID:** `web-001`
* **Canonical Name:** Web Agent
* **Category:** `web`
* **Aliases:** `web`, `web_01`, `web-001`
* **Implementation File:** [`core_ai/src/ai_assistant/agents/web/web_agent.py`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/web/web_agent.py)
* **Base Class:** [`BaseAgent`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/base_agent.py)

---

## ⚙️ Trigger Keywords & Intent Matching
The agent automatically accepts tasks containing:
`browser`, `website`, `browse`, `fill`, `form`, `click`, `selenium`, `monitor`, `webpage`, `visit`, `scrape dynamic`, `http://`, `https://`.

---

## 🛠️ Declared Capabilities & Methods

| Capability | Internal Method | Description | Primary Engine |
| :--- | :--- | :--- | :--- |
| `browse_web` | `_browse(task)` | Fetches HTML, extracts main body text, and lists links and form elements. | `requests` / `BeautifulSoup` |
| `interact_page` | `_interact(task)` | Executes browser clicks, scrolling, or element typing on target selectors. | Selenium / BrowserAutomation |
| `fill_form` | `_fill_form(task)` | Locates input fields by name/id and automatically populates form values. | Selenium / BrowserAutomation |
| `monitor_site` | `_monitor_site(task)` | Checks HTTP status codes, response latencies, and keyword presence. | `requests.head` / `get` |
| `scrape_dynamic` | `_browse(task)` | Executes JavaScript rendering in a headless browser to extract client-side SPAs. | Selenium Chrome |

---

## 📥 Input Parameter Schema (`task.params`)

```json
{
  "url": "https://news.ycombinator.com",
  "use_browser": true,
  "timeout": 15.0,
  "action": "click | type | scroll | inspect",
  "selector": "#submit-button",
  "form_data": {
    "username": "user123",
    "email": "user@example.com"
  }
}
```

---

## 📤 Output Return Schema (`TaskResult`)

```python
TaskResult(
    success=True,
    output_path=None,
    data={
        "url": "https://news.ycombinator.com",
        "title": "Hacker News",
        "text_length": 8420,
        "links_count": 30,
        "forms_count": 1,
        "sample_links": ["https://news.ycombinator.com/item?id=..."],
        "message": "Fetched page 'Hacker News' (8420 characters, 30 links)."
    }
)
```

---

## 🛡️ Error Handling & Fallback Strategy
* **Strict URL Sanitization:** Enforces `urlparse` validation. Rejects dangerous protocols (`file://`, `javascript:`, `data:`) to prevent SSRF and local file disclosure.
* **Dual Execution Mode:** Defaults to high-speed headless HTTP requests; only spins up full browser binaries when `use_browser=True` is explicitly commanded.
* **Timeout Gating:** All web requests enforce timeouts (default: 15s) to prevent hanging the assistant if an external web host stalls.

---

## 🚀 Execution Examples

### 1. Python Direct Invocation
```python
from ai_assistant.agents.loader import get_global_registry
from ai_assistant.agents.models import Task

registry = get_global_registry()
agent = registry.get_agent("web-001")

task = Task(
    task_id="web_browse_01",
    description="Browse python.org and get latest headlines",
    params={"url": "https://www.python.org"}
)
result = await agent.execute(task)
print(result.data["title"], result.data["sample_links"])
```

### 2. REST API Invocation
```http
POST /api/agents/tasks
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>

{
  "agent_id": "web-001",
  "description": "Monitor health and latency of API endpoint",
  "params": {
    "url": "https://httpbin.org/status/200"
  }
}
```
