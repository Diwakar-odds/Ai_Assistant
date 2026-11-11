import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from ..base_agent import BaseAgent
from ..models import Task, TaskResult

logger = logging.getLogger(__name__)


class WebAgent(BaseAgent):
    """
    Handles web page fetching, monitoring, form inspection, and browser automation.
    Uses requests + BeautifulSoup by default (fast & headless-friendly) and can
    optionally drive Selenium BrowserAutomation when params['use_browser']=True.
    """

    def __init__(self, agent_id: str = "web-001", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config or {})
        self.name = "Web Agent"
        self.category = "web"
        self.description = "Browses web pages, monitors sites, inspects forms, and automates browser interactions."
        self.capabilities = [
            "browse_web",
            "interact_page",
            "fill_form",
            "monitor_site",
            "scrape_dynamic",
        ]

    @staticmethod
    def _extract_url(task: Task) -> Optional[str]:
        params = task.params or {}
        url = params.get("url") or params.get("target_url")
        if url:
            return str(url).strip()
        match = re.search(r"(https?://[^\s\"'<>]+)", task.description or "")
        if match:
            return match.group(1).rstrip(".,;)")
        return None

    @staticmethod
    def _validate_url(url: Optional[str]) -> Optional[str]:
        if not url:
            return "A valid http:// or https:// URL is required"
        parsed = urlparse(url)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            return f"Unsupported or invalid URL '{url}'. Only http:// and https:// URLs are allowed."
        return None

    async def can_handle(self, task: Task) -> bool:
        """Check if task involves browsing, site monitoring, or browser interaction."""
        desc = (task.description or "").lower()
        keywords = [
            "browser", "website", "webpage", "browse", "visit",
            "fill form", "form", "login", "click", "interact",
            "monitor site", "scrape dynamic", "http://", "https://",
        ]
        return any(kw in desc for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        """Execute web browsing/monitoring/interaction task."""
        desc = (task.description or "").lower()
        req_caps = set(c.lower() for c in (task.required_capabilities or []))

        if "fill_form" in req_caps or ("fill" in desc and "form" in desc):
            return await self._fill_form(task)
        if "interact_page" in req_caps or any(k in desc for k in ("click", "interact", "type into")):
            return await self._interact(task)
        if "monitor_site" in req_caps or "monitor" in desc or "check status" in desc:
            return await self._monitor_site(task)
        if any(k in desc for k in ("browse", "visit", "open", "fetch", "scrape", "http://", "https://")) or req_caps & {"browse_web", "scrape_dynamic"}:
            return await self._browse(task)

        return TaskResult(success=False, error=f"Unknown web task intent: {task.description}")

    async def _browse(self, task: Task) -> TaskResult:
        """Fetch page content, links, and forms via requests+BS4 or Selenium BrowserAutomation."""
        params = task.params or {}
        url = self._extract_url(task)
        err = self._validate_url(url)
        if err:
            return TaskResult(success=False, error=err)

        use_browser = bool(params.get("use_browser", False))
        timeout = float(params.get("timeout", 15.0))

        if use_browser:
            return await self._browse_with_selenium(url, params)

        def _fetch_http() -> Dict[str, Any]:
            import requests
            from bs4 import BeautifulSoup

            headers = {"User-Agent": str(params.get("user_agent", "CogniBloom-WebAgent/1.0"))}
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            title = soup.title.get_text(strip=True) if soup.title else ""
            text = " ".join(soup.get_text(separator=" ").split())
            links = [
                {"text": a.get_text(strip=True)[:80], "href": urljoin(url, a["href"])}
                for a in soup.find_all("a", href=True)[:25]
            ]
            forms = []
            for form in soup.find_all("form")[:10]:
                inputs = [
                    {"name": inp.get("name") or inp.get("id") or "", "type": inp.get("type", "text")}
                    for inp in form.find_all(["input", "textarea", "select"])
                ]
                forms.append({
                    "action": urljoin(url, form.get("action") or ""),
                    "method": (form.get("method") or "get").upper(),
                    "inputs": inputs,
                })
            return {
                "url": resp.url,
                "status_code": resp.status_code,
                "title": title,
                "text": text[:6000],
                "links": links,
                "forms": forms,
            }

        try:
            page = await asyncio.to_thread(_fetch_http)
            summary = f"Fetched '{page['title'] or page['url']}' (HTTP {page['status_code']})"
            return TaskResult(
                success=True,
                data={
                    **page,
                    "output": page["text"],
                    "summary": summary,
                    "message": summary,
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Failed to fetch {url}: {exc}")

    async def _browse_with_selenium(self, url: str, params: Dict[str, Any]) -> TaskResult:
        """Run optional headless/interactive Selenium session via BrowserAutomation."""
        def _run_browser() -> Dict[str, Any]:
            from ai_assistant.automation.browser_automation import BrowserAutomation, BrowserConfig

            cfg = BrowserConfig(headless=bool(params.get("headless", True)))
            browser = BrowserAutomation(cfg)
            browser.start_browser()
            try:
                browser.driver.get(url)
                title = browser.driver.title or ""
                body_text = ""
                try:
                    el = browser.driver.find_element("tag name", "body")
                    body_text = el.text[:6000] if el else ""
                except Exception:
                    pass
                return {"url": browser.driver.current_url or url, "title": title, "text": body_text}
            finally:
                try:
                    browser.driver.quit()
                except Exception:
                    pass

        try:
            page = await asyncio.to_thread(_run_browser)
            return TaskResult(
                success=True,
                data={
                    **page,
                    "output": page["text"],
                    "summary": f"Browsed '{page['title'] or page['url']}' with Selenium",
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Browser automation failed: {exc}")

    async def _monitor_site(self, task: Task) -> TaskResult:
        """Check HTTP availability, latency, and optional keyword presence."""
        params = task.params or {}
        url = self._extract_url(task)
        err = self._validate_url(url)
        if err:
            return TaskResult(success=False, error=err)

        expected_text = params.get("expected_text")
        timeout = float(params.get("timeout", 10.0))

        def _check() -> Dict[str, Any]:
            import time
            import requests

            t0 = time.monotonic()
            resp = requests.get(url, timeout=timeout)
            elapsed_ms = round((time.monotonic() - t0) * 1000.0, 2)
            has_expected = True
            if expected_text:
                has_expected = str(expected_text) in resp.text
            return {
                "url": resp.url,
                "status_code": resp.status_code,
                "healthy": 200 <= resp.status_code < 400 and has_expected,
                "response_time_ms": elapsed_ms,
                "expected_text_found": has_expected,
            }

        try:
            info = await asyncio.to_thread(_check)
            summary = f"{info['url']} -> HTTP {info['status_code']} ({info['response_time_ms']} ms)"
            return TaskResult(
                success=bool(info["healthy"]),
                error=None if info["healthy"] else f"Site check failed: {summary}",
                data={**info, "summary": summary, "output": summary, "message": summary},
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Site monitor failed for {url}: {exc}")

    async def _fill_form(self, task: Task) -> TaskResult:
        """Inspect a page's forms or submit fields safely (submission requires confirmed=True)."""
        params = task.params or {}
        url = self._extract_url(task)
        err = self._validate_url(url)
        if err:
            return TaskResult(success=False, error=err)

        fields: Dict[str, Any] = params.get("fields") or {}
        submit = bool(params.get("submit", False))
        confirmed = bool(params.get("confirmed") or params.get("confirm"))

        if submit and not confirmed:
            return TaskResult(
                success=False,
                error="Confirmation required before submitting web form. Re-run with params['confirmed']=True.",
                data={"requires_confirmation": True, "url": url, "fields": list(fields.keys())},
                metadata={"requires_confirmation": True},
            )

        def _inspect_or_submit() -> Dict[str, Any]:
            import requests
            from bs4 import BeautifulSoup

            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            forms = soup.find_all("form")
            discovered = []
            for f in forms:
                discovered.append({
                    "action": urljoin(url, f.get("action") or ""),
                    "method": (f.get("method") or "post").upper(),
                    "fields": [i.get("name") for i in f.find_all(["input", "textarea", "select"]) if i.get("name")],
                })

            if submit and confirmed:
                target_action = urljoin(url, params.get("action") or (discovered[0]["action"] if discovered else url))
                post_resp = requests.post(target_action, data=fields, timeout=15)
                return {
                    "status": "submitted",
                    "action": target_action,
                    "status_code": post_resp.status_code,
                    "fields": list(fields.keys()),
                }

            return {
                "status": "inspected",
                "url": url,
                "forms_found": discovered,
                "prepared_fields": list(fields.keys()),
            }

        try:
            res = await asyncio.to_thread(_inspect_or_submit)
            return TaskResult(
                success=True,
                data={**res, "summary": f"Form {res['status']} on {url}", "message": f"Form {res['status']}"},
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Form operation failed: {exc}")

    async def _interact(self, task: Task) -> TaskResult:
        """Click/type via Selenium when use_browser=True, or validate selector cleanly."""
        params = task.params or {}
        url = self._extract_url(task)
        action = str(params.get("action", "click"))
        selector = str(params.get("selector", "body"))

        if params.get("use_browser"):
            err = self._validate_url(url)
            if err:
                return TaskResult(success=False, error=err)

            def _selenium_interact() -> Dict[str, Any]:
                from ai_assistant.automation.browser_automation import BrowserAutomation, BrowserConfig
                from selenium.webdriver.common.by import By

                browser = BrowserAutomation(BrowserConfig(headless=bool(params.get("headless", True))))
                browser.start_browser()
                try:
                    browser.driver.get(url)
                    elem = browser.driver.find_element(By.CSS_SELECTOR, selector)
                    if action == "type" and params.get("text"):
                        elem.clear()
                        elem.send_keys(str(params["text"]))
                    else:
                        elem.click()
                    return {"status": "completed", "url": browser.driver.current_url, "title": browser.driver.title}
                finally:
                    try:
                        browser.driver.quit()
                    except Exception:
                        pass

            try:
                res = await asyncio.to_thread(_selenium_interact)
                return TaskResult(success=True, data=res)
            except Exception as exc:
                return TaskResult(success=False, error=f"Browser interaction failed: {exc}")

        if url:
            err = self._validate_url(url)
            if err:
                return TaskResult(success=False, error=err)
        return TaskResult(
            success=True,
            data={
                "status": "planned",
                "action": action,
                "selector": selector,
                "url": url,
                "summary": f"Prepared '{action}' interaction on '{selector}' (pass use_browser=True for live DOM click)",
            },
        )
