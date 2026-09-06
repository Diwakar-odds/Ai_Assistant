# smart_memory_retrieval.py — DELETE

## Why

Audit finding C3: this module is **dead code**. A full-project grep (excluding
`venv/`, `node_modules/`, `dist_package/`) confirms:

- No `import smart_memory_retrieval` outside the file itself.
- No `from ai_assistant.ai.smart_memory_retrieval import ...` anywhere.
- No reference to `SmartMemoryRetrieval` class.
- No reference to the `enhance_response_with_memory()` export function.
- No reference to any pattern-routing helper it provides.

Additionally (C1), `_search_app_usage()` builds SQL via f-string interpolation
(`f"LOWER(content) LIKE '%{app}%'"`). Currently safe only because `apps` is
hardcoded — a latent SQL-injection surface for future contributors.

(C2) Line 219 has `f"Upcoming events from your history:\\n"` which produces
literal backslash-n in the user-facing output.

## Decision: delete, don't integrate

The functionality it offers is subsumed by:

- `MemoryRetrieval` (active, FTS5) for general memory search.
- `memory.semantic_search_memory()` for vector fallback (now wired into
  `MemoryRetrieval._semantic_fallback` in patch 01).
- A regular SQL query through `MemoryRetrieval` for app-usage stats if you
  actually need that data later.

## How to delete

```bash
# from d:/projects/ai_assistant
git rm core_ai/src/ai_assistant/ai/smart_memory_retrieval.py
```

If you don't want a hard delete yet (e.g. to preserve a reference), replace
the file with the stub below. It keeps the path importable so any leftover
imports don't break, but it does nothing.

## Stub (drop-in replacement)

```python
# core_ai/src/ai_assistant/ai/smart_memory_retrieval.py
"""
DEPRECATED — see rag_patches/03_smart_memory_retrieval_DELETE.md
This module is no longer used. Functionality has moved to MemoryRetrieval
(core_ai/src/ai_assistant/ai/memory_retrieval.py).
"""
import warnings

def __getattr__(name):
    def _missing(*args, **kwargs):
        warnings.warn(
            f"smart_memory_retrieval.{name} is deprecated and returns None. "
            "Use MemoryRetrieval instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return None
    return _missing
```
