# 💬 08: Communication Agent (`comm-001`)

## 📌 Overview
The **Communication Agent** handles digital correspondence and scheduling: reading, searching, drafting, and dispatching emails (Gmail API), sending WhatsApp messages, viewing Google Calendar schedules, and booking meetings. To protect user privacy and prevent unintentional real-world communication, the agent enforces strict human-in-the-loop confirmation guardrails.

* **Agent ID:** `comm-001`
* **Canonical Name:** Communication Agent
* **Category:** `communication`
* **Aliases:** `comm`, `communication`, `communication_01`, `comm-001`
* **Implementation File:** [`core_ai/src/ai_assistant/agents/communication/communication_agent.py`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/communication/communication_agent.py)
* **Base Class:** [`BaseAgent`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/base_agent.py)

---

## ⚙️ Trigger Keywords & Intent Matching
The agent automatically accepts tasks containing:
`email`, `gmail`, `send`, `message`, `whatsapp`, `calendar`, `meeting`, `schedule`, `appointment`, `inbox`, `post`, `social`.

---

## 🛠️ Declared Capabilities & Methods

| Capability | Internal Method | Description | Security Requirements |
| :--- | :--- | :--- | :--- |
| `send_email` | `_send_email(task)` | Sends emails via Gmail API or SMTP integration. | Requires `confirmed=True` |
| `draft_email` | `_draft_email(task)` | Synthesizes a high-quality email draft with recipient and subject without sending. | Safe / No confirmation needed |
| `send_message` | `_send_message(task)` | Dispatches WhatsApp or messaging app text to a phone number. | Requires `confirmed=True` |
| `manage_calendar` | `_get_calendar_events(task)` | Reads scheduled calendar appointments and today's agenda. | Safe / Read-only |
| `schedule_meeting` | `_create_calendar_event(task)` | Books an appointment or meeting with start/end time and attendees. | Requires `confirmed=True` |
| `post_social` | `_post_social(task)` | Posts social media updates or status updates. | Requires `confirmed=True` |

---

## 📥 Input Parameter Schema (`task.params`)

```json
{
  "to": "client@example.com",
  "phone": "+1234567890",
  "subject": "Project Status Update",
  "body": "Here is the summary of this week's progress...",
  "start_time": "2026-11-15T10:00:00Z",
  "end_time": "2026-11-15T11:00:00Z",
  "confirmed": true
}
```

---

## 📤 Output Return Schema (`TaskResult`)

### Safe Draft / Confirmation Request:
```python
TaskResult(
    success=True,
    output_path=None,
    data={
        "status": "confirmation_required",
        "to": "client@example.com",
        "subject": "Project Status Update",
        "draft_body": "Here is the summary...",
        "message": "Email draft created. Please confirm before sending."
    }
)
```

### Executed Dispatch:
```python
TaskResult(
    success=True,
    data={
        "status": "sent",
        "message_id": "msg_987654321",
        "recipient": "client@example.com",
        "message": "Email sent successfully to client@example.com."
    }
)
```

---

## 🛡️ Error Handling & Fallback Strategy
* **Explicit Human Confirmation Guardrail:** Any destructive or real-world dispatch checks `self._is_confirmed(task)`. If `confirmed` is False or missing, the agent drafts the message and pauses with `status: confirmation_required`.
* **LLM Drafting with Static Template Fallback:** If LLM tokens or API connection is down, `_draft_email()` falls back to a clean template layout (`Subject`, `Greeting`, `Context`, `Signature`) so user workflows continue uninterrupted.

---

## 🚀 Execution Examples

### 1. Python Direct Invocation
```python
from ai_assistant.agents.loader import get_global_registry
from ai_assistant.agents.models import Task

registry = get_global_registry()
agent = registry.get_agent("comm-001")

task = Task(
    task_id="comm_draft_01",
    description="Draft an email to team about tomorrow's sync",
    params={
        "to": "team@company.com",
        "subject": "Sprint Sync Tomorrow",
        "body": "Reminder: We will discuss multi-agent architecture."
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
  "agent_id": "comm-001",
  "description": "Send an email update to supervisor",
  "params": {
    "to": "supervisor@example.com",
    "subject": "Documentation Completed",
    "body": "All 14 agent documents have been published.",
    "confirmed": true
  }
}
```
