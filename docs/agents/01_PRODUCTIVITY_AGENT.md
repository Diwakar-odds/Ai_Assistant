# 📄 01: Productivity Agent (`productivity-001`)

## 📌 Overview
The **Productivity Agent** is an enterprise-grade document creation, transformation, and formatting agent. It handles programmatic generation of Microsoft Word documents (`.docx`), Excel spreadsheets (`.xlsx`), PowerPoint presentations (`.pptx`), and Portable Document Format (`.pdf`) files, as well as cross-format conversions.

* **Agent ID:** `productivity-001`
* **Canonical Name:** Productivity Agent
* **Category:** `productivity`
* **Aliases:** `productivity`, `productivity-001`
* **Implementation File:** [`core_ai/src/ai_assistant/agents/productivity/productivity_agent.py`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/productivity/productivity_agent.py)
* **Base Class:** [`BaseAgent`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/base_agent.py)

---

## ⚙️ Trigger Keywords & Intent Matching
The agent automatically accepts tasks whose description or metadata contains:
`word`, `docx`, `excel`, `xlsx`, `spreadsheet`, `powerpoint`, `pptx`, `slides`, `presentation`, `pdf`, `document`, `report`, `convert`, `format`.

---

## 🛠️ Declared Capabilities & Methods

| Capability | Internal Method | Description | Primary Dependencies |
| :--- | :--- | :--- | :--- |
| `create_word_document` | `_create_word_document(task)` | Builds multi-paragraph Word documents with headings and embedded images. | `python-docx` |
| `create_excel_spreadsheet` | `_create_spreadsheet(task)` | Creates formatted Excel sheets with automatic key-value or row-column mapping. | `openpyxl` |
| `create_powerpoint` | `_create_presentation(task)` | Creates multi-slide decks with titles, subtitles, and structured bullet points. | `python-pptx` |
| `create_pdf` | `_create_pdf(task)` | Compiles clean PDF documents from text or structured headings. | `reportlab` |
| `edit_document` | `_create_word_document(task)` | Appends or updates paragraphs/images within existing document models. | `python-docx` |
| `convert_formats` | `_convert_formats(task)` | Converts between DOCX, PDF, and plain text formats. | `docx2pdf` / `pypdf` |

---

## 📥 Input Parameter Schema (`task.params`)

```json
{
  "task_type": "word_document | excel_spreadsheet | powerpoint | pdf | convert",
  "title": "Quarterly Financial Analysis",
  "content": "Paragraph 1...\n\nParagraph 2...",
  "images": ["D:/Projects/Ai_Assistant/outputs/chart.png"],
  "data": [
    {"Metric": "Revenue", "Q1": 120000, "Q2": 145000},
    {"Metric": "Expenses", "Q1": 80000, "Q2": 85000}
  ],
  "slides": [
    {"title": "Executive Summary", "content": "Key takeaways..."},
    {"title": "Roadmap", "content": "Milestones and timeline..."}
  ],
  "source_path": "D:/Projects/Ai_Assistant/outputs/report.docx",
  "target_format": "pdf",
  "output_path": "D:/Projects/Ai_Assistant/outputs/Final_Report.docx"
}
```

---

## 📤 Output Artifacts & Return Schema (`TaskResult`)

Upon completion, the agent saves files to the workspace `outputs/` folder and returns:

```python
TaskResult(
    success=True,
    output_path="D:/Projects/Ai_Assistant/outputs/document_a1b2c3d4.docx",
    artifacts=["D:/Projects/Ai_Assistant/outputs/document_a1b2c3d4.docx"],
    data={
        "filename": "document_a1b2c3d4.docx",
        "output_path": "D:/Projects/Ai_Assistant/outputs/document_a1b2c3d4.docx",
        "rows": 12, # for spreadsheets
        "message": "Word document created at D:/Projects/Ai_Assistant/outputs/document_a1b2c3d4.docx"
    }
)
```

---

## 🛡️ Error Handling & Fallback Strategy
* **Non-blocking Thread Offloading:** Document generation can be CPU-heavy; all file writes use `asyncio.to_thread(_build_docx)` or equivalent to prevent blocking the main event loop.
* **Missing Dependency Detection:** If `python-docx`, `openpyxl`, or `reportlab` are missing, the agent does not crash. It returns `TaskResult(success=False, error="Missing optional dependency 'openpyxl'...")` with clear installation instructions.
* **Upstream Context Extraction:** If `params.content` is omitted, the agent automatically extracts upstream synthesis from parent chained agents (e.g., Writer Agent or Deep Research Agent).

---

## 🚀 Execution Examples

### 1. Python Direct Invocation
```python
from ai_assistant.agents.loader import get_global_registry
from ai_assistant.agents.models import Task

registry = get_global_registry()
agent = registry.get_agent("productivity-001")

task = Task(
    task_id="task_doc_101",
    description="Create an Excel spreadsheet of weekly expenses",
    params={
        "title": "Expenses",
        "data": [
            {"Item": "Hosting", "Cost": 50},
            {"Item": "Domain", "Cost": 12}
        ]
    }
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
  "agent_id": "productivity-001",
  "description": "Generate a Word document summary of AI capabilities",
  "params": {
    "title": "AI Assistant Overview",
    "content": "Pulsar is a complete autonomous agent system."
  }
}
```
