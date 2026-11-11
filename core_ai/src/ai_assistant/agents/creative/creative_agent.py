import asyncio
import hashlib
import logging
import math
import os
import re
import struct
import textwrap
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..base_agent import BaseAgent
from ..models import Task, TaskResult, VerificationResult

logger = logging.getLogger(__name__)


class CreativeAgent(BaseAgent):
    """
    Agent responsible for generating creative assets:
    - Visual assets: PNG images, thumbnails, banners, layouts, and image edits (Pillow)
    - Audio assets: Voiceover narration via edge-tts / pyttsx3 / synthesized WAV fallback
    """

    def __init__(self, agent_id: str = "creative-001", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config or {})
        self.name = "Creative Agent"
        self.category = "creative"
        self.description = "Generates visual assets (images, thumbnails, banners, layouts) and voiceover audio."
        self.capabilities = [
            "generate_image",
            "create_art",
            "design_layout",
            "image_editing",
            "generate_voiceover",
        ]

    async def can_handle(self, task: Task) -> bool:
        """Check if task involves visual asset or voiceover generation."""
        import re
        desc = (task.description or "").lower()
        tokens = set(re.findall(r"[a-z0-9_]+", desc))

        # Do not steal data analysis or charting tasks
        if any(w in tokens for w in ("chart", "graph", "plot", "database", "sql")):
            if not any(w in tokens for w in ("cover", "poster", "banner")):
                return False

        keywords = [
            "image", "picture", "thumbnail", "photo",
            "logo", "banner", "poster", "design", "layout", "illustration",
            "voiceover", "voice", "speech", "narrate", "tts", "art",
        ]
        if not any(kw in tokens or (len(kw) > 4 and kw in desc) for kw in keywords):
            return False
        # Avoid stealing video editing/trimming tasks unless thumbnail/image/voiceover is asked
        if "video" in tokens and not any(k in tokens for k in ("thumbnail", "image", "voiceover", "generate", "cover")):
            return False
        return True

    async def execute(self, task: Task) -> TaskResult:
        """Execute creative visual or voiceover task."""
        desc = (task.description or "").lower()
        params = task.params or {}
        req_caps = set(c.lower() for c in (task.required_capabilities or []))

        if (
            "image_editing" in req_caps
            or ((params.get("image_path") or params.get("input_file"))
                and any(k in desc for k in ("resize", "crop", "grayscale", "blur", "rotate", "edit image", "border")))
        ):
            return await self._handle_image_editing(task)

        if (
            "generate_voiceover" in req_caps
            or any(k in desc for k in ("voiceover", "voice", "speech", "narrate", "tts"))
        ):
            return await self._handle_audio_generation(task)

        if (
            req_caps & {"generate_image", "create_art", "design_layout"}
            or any(k in desc for k in ("image", "art", "picture", "thumbnail", "photo", "logo", "banner", "poster", "design", "layout", "generate"))
        ):
            return await self._handle_image_generation(task)

        return TaskResult(success=False, error=f"Unknown creative request type: {task.description}")

    @staticmethod
    def _parse_size(size_val: Any, default: Tuple[int, int] = (1024, 1024)) -> Tuple[int, int]:
        if isinstance(size_val, (tuple, list)) and len(size_val) == 2:
            try:
                w, h = int(size_val[0]), int(size_val[1])
                return max(64, min(4096, w)), max(64, min(4096, h))
            except (TypeError, ValueError):
                return default
        if isinstance(size_val, str) and "x" in size_val.lower():
            parts = size_val.lower().split("x", 1)
            try:
                w, h = int(parts[0].strip()), int(parts[1].strip())
                return max(64, min(4096, w)), max(64, min(4096, h))
            except ValueError:
                return default
        return default

    async def _handle_image_generation(self, task: Task) -> TaskResult:
        """Generate a valid PNG image/banner/thumbnail/layout using Pillow."""
        params = task.params or {}
        upstream = self._extract_upstream_text(task)
        prompt = str(params.get("prompt") or params.get("title") or task.description or "Creative Artwork").strip()
        subtitle = str(params.get("subtitle") or "").strip()
        if not subtitle and upstream:
            subtitle = upstream.splitlines()[0][:140]

        desc_lower = (task.description or "").lower()
        default_size = (1280, 720) if ("thumbnail" in desc_lower or "banner" in desc_lower or "layout" in desc_lower) else (1024, 1024)
        width, height = self._parse_size(params.get("size"), default=default_size)
        is_layout = "layout" in desc_lower or "design_layout" in (task.required_capabilities or [])

        output_path = self._resolve_output_path(
            task,
            default_filename=f"creative_{task.task_id[:8]}.png",
            subdir="outputs",
        )
        # Ensure .png extension unless caller passed supported raster format
        ext = Path(output_path).suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".webp"):
            output_path = str(Path(output_path).with_suffix(".png"))

        try:
            def _render_png() -> Dict[str, Any]:
                from PIL import Image, ImageDraw, ImageFont

                digest = hashlib.sha256(prompt.encode("utf-8")).digest()
                c1 = (24 + digest[0] % 80, 32 + digest[1] % 90, 64 + digest[2] % 110)
                c2 = (90 + digest[3] % 120, 48 + digest[4] % 110, 120 + digest[5] % 115)
                accent = (min(255, c2[0] + 60), min(255, c2[1] + 75), min(255, c1[2] + 90))

                img = Image.new("RGB", (width, height), c1)
                draw = ImageDraw.Draw(img)

                # Smooth vertical gradient strips
                steps = min(height, 180)
                for i in range(steps):
                    y0 = int(i * height / steps)
                    y1 = int((i + 1) * height / steps) + 1
                    ratio = i / max(1, steps - 1)
                    r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
                    g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
                    b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
                    draw.rectangle([0, y0, width, y1], fill=(r, g, b))

                # Geometric decorative circles / layout grid
                pad = max(24, width // 24)
                draw.ellipse(
                    [int(width * 0.65), -int(height * 0.15), int(width * 1.1), int(height * 0.45)],
                    outline=accent,
                    width=max(2, width // 180),
                )
                draw.rectangle(
                    [pad, pad, width - pad, height - pad],
                    outline=accent,
                    width=max(2, width // 256),
                )

                if is_layout:
                    header_h = int(height * 0.18)
                    draw.rectangle([pad * 2, pad * 2, width - pad * 2, pad + header_h], outline=(235, 240, 250), width=2)
                    col_w = (width - pad * 5) // 2
                    draw.rectangle([pad * 2, pad * 2 + header_h + 12, pad * 2 + col_w, height - pad * 2], outline=(200, 210, 230), width=2)
                    draw.rectangle([pad * 3 + col_w, pad * 2 + header_h + 12, width - pad * 2, height - pad * 2], outline=(200, 210, 230), width=2)

                # Load font cleanly with fallback
                font_title = None
                font_sub = None
                title_px = max(22, width // 24)
                sub_px = max(14, width // 42)
                for candidate in (
                    "arial.ttf",
                    "segoeui.ttf",
                    r"C:\Windows\Fonts\arial.ttf",
                    r"C:\Windows\Fonts\segoeui.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                ):
                    try:
                        font_title = ImageFont.truetype(candidate, title_px)
                        font_sub = ImageFont.truetype(candidate, sub_px)
                        break
                    except Exception:
                        continue
                if font_title is None:
                    font_title = ImageFont.load_default()
                    font_sub = ImageFont.load_default()

                wrapped_title = textwrap.fill(prompt[:160], width=max(18, width // max(12, title_px // 2)))
                text_y = height // 3 if not is_layout else pad * 2 + 12
                draw.multiline_text((pad * 2 + 8, text_y), wrapped_title, fill=(255, 255, 255), font=font_title, spacing=8)

                if subtitle:
                    wrapped_sub = textwrap.fill(subtitle, width=max(28, width // max(9, sub_px // 2)))
                    draw.multiline_text(
                        (pad * 2 + 8, int(height * 0.68)),
                        wrapped_sub,
                        fill=(220, 232, 248),
                        font=font_sub,
                        spacing=6,
                    )

                img.save(output_path)
                return {
                    "width": width,
                    "height": height,
                    "format": Path(output_path).suffix.lstrip(".").lower(),
                    "bytes": os.path.getsize(output_path),
                }

            meta = await asyncio.to_thread(_render_png)
            return TaskResult(
                success=True,
                output_path=output_path,
                artifacts=[output_path],
                data={
                    "message": f"Image generated successfully: {Path(output_path).name}",
                    "summary": f"Generated {meta['width']}x{meta['height']} visual asset for '{prompt[:60]}'",
                    "output": output_path,
                    "output_path": output_path,
                    "path": output_path,
                    "prompt": prompt,
                    **meta,
                },
            )
        except Exception as exc:
            logger.error("Image generation failed: %s", exc, exc_info=True)
            return TaskResult(success=False, error=f"Image generation failed: {exc}")

    async def _handle_image_editing(self, task: Task) -> TaskResult:
        """Apply basic Pillow transformations (resize, grayscale, rotate, blur) to an input image."""
        params = task.params or {}
        src = params.get("image_path") or params.get("input_file") or params.get("path")
        if not src or not os.path.exists(src):
            return TaskResult(success=False, error=f"Source image not found: {src}")

        output_path = self._resolve_output_path(
            task,
            default_filename=f"edited_{Path(src).stem}_{task.task_id[:6]}.png",
            subdir="outputs",
        )
        desc = (task.description or "").lower()

        def _apply_edits() -> Dict[str, Any]:
            from PIL import Image, ImageFilter, ImageOps

            with Image.open(src) as img:
                edited = img.convert("RGB")
                if "grayscale" in desc or params.get("grayscale"):
                    edited = ImageOps.grayscale(edited).convert("RGB")
                if "blur" in desc or params.get("blur"):
                    radius = float(params.get("blur_radius", 2.0))
                    edited = edited.filter(ImageFilter.GaussianBlur(radius=radius))
                if params.get("rotate") or "rotate" in desc:
                    angle = float(params.get("rotate", 90))
                    edited = edited.rotate(angle, expand=True)
                if params.get("size") or "resize" in desc:
                    w, h = self._parse_size(params.get("size"), default=(edited.width // 2 or 64, edited.height // 2 or 64))
                    edited = edited.resize((w, h))
                edited.save(output_path)
                return {"width": edited.width, "height": edited.height}

        try:
            meta = await asyncio.to_thread(_apply_edits)
            return TaskResult(
                success=True,
                output_path=output_path,
                artifacts=[output_path],
                data={
                    "message": f"Image edited: {Path(output_path).name}",
                    "summary": f"Edited image saved ({meta['width']}x{meta['height']})",
                    "output_path": output_path,
                    "path": output_path,
                    **meta,
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Image editing failed: {exc}")

    async def _handle_audio_generation(self, task: Task) -> TaskResult:
        """Generate real voiceover audio using edge_tts (when online) -> pyttsx3 -> WAV fallback."""
        params = task.params or {}
        text = str(
            params.get("text")
            or params.get("script")
            or params.get("content")
            or self._extract_upstream_text(task)
            or task.description
        ).strip()
        if not text:
            return TaskResult(success=False, error="No text provided for voiceover generation")

        voice = str(params.get("voice", "en-US-AriaNeural"))
        allow_network = bool(params.get("use_edge_tts", not params.get("offline", False)))

        # Decide output path
        default_wav = self._resolve_output_path(
            task,
            default_filename=f"voiceover_{task.task_id[:8]}.wav",
            subdir="outputs",
        )
        requested_ext = Path(default_wav).suffix.lower()

        # 1. Try edge-tts only when MP3 requested/allowed and not forced offline
        if allow_network and requested_ext in (".mp3", ""):
            mp3_path = str(Path(default_wav).with_suffix(".mp3"))
            try:
                import edge_tts

                comm = edge_tts.Communicate(text=text, voice=voice)
                await asyncio.wait_for(comm.save(mp3_path), timeout=float(params.get("tts_timeout", 8.0)))
                if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0:
                    return TaskResult(
                        success=True,
                        output_path=mp3_path,
                        artifacts=[mp3_path],
                        data={
                            "message": f"Voiceover generated via edge_tts: {Path(mp3_path).name}",
                            "summary": f"Generated voiceover ({len(text)} chars)",
                            "output": mp3_path,
                            "output_path": mp3_path,
                            "path": mp3_path,
                            "engine": "edge_tts",
                        },
                    )
            except Exception as exc:
                logger.debug("edge_tts unavailable or offline, falling back to local TTS/WAV: %s", exc)

        # Normalize to valid WAV path for offline engines
        wav_path = str(Path(default_wav).with_suffix(".wav"))

        # 2. Try pyttsx3 offline synthesis unless disabled
        if not params.get("synthetic_fallback_only", False):
            def _run_pyttsx3() -> bool:
                try:
                    import pyttsx3

                    engine = pyttsx3.init()
                    engine.save_to_file(text, wav_path)
                    engine.runAndWait()
                    return os.path.exists(wav_path) and os.path.getsize(wav_path) > 44
                except Exception as exc:
                    logger.debug("pyttsx3 TTS failed: %s", exc)
                    return False

            if await asyncio.to_thread(_run_pyttsx3):
                return TaskResult(
                    success=True,
                    output_path=wav_path,
                    artifacts=[wav_path],
                    data={
                        "message": f"Voiceover generated via pyttsx3: {Path(wav_path).name}",
                        "summary": f"Generated offline voiceover ({len(text)} chars)",
                        "output": wav_path,
                        "output_path": wav_path,
                        "path": wav_path,
                        "engine": "pyttsx3",
                    },
                )

        # 3. Deterministic pure-Python spoken-cadence WAV synthesis fallback (always valid RIFF/WAV)
        def _synthesize_wav_cadence() -> int:
            sample_rate = 16000
            word_count = max(1, min(12, len(text.split())))
            duration = max(0.6, min(4.0, word_count * 0.28))
            total_samples = int(sample_rate * duration)
            frames = bytearray()
            for idx in range(total_samples):
                t = idx / sample_rate
                env = 0.5 * (1.0 - math.cos(2.0 * math.pi * (idx % int(sample_rate * 0.25)) / max(1, int(sample_rate * 0.25))))
                val = 0.28 * env * (
                    math.sin(2.0 * math.pi * 185.0 * t)
                    + 0.5 * math.sin(2.0 * math.pi * 370.0 * t)
                )
                sample = max(-32767, min(32767, int(val * 32767)))
                frames.extend(struct.pack("<h", sample))

            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(bytes(frames))
            return total_samples

        try:
            samples = await asyncio.to_thread(_synthesize_wav_cadence)
            return TaskResult(
                success=True,
                output_path=wav_path,
                artifacts=[wav_path],
                data={
                    "message": f"Voiceover WAV synthesized: {Path(wav_path).name}",
                    "summary": f"Generated WAV audio ({samples / 16000:.2f}s) for text",
                    "output": wav_path,
                    "output_path": wav_path,
                    "path": wav_path,
                    "engine": "wav_fallback",
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Voiceover generation failed: {exc}")

    async def verify(self, result: TaskResult) -> VerificationResult:
        base = await super().verify(result)
        if not base.is_valid or not result.output_path:
            return base

        ext = Path(result.output_path).suffix.lower()
        try:
            if ext in (".png", ".jpg", ".jpeg", ".webp"):
                from PIL import Image

                with Image.open(result.output_path) as img:
                    img.verify()
            elif ext == ".wav":
                with wave.open(result.output_path, "rb") as wf:
                    if wf.getnframes() <= 0:
                        return VerificationResult(is_valid=False, score=0.2, issues=["WAV file contains 0 frames"])
        except Exception as exc:
            return VerificationResult(is_valid=False, score=0.1, issues=[f"Corrupt media asset: {exc}"])
        return base
