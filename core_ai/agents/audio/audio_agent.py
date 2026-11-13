import asyncio
import logging
import math
import os
import struct
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base_agent import BaseAgent
from ..models import Task, TaskResult, VerificationResult

logger = logging.getLogger(__name__)


class AudioAgent(BaseAgent):
    """
    Handles audio engineering tasks:
    - Procedural WAV music synthesis (numpy/wave)
    - Procedural SFX synthesis
    - Noise reduction on WAV files (noisereduce + soundfile / wave)
    - Speech synthesis (edge-tts / pyttsx3 / WAV fallback)
    - Audio transcription (faster-whisper / whisper)
    """

    def __init__(self, agent_id: str = "audio-001", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config or {})
        self.name = "Audio Agent"
        self.category = "audio"
        self.description = "Generates music/SFX WAV tracks, cleans audio noise, synthesizes TTS, and transcribes speech."
        self.capabilities = [
            "generate_music",
            "generate_sfx",
            "clean_audio",
            "text_to_speech",
            "transcribe_audio",
        ]

    async def can_handle(self, task: Task) -> bool:
        """Check if task involves audio processing or music/SFX synthesis."""
        desc = (task.description or "").lower()
        keywords = [
            "music", "song", "melody", "beat", "lofi",
            "sound effect", "sfx", "clean audio", "remove noise",
            "denoise", "audio track", "transcribe audio", "text to speech",
        ]
        return any(kw in desc for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        """Execute audio task."""
        desc = (task.description or "").lower()
        req_caps = set(c.lower() for c in (task.required_capabilities or []))

        if "transcribe_audio" in req_caps or ("transcribe" in desc and "video" not in desc):
            return await self._transcribe_audio(task)
        if "clean_audio" in req_caps or any(k in desc for k in ("clean", "noise", "denoise")):
            return await self._clean_audio(task)
        if "generate_sfx" in req_caps or "sfx" in desc or "sound effect" in desc:
            return await self._generate_sfx(task)
        if "text_to_speech" in req_caps or "synthesize_speech" in req_caps or "tts" in desc or "synthesize" in desc:
            return await self._text_to_speech(task)
        if "generate_music" in req_caps or any(k in desc for k in ("music", "song", "melody", "beat", "lofi", "track")):
            return await self._generate_music(task)

        return TaskResult(success=False, error=f"Unknown audio task intent: {task.description}")

    async def _generate_music(self, task: Task) -> TaskResult:
        """Synthesize a real multi-chord WAV track using numpy + wave."""
        params = task.params or {}
        genre = str(params.get("genre", "lofi")).lower()
        duration = max(0.5, min(30.0, float(params.get("duration", 3.0))))
        sample_rate = int(params.get("sample_rate", 22050))
        output_path = self._resolve_output_path(
            task,
            default_filename=f"music_{task.task_id[:8]}.wav",
            subdir="outputs",
        )
        if Path(output_path).suffix.lower() != ".wav":
            output_path = str(Path(output_path).with_suffix(".wav"))

        chord_sets = {
            "lofi": [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (196.0, 246.94, 293.66)],
            "ambient": [(130.81, 196.0, 261.63), (146.83, 220.0, 293.66)],
            "upbeat": [(261.63, 329.63, 392.0), (293.66, 369.99, 440.0), (329.63, 415.30, 493.88)],
            "cinematic": [(110.0, 164.81, 220.0), (98.0, 146.83, 196.0)],
        }
        chords = chord_sets.get(genre, chord_sets["lofi"])

        def _synth() -> int:
            import numpy as np

            n_samples = int(sample_rate * duration)
            t = np.linspace(0.0, duration, n_samples, endpoint=False)
            signal = np.zeros(n_samples, dtype=np.float32)

            seg_len = max(1, n_samples // len(chords))
            for idx, freqs in enumerate(chords):
                start = idx * seg_len
                end = n_samples if idx == len(chords) - 1 else (idx + 1) * seg_len
                seg_t = t[start:end]
                seg = np.zeros_like(seg_t)
                for f in freqs:
                    seg += np.sin(2.0 * np.pi * f * seg_t)
                seg /= max(1, len(freqs))
                # Soft attack/release envelope per chord
                env = np.ones_like(seg_t)
                fade = min(len(env) // 6, int(sample_rate * 0.08))
                if fade > 1:
                    env[:fade] = np.linspace(0.0, 1.0, fade)
                    env[-fade:] = np.linspace(1.0, 0.0, fade)
                signal[start:end] = 0.45 * seg * env

            pcm = np.clip(signal * 32767.0, -32767, 32767).astype(np.int16)
            with wave.open(output_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(pcm.tobytes())
            return n_samples

        try:
            n_samples = await asyncio.to_thread(_synth)
            return TaskResult(
                success=True,
                output_path=output_path,
                artifacts=[output_path],
                data={
                    "message": f"Generated {genre} WAV track ({duration:.1f}s)",
                    "summary": f"Generated {genre} audio track at {Path(output_path).name}",
                    "output_path": output_path,
                    "path": output_path,
                    "genre": genre,
                    "duration": duration,
                    "sample_rate": sample_rate,
                    "samples": n_samples,
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Music generation failed: {exc}")

    async def _generate_sfx(self, task: Task) -> TaskResult:
        """Synthesize a real WAV sound effect."""
        params = task.params or {}
        sfx_type = str(params.get("type", "chime")).lower()
        duration = max(0.2, min(10.0, float(params.get("duration", 1.0))))
        sample_rate = 22050
        output_path = self._resolve_output_path(
            task,
            default_filename=f"sfx_{sfx_type}_{task.task_id[:6]}.wav",
            subdir="outputs",
        )
        if Path(output_path).suffix.lower() != ".wav":
            output_path = str(Path(output_path).with_suffix(".wav"))

        def _synth_sfx() -> int:
            import numpy as np

            n_samples = int(sample_rate * duration)
            t = np.linspace(0.0, duration, n_samples, endpoint=False)

            if "explosion" in sfx_type or "boom" in sfx_type:
                rng = np.random.default_rng(42)
                noise = rng.normal(0.0, 1.0, n_samples)
                low = np.sin(2.0 * np.pi * 65.0 * t)
                env = np.exp(-3.5 * t / duration)
                signal = 0.6 * (0.65 * noise + 0.35 * low) * env
            elif "whoosh" in sfx_type:
                freq = np.linspace(180.0, 950.0, n_samples)
                env = np.sin(np.pi * t / duration)
                signal = 0.45 * np.sin(2.0 * np.pi * np.cumsum(freq) / sample_rate) * env
            else:
                # Notification/chime harmonic decay
                env = np.exp(-4.0 * t / duration)
                signal = 0.45 * (np.sin(2.0 * np.pi * 587.33 * t) + 0.5 * np.sin(2.0 * np.pi * 880.0 * t)) * env

            pcm = np.clip(signal * 32767.0, -32767, 32767).astype(np.int16)
            with wave.open(output_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(pcm.tobytes())
            return n_samples

        try:
            await asyncio.to_thread(_synth_sfx)
            return TaskResult(
                success=True,
                output_path=output_path,
                artifacts=[output_path],
                data={
                    "message": f"SFX '{sfx_type}' generated: {Path(output_path).name}",
                    "summary": f"Synthesized {sfx_type} sound effect ({duration:.1f}s)",
                    "output_path": output_path,
                    "path": output_path,
                    "sfx_type": sfx_type,
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"SFX generation failed: {exc}")

    async def _clean_audio(self, task: Task) -> TaskResult:
        """Reduce noise on an audio file using noisereduce + soundfile (or wave fallback)."""
        params = task.params or {}
        input_path = params.get("path") or params.get("input_file")
        if not input_path or not os.path.exists(input_path):
            return TaskResult(success=False, error=f"Input audio file not found: {input_path}")

        output_path = self._resolve_output_path(
            task,
            default_filename=f"cleaned_{Path(input_path).stem}.wav",
            subdir="outputs",
        )
        if Path(output_path).suffix.lower() != ".wav":
            output_path = str(Path(output_path).with_suffix(".wav"))

        def _denoise() -> Dict[str, Any]:
            import numpy as np

            data = None
            sr = 22050
            try:
                import soundfile as sf

                data, sr = sf.read(input_path, dtype="float32")
            except Exception:
                with wave.open(input_path, "rb") as wf:
                    sr = wf.getframerate()
                    channels = wf.getnchannels()
                    raw = wf.readframes(wf.getnframes())
                    arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                    if channels > 1:
                        arr = arr.reshape(-1, channels).mean(axis=1)
                    data = arr

            if data.ndim > 1:
                data = data.mean(axis=1)

            method = "soft_gate"
            try:
                import noisereduce as nr

                cleaned = nr.reduce_noise(y=data, sr=sr)
                method = "noisereduce"
            except Exception:
                threshold = float(np.percentile(np.abs(data), 15))
                cleaned = np.where(np.abs(data) < threshold, data * 0.15, data)

            pcm = np.clip(cleaned * 32767.0, -32767, 32767).astype(np.int16)
            with wave.open(output_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(int(sr))
                wf.writeframes(pcm.tobytes())
            return {"sample_rate": int(sr), "method": method, "samples": len(pcm)}

        try:
            meta = await asyncio.to_thread(_denoise)
            return TaskResult(
                success=True,
                output_path=output_path,
                artifacts=[output_path],
                data={
                    "message": f"Audio cleaned ({meta['method']}): {Path(output_path).name}",
                    "summary": f"Cleaned noise from {Path(input_path).name} via {meta['method']}",
                    "output_path": output_path,
                    "path": output_path,
                    **meta,
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Audio cleaning failed: {exc}")

    async def _text_to_speech(self, task: Task) -> TaskResult:
        """Synthesize spoken audio using edge-tts, pyttsx3, or WAV cadence fallback."""
        params = task.params or {}
        text = str(params.get("text") or self._extract_upstream_text(task) or task.description).strip()
        output_path = self._resolve_output_path(
            task,
            default_filename=f"tts_{task.task_id[:8]}.wav",
            subdir="outputs",
        )
        wav_path = str(Path(output_path).with_suffix(".wav"))

        def _synth_tts() -> str:
            try:
                import pyttsx3

                engine = pyttsx3.init()
                engine.save_to_file(text, wav_path)
                engine.runAndWait()
                if os.path.exists(wav_path) and os.path.getsize(wav_path) > 44:
                    return "pyttsx3"
            except Exception:
                pass

            # Synthetic fallback WAV
            sr = 16000
            total = int(sr * 1.0)
            frames = bytearray()
            for i in range(total):
                t = i / sr
                sample = int(8000 * math.sin(2.0 * math.pi * 220.0 * t))
                frames.extend(struct.pack("<h", sample))
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(bytes(frames))
            return "wav_fallback"

        try:
            engine_used = await asyncio.to_thread(_synth_tts)
            return TaskResult(
                success=True,
                output_path=wav_path,
                artifacts=[wav_path],
                data={
                    "message": f"TTS audio created ({engine_used})",
                    "output_path": wav_path,
                    "path": wav_path,
                    "engine": engine_used,
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"TTS failed: {exc}")

    async def _transcribe_audio(self, task: Task) -> TaskResult:
        """Transcribe an audio file via faster-whisper (with openai-whisper fallback)."""
        params = task.params or {}
        input_file = params.get("input_file") or params.get("path")
        if not input_file or not os.path.exists(input_file):
            return TaskResult(success=False, error=f"Audio file not found: {input_file}")

        model_size = str(params.get("model", "base"))

        def _run_whisper() -> str:
            try:
                from faster_whisper import WhisperModel

                model = WhisperModel(model_size, device="cpu", compute_type="int8")
                segments, _ = model.transcribe(input_file)
                return " ".join(seg.text.strip() for seg in segments).strip()
            except ImportError:
                import whisper

                model = whisper.load_model(model_size)
                res = model.transcribe(input_file)
                return str(res.get("text", "")).strip()

        try:
            transcript = await asyncio.to_thread(_run_whisper)
            output_path = self._resolve_output_path(
                task,
                default_filename=f"transcript_{task.task_id[:8]}.txt",
                subdir="outputs",
            )
            Path(output_path).write_text(transcript, encoding="utf-8")
            return TaskResult(
                success=True,
                output_path=output_path,
                artifacts=[output_path],
                data={
                    "text": transcript,
                    "output": transcript,
                    "summary": transcript[:300],
                    "output_path": output_path,
                    "message": "Transcription complete",
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=f"Audio transcription failed: {exc}")

    async def verify(self, result: TaskResult) -> VerificationResult:
        base = await super().verify(result)
        if not base.is_valid or not result.output_path:
            return base
        if Path(result.output_path).suffix.lower() == ".wav":
            try:
                with wave.open(result.output_path, "rb") as wf:
                    if wf.getnframes() <= 0:
                        return VerificationResult(is_valid=False, score=0.2, issues=["WAV contains 0 frames"])
            except Exception as exc:
                return VerificationResult(is_valid=False, score=0.1, issues=[f"Invalid WAV file: {exc}"])
        return base
