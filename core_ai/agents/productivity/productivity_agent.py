import asyncio
import csv
import importlib.util
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base_agent import BaseAgent
from ..models import Task, TaskResult, VerificationResult

logger = logging.getLogger(__name__)


class ProductivityAgent(BaseAgent):
    """Handles office productivity tasks: Word, Excel, PowerPoint, PDF, and format conversions."""

    def __init__(self, agent_id: str = "productivity-001", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config or {})
        self.name = "Productivity Agent"
        self.category = "productivity"
        self.description = "Handles Word, Excel, PowerPoint, PDF creation and document conversion."
        self.capabilities = [
            "create_word_document",
            "create_excel_spreadsheet",
            "create_powerpoint",
            "create_pdf",
            "edit_document",
            "convert_formats",
        ]

    async def can_handle(self, task: Task) -> bool:
        keywords = [
            "document", "spreadsheet", "presentation", "pdf",
            "word", "excel", "powerpoint", "ppt", "pptx", "docx",
            "xlsx", "doc", "xls", "slides", "convert",
        ]
        return any(kw in (task.description or "").lower() for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        try:
            task_type = self._identify_task_type(task)
            logger.debug("[%s] Executing task type: %s", self.agent_id, task_type)

            if task_type == "word_document":
                return await self._create_word_document(task)
            if task_type == "excel_spreadsheet":
                return await self._create_spreadsheet(task)
            if task_type == "powerpoint":
                return await self._create_presentation(task)
            if task_type == "pdf":
                return await self._create_pdf(task)
            if task_type == "convert":
                return await self._convert_formats(task)
            return TaskResult(success=False, error=f"Unknown or unsupported document type: {task_type}")
        except Exception as exc:
            logger.error("[%s] Productivity execution failed: %s", self.agent_id, exc, exc_info=True)
            return TaskResult(success=False, error=str(exc))

    def _identify_task_type(self, task: Task) -> str:
        desc = (task.description or "").lower()
        fmt = str(task.params.get("format") or "").lower()
        if fmt == "pdf" or "pdf" in desc:
            return "pdf"
        if "convert" in desc or (task.params.get("source_path") and task.params.get("target_format")):
            return "convert"
        if any(x in desc for x in ("powerpoint", "pptx", "ppt", "slide", "presentation")):
            return "powerpoint"
        if any(x in desc for x in ("excel", "xlsx", "spreadsheet", "csv", "sheet", "xls")):
            return "excel_spreadsheet"
        if any(x in desc for x in ("word", "docx", "doc")):
            return "word_document"
        if any(x in desc for x in ("document", "report", "text file")):
            if importlib.util.find_spec("docx") is not None:
                return "word_document"
            return "pdf"
        return "unknown"

    async def _create_word_document(self, task: Task) -> TaskResult:
        try:
            from docx import Document
            from docx.shared import Inches
        except ImportError:
            return TaskResult(
                success=False,
                error="Missing optional dependency 'python-docx'. Install with: pip install python-docx",
            )

        title = str(task.params.get("title") or "Document")
        content = task.params.get("content")
        if content is None:
            content = self._extract_upstream_text(task) or task.description
        images = task.params.get("images") or []
        output_path = self._resolve_output_path(task, f"document_{task.task_id[:8]}.docx")

        def _build_docx() -> None:
            doc = Document()
            doc.add_heading(title, 0)
            if isinstance(content, str):
                for block in content.split("\n\n"):
                    if block.strip():
                        doc.add_paragraph(block.strip())
            elif isinstance(content, list):
                for para in content:
                    doc.add_paragraph(str(para))
            for img in images:
                if img and os.path.exists(str(img)):
                    doc.add_picture(str(img), width=Inches(5.5))
            doc.save(output_path)

        await asyncio.to_thread(_build_docx)
        msg = f"Word document created at {output_path}"
        return TaskResult(
            success=True,
            output_path=output_path,
            artifacts=[output_path],
            data={
                "filename": os.path.basename(output_path),
                "output_path": output_path,
                "output": msg,
                "message": msg,
            },
        )

    async def _create_spreadsheet(self, task: Task) -> TaskResult:
        try:
            from openpyxl import Workbook
        except ImportError:
            return TaskResult(
                success=False,
                error="Missing optional dependency 'openpyxl'. Install with: pip install openpyxl",
            )

        title = str(task.params.get("title") or "Sheet1")[:31]
        data = task.params.get("data", [])
        output_path = self._resolve_output_path(task, f"sheet_{task.task_id[:8]}.xlsx")

        def _build_xlsx() -> int:
            wb = Workbook()
            ws = wb.active
            ws.title = title
            rows_written = 0
            if isinstance(data, list) and data:
                if isinstance(data[0], dict):
                    headers = list(data[0].keys())
                    ws.append(headers)
                    rows_written += 1
                    for row in data:
                        ws.append([row.get(h) for h in headers])
                        rows_written += 1
                else:
                    for row in data:
                        ws.append(list(row) if isinstance(row, (list, tuple)) else [row])
                        rows_written += 1
            elif isinstance(data, dict) and data:
                ws.append(["Key", "Value"])
                rows_written += 1
                for k, v in data.items():
                    ws.append([str(k), str(v)])
                    rows_written += 1
            wb.save(output_path)
            return rows_written

        rows_count = await asyncio.to_thread(_build_xlsx)
        msg = f"Excel spreadsheet created at {output_path} ({rows_count} rows)"
        return TaskResult(
            success=True,
            output_path=output_path,
            artifacts=[output_path],
            data={
                "filename": os.path.basename(output_path),
                "output_path": output_path,
                "rows": rows_count,
                "output": msg,
                "message": msg,
            },
        )

    async def _create_presentation(self, task: Task) -> TaskResult:
        try:
            from pptx import Presentation
            from pptx.util import Inches
        except ImportError:
            return TaskResult(
                success=False,
                error="Missing optional dependency 'python-pptx'. Install with: pip install python-pptx",
            )

        title = str(task.params.get("title") or "Presentation")
        subtitle = str(task.params.get("subtitle") or "")
        slides_data = task.params.get("slides")
        if not slides_data:
            upstream = self._extract_upstream_text(task)
            if upstream:
                slides_data = [
                    {"title": f"Section {i+1}", "content": chunk[:400]}
                    for i, chunk in enumerate([c for c in upstream.split("\n\n") if c.strip()][:5])
                ]
            else:
                slides_data = []

        output_path = self._resolve_output_path(task, f"presentation_{task.task_id[:8]}.pptx")

        def _build_pptx() -> int:
            prs = Presentation()
            title_slide = prs.slides.add_slide(prs.slide_layouts[0])
            if title_slide.shapes.title:
                title_slide.shapes.title.text = title
            if len(title_slide.placeholders) > 1:
                title_slide.placeholders[1].text = subtitle

            for slide_info in slides_data:
                if isinstance(slide_info, str):
                    slide_info = {"title": "Slide", "content": slide_info}
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                if slide.shapes.title and "title" in slide_info:
                    slide.shapes.title.text = str(slide_info["title"])
                if len(slide.placeholders) > 1 and "content" in slide_info:
                    slide.placeholders[1].text_frame.text = str(slide_info["content"])
                img_path = slide_info.get("image")
                if img_path and os.path.exists(str(img_path)):
                    slide.shapes.add_picture(str(img_path), Inches(5.5), Inches(2.0), width=Inches(3.5))

            prs.save(output_path)
            return len(prs.slides)

        slide_count = await asyncio.to_thread(_build_pptx)
        msg = f"PowerPoint presentation created at {output_path} ({slide_count} slides)"
        return TaskResult(
            success=True,
            output_path=output_path,
            artifacts=[output_path],
            data={
                "filename": os.path.basename(output_path),
                "output_path": output_path,
                "slide_count": slide_count,
                "output": msg,
                "message": msg,
            },
        )

    async def _create_pdf(self, task: Task) -> TaskResult:
        title = str(task.params.get("title") or "Document")
        content = task.params.get("content")
        if content is None:
            content = self._extract_upstream_text(task) or task.description
        if isinstance(content, list):
            content_text = "\n\n".join(str(x) for x in content)
        else:
            content_text = str(content or "")

        output_path = self._resolve_output_path(task, f"document_{task.task_id[:8]}.pdf")

        def _build_pdf() -> None:
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas

                c = canvas.Canvas(output_path, pagesize=letter)
                width, height = letter
                y = height - 60
                c.setFont("Helvetica-Bold", 16)
                c.drawString(50, y, title[:90])
                y -= 30
                c.setFont("Helvetica", 11)
                for line in content_text.splitlines():
                    wrapped = [line[i:i + 88] for i in range(0, max(1, len(line)), 88)]
                    for wline in wrapped:
                        if y < 50:
                            c.showPage()
                            y = height - 50
                            c.setFont("Helvetica", 11)
                        c.drawString(50, y, wline)
                        y -= 16
                c.save()
                return
            except ImportError:
                pass

            # Pillow PDF fallback (PIL is installed in venv)
            from PIL import Image, ImageDraw, ImageFont

            page_w, page_h = 1240, 1754
            margin = 90
            font = ImageFont.load_default()
            lines: List[str] = [title, "=" * min(60, max(10, len(title))), ""]
            for raw_line in content_text.splitlines():
                if not raw_line.strip():
                    lines.append("")
                    continue
                for i in range(0, len(raw_line), 95):
                    lines.append(raw_line[i:i + 95])

            pages: List[Image.Image] = []
            lines_per_page = 65
            for idx in range(0, max(1, len(lines)), lines_per_page):
                img = Image.new("RGB", (page_w, page_h), color=(255, 255, 255))
                draw = ImageDraw.Draw(img)
                y = margin
                for ln in lines[idx:idx + lines_per_page]:
                    draw.text((margin, y), ln, fill=(20, 20, 20), font=font)
                    y += 24
                pages.append(img)

            pages[0].save(
                output_path,
                "PDF",
                resolution=150.0,
                save_all=len(pages) > 1,
                append_images=pages[1:],
            )

        await asyncio.to_thread(_build_pdf)
        msg = f"PDF created at {output_path}"
        return TaskResult(
            success=True,
            output_path=output_path,
            artifacts=[output_path],
            data={
                "filename": os.path.basename(output_path),
                "output_path": output_path,
                "output": msg,
                "message": msg,
            },
        )

    async def _convert_formats(self, task: Task) -> TaskResult:
        source_path = str(task.params.get("source_path") or task.params.get("input_path") or "")
        if not source_path or not os.path.exists(source_path):
            return TaskResult(success=False, error=f"Source file not found: {source_path}")

        target_fmt = str(task.params.get("target_format") or "pdf").lower().lstrip(".")
        src_ext = Path(source_path).suffix.lower().lstrip(".")
        stem = Path(source_path).stem
        out_path = self._resolve_output_path(task, f"{stem}.{target_fmt}")

        if target_fmt == "pdf" and src_ext in ("txt", "md", "json", "csv"):
            text = Path(source_path).read_text(encoding="utf-8", errors="ignore")
            sub_task = Task(
                description=f"Convert {stem} to PDF",
                params={"title": stem, "content": text, "output_path": out_path},
            )
            return await self._create_pdf(sub_task)

        if src_ext == "csv" and target_fmt == "json":
            def _csv_to_json():
                with open(source_path, "r", encoding="utf-8-sig", newline="") as f:
                    rows = list(csv.DictReader(f))
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(rows, f, indent=2)
                return len(rows)

            count = await asyncio.to_thread(_csv_to_json)
            return TaskResult(
                success=True,
                output_path=out_path,
                artifacts=[out_path],
                data={"message": f"Converted {count} CSV rows to JSON.", "output_path": out_path, "output": out_path},
            )

        return TaskResult(success=False, error=f"Unsupported conversion: {src_ext} -> {target_fmt}")

    async def verify(self, result: TaskResult) -> VerificationResult:
        base = await super().verify(result)
        if not base.is_valid or not result.output_path:
            return base
        if result.output_path.lower().endswith(".pdf"):
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(result.output_path)
                if len(reader.pages) == 0:
                    return VerificationResult(is_valid=False, score=0.2, issues=["PDF has 0 pages"])
                return VerificationResult(
                    is_valid=True,
                    score=1.0,
                    details={"pages": len(reader.pages)},
                )
            except Exception as exc:
                return VerificationResult(is_valid=False, score=0.3, issues=[f"Invalid PDF: {exc}"])
        return base
