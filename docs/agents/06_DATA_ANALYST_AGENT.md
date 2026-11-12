# 📊 06: Data Analyst Agent (`data-001`)

## 📌 Overview
The **Data Analyst Agent** ingests structured datasets (CSV, JSON, Python lists/dicts), performs descriptive statistical computations (mean, median, standard deviation, min/max, percentiles), and renders visual charts (bar, line, pie, histogram, scatter plots) using `matplotlib` or a pure Pillow chart fallback.

* **Agent ID:** `data-001`
* **Canonical Name:** Data Analyst Agent
* **Category:** `data`
* **Aliases:** `data`, `data_analyst`, `data-analyst`, `data-001`
* **Implementation File:** [`core_ai/src/ai_assistant/agents/data/data_analyst_agent.py`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/data/data_analyst_agent.py)
* **Base Class:** [`BaseAgent`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/base_agent.py)

---

## ⚙️ Trigger Keywords & Intent Matching
The agent automatically accepts tasks containing:
`chart`, `graph`, `plot`, `bar`, `line`, `pie`, `scatter`, `analyze`, `data`, `statistics`, `metrics`, `visualize`, `csv`, `trend`, `correlation`.

---

## 🛠️ Declared Capabilities & Methods

| Capability | Internal Method | Description | Primary Engine |
| :--- | :--- | :--- | :--- |
| `analyze_data` | `_analyze_dataset(...)` | Computes statistical metrics across numeric columns and generates an analysis report. | Python `statistics` / `pandas` |
| `visualize_data` / `create_chart`| `_create_chart(...)` | Generates publication-ready PNG/SVG charts with titles, legends, and gridlines. | `matplotlib` / Pillow Fallback |
| `statistical_analysis` | `_analyze_dataset(...)` | Analyzes correlation, variance, distributions, and summary tables. | `statistics` module |

---

## 📥 Input Parameter Schema (`task.params`)

```json
{
  "chart_type": "bar | line | pie | scatter | histogram",
  "title": "Monthly Cloud Infrastructure Spend",
  "data_path": "D:/Projects/Ai_Assistant/data/costs.csv",
  "data": [
    {"Month": "Jan", "Spend": 450},
    {"Month": "Feb", "Spend": 520},
    {"Month": "Mar", "Spend": 490}
  ],
  "x_col": "Month",
  "y_col": "Spend"
}
```

---

## 📤 Output Return Schema (`TaskResult`)

```python
TaskResult(
    success=True,
    output_path="D:/Projects/Ai_Assistant/outputs/chart_spend_bar.png",
    artifacts=["D:/Projects/Ai_Assistant/outputs/chart_spend_bar.png"],
    data={
        "chart_type": "bar",
        "title": "Monthly Cloud Infrastructure Spend",
        "output_path": "D:/Projects/Ai_Assistant/outputs/chart_spend_bar.png",
        "statistics": {
            "Spend": {
                "mean": 486.67,
                "median": 490,
                "min": 450,
                "max": 520
            }
        },
        "message": "Rendered bar chart to D:/Projects/Ai_Assistant/outputs/chart_spend_bar.png"
    }
)
```

---

## 🛡️ Error Handling & Fallback Strategy
* **Autonomous File Discovery:** If `data_path` is omitted but the prompt mentions `D:\data\sales.csv`, regex pattern matchers automatically locate and validate the CSV on disk.
* **Headless Matplotlib Engine:** Automatically enforces `matplotlib.use('Agg')` in worker threads to prevent GUI window deadlocks on Windows desktop.
* **Zero-Matplotlib Pillow Renderer:** If `matplotlib` is not installed, a custom pure-Python Pillow vector engine generates clean 2D bar and line charts without external C-extensions.

---

## 🚀 Execution Examples

### 1. Python Direct Invocation
```python
from ai_assistant.agents.loader import get_global_registry
from ai_assistant.agents.models import Task

registry = get_global_registry()
agent = registry.get_agent("data-001")

task = Task(
    task_id="data_task_01",
    description="Plot a bar chart of server latencies",
    params={
        "chart_type": "bar",
        "title": "API Latency (ms)",
        "data": [
            {"Route": "/chat", "Latency": 120},
            {"Route": "/agents", "Latency": 45},
            {"Route": "/auth", "Latency": 15}
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
  "agent_id": "data-001",
  "description": "Analyze dataset and create summary statistics",
  "params": {
    "data_path": "D:/Projects/Ai_Assistant/data/metrics.csv"
  }
}
```
