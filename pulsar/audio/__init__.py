"""
Pulsar Audio Worker Package (Single Microphone Owner)
Paradigm B: Strict Audio Invariant

Invariants:
- Exactly ONE microphone capture client running in the system.
- Sounddevice with WasapiSettings(auto_convert=True) for seamless array mic resampling.
- Audio callback only pushes frames to a bounded queue (zero inference in callback).
- Live RMS volume streaming to 4D Orb state.
- Offline wake word ("Hey Pulsar") detection with automatic speech segmenting.
"""

__all__ = ["mic_stream", "wake_engine", "worker"]
