import asyncio
import logging
from typing import Any, Dict, List, Optional

from ..base_agent import BaseAgent
from ..models import Task, TaskResult

logger = logging.getLogger(__name__)


class CommunicationAgent(BaseAgent):
    """
    Handles external communications and scheduling:
    - Reading/searching/drafting/sending emails (Gmail integration)
    - Sending WhatsApp messages
    - Viewing and creating Google Calendar events
    Includes explicit confirmation guardrails before sending external messages or creating events.
    """

    def __init__(self, agent_id: str = "comm-001", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config or {})
        self.name = "Communication Agent"
        self.category = "communication"
        self.description = "Drafts and sends emails, WhatsApp messages, and manages calendar events."
        self.capabilities = [
            "send_email",
            "send_message",
            "schedule_meeting",
            "manage_calendar",
            "post_social",
        ]

    async def can_handle(self, task: Task) -> bool:
        """Check if task involves communication or calendar management."""
        desc = (task.description or "").lower()
        keywords = [
            "email", "gmail", "mail", "send", "message", "whatsapp",
            "calendar", "meeting", "schedule", "appointment", "inbox", "post", "social",
        ]
        return any(kw in desc for kw in keywords)

    @staticmethod
    def _is_confirmed(task: Task) -> bool:
        params = task.params or {}
        if params.get("confirmed") is True or params.get("confirm") is True:
            return True
        return False

    async def execute(self, task: Task) -> TaskResult:
        """Execute communication or calendar task."""
        desc = (task.description or "").lower()
        params = task.params or {}
        req_caps = set(c.lower() for c in (task.required_capabilities or []))

        if "calendar" in desc or "meeting" in desc or "schedule" in desc or (req_caps & {"schedule_meeting", "manage_calendar"}):
            if any(k in desc for k in ("list", "get", "check", "upcoming", "show", "today", "read")) and not any(k in desc for k in ("create", "schedule", "book", "add")):
                return await self._get_calendar_events(task)
            return await self._create_calendar_event(task)

        if "inbox" in desc or ("read" in desc and "email" in desc) or ("search" in desc and "email" in desc):
            return await self._read_or_search_emails(task)

        if "draft" in desc and ("email" in desc or "mail" in desc):
            return await self._draft_email(task)

        if "email" in desc or "gmail" in desc or "send_email" in req_caps:
            return await self._send_email(task)

        if "whatsapp" in desc or "message" in desc or "send_message" in req_caps:
            return await self._send_message(task)

        if "post" in desc or "social" in desc or "post_social" in req_caps:
            return await self._post_social(task)

        return TaskResult(success=False, error=f"Unknown communication task intent: {task.description}")

    async def _draft_email(self, task: Task) -> TaskResult:
        """Draft an email using LLM (or template fallback) without sending."""
        params = task.params or {}
        recipient = str(params.get("to") or params.get("recipient") or "recipient@example.com")
        subject = str(params.get("subject") or "Follow-up")
        upstream = self._extract_upstream_text(task)
        prompt_body = str(params.get("body") or upstream or task.description)

        draft = await self.chat_llm(
            f"Draft a concise, professional email.\nTo: {recipient}\nSubject: {subject}\nContext:\n{prompt_body}",
            system_message="You write clear, concise professional emails.",
        )
        if not draft:
            draft = f"Subject: {subject}\n\nHello,\n\n{prompt_body}\n\nBest regards,\nAI Assistant"

        return TaskResult(
            success=True,
            data={
                "status": "draft",
                "to": recipient,
                "subject": subject,
                "body": draft,
                "output": draft,
                "text": draft,
                "summary": f"Drafted email to {recipient} ('{subject}')",
                "message": "Email draft ready",
            },
        )

    async def _read_or_search_emails(self, task: Task) -> TaskResult:
        """Read inbox summary or search emails via Gmail integration."""
        params = task.params or {}
        query = params.get("query")
        max_results = int(params.get("max_results", 10))

        def _fetch() -> str:
            from ai_assistant.integrations.email_handler import get_inbox_summary, search_emails

            if query:
                return search_emails(str(query), max_results=max_results)
            return get_inbox_summary(max_emails=max_results)

        try:
            report = await asyncio.to_thread(_fetch)
            if report.startswith("❌"):
                return TaskResult(success=False, error=report)
            return TaskResult(
                success=True,
                data={"output": report, "text": report, "summary": report[:240], "message": "Email query completed"},
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Email integration error: {exc}")

    async def _send_email(self, task: Task) -> TaskResult:
        """Send (or draft/confirm-gate) an email via Gmail integration."""
        params = task.params or {}
        recipient = str(params.get("to") or params.get("recipient") or "").strip()
        subject = str(params.get("subject") or "Update from AI Assistant").strip()
        upstream = self._extract_upstream_text(task)
        body = str(params.get("body") or upstream or task.description).strip()

        if not recipient:
            return TaskResult(success=False, error="Recipient email ('to') is required")

        if params.get("dry_run") or params.get("draft_only"):
            return TaskResult(
                success=True,
                data={
                    "status": "draft",
                    "to": recipient,
                    "subject": subject,
                    "body": body,
                    "output": body,
                    "message": f"Dry-run email prepared for {recipient}",
                },
            )

        if not self._is_confirmed(task):
            return TaskResult(
                success=False,
                error=f"Confirmation required before sending email to {recipient}. Re-run with params['confirmed']=True.",
                data={
                    "requires_confirmation": True,
                    "action": "send_email",
                    "to": recipient,
                    "subject": subject,
                    "preview": body[:300],
                },
                metadata={"requires_confirmation": True},
            )

        cc = str(params.get("cc", ""))
        bcc = str(params.get("bcc", ""))

        def _send() -> str:
            from ai_assistant.integrations.email_handler import send_email

            return send_email(to=recipient, subject=subject, body=body, cc=cc, bcc=bcc)

        try:
            resp = await asyncio.to_thread(_send)
            if resp.startswith("❌"):
                return TaskResult(success=False, error=resp)
            return TaskResult(
                success=True,
                data={
                    "status": "sent",
                    "recipient": recipient,
                    "subject": subject,
                    "type": "email",
                    "output": resp,
                    "message": resp,
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Email send failed: {exc}")

    async def _send_message(self, task: Task) -> TaskResult:
        """Send (or confirm-gate) a WhatsApp/instant message."""
        params = task.params or {}
        recipient = str(params.get("to") or params.get("contact") or params.get("recipient") or "").strip()
        upstream = self._extract_upstream_text(task)
        body = str(params.get("body") or params.get("message") or upstream or task.description).strip()

        if not recipient:
            return TaskResult(success=False, error="Recipient contact ('to') is required")

        if params.get("dry_run") or params.get("draft_only"):
            return TaskResult(
                success=True,
                data={
                    "status": "draft",
                    "recipient": recipient,
                    "body": body,
                    "output": body,
                    "message": f"Dry-run message prepared for {recipient}",
                },
            )

        if not self._is_confirmed(task):
            return TaskResult(
                success=False,
                error=f"Confirmation required before sending message to {recipient}. Re-run with params['confirmed']=True.",
                data={
                    "requires_confirmation": True,
                    "action": "send_message",
                    "recipient": recipient,
                    "preview": body[:300],
                },
                metadata={"requires_confirmation": True},
            )

        def _send_wa() -> str:
            from ai_assistant.integrations.whatsapp import send_whatsapp_message

            return send_whatsapp_message(contact_name=recipient, message=body)

        try:
            resp = await asyncio.to_thread(_send_wa)
            if resp.startswith("❌"):
                return TaskResult(success=False, error=resp)
            return TaskResult(
                success=True,
                data={
                    "status": "delivered",
                    "recipient": recipient,
                    "type": "message",
                    "output": resp,
                    "message": resp,
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"WhatsApp send failed: {exc}")

    async def _get_calendar_events(self, task: Task) -> TaskResult:
        days_ahead = int((task.params or {}).get("days_ahead", 7))

        def _fetch() -> str:
            from ai_assistant.integrations.google_calendar import get_upcoming_events

            return get_upcoming_events(days_ahead=days_ahead)

        try:
            resp = await asyncio.to_thread(_fetch)
            if resp.startswith("❌"):
                return TaskResult(success=False, error=resp)
            return TaskResult(
                success=True,
                data={"output": resp, "text": resp, "summary": resp[:240], "message": "Calendar events retrieved"},
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Calendar fetch failed: {exc}")

    async def _create_calendar_event(self, task: Task) -> TaskResult:
        params = task.params or {}
        title = str(params.get("title") or task.description or "Meeting").strip()
        date_str = str(params.get("date") or "").strip()
        time_str = str(params.get("time") or "").strip()
        duration_hours = int(params.get("duration_hours", 1))
        description = str(params.get("description") or self._extract_upstream_text(task) or "")
        location = str(params.get("location") or "")

        if not date_str:
            return TaskResult(success=False, error="Event 'date' (YYYY-MM-DD or MM/DD/YYYY) is required")

        if params.get("dry_run"):
            return TaskResult(
                success=True,
                data={"status": "draft", "title": title, "date": date_str, "time": time_str},
            )

        if not self._is_confirmed(task):
            return TaskResult(
                success=False,
                error=f"Confirmation required before scheduling event '{title}' on {date_str}. Re-run with params['confirmed']=True.",
                data={
                    "requires_confirmation": True,
                    "action": "create_calendar_event",
                    "title": title,
                    "date": date_str,
                    "time": time_str,
                },
                metadata={"requires_confirmation": True},
            )

        def _create() -> str:
            from ai_assistant.integrations.google_calendar import create_calendar_event

            return create_calendar_event(
                title=title,
                date=date_str,
                time=time_str,
                duration_hours=duration_hours,
                description=description,
                location=location,
            )

        try:
            resp = await asyncio.to_thread(_create)
            if resp.startswith("❌"):
                return TaskResult(success=False, error=resp)
            return TaskResult(
                success=True,
                data={"status": "created", "title": title, "date": date_str, "output": resp, "message": resp},
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Calendar event creation failed: {exc}")

    async def _post_social(self, task: Task) -> TaskResult:
        params = task.params or {}
        platform = str(params.get("platform", "social"))
        upstream = self._extract_upstream_text(task)
        content = str(params.get("content") or params.get("text") or upstream or task.description)

        if not self._is_confirmed(task) and not params.get("dry_run"):
            return TaskResult(
                success=False,
                error=f"Confirmation required before posting to {platform}. Re-run with params['confirmed']=True.",
                data={"requires_confirmation": True, "action": "post_social", "platform": platform, "preview": content[:280]},
                metadata={"requires_confirmation": True},
            )
        return TaskResult(
            success=True,
            data={
                "status": "draft" if params.get("dry_run") else "ready_to_publish",
                "platform": platform,
                "content": content,
                "output": content,
                "message": f"Social post prepared for {platform}",
            },
        )
