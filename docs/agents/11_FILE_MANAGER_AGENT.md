# 📁 11: File Manager Agent (`file-001`)

## 📌 Overview
The **File Manager Agent** executes safe file system organization, listing, searching, batch renaming, moving, copying, and archiving. It categorizes cluttered folders (Downloads, Desktop, Documents) by MIME/extension type into subfolders (`images/`, `documents/`, `audio/`, `code/`), creates timestamped directory backups, and searches files across local drives.

* **Agent ID:** `file-001`
* **Canonical Name:** File Manager Agent
* **Category:** `file`
* **Aliases:** `file`, `file_01`, `file_manager`, `file-001`
* **Implementation File:** [`core_ai/src/ai_assistant/agents/file/file_manager_agent.py`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/file/file_manager_agent.py)
* **Base Class:** [`BaseAgent`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/base_agent.py)

---

## ⚙️ Trigger Keywords & Intent Matching
The agent automatically accepts tasks containing:
`file`, `folder`, `directory`, `organize`, `rename`, `move`, `copy`, `backup`, `cleanup`, `list files`, `find file`.

---

## 🛠️ Declared Capabilities & Methods

| Capability | Internal Method | Description | Primary Engine |
| :--- | :--- | :--- | :--- |
| `organize_files` | `_organize_files(task)` | Groups files into extension categories (`images`, `documents`, `code`, etc.). | `shutil` / FileAutomation |
| `search_files` | `_search_files(task)` | Recursively finds files matching wildcard patterns, names, or extensions. | `pathlib.Path.rglob` |
| `list_files` | `_list_files(task)` | Returns detailed directory trees with file sizes and modification timestamps. | `os.scandir` |
| `rename_files` | `_rename_files(task)` | Performs single or batch pattern-based renaming with rollback protection. | `os.replace` |
| `move_files` | `_move_files(task)` | Moves or copies files safely to target directories. | `shutil.move` / `copy2` |
| `backup_files` | `_backup_files(task)` | Compresses target directories into timestamped `.zip` archives. | `shutil.make_archive` |

---

## 📥 Input Parameter Schema (`task.params`)

```json
{
  "directory": "D:/Downloads",
  "source": "D:/Projects/Ai_Assistant/outputs/report.pdf",
  "destination": "D:/Documents/Reports/report.pdf",
  "pattern": "*.png",
  "query": "budget_2026",
  "recursive": true
}
```

---

## 📤 Output Return Schema (`TaskResult`)

```python
TaskResult(
    success=True,
    output_path="D:/Backups/Ai_Assistant_backup_20261112_090000.zip",
    artifacts=["D:/Backups/Ai_Assistant_backup_20261112_090000.zip"],
    data={
        "status": "organized",
        "moved_count": 48,
        "categories": {
            "images": 22,
            "documents": 18,
            "archives": 8
        },
        "target_directory": "D:/Downloads",
        "message": "Organized 48 files into 3 category subfolders."
    }
)
```

---

## 🛡️ Error Handling & Fallback Strategy
* **System Directory Safeguards:** Automatically verifies and protects Windows system directories (`C:\Windows`, `C:\Program Files`) from destructive moving or deletion.
* **Standard Folder Aliasing:** Resolves user terms like `"downloads"`, `"desktop"`, `"documents"` into actual resolved Windows User profile paths via [`FileAutomation.get_standard_folder`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/automation/file_automation.py).
* **Safe Overwrite Prevention:** When moving or organizing files, existing destination files are not silently overwritten; collision counters (`_1`, `_2`) are applied automatically.

---

## 🚀 Execution Examples

### 1. Python Direct Invocation
```python
from ai_assistant.agents.loader import get_global_registry
from ai_assistant.agents.models import Task

registry = get_global_registry()
agent = registry.get_agent("file-001")

task = Task(
    task_id="file_org_01",
    description="Organize files in Downloads folder",
    params={"directory": "downloads"}
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
  "agent_id": "file-001",
  "description": "Create a zip backup of the docs folder",
  "params": {
    "directory": "D:/Projects/Ai_Assistant/docs"
  }
}
```
