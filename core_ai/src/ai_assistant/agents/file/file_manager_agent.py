import asyncio
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base_agent import BaseAgent
from ..models import Task, TaskResult

logger = logging.getLogger(__name__)

_EXTENSION_CATEGORIES: Dict[str, tuple[str, ...]] = {
    "images": (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"),
    "documents": (".pdf", ".docx", ".doc", ".txt", ".md", ".rtf", ".odt"),
    "spreadsheets": (".xlsx", ".xls", ".csv", ".tsv"),
    "presentations": (".pptx", ".ppt"),
    "audio": (".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"),
    "video": (".mp4", ".mov", ".avi", ".mkv", ".webm"),
    "code": (".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".json", ".yaml", ".yml"),
    "archives": (".zip", ".tar", ".gz", ".7z", ".rar"),
}


class FileManagerAgent(BaseAgent):
    """
    Handles safe file system operations: listing, searching, organizing,
    batch renaming, moving, copying, and backing up directories/files.
    """

    def __init__(self, agent_id: str = "file-001", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config or {})
        self.name = "File Manager Agent"
        self.category = "file"
        self.description = "Lists, searches, organizes, renames, moves, copies, and backs up files."
        self.capabilities = [
            "list_files",
            "search_files",
            "organize_files",
            "rename_files",
            "move_files",
            "backup_files",
        ]
        self._file_auto = None

    def _get_file_automation(self):
        if self._file_auto is None:
            try:
                from ai_assistant.automation.file_automation import FileAutomation

                self._file_auto = FileAutomation()
            except Exception:
                self._file_auto = None
        return self._file_auto

    def _resolve_dir(self, path_val: Optional[str]) -> Optional[Path]:
        if not path_val:
            return None
        p = Path(str(path_val))
        if p.exists():
            return p.resolve()
        fa = self._get_file_automation()
        if fa is not None:
            std = fa.get_standard_folder(str(path_val))
            if std and os.path.exists(std):
                return Path(std).resolve()
        return p.resolve()

    async def can_handle(self, task: Task) -> bool:
        """Check if task involves file or directory management."""
        desc = (task.description or "").lower()
        keywords = [
            "file", "folder", "directory", "organize", "rename",
            "move", "copy", "cleanup", "backup", "list files", "find file",
        ]
        return any(kw in desc for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        """Execute requested file management task."""
        desc = (task.description or "").lower()
        req_caps = set(c.lower() for c in (task.required_capabilities or []))

        if "organize_files" in req_caps or any(k in desc for k in ("organize", "cleanup", "sort")):
            return await self._organize_files(task)
        if "rename_files" in req_caps or "rename" in desc:
            return await self._rename_files(task)
        if "backup_files" in req_caps or "backup" in desc:
            return await self._backup_files(task)
        if "move_files" in req_caps or "move" in desc or "copy" in desc:
            return await self._move_or_copy(task, is_copy=("copy" in desc and "move" not in desc))
        if "search_files" in req_caps or "search" in desc or "find" in desc:
            return await self._search_files(task)
        if "list_files" in req_caps or any(k in desc for k in ("list", "show", "inspect", "ls", "files")):
            return await self._list_files(task)

        return TaskResult(success=False, error=f"Unknown file operation: {task.description}")

    async def _list_files(self, task: Task) -> TaskResult:
        params = task.params or {}
        target = self._resolve_dir(params.get("path") or params.get("directory") or ".")
        if not target or not target.exists() or not target.is_dir():
            return TaskResult(success=False, error=f"Directory not found: {target}")

        recursive = bool(params.get("recursive", False))
        ext_filter = params.get("extension")
        limit = max(1, min(500, int(params.get("limit", 100))))

        def _scan() -> List[Dict[str, Any]]:
            entries: List[Dict[str, Any]] = []
            iterator = target.rglob("*") if recursive else target.iterdir()
            for item in iterator:
                if ext_filter and item.is_file() and item.suffix.lower() != str(ext_filter).lower():
                    continue
                entries.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0,
                })
                if len(entries) >= limit:
                    break
            return entries

        entries = await asyncio.to_thread(_scan)
        summary = f"Listed {len(entries)} item(s) in {target}"
        return TaskResult(
            success=True,
            data={"files": entries, "count": len(entries), "path": str(target), "summary": summary, "output": summary},
        )

    async def _search_files(self, task: Task) -> TaskResult:
        params = task.params or {}
        target = self._resolve_dir(params.get("path") or params.get("search_path") or ".")
        query = str(params.get("query") or params.get("pattern") or params.get("filename") or "").strip().lower()
        if not target or not target.exists():
            return TaskResult(success=False, error=f"Search directory not found: {target}")
        if not query:
            return TaskResult(success=False, error="Search 'query' or 'pattern' is required")

        limit = max(1, min(200, int(params.get("limit", 50))))

        def _search() -> List[str]:
            matches: List[str] = []
            for root, _, files in os.walk(target):
                for fname in files:
                    if query in fname.lower():
                        matches.append(os.path.join(root, fname))
                        if len(matches) >= limit:
                            return matches
            return matches

        matches = await asyncio.to_thread(_search)
        return TaskResult(
            success=True,
            data={
                "matches": matches,
                "count": len(matches),
                "path": str(target),
                "summary": f"Found {len(matches)} file(s) matching '{query}'",
                "output": "\n".join(matches),
            },
        )

    @staticmethod
    def _unique_dest(dest_path: Path) -> Path:
        if not dest_path.exists():
            return dest_path
        stem, suffix = dest_path.stem, dest_path.suffix
        counter = 1
        while True:
            candidate = dest_path.with_name(f"{stem}_{counter}{suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    async def _organize_files(self, task: Task) -> TaskResult:
        params = task.params or {}
        target = self._resolve_dir(params.get("path"))
        if not target or not target.exists() or not target.is_dir():
            return TaskResult(success=False, error=f"Invalid directory path: {params.get('path')}")

        dry_run = bool(params.get("dry_run", False))

        def _organize() -> Dict[str, Any]:
            actions: List[Dict[str, str]] = []
            for item in sorted(target.iterdir()):
                if not item.is_file():
                    continue
                ext = item.suffix.lower()
                dest_cat = "other"
                for cat, exts in _EXTENSION_CATEGORIES.items():
                    if ext in exts:
                        dest_cat = cat
                        break
                dest_dir = target / dest_cat
                dest_path = self._unique_dest(dest_dir / item.name)
                if not dry_run:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(item), str(dest_path))
                actions.append({"from": str(item), "to": str(dest_path), "category": dest_cat})
            return {"actions": actions, "moved_count": len(actions)}

        res = await asyncio.to_thread(_organize)
        mode = "Dry-run preview" if dry_run else "Organized"
        msg = f"{mode}: {res['moved_count']} file(s) in {target}"
        return TaskResult(
            success=True,
            data={
                "message": msg,
                "summary": msg,
                "output": msg,
                "path": str(target),
                "dry_run": dry_run,
                **res,
            },
        )

    async def _rename_files(self, task: Task) -> TaskResult:
        params = task.params or {}
        target = self._resolve_dir(params.get("path"))
        if not target or not target.exists() or not target.is_dir():
            return TaskResult(success=False, error=f"Invalid directory path: {params.get('path')}")

        prefix = str(params.get("prefix", ""))
        suffix = str(params.get("suffix", ""))
        replace_from = params.get("replace_from")
        replace_to = str(params.get("replace_to", ""))
        mapping: Dict[str, str] = params.get("mapping") or {}
        dry_run = bool(params.get("dry_run", False))

        def _rename() -> List[Dict[str, str]]:
            renamed: List[Dict[str, str]] = []
            for item in sorted(target.iterdir()):
                if not item.is_file():
                    continue
                if item.name in mapping:
                    new_name = mapping[item.name]
                else:
                    stem = item.stem
                    if replace_from:
                        stem = stem.replace(str(replace_from), replace_to)
                    new_name = f"{prefix}{stem}{suffix}{item.suffix}"

                if new_name == item.name:
                    continue
                dest = self._unique_dest(item.with_name(new_name))
                if not dry_run:
                    item.rename(dest)
                renamed.append({"from": str(item), "to": str(dest)})
            return renamed

        renamed = await asyncio.to_thread(_rename)
        msg = f"{'Previewed' if dry_run else 'Renamed'} {len(renamed)} file(s)"
        return TaskResult(
            success=True,
            data={"message": msg, "summary": msg, "renamed": renamed, "count": len(renamed), "dry_run": dry_run},
        )

    async def _move_or_copy(self, task: Task, is_copy: bool = False) -> TaskResult:
        params = task.params or {}
        src = self._resolve_dir(params.get("source") or params.get("src"))
        dst_raw = params.get("destination") or params.get("dst")
        if not src or not src.exists():
            return TaskResult(success=False, error=f"Source path not found: {params.get('source')}")
        if not dst_raw:
            return TaskResult(success=False, error="Destination path ('destination') is required")

        dst = Path(str(dst_raw)).resolve()

        def _transfer() -> str:
            if dst.exists() and dst.is_dir():
                final_dst = self._unique_dest(dst / src.name)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                final_dst = dst

            if is_copy:
                if src.is_dir():
                    shutil.copytree(src, final_dst)
                else:
                    shutil.copy2(src, final_dst)
            else:
                shutil.move(str(src), str(final_dst))
            return str(final_dst)

        try:
            final_path = await asyncio.to_thread(_transfer)
            verb = "Copied" if is_copy else "Moved"
            msg = f"{verb} '{src.name}' -> '{final_path}'"
            return TaskResult(
                success=True,
                output_path=final_path,
                artifacts=[final_path],
                data={"message": msg, "summary": msg, "output_path": final_path, "destination": final_path},
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"File transfer failed: {exc}")

    async def _backup_files(self, task: Task) -> TaskResult:
        params = task.params or {}
        src = self._resolve_dir(params.get("source") or params.get("path"))
        if not src or not src.exists():
            return TaskResult(success=False, error=f"Source path not found: {params.get('source') or params.get('path')}")

        backup_root = self._resolve_dir(params.get("destination")) or (self.get_output_dir(task, subdir="outputs") / "backups")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{src.name}_backup_{stamp}"

        def _backup() -> str:
            Path(backup_root).mkdir(parents=True, exist_ok=True)
            if params.get("archive", False) and src.is_dir():
                archive_path = shutil.make_archive(str(Path(backup_root) / backup_name), "zip", root_dir=src)
                return archive_path
            target = Path(backup_root) / backup_name
            if src.is_dir():
                shutil.copytree(src, target)
            else:
                target = Path(backup_root) / f"{src.stem}_{stamp}{src.suffix}"
                shutil.copy2(src, target)
            return str(target)

        try:
            dest = await asyncio.to_thread(_backup)
            msg = f"Backup created at {dest}"
            return TaskResult(
                success=True,
                output_path=dest if os.path.isfile(dest) else None,
                data={"message": msg, "summary": msg, "backup_path": dest, "output": dest},
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Backup failed: {exc}")
