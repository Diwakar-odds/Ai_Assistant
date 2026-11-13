import logging
from typing import Any, Dict, Optional

from ..base_agent import BaseAgent
from ..models import Task, TaskResult

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    """Handles content generation, writing, proofreading, and summarization using LLMs."""

    def __init__(self, agent_id: str = "writer-001", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config or {})
        self.name = "Writer Agent"
        self.category = "writer"
        self.description = "Generates high-quality text content, articles, emails, scripts, and summaries."
        self.capabilities = [
            "write_article",
            "summarize_text",
            "draft_email",
            "proofread",
            "creative_writing",
        ]
        self._mock_mode = bool(self.config.get("mock_mode", False))

    async def can_handle(self, task: Task) -> bool:
        keywords = [
            "write", "draft", "summarize", "summary", "blog", "article",
            "email", "essay", "proofread", "script", "story", "poem", "rewrite",
        ]
        return any(kw in (task.description or "").lower() for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        try:
            desc = task.description or ""
            desc_low = desc.lower()
            topic = str(task.params.get("topic") or desc)
            content_type = str(task.params.get("type") or self._infer_type(desc_low))
            tone = str(task.params.get("tone") or "professional")
            length = task.params.get("length", 400)
            upstream_context = self._extract_upstream_text(task)
            source_text = str(task.params.get("text") or task.params.get("content") or upstream_context or "")

            force_mock = self._mock_mode or bool(task.params.get("mock", False))
            used_llm = False
            content: Optional[str] = None

            if not force_mock:
                prompt = self._build_prompt(
                    description=desc,
                    topic=topic,
                    content_type=content_type,
                    tone=tone,
                    length=length,
                    source_text=source_text,
                )
                content = await self.chat_llm(
                    prompt,
                    system_message=(
                        "You are an expert writer and editor. Produce clear, accurate, "
                        "well-structured writing directly without preamble."
                    ),
                    max_tokens=1200,
                    temperature=0.6,
                )
                if content:
                    used_llm = True

            if not content:
                content = self._generate_fallback_content(
                    topic=topic,
                    content_type=content_type,
                    source_text=source_text,
                )

            output_path = None
            if task.params.get("filename") or task.params.get("output_path"):
                output_path = self._resolve_output_path(
                    task,
                    default_filename=f"writer_{task.task_id[:8]}.md",
                )
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)

            summary = content[:240] + ("..." if len(content) > 240 else "")
            return TaskResult(
                success=True,
                output_path=output_path,
                artifacts=[output_path] if output_path else [],
                data={
                    "content": content,
                    "text": content,
                    "output": content,
                    "summary": summary,
                    "used_llm": used_llm,
                    "message": f"Generated {content_type} ({len(content)} chars).",
                },
                metadata={"used_llm": used_llm, "content_type": content_type},
            )
        except Exception as exc:
            logger.error("[%s] Writer execution failed: %s", self.agent_id, exc, exc_info=True)
            return TaskResult(success=False, error=str(exc))

    @staticmethod
    def _infer_type(desc_low: str) -> str:
        if "proofread" in desc_low or "grammar" in desc_low:
            return "proofread"
        if "summar" in desc_low:
            return "summary"
        if "email" in desc_low or "mail" in desc_low:
            return "email"
        if "script" in desc_low:
            return "script"
        if "essay" in desc_low:
            return "essay"
        return "article"

    @staticmethod
    def _build_prompt(
        description: str,
        topic: str,
        content_type: str,
        tone: str,
        length: Any,
        source_text: str,
    ) -> str:
        ctx_block = f"\n\nReference Material / Context:\n{source_text[:4000]}" if source_text else ""
        if content_type == "proofread":
            return (
                f"Proofread and improve the following text for grammar, clarity, and style "
                f"(tone: {tone}). List brief corrections followed by the revised text.{ctx_block}\n\n"
                f"Instruction: {description}"
            )
        if content_type == "summary":
            return (
                f"Write a concise, clear summary (~{length} words, tone: {tone}) for: {topic}.{ctx_block}"
            )
        if content_type == "email":
            return (
                f"Draft a {tone} email about '{topic}' (include Subject line and clear body).{ctx_block}"
            )
        if content_type == "script":
            return (
                f"Write an engaging {tone} script (~{length} words) about '{topic}'.{ctx_block}"
            )
        return (
            f"Write a well-structured {content_type} (~{length} words, tone: {tone}) on '{topic}'. "
            f"Original request: {description}.{ctx_block}"
        )

    @staticmethod
    def _generate_fallback_content(topic: str, content_type: str, source_text: str = "") -> str:
        if content_type == "email" or "email" in topic.lower():
            body = source_text[:500] if source_text else f"I wanted to share an update regarding {topic}."
            return (
                f"Subject: Update regarding {topic}\n\n"
                f"Hello,\n\n{body}\n\nBest regards,\nAI Assistant"
            )
        if content_type == "summary":
            if source_text:
                sentences = [s.strip() for s in source_text.replace("\n", " ").split(".") if s.strip()]
                condensed = ". ".join(sentences[:4]) + ("." if sentences else "")
                return f"Summary ({topic}):\n{condensed}"
            return f"Summary of {topic}: Key points compiled and organized for quick review."
        if content_type == "proofread":
            target = source_text or topic
            return f"Proofread Review:\n- Checked clarity and structure.\n\nRevised Text:\n{target}"

        ctx_section = f"\n\n## Research Context\n{source_text[:1000]}" if source_text else ""
        return (
            f"# {topic.strip().title()}\n\n"
            f"## Overview\nThis document covers {topic.strip()}.\n\n"
            f"## Key Takeaways\n- Core principles and practical context for {topic.strip()}\n"
            f"- Structured breakdown ready for presentation or publication"
            f"{ctx_section}\n\n"
            f"## Conclusion\n{topic.strip()} remains an impactful area of focus."
        )
