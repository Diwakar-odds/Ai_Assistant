import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base_agent import BaseAgent
from ..models import Task, TaskResult

logger = logging.getLogger(__name__)


class StudentAgent(BaseAgent):
    """
    Educational & study assistant agent:
    - Symbolic math solving via SymPy (safe parser, no eval)
    - Flashcards, study notes, and topic explanations via Unified LLM (with offline fallback)
    - Local folder document ingestion (.pdf, .txt, .md, .csv, .json) + portable RAG Q&A
    """

    def __init__(self, agent_id: str = "student-001", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config or {})
        self.name = "Student Agent"
        self.category = "education"
        self.description = "Supports studying, math solving, flashcards, summaries, and RAG over local notes."
        self.capabilities = [
            "learn_topic",
            "take_notes",
            "summarize_learning",
            "create_flashcards",
            "solve_math",
            "study_folder",
            "answer_exam_questions",
        ]
        persist_cfg = self.config.get("persist_directory")
        self.persist_directory = str(Path(persist_cfg).resolve()) if persist_cfg else str(Path(os.getcwd()) / "data" / "rag_db")
        self._chunks: List[Dict[str, str]] = []
        self.vector_store = None

    def _index_file_path(self) -> Path:
        return Path(self.persist_directory) / "notes_index.json"

    async def can_handle(self, task: Task) -> bool:
        """Check if task is educational, math solving, flashcards, or notes RAG."""
        desc = (task.description or "").lower()
        keywords = [
            "study", "exam", "quiz", "flashcard", "notes", "learn", "explain",
            "solve", "equation", "math", "algebra", "calculus", "derivative", "integral",
            "folder", "read my", "rag", "tutor", "homework",
        ]
        return any(kw in desc for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        """Execute student/study/math task."""
        desc = (task.description or "").lower()
        req_caps = set(c.lower() for c in (task.required_capabilities or []))

        if "solve_math" in req_caps or any(k in desc for k in ("solve ", "equation", "math", "derivative", "integral", "simplify", "factor ")) or re.search(r"\b[0-9x]\s*[+\-*/^=]\s*[0-9x]", desc):
            return await self._solve_math(task)

        if "study_folder" in req_caps or ("folder" in desc and any(k in desc for k in ("read", "ingest", "study", "prepare", "load"))):
            return await self._ingest_folder(task)

        if "create_flashcards" in req_caps or "flashcard" in desc or "quiz" in desc:
            return await self._create_flashcards(task)

        if "answer_exam_questions" in req_caps or task.params.get("folder_rag") or (self._chunks or self._index_file_path().exists()):
            if "question" in desc or "?" in desc or "from notes" in desc or "rag" in desc or "exam" in desc:
                return await self._answer_question(task)

        if "summarize_learning" in req_caps or "take_notes" in req_caps or "note" in desc or "summarize" in desc:
            return await self._summarize_or_notes(task)

        return await self._learn_topic(task)

    async def _solve_math(self, task: Task) -> TaskResult:
        """Safely solve algebraic equations, calculus, or numeric expressions using SymPy."""
        params = task.params or {}
        raw_expr = str(params.get("expression") or params.get("equation") or task.description).strip()
        desc = (task.description or "").lower()

        def _compute() -> Dict[str, Any]:
            import sympy as sp
            from sympy.parsing.sympy_parser import (
                implicit_multiplication_application,
                parse_expr,
                standard_transformations,
            )

            transformations = standard_transformations + (implicit_multiplication_application,)

            cleaned = re.sub(
                r"^(solve|calculate|compute|simplify|evaluate|find\s+derivative\s+of|differentiate|integrate)\s+",
                "",
                raw_expr,
                flags=re.IGNORECASE,
            ).strip()
            cleaned = cleaned.replace("^", "**").strip(" .?")

            # Extract mathematical snippet if embedded in prose
            if "=" in cleaned:
                # Find equation segment around '='
                eq_match = re.search(r"([A-Za-z0-9_.\+\-\*/\(\)\s\*]+\s*=\s*[A-Za-z0-9_.\+\-\*/\(\)\s\*]+)", cleaned)
                eq_str = eq_match.group(1) if eq_match else cleaned
                lhs_s, rhs_s = eq_str.split("=", 1)
                lhs = parse_expr(lhs_s.strip(), transformations=transformations)
                rhs = parse_expr(rhs_s.strip(), transformations=transformations)
                equation = sp.Eq(lhs, rhs)
                free = sorted(equation.free_symbols, key=lambda s: s.name)
                var_name = params.get("variable")
                target_sym = sp.Symbol(var_name) if var_name else (free[0] if free else sp.Symbol("x"))
                sol = sp.solve(equation, target_sym)
                return {
                    "kind": "equation",
                    "input": f"{lhs} = {rhs}",
                    "variable": str(target_sym),
                    "solutions": [str(s) for s in sol],
                    "answer": f"{target_sym} = {', '.join(str(s) for s in sol)}" if sol else "No solution",
                }

            expr = parse_expr(cleaned, transformations=transformations)
            free = sorted(expr.free_symbols, key=lambda s: s.name)
            sym = sp.Symbol(params["variable"]) if params.get("variable") else (free[0] if free else sp.Symbol("x"))

            if "derivative" in desc or "differentiate" in desc:
                res = sp.diff(expr, sym)
                return {"kind": "derivative", "input": str(expr), "answer": str(res)}
            if "integrate" in desc or "integral" in desc:
                res = sp.integrate(expr, sym)
                return {"kind": "integral", "input": str(expr), "answer": str(res)}
            if "factor" in desc:
                res = sp.factor(expr)
                return {"kind": "factor", "input": str(expr), "answer": str(res)}

            if not free:
                simplified = sp.simplify(expr)
                numeric = float(simplified.evalf()) if simplified.is_real else str(simplified.evalf())
                return {"kind": "arithmetic", "input": str(expr), "answer": str(simplified), "numeric": numeric}

            simplified = sp.simplify(expr)
            return {"kind": "simplify", "input": str(expr), "answer": str(simplified)}

        try:
            res = await asyncio.to_thread(_compute)
            ans = str(res["answer"])
            return TaskResult(
                success=True,
                data={
                    **res,
                    "output": ans,
                    "text": ans,
                    "summary": f"Solved {res['kind']}: {ans}",
                    "message": ans,
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Math solving failed for '{raw_expr}': {exc}")

    @staticmethod
    def _chunk_text(text: str, source: str, chunk_size: int = 900, overlap: int = 120) -> List[Dict[str, str]]:
        clean = " ".join(text.split())
        if not clean:
            return []
        chunks: List[Dict[str, str]] = []
        start = 0
        while start < len(clean):
            end = start + chunk_size
            chunks.append({"text": clean[start:end], "source": source})
            if end >= len(clean):
                break
            start = max(start + 1, end - overlap)
        return chunks

    async def _ingest_folder(self, task: Task) -> TaskResult:
        """Read PDF, TXT, MD, CSV, and JSON notes in a folder into portable RAG index."""
        params = task.params or {}
        folder_path = params.get("path")
        if not folder_path or not os.path.exists(folder_path):
            matches = re.findall(r"([A-Za-z]:\\[^\s'\"]+|/[^\s'\"]+)", task.description or "")
            if matches and os.path.exists(matches[0]):
                folder_path = matches[0]
            else:
                return TaskResult(success=False, error="Please provide a valid folder path via params['path'].")

        root_path = Path(folder_path).resolve()
        if not root_path.is_dir():
            return TaskResult(success=False, error=f"Path is not a directory: {root_path}")

        def _load_documents() -> Dict[str, Any]:
            all_chunks: List[Dict[str, str]] = []
            files_read: List[str] = []
            supported = {".txt", ".md", ".csv", ".json", ".pdf"}

            for p in sorted(root_path.rglob("*")):
                if not p.is_file() or p.suffix.lower() not in supported:
                    continue
                content = ""
                try:
                    if p.suffix.lower() == ".pdf":
                        import PyPDF2

                        with open(p, "rb") as fh:
                            reader = PyPDF2.PdfReader(fh)
                            content = "\n".join(page.extract_text() or "" for page in reader.pages)
                    else:
                        content = p.read_text(encoding="utf-8", errors="ignore")
                except Exception as read_exc:
                    logger.debug("Skipping unreadable file %s: %s", p, read_exc)
                    continue

                file_chunks = self._chunk_text(content, source=str(p))
                if file_chunks:
                    files_read.append(str(p))
                    all_chunks.extend(file_chunks)

            Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
            index_path = self._index_file_path()
            index_path.write_text(json.dumps({"chunks": all_chunks, "files": files_read}, indent=2), encoding="utf-8")
            return {"chunks": all_chunks, "files": files_read, "index_path": str(index_path)}

        try:
            loaded = await asyncio.to_thread(_load_documents)
            if not loaded["chunks"]:
                return TaskResult(success=False, error=f"No readable PDF/TXT/MD/CSV/JSON notes found in {root_path}")

            self._chunks = loaded["chunks"]
            msg = f"Indexed {len(loaded['chunks'])} chunk(s) from {len(loaded['files'])} file(s) in {root_path}."
            return TaskResult(
                success=True,
                output_path=loaded["index_path"],
                data={
                    "message": msg,
                    "summary": msg,
                    "output": msg,
                    "files_count": len(loaded["files"]),
                    "chunks_count": len(loaded["chunks"]),
                    "files": loaded["files"],
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Failed to ingest folder: {exc}")

    def _retrieve_relevant_chunks(self, query: str, k: int = 3) -> List[Dict[str, str]]:
        chunks = list(self._chunks)
        if not chunks and self._index_file_path().exists():
            try:
                payload = json.loads(self._index_file_path().read_text(encoding="utf-8"))
                chunks = payload.get("chunks", [])
                self._chunks = chunks
            except Exception:
                chunks = []
        if not chunks:
            return []

        query_terms = set(re.findall(r"[a-z0-9]{2,}", query.lower()))
        scored = []
        for idx, chunk in enumerate(chunks):
            chunk_terms = set(re.findall(r"[a-z0-9]{2,}", chunk.get("text", "").lower()))
            overlap = len(query_terms & chunk_terms)
            scored.append((overlap, -idx, chunk))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [item[2] for item in scored[:k]]

    async def _answer_question(self, task: Task) -> TaskResult:
        """Answer a question using indexed notes and Unified LLM (with extractive fallback)."""
        params = task.params or {}
        question = str(params.get("query") or params.get("question") or task.description).strip()
        top_chunks = await asyncio.to_thread(self._retrieve_relevant_chunks, question, 3)

        if not top_chunks:
            return await self._learn_topic(task)

        context = "\n\n".join(c["text"] for c in top_chunks)
        sources = list(dict.fromkeys(c["source"] for c in top_chunks))

        answer = await self.chat_llm(
            f"Use ONLY the notes below to answer the student's question accurately.\n\nNOTES:\n{context}\n\nQUESTION: {question}",
            system_message="You are a patient AI tutor helping a student study from their own notes.",
        )
        if not answer:
            answer = f"Based on your notes ({', '.join(Path(s).name for s in sources)}):\n\n{top_chunks[0]['text'][:600]}"

        return TaskResult(
            success=True,
            data={
                "answer": answer,
                "output": answer,
                "text": answer,
                "summary": answer[:240],
                "sources": sources,
            },
        )

    async def _create_flashcards(self, task: Task) -> TaskResult:
        """Generate Q&A flashcards for a topic or upstream notes."""
        params = task.params or {}
        topic = str(params.get("topic") or task.description).strip()
        upstream = self._extract_upstream_text(task)
        count = max(1, min(20, int(params.get("count", 5))))

        source_text = upstream or str(params.get("content") or topic)
        llm_resp = await self.chat_llm(
            f"Create {count} concise study flashcards as a JSON array of objects with keys 'question' and 'answer'.\n\nMaterial:\n{source_text}",
            system_message="You are an educational flashcard author. Output valid JSON array.",
        )

        cards: List[Dict[str, str]] = []
        if llm_resp:
            try:
                raw = llm_resp
                if "```json" in raw:
                    raw = raw.split("```json", 1)[1].split("```", 1)[0]
                elif "```" in raw:
                    raw = raw.split("```", 1)[1].split("```", 1)[0]
                parsed = json.loads(raw.strip())
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict) and item.get("question"):
                            cards.append({"question": str(item["question"]), "answer": str(item.get("answer", ""))})
            except Exception:
                cards = []

        if not cards:
            lines = [ln.strip("-* ") for ln in source_text.splitlines() if ln.strip()]
            cards = [
                {
                    "question": f"What is the key concept #{i + 1} regarding {topic[:60]}?",
                    "answer": lines[i] if i < len(lines) else f"Core idea {i + 1} related to {topic}.",
                }
                for i in range(min(count, max(3, len(lines))))
            ]

        formatted = "\n\n".join(f"Q{i+1}: {c['question']}\nA{i+1}: {c['answer']}" for i, c in enumerate(cards))
        return TaskResult(
            success=True,
            data={
                "cards": cards,
                "count": len(cards),
                "output": formatted,
                "text": formatted,
                "summary": f"Created {len(cards)} flashcards for '{topic[:60]}'",
            },
        )

    async def _summarize_or_notes(self, task: Task) -> TaskResult:
        """Create structured study notes or summarize material."""
        params = task.params or {}
        upstream = self._extract_upstream_text(task)
        material = str(params.get("content") or upstream or task.description).strip()
        topic = str(params.get("topic") or task.description[:80]).strip()

        notes = await self.chat_llm(
            f"Create structured study notes with Key Takeaways and Definitions for:\n{material}",
            system_message="You are an expert academic note-taker.",
        )
        if not notes:
            bullets = [ln.strip() for ln in re.split(r"[.\n]+", material) if len(ln.strip()) > 10][:6]
            notes = f"# Study Notes: {topic}\n\n" + "\n".join(f"- {b}" for b in (bullets or [material]))

        output_path = None
        if params.get("save") or params.get("output_path") or params.get("filename"):
            output_path = self._resolve_output_path(task, default_filename=f"notes_{task.task_id[:8]}.md")
            Path(output_path).write_text(notes, encoding="utf-8")

        return TaskResult(
            success=True,
            output_path=output_path,
            artifacts=[output_path] if output_path else [],
            data={"notes": notes, "output": notes, "text": notes, "summary": notes[:240]},
        )

    async def _learn_topic(self, task: Task) -> TaskResult:
        """Explain a concept cleanly for learning."""
        params = task.params or {}
        topic = str(params.get("topic") or task.description).strip()
        upstream = self._extract_upstream_text(task)
        prompt = f"Explain the topic clearly with examples and a quick check question:\n{topic}"
        if upstream:
            prompt += f"\n\nReference context:\n{upstream}"

        explanation = await self.chat_llm(
            prompt,
            system_message="You are an encouraging, clear STEM/humanities tutor.",
        )
        if not explanation:
            explanation = (
                f"Study Guide for '{topic}':\n"
                f"1. Core definition and intuition of {topic}.\n"
                f"2. Key mechanisms/examples.\n"
                f"3. Common pitfalls and practice question."
            )

        return TaskResult(
            success=True,
            data={"answer": explanation, "output": explanation, "text": explanation, "summary": explanation[:240]},
        )
