import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base_agent import BaseAgent
from ..models import Task, TaskResult
from .gui_controller import AppControllerFactory
from .training_mode import TrainingMode
from .visual_verifier import VisualVerifier

logger = logging.getLogger(__name__)


class VideoAgent(BaseAgent):
    """
    Handles video editing, transcription (faster-whisper / whisper),
    audio extraction, thumbnail creation (OpenCV / Pillow fallback),
    workflow training, and GUI app control.
    """

    def __init__(self, agent_id: str = "video-001", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config or {})
        self.name = "Video Agent"
        self.category = "video"
        self.description = "Handles video editing, transcription, audio extraction, thumbnails, and GUI app control."
        self.capabilities = [
            "create_video",
            "edit_video",
            "transcribe_video",
            "extract_audio",
            "create_thumbnail",
            "add_subtitles",
            "control_external_app",
        ]

        self._moviepy = None
        self._whisper = None
        self._whisper_model = None
        self.training_session: Optional[TrainingMode] = None
        self._verifier: Optional[VisualVerifier] = None

    @property
    def verifier(self) -> VisualVerifier:
        if self._verifier is None:
            self._verifier = VisualVerifier()
        return self._verifier

    async def can_handle(self, task: Task) -> bool:
        """Check if task involves video operations or external video app control."""
        desc = (task.description or "").lower()
        keywords = [
            "video", "movie", "clip", "trim", "cut video", "edit video",
            "transcribe", "subtitle", "caption", "extract audio",
            "premiere", "davinci", "filmora", "capcut", "control app", "train workflow",
        ]
        return any(kw in desc for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        """Execute video, thumbnail, transcription, or app control task."""
        try:
            desc = (task.description or "").lower()
            req_caps = set(c.lower() for c in (task.required_capabilities or []))

            if "train" in desc or "tune" in desc:
                return await self._handle_training(task)
            if "create_thumbnail" in req_caps or ("thumbnail" in desc and (task.params.get("input_file") or "video" in desc)):
                return await self._create_thumbnail(task)
            if "control_external_app" in req_caps or "control" in desc or any(app in desc for app in ("premiere", "davinci", "capcut", "filmora")):
                return await self._control_app(task)
            if "transcribe_video" in req_caps or "add_subtitles" in req_caps or "transcribe" in desc or "subtitle" in desc or "caption" in desc:
                return await self._transcribe_video(task)
            if "extract_audio" in req_caps or "extract audio" in desc:
                return await self._extract_audio(task)
            if "edit_video" in req_caps or "create_video" in req_caps or any(k in desc for k in ("cut", "trim", "edit")):
                return await self._edit_video(task)

            return TaskResult(success=False, error=f"Unknown video task: {task.description}")
        except Exception as exc:
            logger.error("VideoAgent execution error: %s", exc, exc_info=True)
            return TaskResult(success=False, error=str(exc))

    # --- Lazy Library Loaders ---

    def _load_moviepy(self):
        if self._moviepy is None:
            try:
                import moviepy as mp

                if hasattr(mp, "VideoFileClip"):
                    self._moviepy = mp
                else:
                    import moviepy.editor as mp_ed

                    self._moviepy = mp_ed
            except ImportError as exc:
                raise ImportError("moviepy is not installed. Install with: pip install moviepy") from exc
        return self._moviepy

    # --- Core Video Operations ---

    async def _edit_video(self, task: Task) -> TaskResult:
        """Trim or edit a video file via MoviePy in a worker thread."""
        params = task.params or {}
        input_file = params.get("input_file") or params.get("path")
        if not input_file or not os.path.exists(input_file):
            return TaskResult(success=False, error=f"Input video file not found: {input_file}")

        start_time = float(params.get("start_time", 0))
        end_time = params.get("end_time")
        output_path = self._resolve_output_path(
            task,
            default_filename=f"edited_{task.task_id[:8]}.mp4",
            subdir="outputs",
        )

        def _trim() -> Dict[str, Any]:
            mp = self._load_moviepy()
            clip = mp.VideoFileClip(input_file)
            trimmed = None
            try:
                if hasattr(clip, "subclipped"):
                    trimmed = clip.subclipped(start_time, end_time) if end_time is not None else clip.subclipped(start_time)
                else:
                    trimmed = clip.subclip(start_time, end_time) if end_time is not None else clip.subclip(start_time)
                duration = getattr(trimmed, "duration", None)
                trimmed.write_videofile(output_path, codec="libx264", audio_codec="aac")
                return {"duration": duration}
            finally:
                for obj in (trimmed, clip):
                    if obj is not None:
                        try:
                            obj.close()
                        except Exception:
                            pass

        try:
            meta = await asyncio.to_thread(_trim)
            return TaskResult(
                success=True,
                output_path=output_path,
                artifacts=[output_path],
                data={
                    "output_path": output_path,
                    "duration": meta.get("duration"),
                    "summary": f"Edited video saved to {Path(output_path).name}",
                    "message": "Video editing complete",
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Editing failed: {exc}")

    async def _extract_audio(self, task: Task) -> TaskResult:
        """Extract audio track from a video file."""
        params = task.params or {}
        input_file = params.get("input_file") or params.get("path")
        if not input_file or not os.path.exists(input_file):
            return TaskResult(success=False, error=f"Input video file not found: {input_file}")

        output_path = self._resolve_output_path(
            task,
            default_filename=f"audio_{task.task_id[:8]}.mp3",
            subdir="outputs",
        )

        def _extract() -> None:
            mp = self._load_moviepy()
            clip = mp.VideoFileClip(input_file)
            try:
                if not clip.audio:
                    raise ValueError("Video has no audio track")
                clip.audio.write_audiofile(output_path)
            finally:
                try:
                    clip.close()
                except Exception:
                    pass

        try:
            await asyncio.to_thread(_extract)
            return TaskResult(
                success=True,
                output_path=output_path,
                artifacts=[output_path],
                data={
                    "output_path": output_path,
                    "summary": f"Extracted audio to {Path(output_path).name}",
                    "message": "Audio extracted successfully",
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Audio extraction failed: {exc}")

    async def _create_thumbnail(self, task: Task) -> TaskResult:
        """Extract a video thumbnail via OpenCV or render a fallback thumbnail via Pillow."""
        params = task.params or {}
        input_file = params.get("input_file") or params.get("path")
        timestamp_sec = float(params.get("timestamp", 1.0))
        output_path = self._resolve_output_path(
            task,
            default_filename=f"thumbnail_{task.task_id[:8]}.png",
            subdir="outputs",
        )
        if Path(output_path).suffix.lower() not in (".png", ".jpg", ".jpeg"):
            output_path = str(Path(output_path).with_suffix(".png"))

        def _make_thumb() -> str:
            if input_file and os.path.exists(input_file):
                import cv2

                cap = cv2.VideoCapture(input_file)
                try:
                    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
                    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
                    target_frame = int(timestamp_sec * fps)
                    if total_frames > 0:
                        target_frame = min(max(0, target_frame), int(total_frames - 1))
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                    ok, frame = cap.read()
                    if not ok:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ok, frame = cap.read()
                    if ok and frame is not None:
                        cv2.imwrite(output_path, frame)
                        return "opencv_frame"
                finally:
                    cap.release()

            # Fallback: Pillow thumbnail card when no readable video exists
            from PIL import Image, ImageDraw

            img = Image.new("RGB", (1280, 720), (24, 34, 56))
            draw = ImageDraw.Draw(img)
            title = str(params.get("title") or task.description or "Video Thumbnail")[:120]
            draw.rectangle([32, 32, 1248, 688], outline=(100, 180, 255), width=4)
            draw.text((80, 320), title, fill=(255, 255, 255))
            img.save(output_path)
            return "pillow_card"

        try:
            method = await asyncio.to_thread(_make_thumb)
            return TaskResult(
                success=True,
                output_path=output_path,
                artifacts=[output_path],
                data={
                    "output_path": output_path,
                    "path": output_path,
                    "method": method,
                    "summary": f"Created thumbnail ({method}): {Path(output_path).name}",
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Thumbnail creation failed: {exc}")

    async def _transcribe_video(self, task: Task) -> TaskResult:
        """Transcribe video/audio via faster-whisper or openai-whisper fallback."""
        params = task.params or {}
        input_file = params.get("input_file") or params.get("path")
        if not input_file or not os.path.exists(input_file):
            return TaskResult(success=False, error=f"Input file not found: {input_file}")

        model_size = str(params.get("model", "base"))
        output_path = self._resolve_output_path(
            task,
            default_filename=f"transcription_{task.task_id[:8]}.txt",
            subdir="outputs",
        )

        def _transcribe() -> str:
            try:
                from faster_whisper import WhisperModel

                if self._whisper_model is None:
                    self._whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
                segments, _ = self._whisper_model.transcribe(input_file)
                return " ".join(seg.text.strip() for seg in segments).strip()
            except ImportError:
                import whisper

                model = whisper.load_model(model_size)
                result = model.transcribe(input_file)
                return str(result.get("text", "")).strip()

        try:
            text = await asyncio.to_thread(_transcribe)
            Path(output_path).write_text(text, encoding="utf-8")
            return TaskResult(
                success=True,
                output_path=output_path,
                artifacts=[output_path],
                data={
                    "text": text,
                    "output": text,
                    "summary": text[:300] or f"Transcribed {Path(input_file).name}",
                    "output_path": output_path,
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Transcription failed: {exc}")

    # --- GUI Automation & Training ---

    async def _control_app(self, task: Task) -> TaskResult:
        """Control an external video editing app safely inside a worker thread."""
        params = task.params or {}
        app_name = str(params.get("app_name", "premiere"))
        action = params.get("action")
        text = params.get("text")
        dry_run = bool(params.get("dry_run", False))

        if dry_run:
            return TaskResult(
                success=True,
                data={
                    "status": "dry_run",
                    "app_name": app_name,
                    "action": action,
                    "text": text,
                    "message": f"Dry-run: would run action '{action}' on '{app_name}'",
                },
            )

        def _drive() -> Dict[str, Any]:
            controller = AppControllerFactory.get_controller(app_name)
            is_focused = controller.focus_window(app_name)
            if not is_focused and not params.get("allow_unfocused", False):
                return {"focused": False}
            if action and hasattr(controller, "execute_action"):
                controller.execute_action(str(action))
            if text:
                controller.type_text(str(text))
            verified = None
            if params.get("verify"):
                verified = self.verifier.verify_state(f"after_{action}", app_name)
            return {"focused": is_focused, "verified": verified}

        try:
            outcome = await asyncio.to_thread(_drive)
            if not outcome.get("focused") and not params.get("allow_unfocused", False):
                return TaskResult(success=False, error=f"Could not find or focus window: {app_name}")
            return TaskResult(
                success=True,
                data={
                    "message": f"Executed action '{action}' on '{app_name}'",
                    "summary": f"Controlled '{app_name}' ({action or 'type'})",
                    **outcome,
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"App control failed: {exc}")

    async def _handle_training(self, task: Task) -> TaskResult:
        """Handle training workflow definitions."""
        params = task.params or {}
        mode = str(params.get("mode", "start")).lower()

        if mode == "start":
            profile = str(params.get("profile", "custom"))
            self.training_session = TrainingMode(profile)
            return TaskResult(success=True, data={"message": f"Started training session for '{profile}'"})

        if mode == "add":
            if not self.training_session:
                return TaskResult(success=False, error="No active training session. Start one first.")
            action_type = str(params.get("action_type", "hotkey"))
            action_params = params.get("params", {})
            self.training_session.add_action(action_type, action_params)
            return TaskResult(success=True, data={"message": "Action recorded"})

        if mode == "save":
            if not self.training_session:
                return TaskResult(success=False, error="No active training session.")
            output_dir = params.get("output_dir")
            filename = params.get("filename")
            path = self.training_session.save_workflow(filename=filename, output_dir=output_dir)
            self.training_session = None
            return TaskResult(
                success=True,
                output_path=path,
                artifacts=[path],
                data={"message": f"Workflow saved to {path}", "output_path": path},
            )

        return TaskResult(success=False, error=f"Unknown training mode: {mode}")
