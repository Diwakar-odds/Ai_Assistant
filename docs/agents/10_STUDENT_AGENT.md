# 🎓 10: Student Agent (`student-001`)

## 📌 Overview
The **Student Agent** is an educational and study assistant. It solves mathematical expressions, algebraic equations, and calculus derivatives symbolically via SymPy (without unsafe `eval()`), generates interactive flashcards and quiz questions, ingests study folders (`.pdf`, `.txt`, `.md`, `.csv`, `.json`), and performs Retrieval-Augmented Generation (RAG) over student course notes.

* **Agent ID:** `student-001`
* **Canonical Name:** Student Agent
* **Category:** `education`
* **Aliases:** `student`, `student_01`, `student-001`
* **Implementation File:** [`core_ai/src/ai_assistant/agents/student/student_agent.py`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/student/student_agent.py)
* **Base Class:** [`BaseAgent`](file:///d:/Projects/Ai_Assistant/core_ai/src/ai_assistant/agents/base_agent.py)

---

## ⚙️ Trigger Keywords & Intent Matching
The agent automatically accepts tasks containing:
`study`, `exam`, `homework`, `notes`, `flashcard`, `quiz`, `equation`, `solve`, `math`, `algebra`, `calculus`, `derivative`, `integral`, `rag`, `tutor`.

---

## 🛠️ Declared Capabilities & Methods

| Capability | Internal Method | Description | Primary Engine |
| :--- | :--- | :--- | :--- |
| `solve_math` | `_solve_math(task)` | Solves equations, derivatives, integrals, and factorizations safely without `eval()`. | `sympy` parse_expr |
| `study_folder` | `_ingest_folder(task)` | Ingests all text, PDF, and markdown files in a course directory into a local RAG index. | Ingestion Pipeline & Chunker |
| `answer_exam_questions` | `_answer_question(task)` | Retrieves semantic passages from indexed notes and provides cited study answers. | Local Note Index / Vector RAG |
| `create_flashcards` | `_create_flashcards(task)` | Parses key concepts into Question/Answer study flashcards (JSON & Markdown). | Unified LLM / Heuristics |
| `learn_topic` / `take_notes` | `_learn_topic(task)` | Produces structured Cornell-style or concept-map revision notes on a subject. | Unified LLM |

---

## 📥 Input Parameter Schema (`task.params`)

```json
{
  "expression": "diff(x**3 + 2*x**2 - 5*x + 7, x)",
  "topic": "Newton's Laws of Motion",
  "folder_path": "D:/MyCourseNotes/Physics101",
  "question": "What is the third law of thermodynamics according to the lecture notes?",
  "count": 5
}
```

---

## 📤 Output Return Schema (`TaskResult`)

### Math Solution:
```python
TaskResult(
    success=True,
    output_path=None,
    data={
        "input_expression": "diff(x**3 + 2*x**2 - 5*x + 7, x)",
        "result": "3*x**2 + 4*x - 5",
        "operation": "derivative",
        "message": "Solved: diff(x**3 + 2*x**2 - 5*x + 7, x) => 3*x**2 + 4*x - 5"
    }
)
```

### Flashcards:
```python
TaskResult(
    success=True,
    data={
        "topic": "Machine Learning",
        "flashcards": [
            {"front": "What is Overfitting?", "back": "When a model learns noise in training data..."},
            {"front": "What is Regularization?", "back": "Techniques to reduce overfitting by penalizing complexity..."}
        ],
        "count": 2
    }
)
```

---

## 🛡️ Error Handling & Fallback Strategy
* **Zero-`eval()` Mathematical Security:** SymPy formulas are parsed via `sympy.parsing.sympy_parser.parse_expr` using explicit whitelist transformations. Python's built-in `eval()` is strictly prohibited to prevent arbitrary code execution attacks.
* **Local Persistent Index:** Student RAG notes are saved locally to `data/rag_db/notes_index.json`, allowing instant offline recall without requiring expensive cloud vector database subscriptions.

---

## 🚀 Execution Examples

### 1. Python Direct Invocation
```python
from ai_assistant.agents.loader import get_global_registry
from ai_assistant.agents.models import Task

registry = get_global_registry()
agent = registry.get_agent("student-001")

task = Task(
    task_id="math_01",
    description="Solve derivative of x**4 - 3*x**2 + 2",
    params={"expression": "diff(x**4 - 3*x**2 + 2, x)"}
)
result = await agent.execute(task)
print(result.data["result"])
```

### 2. REST API Invocation
```http
POST /api/agents/tasks
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>

{
  "agent_id": "student-001",
  "description": "Create 5 flashcards on Cellular Respiration",
  "params": {
    "topic": "Cellular Respiration",
    "count": 5
  }
}
```
