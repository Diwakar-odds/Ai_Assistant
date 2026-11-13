# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Retrieval trace logger (audit fix X1).

Writes one JSONL line per LLM call to data/rag_traces.jsonl capturing:
  - timestamp
  - query
  - which retriever ran (and whether it was gated on or off)
  - retrieved ids (conversation_ids or interaction_ids)
  - the injected context preview (first 800 chars)
  - source (memory_retrieval, historical_rag, semantic_fallback, none)
  - response id (if available)

This is the surface that closes the improvement loop — when the LLM
hallucinates a wrong answer, you can grep rag_traces.jsonl for the call and
inspect exactly what context was injected.
"""

import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

_MODULE_DIR = Path(__file__).resolve().parent
_TRACE_DIR = _MODULE_DIR.parent.parent.parent / "data"
_TRACE_PATH = _TRACE_DIR / "rag_traces.jsonl"
_WRITE_LOCK = threading.Lock()


def _ensure_path() -> Path:
    _TRACE_DIR.mkdir(parents=True, exist_ok=True)
    return _TRACE_PATH


def write_trace(
    query: str,
    retriever: str,
    retrieved_ids: List[Any],
    injected_preview: str,
    response_id: Optional[str] = None,
    source: str = "memory_retrieval",
    extra: Optional[Dict[str, Any]] = None,
    max_preview_chars: int = 800,
) -> str:
    """
    Append a trace line. Returns the trace_id (also written to the line).
    Never raises — failures are logged but don't break the live path.
    """
    trace_id = uuid.uuid4().hex[:12]
    record = {
        "trace_id": trace_id,
        "ts": datetime.now().isoformat(timespec="seconds"),
        "epoch": int(time.time()),
        "retriever": retriever,
        "source": source,
        "query": query,
        "retrieved_ids": retrieved_ids,
        "injected_chars": len(injected_preview),
        "injected_preview": injected_preview[:max_preview_chars],
        "response_id": response_id,
    }
    if extra:
        record["extra"] = extra
    try:
        path = _ensure_path()
        with _WRITE_LOCK:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"[RAG-TRACE] write failed: {e}")
    return trace_id


def tail(n: int = 20) -> List[Dict[str, Any]]:
    """Return the last n trace records. Cheap; safe to call from a debug command."""
    try:
        path = _ensure_path()
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()[-n:]
        return [json.loads(line) for line in lines if line.strip()]
    except Exception as e:
        logger.warning(f"[RAG-TRACE] read failed: {e}")
        return []


def grep(query_substring: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search traces by substring of the query (case-insensitive)."""
    try:
        path = _ensure_path()
        if not path.exists():
            return []
        q = query_substring.lower()
        out: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if q in rec.get("query", "").lower():
                    out.append(rec)
                    if len(out) >= limit:
                        break
        return out
    except Exception as e:
        logger.warning(f"[RAG-TRACE] grep failed: {e}")
        return []
