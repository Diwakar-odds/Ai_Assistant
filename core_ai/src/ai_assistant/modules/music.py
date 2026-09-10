def get_spotify_status() -> dict:
    """Mock implementation to get Spotify status."""
    return {"status": "paused", "track": None, "artist": None}

def spotify_play_pause() -> str:
    """Mock implementation for play/pause."""
    return "Mock: Toggled play/pause"

def spotify_next_track() -> str:
    """Mock implementation for next track."""
    return "Mock: Skipped to next track"

def spotify_previous_track() -> str:
    """Mock implementation for previous track."""
    return "Mock: Skipped to previous track"
