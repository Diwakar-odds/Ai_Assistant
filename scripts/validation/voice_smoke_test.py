"""
Minimal voice smoke test: mic -> wake word (text match) -> Vosk ASR -> Edge-TTS/pyttsx3 talkback.
- Requires: pyaudio, vosk, edge-tts (optional for better TTS), pygame (optional playback), pyttsx3 (fallback).
- Models: expects Vosk model folders under ./model (en: vosk-model-small-en-us-0.15, hi: vosk-model-small-hi-0.22).
"""
import asyncio
import json
import os
import sys
import time
import tempfile
from pathlib import Path

import pyaudio
from vosk import Model, KaldiRecognizer

try:
    import webrtcvad
    HAS_VAD = True
except Exception:
    HAS_VAD = False

try:
    import edge_tts
    HAS_EDGE = True
except Exception:
    HAS_EDGE = False

try:
    import pygame
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False

try:
    import pyttsx3
    HAS_PYTTSX3 = True
except Exception:
    HAS_PYTTSX3 = False

RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK = 1600  # 0.1s at 16k
WAKE_WORDS = ["hey assistant", "ok assistant", "assistant"]
VOSK_MODEL_MAP = {
    "en": Path("model/vosk-model-small-en-us-0.15"),
    "hi": Path("model/vosk-model-small-hi-0.22"),
}


def contains_wake_word(text: str) -> bool:
    lower = text.lower()
    return any(w in lower for w in WAKE_WORDS)


def load_vosk_model(lang: str = "en") -> Model:
    model_path = VOSK_MODEL_MAP.get(lang)
    if not model_path or not model_path.exists():
        raise RuntimeError(f"Vosk model for {lang} not found at {model_path}")
    try:
        # Newer vosk supports lang argument (downloads automatically); prefer local path when present.
        return Model(lang=lang, model_path=str(model_path))  # type: ignore
    except TypeError:
        return Model(str(model_path))


def play_mp3(path: str):
    if HAS_PYGAME:
        pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.music.unload()
    else:
        if os.name == "nt":
            os.startfile(path)  # type: ignore
        else:
            print(f"Saved TTS to {path}; playback skipped (pygame not available)")


def tts_speak(text: str, language: str = "en"):
    if not text:
        return

    if HAS_EDGE:
        voice = "en-US-AriaNeural" if language.startswith("en") else "hi-IN-SwaraNeural"

        async def _run():
            fd, out_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            communicator = edge_tts.Communicate(text, voice)
            await communicator.save(out_path)
            play_mp3(out_path)
            try:
                os.remove(out_path)
            except OSError:
                pass

        asyncio.run(_run())
        return

    if HAS_PYTTSX3:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return

    print(f"[TTS skipped] {text}")


def energy_level(audio_bytes: bytes) -> float:
    # Quick RMS check for silence gating when VAD is unavailable.
    import array

    samples = array.array("h", audio_bytes)
    if not samples:
        return 0.0
    squares = sum(s * s for s in samples)
    return (squares / len(samples)) ** 0.5


def record_command(stream, lang: str, silence_ms: int = 800, max_ms: int = 6000) -> str:
    model = load_vosk_model(lang)
    rec = KaldiRecognizer(model, RATE)
    frames = []
    start = time.time()
    silence_start = None
    vad = webrtcvad.Vad(2) if HAS_VAD else None

    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

        if vad:
            is_speech = vad.is_speech(data, RATE)
        else:
            is_speech = energy_level(data) > 500

        if is_speech:
            silence_start = None
        else:
            silence_start = silence_start or time.time()

        if silence_start and (time.time() - silence_start) * 1000 >= silence_ms:
            break
        if (time.time() - start) * 1000 >= max_ms:
            break

    for chunk in frames:
        rec.AcceptWaveform(chunk)
    result = json.loads(rec.FinalResult())
    return result.get("text", "")


def listen_for_wake(stream, lang: str = "en"):
    model = load_vosk_model(lang)
    rec = KaldiRecognizer(model, RATE)

    print(f"Listening for wake words: {', '.join(WAKE_WORDS)}")
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            text = res.get("text", "")
        else:
            partial = json.loads(rec.PartialResult())
            text = partial.get("partial", "")

        if contains_wake_word(text):
            print(f"Wake word heard ({text}). Listening for command...")
            return


def main(lang: str = "en"):
    pa = pyaudio.PyAudio()
    stream = pa.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    try:
        while True:
            listen_for_wake(stream, lang)
            command_text = record_command(stream, lang)
            if not command_text:
                print("Heard nothing after wake word.")
                continue
            print(f"You said: {command_text}")
            reply = f"You said: {command_text}"
            tts_speak(reply, language=lang)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    main(lang)
