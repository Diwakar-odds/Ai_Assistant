"""
pulsar_memory.py - local-first, 3-tier memory for Pulsar (Windows 11, no Docker).

Tier 1  WorkingMemory        RAM ring buffer, token/char-bounded (current session)
Tier 2  episodes table       append-only SQLite turn log (today's raw turns; pruned after distillation)
Tier 3  memories table       distilled facts / commitments / project state / relations
                             FTS5 (BM25) + L2-normalised float32 vectors, fused with RRF,
                             filtered by lifecycle status and event time in plain SQL.

Deps: numpy, sentence-transformers (share the instance you already load for Tier 1.5),
      optional: psutil (power/CPU gating), llama-cpp-python (local extraction).
"""
from __future__ import annotations

import asyncio
import calendar
import ctypes
import gc
import json
import logging
import math
import re
import sqlite3
import threading
import time
import uuid
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

import numpy as np

log = logging.getLogger("pulsar.memory")

DIM = 384                                   # all-MiniLM-L6-v2
LIVE = ("active", "due", "past")            # statuses that stay searchable
LIVE_SQL = "('active','due','past')"

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
CREATE TABLE IF NOT EXISTS episodes(
  id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, ts REAL NOT NULL,
  role TEXT NOT NULL, source TEXT DEFAULT 'chat', text TEXT NOT NULL, processed INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS ix_ep_pending ON episodes(processed, ts);
CREATE TABLE IF NOT EXISTS memories(
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, subject TEXT DEFAULT '', content TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  importance REAL DEFAULT 0.5, confidence REAL DEFAULT 0.7,
  event_start REAL, event_end REAL, precision TEXT, time_expr TEXT,
  source_ts REAL, created_at REAL, updated_at REAL, last_confirmed_at REAL,
  last_nudged_at REAL, nudge_stage INTEGER DEFAULT 0, dismissals INTEGER DEFAULT 0, snoozed_until REAL,
  payload TEXT, embedding BLOB);
CREATE INDEX IF NOT EXISTS ix_mem_live ON memories(status, kind, event_start);
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
  id UNINDEXED, content, subject, tokenize='porter unicode61');
CREATE TABLE IF NOT EXISTS relations(
  src TEXT, rel TEXT, dst TEXT, ts REAL, PRIMARY KEY(src, rel, dst));
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT);
"""

_STOP = set("the a an is are was were to of in on for and or my me i it that this what when "
            "where how do does did can you your with about at be".split())


# ----------------------------------------------------------------------------
# Embeddings
# ----------------------------------------------------------------------------
class Embedder:
    """Pass the SentenceTransformer you already load for Tier 1.5 so there is ONE copy in RAM."""

    def __init__(self, model=None, name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self._model, self._name, self._lock = model, name, threading.Lock()

    def encode(self, texts) -> np.ndarray:
        with self._lock:
            if self._model is None:                       # lazy: no model load at startup
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._name, device="cpu")
            v = self._model.encode(list(texts), normalize_embeddings=True,
                                   convert_to_numpy=True, show_progress_bar=False)
        return np.asarray(v, dtype=np.float32)            # unit vectors: dot product == cosine


# ----------------------------------------------------------------------------
# Deterministic temporal resolver (the LLM never does date math)
# ----------------------------------------------------------------------------
_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
_MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
_MONTHS["sept"] = 9
_WEEKDAYS = {d.lower(): i for i, d in enumerate(calendar.day_name)}
_MON_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))


@dataclass
class Resolved:
    start: datetime
    end: datetime
    precision: str          # day | week | month
    confidence: float


def _span(start: datetime, days: int, precision: str, conf: float) -> Resolved:
    return Resolved(start, start + timedelta(days=days) - timedelta(seconds=1), precision, conf)


def _month_span(year: int, month: int, conf: float = 0.85) -> Resolved:
    last = calendar.monthrange(year, month)[1]
    return _span(datetime(year, month, 1), last, "month", conf)


def resolve_time(expr: str, anchor: datetime) -> Optional[Resolved]:
    """Resolve a time phrase relative to `anchor` (when the user SAID it, not 'now')."""
    s = (expr or "").lower().strip()
    if not s:
        return None
    today = anchor.replace(hour=0, minute=0, second=0, microsecond=0)
    day = lambda d, c=0.95: _span(d, 1, "day", c)

    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", s)
    if m:
        try:
            return day(datetime(int(m[1]), int(m[2]), int(m[3])), 1.0)
        except ValueError:
            return None
    if "day after tomorrow" in s:
        return day(today + timedelta(days=2))
    if "tomorrow" in s:
        return day(today + timedelta(days=1))
    if re.search(r"\b(today|tonight)\b", s):
        return day(today)

    m = re.search(r"\bin (\d+) (day|week|month)s?\b", s)
    if m:
        n, unit = int(m[1]), m[2]
        if unit == "month":
            idx = today.month - 1 + n
            return _month_span(today.year + idx // 12, idx % 12 + 1, 0.6)
        return day(today + timedelta(days=n * (7 if unit == "week" else 1)), 0.8)
    if "next week" in s:
        return _span(today + timedelta(days=7 - today.weekday()), 7, "week", 0.8)
    if "this weekend" in s:
        return _span(today + timedelta(days=(5 - today.weekday()) % 7), 2, "week", 0.8)
    if "next month" in s:
        idx = today.month
        return _month_span(today.year + idx // 12, idx % 12 + 1, 0.8)

    m = re.search(r"\b(?:next |this |on )?(" + "|".join(_WEEKDAYS) + r")\b", s)
    if m:
        delta = (_WEEKDAYS[m[1]] - today.weekday()) % 7 or 7
        return day(today + timedelta(days=delta), 0.8)

    # "15 january [2027]" / "january 15[th] [2027]"
    m = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MON_RE})\b(?:,?\s+(\d{{4}}))?", s)
    if m:
        d, mi, y = int(m[1]), _MONTHS[m[2]], m[3]
    else:
        m = re.search(rf"\b({_MON_RE})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?:,?\s+(\d{{4}}))?", s)
        d, mi, y = (int(m[2]), _MONTHS[m[1]], m[3]) if m else (0, 0, None)
    if m:
        try:
            dt = datetime(int(y) if y else today.year, mi, d)
            if not y and dt < today:
                dt = datetime(today.year + 1, mi, d)
            return day(dt)
        except ValueError:
            return None

    # month only: "january", "next january", "in march 2027"
    m = re.search(rf"\b(next |this |coming )?({_MON_RE})\b(?:,?\s+(\d{{4}}))?", s)
    if m:
        mi = _MONTHS[m[2]]
        if m[3]:
            year = int(m[3])
        else:
            year = today.year
            strictly_after = bool(m[1] and m[1].strip() == "next")
            if mi < today.month or (mi == today.month and strictly_after):
                year += 1
        return _month_span(year, mi)
    return None


# ----------------------------------------------------------------------------
# Tier 1: working memory
# ----------------------------------------------------------------------------
class WorkingMemory:
    def __init__(self, max_turns: int = 12, max_chars: int = 6000):
        self.turns: deque = deque(maxlen=max_turns)
        self.max_chars = max_chars

    def add(self, role: str, text: str) -> None:
        self.turns.append((role, text))

    def render(self) -> str:
        out, used = [], 0
        for role, text in reversed(self.turns):
            if used + len(text) > self.max_chars:
                break
            out.append(f"{role}: {text}")
            used += len(text)
        return "\n".join(reversed(out))


# ----------------------------------------------------------------------------
# Tier 2 + 3: HybridMemoryStore
# ----------------------------------------------------------------------------
class HybridMemoryStore:
    def __init__(self, path, embedder: Embedder):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.emb = embedder
        self._lock = threading.RLock()
        self._ids: list = []
        self._kinds: list = []
        self._mat = np.zeros((0, DIM), np.float32)
        self._dirty = True
        self.on_change: Optional[Callable[[], None]] = None

    # ---- kv -----------------------------------------------------------------
    def kv_get(self, k, default=None):
        r = self.db.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
        return r["v"] if r else default

    def kv_set(self, k, v):
        with self._lock, self.db:
            self.db.execute("INSERT INTO kv(k, v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))

    # ---- Tier 2: episodes ---------------------------------------------------
    def log_turn(self, session_id, role, text, source="chat"):
        with self._lock, self.db:
            self.db.execute("INSERT INTO episodes(session_id, ts, role, source, text) VALUES (?,?,?,?,?)",
                            (session_id, time.time(), role, source, text))

    def recent_turns(self, n=8, max_age_h=12):
        rows = self.db.execute("SELECT role, text FROM episodes WHERE ts > ? ORDER BY id DESC LIMIT ?",
                               (time.time() - max_age_h * 3600, n)).fetchall()
        return list(reversed([dict(r) for r in rows]))

    def pending_count(self) -> int:
        return self.db.execute("SELECT COUNT(*) c FROM episodes WHERE processed=0").fetchone()["c"]

    def pending_turns(self, limit=80):
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM episodes WHERE processed=0 ORDER BY id LIMIT ?", (limit,))]

    def mark_processed(self, ids):
        with self._lock, self.db:
            self.db.executemany("UPDATE episodes SET processed=1 WHERE id=?", [(i,) for i in ids])

    def prune_episodes(self, keep_days=7):
        with self._lock, self.db:
            self.db.execute("DELETE FROM episodes WHERE processed=1 AND ts < ?", (time.time() - keep_days * 86400,))

    # ---- vector cache -------------------------------------------------------
    def _index(self):
        if self._dirty:
            rows = self.db.execute(
                f"SELECT id, kind, embedding FROM memories WHERE status IN {LIVE_SQL} AND embedding IS NOT NULL").fetchall()
            self._ids = [r["id"] for r in rows]
            self._kinds = [r["kind"] for r in rows]
            self._mat = (np.vstack([np.frombuffer(r["embedding"], np.float32) for r in rows])
                         if rows else np.zeros((0, DIM), np.float32))
            self._dirty = False
        return self._ids, self._kinds, self._mat

    def _nearest(self, vec, kind):
        ids, kinds, mat = self._index()
        if not ids:
            return None
        sims = mat @ vec
        for i in np.argsort(-sims)[:10]:
            if kinds[i] == kind:
                return ids[i], float(sims[i])
        return None

    def _retire(self, ids, status):
        if not ids:
            return
        q = ",".join("?" * len(ids))
        self.db.execute(f"UPDATE memories SET status=?, updated_at=? WHERE id IN ({q})", (status, time.time(), *ids))
        self.db.execute(f"DELETE FROM memories_fts WHERE id IN ({q})", list(ids))
        self._dirty = True

    # ---- write path ---------------------------------------------------------
    def upsert(self, kind, content, subject="", *, importance=0.5, confidence=0.7,
               event_start=None, event_end=None, precision=None, time_expr=None,
               source_ts=None, payload=None) -> str:
        vec = self.emb.encode([f"{subject}: {content}" if subject else content])[0]
        now = time.time()
        with self._lock, self.db:
            if kind in ("fact", "project_state") and subject:
                same = self.db.execute(
                    f"SELECT id, content FROM memories WHERE kind=? AND lower(subject)=lower(?) AND status IN {LIVE_SQL}",
                    (kind, subject)).fetchall()
                for r in same:
                    if r["content"].strip().lower() == content.strip().lower():
                        self.db.execute("UPDATE memories SET last_confirmed_at=?, updated_at=? WHERE id=?", (now, now, r["id"]))
                        return r["id"]
                self._retire([r["id"] for r in same], "superseded")   # newer value wins (e.g. preference re-mapped)
            else:
                hit = self._nearest(vec, kind)
                if hit and (hit[1] >= 0.95 or (kind == "commitment" and hit[1] >= 0.88)):
                    mid = hit[0]
                    old = self.db.execute("SELECT event_start FROM memories WHERE id=?", (mid,)).fetchone()
                    moved = event_start is not None and old["event_start"] != event_start
                    self.db.execute(
                        """UPDATE memories SET last_confirmed_at=?, updated_at=?, confidence=max(confidence, ?),
                           event_start=COALESCE(?, event_start), event_end=COALESCE(?, event_end),
                           precision=COALESCE(?, precision), time_expr=COALESCE(?, time_expr),
                           nudge_stage=CASE WHEN ? THEN 0 ELSE nudge_stage END WHERE id=?""",
                        (now, now, confidence, event_start, event_end, precision, time_expr, int(moved), mid))
                    return mid
            mid = uuid.uuid4().hex[:12]
            self.db.execute(
                """INSERT INTO memories(id, kind, subject, content, importance, confidence, event_start, event_end,
                   precision, time_expr, source_ts, created_at, updated_at, last_confirmed_at, payload, embedding)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (mid, kind, subject, content, importance, confidence, event_start, event_end, precision, time_expr,
                 source_ts, now, now, now, json.dumps(payload or {}), vec.tobytes()))
            self.db.execute("INSERT INTO memories_fts(id, content, subject) VALUES (?,?,?)", (mid, content, subject))
            self._dirty = True
        if self.on_change:
            self.on_change()
        return mid

    def set_status(self, mid, status):
        with self._lock, self.db:
            if status in LIVE:
                self.db.execute("UPDATE memories SET status=?, updated_at=? WHERE id=?", (status, time.time(), mid))
            else:
                self._retire([mid], status)
        if self.on_change:
            self.on_change()

    def add_relation(self, src, rel, dst):
        with self._lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO relations(src, rel, dst, ts) VALUES (?,?,?,?)",
                            (src.strip().lower(), rel.strip().lower(), dst.strip().lower(), time.time()))

    # ---- read path ----------------------------------------------------------
    def search(self, query, k=5, kinds=None, vectors=True):
        """Hybrid retrieval: cosine top-N + BM25 top-N, fused with Reciprocal Rank Fusion."""
        scores: dict = {}
        sims: dict = {}
        lex: set = set()
        with self._lock:
            if vectors:
                ids, kd, mat = self._index()
                if len(ids):
                    s = mat @ self.emb.encode([query])[0]
                    rank = 0
                    for i in np.argsort(-s)[:40]:
                        if s[i] < 0.25:
                            break
                        if kinds and kd[i] not in kinds:
                            continue
                        scores[ids[i]] = scores.get(ids[i], 0.0) + 1 / (60 + rank)
                        sims[ids[i]] = float(s[i])
                        rank += 1
            toks = [t for t in re.findall(r"\w{2,}", query.lower()) if t not in _STOP][:12]
            if toks:
                fq = " OR ".join(f'"{t}"' for t in toks)
                for rank, r in enumerate(self.db.execute(
                        "SELECT id FROM memories_fts WHERE memories_fts MATCH ? ORDER BY bm25(memories_fts) LIMIT 40", (fq,))):
                    scores[r["id"]] = scores.get(r["id"], 0.0) + 1 / (60 + rank)
                    lex.add(r["id"])
            if not scores:
                return []
            marks = ",".join("?" * len(scores))
            rows = {r["id"]: dict(r) for r in self.db.execute(
                f"SELECT * FROM memories WHERE id IN ({marks})", list(scores))}
        now, out = time.time(), []
        for mid, sc in scores.items():
            r = rows.get(mid)
            if not r or r["status"] not in LIVE or (kinds and r["kind"] not in kinds):
                continue
            r.pop("embedding", None)
            age_d = (now - (r["updated_at"] or now)) / 86400
            boost = 0.004 * (r["importance"] or 0.5) + 0.002 * math.exp(-age_d / 30)
            if r["event_start"] and 0 <= r["event_start"] - now <= 30 * 86400:
                boost += 0.004                                   # imminent events float up
            r["score"], r["sim"], r["lex"] = sc + boost, sims.get(mid, 0.0), mid in lex
            out.append(r)
        return sorted(out, key=lambda r: -r["score"])[:k]

    def upcoming(self, within_days, now=None):
        now = now or time.time()
        return [dict(r) for r in self.db.execute(
            """SELECT * FROM memories WHERE kind='commitment' AND status IN ('active','due')
               AND event_start IS NOT NULL AND event_start <= ? ORDER BY event_start""",
            (now + within_days * 86400,))]

    def past_commitments(self, since, until):
        return [dict(r) for r in self.db.execute(
            """SELECT * FROM memories WHERE kind='commitment' AND status='past'
               AND event_end BETWEEN ? AND ? AND nudge_stage < 99""", (since, until))]

    # ---- lifecycle ----------------------------------------------------------
    def sweep_lifecycle(self, now=None, archive_after_days=14, ephemeral_ttl_days=45, purge_days=365) -> int:
        """active -> due (window opens in <=24h) -> past (window over) -> archived. Pure SQL; run at startup + daily."""
        now = now or time.time()
        n = 0
        with self._lock, self.db:
            def run(sql, args):
                nonlocal n
                n += self.db.execute(sql, args).rowcount

            run("""UPDATE memories SET status='due', updated_at=? WHERE kind='commitment' AND status='active'
                   AND event_start IS NOT NULL AND event_start - 86400 <= ?""", (now, now))
            run("""UPDATE memories SET status='past', updated_at=? WHERE kind='commitment'
                   AND status IN ('active','due') AND event_end IS NOT NULL AND event_end < ?""", (now, now))
            run("""UPDATE memories SET status='archived', updated_at=? WHERE kind='commitment' AND status='past'
                   AND event_end < ?""", (now, now - archive_after_days * 86400))
            run("""UPDATE memories SET status='archived', updated_at=? WHERE status IN ('completed','cancelled')
                   AND updated_at < ?""", (now, now - 30 * 86400))
            run("""UPDATE memories SET status='archived', updated_at=? WHERE kind='project_state' AND status='active'
                   AND updated_at < ?""", (now, now - ephemeral_ttl_days * 86400))
            run("""UPDATE memories SET status='archived', updated_at=? WHERE kind='commitment' AND status='active'
                   AND event_start IS NULL AND created_at < ?""", (now, now - 60 * 86400))     # undated plans rot
            self.db.execute(f"DELETE FROM memories_fts WHERE id IN (SELECT id FROM memories WHERE status NOT IN {LIVE_SQL})")
            self.db.execute("DELETE FROM memories WHERE status IN ('archived','superseded') AND updated_at < ?",
                            (now - purge_days * 86400,))
            if n:
                self._dirty = True
        return n


# ----------------------------------------------------------------------------
# Idle / power gate (Windows)
# ----------------------------------------------------------------------------
class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def idle_seconds() -> float:
    try:
        lii = _LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(lii)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        return ((ctypes.windll.kernel32.GetTickCount() - lii.dwTime) & 0xFFFFFFFF) / 1000.0
    except Exception:
        return 1e9                                           # non-Windows / unavailable: assume idle


class IdleGate:
    def __init__(self, min_idle_s=120, max_cpu=35.0, require_ac=True):
        self.min_idle_s, self.max_cpu, self.require_ac = min_idle_s, max_cpu, require_ac

    def ok(self) -> bool:
        if idle_seconds() < self.min_idle_s:
            return False
        try:
            import psutil
            b = psutil.sensors_battery()
            if self.require_ac and b is not None and not b.power_plugged:
                return False
            if psutil.cpu_percent(interval=None) > self.max_cpu:
                return False
        except ImportError:
            pass
        return True


def _background_thread_mode() -> None:
    """Lower CPU + I/O + memory priority for the current thread (Windows THREAD_MODE_BACKGROUND_BEGIN)."""
    try:
        k = ctypes.windll.kernel32
        k.SetThreadPriority(k.GetCurrentThread(), 0x00010000)
    except Exception:
        pass


# ----------------------------------------------------------------------------
# Extraction schema / prompt
# ----------------------------------------------------------------------------
def _obj(props: dict, req: list) -> dict:
    return {"type": "object", "properties": props, "required": req}


_S, _N = {"type": "string"}, {"type": ["string", "null"]}
_NUM = {"type": "number"}
EXTRACTION_SCHEMA = _obj({
    "facts": {"type": "array", "items": _obj({
        "subject": _S, "key": _S, "value": _S,
        "category": {"enum": ["identity", "preference", "environment", "habit", "association"]},
        "confidence": _NUM, "evidence": _S},
        ["subject", "key", "value", "category", "confidence", "evidence"])},
    "commitments": {"type": "array", "items": _obj({     # deadlines are commitments with type="deadline"
        "title": _S,
        "type": {"enum": ["exam", "trip", "deadline", "meeting", "task", "other"]},
        "time_expression": _N, "explicit_date": _N,
        "importance": {"type": "integer"}, "confidence": _NUM, "evidence": _S},
        ["title", "type", "time_expression", "explicit_date", "importance", "confidence", "evidence"])},
    "status_updates": {"type": "array", "items": _obj({
        "refers_to": _S, "new_status": {"enum": ["completed", "cancelled", "rescheduled"]}, "evidence": _S},
        ["refers_to", "new_status", "evidence"])},
    "project_states": {"type": "array", "items": _obj({
        "project": _S, "path": _N, "state": _S, "next_step": _N, "evidence": _S},
        ["project", "path", "state", "next_step", "evidence"])},
    "entity_relations": {"type": "array", "items": _obj({
        "subject": _S, "relation": _S, "object": _S, "evidence": _S},
        ["subject", "relation", "object", "evidence"])},
}, ["facts", "commitments", "status_updates", "project_states", "entity_relations"])

SYSTEM_PROMPT = r"""You extract durable memory from a chat log between a USER and their desktop assistant PULSAR.
Return ONLY JSON that matches the schema. Use [] when a list has nothing.

RULES
1. Extract only what the USER said about themselves, their plans, files/projects or accounts. Never extract what PULSAR said.
2. Ignore one-off commands ("open chrome", "what time is it") and small talk.
3. facts = stable truths: preferences, associations ("Chrome profile 2 is Work"), locations ("projects live in C:\Projects").
   Use a short, stable snake_case `key` (e.g. "chrome_profile_2") so a later value can replace this one.
4. commitments = future events/deadlines/plans. Copy the user's time words EXACTLY into time_expression
   (e.g. "next January"). NEVER compute or guess a date. Fill explicit_date only if the user wrote a full ISO date.
5. status_updates = the user says an earlier plan is finished, cancelled or moved.
6. project_states = work left unfinished/in progress, with a path only if the user gave one.
7. `evidence` must be a short VERBATIM quote (<=200 chars) from a USER line. If you cannot quote it, omit the item.
8. confidence: 0.9 explicit, 0.6 implied. Below 0.5 -> omit. importance: 1 (trivial) .. 5 (critical).

EXAMPLE
USER: my project deadline is in March, remind me later. also chrome profile 2 is my work profile
-> {"facts":[{"subject":"user","key":"chrome_profile_2","value":"Work","category":"association","confidence":0.9,
"evidence":"chrome profile 2 is my work profile"}],
"commitments":[{"title":"Project Deadline","type":"deadline","time_expression":"in March","explicit_date":null,"importance":4,
"confidence":0.9,"evidence":"my project deadline is in March"}],"status_updates":[],"project_states":[],"entity_relations":[]}"""

_SIGNAL = re.compile(
    r"(\b(remember|my|i'm|i am|i will|i'll|plan|planning|exam|deadline|due|tomorrow|next|always|never|prefer|"
    r"project|profile|trip|meeting|cancel\w*|done|finished|postponed|moved)\b|\b(" + _MON_RE + r")\b|[A-Za-z]:\\|\d{4}-\d{2}-\d{2})",
    re.I)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", (s or "").lower())).strip()


def _grounded(evidence: str, user_norm: str) -> bool:
    e = _norm(evidence)
    if len(e) < 6:
        return False
    if e in user_norm:
        return True
    toks, hs = e.split(), set(user_norm.split())
    return sum(t in hs for t in toks) / len(toks) >= 0.85


def _f(x, default=0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


class LlamaJSON:
    """Schema-constrained local extraction. Lazy-loads the GGUF and unloads it after each consolidation run."""

    def __init__(self, gguf_path: str, n_ctx: int = 4096, n_threads: int = 2):
        self.path, self.n_ctx, self.n_threads, self._llm = gguf_path, n_ctx, n_threads, None

    def __call__(self, system: str, user: str, schema: dict) -> str:
        if self._llm is None:
            from llama_cpp import Llama
            self._llm = Llama(model_path=self.path, n_ctx=self.n_ctx, n_threads=self.n_threads, verbose=False)
        out = self._llm.create_chat_completion(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.0, max_tokens=900,
            response_format={"type": "json_object", "schema": schema})
        return out["choices"][0]["message"]["content"]

    def unload(self):
        self._llm = None
        gc.collect()


# ----------------------------------------------------------------------------
# MemoryConsolidator
# ----------------------------------------------------------------------------
class MemoryConsolidator:
    def __init__(self, store: HybridMemoryStore, llm_json: Callable[[str, str, dict], str],
                 idle_gate: Optional[IdleGate] = None, chunk_chars: int = 5000,
                 min_conf: float = 0.6, min_batch: int = 12):
        self.store, self.llm_json, self.gate = store, llm_json, idle_gate
        self.chunk_chars, self.min_conf, self.min_batch = chunk_chars, min_conf, min_batch
        self._fails: Counter = Counter()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._wake: Optional[asyncio.Event] = None
        self._force = False

    # -- scheduling (event-driven: zero polling while idle) --------------------
    def notify(self, force: bool = False) -> None:
        """Thread-safe. Call with force=True at session end / app exit."""
        self._force = self._force or force
        if self._loop and self._wake:
            self._loop.call_soon_threadsafe(self._wake.set)

    async def run_forever(self):
        self._loop, self._wake = asyncio.get_running_loop(), asyncio.Event()
        while True:
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=600)   # backstop retry if the gate was closed
            except asyncio.TimeoutError:
                pass
            self._wake.clear()
            pending = self.store.pending_count()
            stale = time.time() - float(self.store.kv_get("last_consolidation", 0)) > 20 * 3600
            if pending == 0 or not (pending >= self.min_batch or self._force or stale):
                continue
            await self._loop.run_in_executor(None, self._guarded_run)

    def _guarded_run(self):
        _background_thread_mode()
        try:
            stats = self.run_once()
            if not stats.get("paused") and not stats.get("llm_error"):
                self._force = False
                self.store.kv_set("last_consolidation", time.time())
                self.store.prune_episodes(7)
                self.store.sweep_lifecycle()
                self.store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            log.info("consolidation: %s", dict(stats))
        finally:
            getattr(self.llm_json, "unload", lambda: None)()           # give the RAM back

    # -- the actual work ---------------------------------------------------------
    def run_once(self, max_chunks: int = 8) -> Counter:
        stats: Counter = Counter()
        for _ in range(max_chunks):
            if self.gate and not self.gate.ok():                       # user came back -> stop immediately
                stats["paused"] += 1
                break
            turns = self.store.pending_turns(80)
            if not turns:
                break
            sid, chunk, size = turns[0]["session_id"], [], 0
            for t in turns:
                if t["session_id"] != sid or (chunk and size + len(t["text"]) > self.chunk_chars):
                    break
                chunk.append(t)
                size += len(t["text"])
            text = "\n".join(f"{t['role'].upper()}: {t['text'][:self.chunk_chars]}" for t in chunk)
            user_norm = _norm(" ".join(t["text"] for t in chunk if t["role"] == "user"))
            anchor = datetime.fromtimestamp(chunk[-1]["ts"])
            ids = [t["id"] for t in chunk]

            if any(t["role"] == "user" and _SIGNAL.search(t["text"]) for t in chunk):   # cheap pre-filter
                try:
                    data = json.loads(self.llm_json(SYSTEM_PROMPT, text, EXTRACTION_SCHEMA))
                    stats.update(self._persist(data, user_norm, anchor))
                except Exception as e:                                  # bad JSON / model error
                    self._fails[ids[0]] += 1
                    log.warning("extraction failed (%s): %r", self._fails[ids[0]], e)
                    if self._fails[ids[0]] < 2:
                        stats["llm_error"] += 1
                        break                                           # retry later
            else:
                stats["skipped_chunks"] += 1
            self.store.mark_processed(ids)
            stats["chunks"] += 1
        return stats

    def _persist(self, data: dict, user_norm: str, anchor: datetime) -> Counter:
        st, ok = Counter(), lambda x: _f(x.get("confidence"), 0) >= self.min_conf and _grounded(x.get("evidence"), user_norm)
        src = anchor.timestamp()

        for x in data.get("facts", []):
            if not ok(x):
                st["dropped"] += 1
                continue
            subj = f"{_norm(x.get('subject') or 'user')}.{_norm(x.get('key', '')).replace(' ', '_')}"
            self.store.upsert("fact", f"{x['key']} = {x['value']}", subj, importance=0.6,
                              confidence=_f(x["confidence"]), source_ts=src, payload={"category": x.get("category")})
            st["facts"] += 1

        for x in data.get("commitments", []):
            if not ok(x):
                st["dropped"] += 1
                continue
            res = resolve_time(x.get("explicit_date") or "", anchor) or resolve_time(x.get("time_expression") or "", anchor)
            imp = {1: .2, 2: .35, 3: .5, 4: .75, 5: .95}.get(int(_f(x.get("importance"), 3)), .5)
            self.store.upsert(
                "commitment", x["title"], x.get("type", "other"), importance=imp,
                confidence=_f(x["confidence"]) * (res.confidence if res else 0.7),
                event_start=res.start.timestamp() if res else None, event_end=res.end.timestamp() if res else None,
                precision=res.precision if res else None, time_expr=x.get("time_expression"),
                source_ts=src, payload={"type": x.get("type", "other")})
            st["commitments"] += 1

        for x in data.get("status_updates", []):
            if not ok({"confidence": 0.9, "evidence": x.get("evidence")}) or x.get("new_status") == "rescheduled":
                continue                                                # reschedules arrive as a re-stated commitment
            hits = self.store.search(x["refers_to"], k=1, kinds=("commitment",))
            if hits and hits[0]["sim"] >= 0.55:
                self.store.set_status(hits[0]["id"], x["new_status"])
                st["closed"] += 1

        for x in data.get("project_states", []):
            if not ok({"confidence": 0.9, "evidence": x.get("evidence")}):
                continue
            self.store.upsert("project_state", f"{x['state']}" + (f"; next: {x['next_step']}" if x.get("next_step") else ""),
                              x["project"], importance=0.6, source_ts=src,
                              payload={"path": x.get("path"), "next_step": x.get("next_step")})
            st["projects"] += 1

        for x in data.get("entity_relations", []):
            if ok({"confidence": 0.9, "evidence": x.get("evidence")}):
                self.store.add_relation(x["subject"], x["relation"], x["object"])
                st["relations"] += 1
        return st


# ----------------------------------------------------------------------------
# ProactiveFollowUpManager
# ----------------------------------------------------------------------------
LADDER = (60, 30, 14, 7, 3, 1, 0)       # days-before thresholds; each rung fires at most once per item


@dataclass
class Nudge:
    memory_id: str
    kind: str                # upcoming | followup
    title: str
    days_left: Optional[int]
    stage: int
    score: float
    actions: list
    text: str


class ProactiveFollowUpManager:
    def __init__(self, store: HybridMemoryStore, user_name: str = "", quiet_hours=(22, 8),
                 max_per_day: int = 2, cooldown_h: float = 18,
                 can_interrupt: Callable[[], bool] = lambda: True,
                 polish: Optional[Callable[[str], str]] = None):
        self.store, self.user_name, self.quiet = store, user_name, quiet_hours
        self.max_per_day, self.cooldown_h = max_per_day, cooldown_h
        self.can_interrupt, self.polish = can_interrupt, polish
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._poke: Optional[asyncio.Event] = None

    # -- gating ------------------------------------------------------------------
    def may_nudge(self, now=None) -> bool:
        now = now or time.time()
        h = datetime.fromtimestamp(now).hour
        qs, qe = self.quiet
        if (h >= qs or h < qe) if qs > qe else (qs <= h < qe):
            return False
        if int(self.store.kv_get(f"nudges:{datetime.fromtimestamp(now):%Y-%m-%d}", 0)) >= self.max_per_day:
            return False
        return bool(self.can_interrupt())       # False while a chain is running / voice turn active / DND

    # -- candidate selection (pure SQL + arithmetic, no model needed) ------------
    def collect(self, now=None) -> list:
        now = now or time.time()
        self.store.sweep_lifecycle(now)
        out = []
        for m in self.store.upcoming(LADDER[0], now):
            if (m["snoozed_until"] or 0) > now or now - (m["last_nudged_at"] or 0) < self.cooldown_h * 3600:
                continue
            in_window = bool(m["event_end"]) and m["event_start"] <= now <= m["event_end"]
            days = 0 if in_window else max(0, math.ceil((m["event_start"] - now) / 86400))
            stage = sum(1 for t in LADDER if days <= t)
            if stage <= (m["nudge_stage"] or 0):
                continue
            acts = self._actions(m)
            urgency = 1 / (1 + days)
            out.append(Nudge(m["id"], "upcoming", m["content"], days, stage,
                             0.6 * (m["importance"] or .5) + 0.4 * urgency, acts, self._render(m, days, acts)))
        for m in self.store.past_commitments(now - 3 * 86400, now):
            if (m["snoozed_until"] or 0) > now:
                continue
            out.append(Nudge(m["id"], "followup", m["content"], None, 99, 0.3 * (m["importance"] or .5),
                             [{"type": "mark_done", "label": "mark it done", "memory_id": m["id"]},
                              {"type": "reschedule", "label": "reschedule it", "memory_id": m["id"]}],
                             self._render(m, None, [])))
        return sorted(out, key=lambda n: -n.score)

    def _actions(self, m) -> list:
        """Only actions backed by stored data - nothing the model invents."""
        acts, typ = [], json.loads(m["payload"] or "{}").get("type", "other")
        if typ in ("exam", "deadline"):
            acts.append({"type": "start_prep", "label": f"start preparing for {m['content']}", "memory_id": m["id"]})
        row = self.store.db.execute(
            "SELECT subject, payload FROM memories WHERE kind='project_state' AND status='active' "
            "ORDER BY updated_at DESC LIMIT 1").fetchone()
        if row:
            p = json.loads(row["payload"] or "{}")
            if p.get("path"):
                acts.append({"type": "open_project", "label": f"open {row['subject']} ({p['path']})", "path": p["path"]})
        return acts[:2]

    def _render(self, m, days, acts) -> str:
        t, d = m["content"], datetime.fromtimestamp(m["event_start"]) if m["event_start"] else None
        prec = m["precision"]
        if days is None:
            body = f"{t} was scheduled around {d:%d %b %Y}. How did it go?"
        elif prec == "month":
            body = (f"{t} falls this month ({d:%B %Y})." if days == 0 else
                    f"{t} is planned for {d:%B %Y} - about {days} days until that month starts.")
        elif prec == "week":
            body = f"{t} is the week of {d:%d %b} ({days} days)." if days else f"{t} is this week."
        else:
            body = (f"{t} is today." if days == 0 else f"{t} is tomorrow." if days == 1 else
                    f"{t} is {days} days away ({d:%a, %d %b %Y}).")
        if prec in ("month", "week") and days is not None and days <= 14:
            body += " Do you know the exact date? I can pin it."
        if acts:
            body += " Should we " + " or ".join(a["label"] for a in acts) + "?"
        text = (f"Hey {self.user_name}, " if self.user_name else "") + body
        if self.polish:                                   # optional LLM rewording, accepted only if no new numbers appear
            try:
                alt = self.polish(text)
                if set(re.findall(r"\d+", alt)) <= set(re.findall(r"\d+", text)):
                    return alt
            except Exception:
                pass
        return text

    # -- emission ----------------------------------------------------------------
    def next_payload(self, now=None) -> Optional[dict]:
        now = now or time.time()
        if not self.may_nudge(now):
            return None
        nudges = self.collect(now)
        if not nudges:
            return None
        top = nudges[0]
        with self.store._lock, self.store.db:
            self.store.db.execute("UPDATE memories SET last_nudged_at=?, nudge_stage=? WHERE id=?",
                                  (now, top.stage, top.memory_id))
        self.store.kv_set(f"nudges:{datetime.fromtimestamp(now):%Y-%m-%d}",
                          int(self.store.kv_get(f"nudges:{datetime.fromtimestamp(now):%Y-%m-%d}", 0)) + 1)
        extra = len(nudges) - 1
        return {"type": "proactive.nudge", "memory_id": top.memory_id, "kind": top.kind,
                "text": top.text + (f" ({extra} more coming up - ask 'what's ahead'.)" if extra else ""),
                "actions": top.actions, "replies": ["accept", "snooze", "dismiss", "done"]}

    def acknowledge(self, memory_id: str, outcome: str, snooze_h: float = 24) -> None:
        now = time.time()
        if outcome == "done":
            self.store.set_status(memory_id, "completed")
        elif outcome == "snooze":
            self._set(memory_id, "snoozed_until=?", now + snooze_h * 3600)
        elif outcome == "dismiss":
            with self.store._lock, self.store.db:
                self.store.db.execute(
                    "UPDATE memories SET dismissals=dismissals+1, "
                    "nudge_stage=CASE WHEN dismissals+1>=2 THEN 99 ELSE nudge_stage END WHERE id=?", (memory_id,))
        # "accept": the orchestrator runs the chosen action; nothing to store

    def _set(self, mid, assignment, val):
        with self.store._lock, self.store.db:
            self.store.db.execute(f"UPDATE memories SET {assignment} WHERE id=?", (val, mid))

    # -- idle loop: sleeps until the next ladder crossing, never polls ---------------
    def poke(self) -> None:
        """Thread-safe. Call on: window focus, user returning from idle, new/changed commitments, resume-from-sleep."""
        if self._loop and self._poke:
            self._loop.call_soon_threadsafe(self._poke.set)

    def next_wake(self, now=None) -> float:
        now = now or time.time()
        best = now + 3 * 3600                       # cap: survives sleep/hibernate and clock changes
        for m in self.store.upcoming(400, now):
            for t in LADDER:                        # descending -> first future crossing is the earliest
                ts = m["event_start"] - t * 86400
                if ts > now:
                    best = min(best, ts)
                    break
        return best

    async def run(self, emit: Callable[[dict], None], user_present: Callable[[], bool]):
        self._loop, self._poke = asyncio.get_running_loop(), asyncio.Event()
        while True:
            timeout = max(5.0, self.next_wake() - time.time())
            try:
                await asyncio.wait_for(self._poke.wait(), timeout)
            except asyncio.TimeoutError:
                pass
            self._poke.clear()
            if user_present():                      # nobody home -> hold it until they return
                payload = await self._loop.run_in_executor(None, self.next_payload)
                if payload:
                    emit(payload)


# ----------------------------------------------------------------------------
# Facade: ONE instance per process, shared by Voice / Chat / Orchestrator threads
# ----------------------------------------------------------------------------
class MemoryService:
    _inst: Optional["MemoryService"] = None
    _guard = threading.Lock()

    @classmethod
    def get(cls, **kw) -> "MemoryService":
        with cls._guard:
            if cls._inst is None:
                cls._inst = cls(**kw)
            return cls._inst

    def __init__(self, data_dir="data/memory", embedder: Optional[Embedder] = None,
                 llm_json=None, user_name: str = "", can_interrupt=lambda: True):
        import os
        if not user_name:
            try:
                from core_ai.core.jarvis_persona import get_persona_settings
                cfg = get_persona_settings()
                user_name = cfg.get("userTitle", "")
            except Exception:
                user_name = os.environ.get("USERNAME", "")
        self.store = HybridMemoryStore(Path(data_dir) / "pulsar_memory.db", embedder or Embedder())
        self.session_id = uuid.uuid4().hex[:8]           # per launch; the DB, not this id, is the memory identity
        self.working = WorkingMemory()
        for r in self.store.recent_turns(8):             # one indexed query: restart no longer forgets the last turns
            self.working.add(r["role"], r["text"])
        self.store.sweep_lifecycle()
        self.consolidator = MemoryConsolidator(self.store, llm_json, IdleGate()) if llm_json else None
        self.proactive = ProactiveFollowUpManager(self.store, user_name, can_interrupt=can_interrupt)
        self.store.on_change = self.proactive.poke

    def record_turn(self, role: str, text: str, source: str = "chat") -> None:
        self.working.add(role, text)
        self.store.log_turn(self.session_id, role, text, source)
        if self.consolidator and self.store.pending_count() % 12 == 0:
            self.consolidator.notify()

    def build_context(self, query: str, max_chars: int = 1600) -> str:
        hits = [h for h in self.store.search(query, k=6, kinds=("fact", "project_state"))
                if h["sim"] >= 0.30 or h["lex"]]
        soon = self.store.upcoming(30)[:3]
        parts = []
        if hits:
            parts.append("[KNOWN ABOUT USER]\n" + "\n".join(f"- {h['content']}" for h in hits))
        if soon:
            parts.append("[UPCOMING]\n" + "\n".join(
                f"- {s['content']} ({datetime.fromtimestamp(s['event_start']):%d %b %Y}"
                f"{', month-level' if s['precision'] == 'month' else ''})" for s in soon))
        parts.append("[RECENT]\n" + self.working.render())
        return "\n\n".join(parts)[-max_chars:]

    def end_session(self) -> None:
        if self.consolidator:
            self.consolidator.notify(force=True)
