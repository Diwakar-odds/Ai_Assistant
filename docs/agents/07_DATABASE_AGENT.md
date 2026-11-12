# 🗄️ 07: Database Agent (`database-001`)

## 📌 Overview
The **Database Agent** manages relational SQLite and SQL databases. It inspects schemas, tables, and column metadata, executes queries with read/write safety guardrails, blocks destructive operations (`DROP`, `TRUNCATE`, `ALTER`) unless explicitly authorized, and computes performance and structural analysis.

* **Agent ID:** `database-001`
* **Canonical Name:** Database Agent
* **Category:** `data`
* **Aliases:** `database`, `database-001`
* **Implementation File:** [`core_ai/src/ai_assistant/agents/data/database_agent.py`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/data/database_agent.py)
* **Base Class:** [`BaseAgent`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/base_agent.py)

---

## ⚙️ Trigger Keywords & Intent Matching
The agent automatically accepts tasks containing:
`sql`, `database`, `sqlite`, `query`, `schema`, `table`, `db`, `migration`, `select`, `insert`, `records`.

---

## 🛠️ Declared Capabilities & Methods

| Capability | Internal Method | Description | Security Guardrails |
| :--- | :--- | :--- | :--- |
| `query_database` | `_execute_query(task, ...)` | Executes `SELECT` statements and returns JSON-formatted record lists. | Parameterized queries, read-only default |
| `manage_schema` | `_get_schema(conn)` | Discovers all tables, columns, data types, and primary keys. | Non-locking PRAGMA table_info |
| `sql_analysis` | `execute(task)` | Inspects table cardinality and index health. | Query planner inspection |
| `db_migration` | `execute(task)` | Runs table creation and schema migration scripts. | Write-confirmation requirement |

---

## 📥 Input Parameter Schema (`task.params`)

```json
{
  "sql": "SELECT username, role, created_at FROM users WHERE role = ? LIMIT 10",
  "params": ["admin"],
  "db_name": "users | personal_knowledge | memory",
  "db_path": "D:/Projects/Ai_Assistant/memory.db",
  "allow_write": false
}
```

---

## 📤 Output Return Schema (`TaskResult`)

```python
TaskResult(
    success=True,
    output_path=None,
    data={
        "rows": [
            {"username": "admin", "role": "admin", "created_at": "2026-11-01T12:00:00"}
        ],
        "row_count": 1,
        "columns": ["username", "role", "created_at"],
        "db_path": "D:/Projects/Ai_Assistant/memory.db",
        "message": "Query returned 1 row(s)."
    }
)
```

---

## 🛡️ Error Handling & Fallback Strategy
* **Destructive SQL Protection:** All queries pass through `_DESTRUCTIVE_PATTERN` regex (`DROP`, `TRUNCATE`, `ALTER`, `ATTACH`, `DETACH`, `VACUUM`). Destructive operations are immediately rejected unless explicit administrative authorization is provided.
* **Write Gating:** Queries starting with `INSERT`, `UPDATE`, or `DELETE` require `params['allow_write'] == True`.
* **Path Resolution via Config:** If `db_name` is passed instead of absolute paths, the agent utilizes [`get_db_path_str`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/core/database_config.py) to resolve sanctioned sandbox database paths securely.

---

## 🚀 Execution Examples

### 1. Python Direct Invocation
```python
from ai_assistant.agents.loader import get_global_registry
from ai_assistant.agents.models import Task

registry = get_global_registry()
agent = registry.get_agent("database-001")

task = Task(
    task_id="db_inspect_01",
    description="Inspect table schemas in memory database",
    params={"db_name": "personal_knowledge"}
)
result = await agent.execute(task)
print(result.data["schema"])
```

### 2. REST API Invocation
```http
POST /api/agents/tasks
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>

{
  "agent_id": "database-001",
  "description": "Query recent user queries",
  "params": {
    "sql": "SELECT id, query_text, timestamp FROM queries ORDER BY id DESC LIMIT 5",
    "db_name": "memory"
  }
}
```
