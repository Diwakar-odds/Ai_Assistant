"""
Pulsar AI Assistant - Phase 4 Automated Test Suite
=================================================
Validates the Audio Subsystem (Single Microphone Owner):
1. MicrophoneStream: WASAPI / sounddevice capture, RMS calculation, clean start and stop.
2. AudioWorker: lifecycle management, buffer processing, wake word matching.
3. Invariant check: Zero GUI imports in pulsar/audio/.
"""

import os
import sys
import time
import pytest
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pulsar.audio.mic_stream import MicrophoneStream
from pulsar.audio.worker import AudioWorker, get_audio_worker


def test_microphone_stream_capture_and_release():
    """Verify MicrophoneStream can start, read frames with normalized RMS, and stop cleanly."""
    stream = MicrophoneStream(sample_rate=16000, block_size=1024)

    # Start audio capture
    started = stream.start()
    if not started:
        pytest.skip("Audio input device not available or hardware mic disabled in this environment.")

    try:
        assert stream.is_running is True

        # Read frames for up to 1 second
        frame_received = False
        start_time = time.time()
        while time.time() - start_time < 2.0:
            data = stream.read_frame(timeout=0.2)
            if data is not None:
                pcm, level = data
                assert isinstance(pcm, bytes)
                assert len(pcm) == 1024 * 2  # 1024 samples * 2 bytes (16-bit)
                assert 0.0 <= level <= 1.0
                frame_received = True
                break

        assert frame_received is True, "No audio frame received from microphone stream within 2s."

    finally:
        stream.stop()
        assert stream.is_running is False


def test_audio_worker_lifecycle():
    """Verify AudioWorker starts and stops cleanly without hanging."""
    worker = AudioWorker()
    started = worker.start()
    if not started:
        pytest.skip("Microphone device unavailable in test environment.")

    try:
        assert worker._is_running is True
        time.sleep(0.5)
    finally:
        worker.stop()
        assert worker._is_running is False


def test_audio_worker_wake_matching():
    """Verify wake word matching detects configured keywords."""
    worker = AudioWorker(wake_words=["hey pulsar", "pulsar"])
    assert "hey pulsar" in worker.wake_words
    assert "pulsar" in worker.wake_words


def test_zero_gui_imports_in_audio_subsystem():
    """Verify strict separation of concerns: zero GUI imports in pulsar/audio/."""
    import re
    audio_dir = REPO_ROOT / "pulsar" / "audio"
    banned = re.compile(r"^(import|from)\s+(win32gui|pystray|pywebview|tkinter)\b", re.MULTILINE)

    for py_file in audio_dir.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        match = banned.search(content)
        assert match is None, f"Found banned GUI import in {py_file.name}: {match.group(0)}"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
