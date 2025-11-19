# 🎵 Spotify Integration Documentation

## Overview

The Music module provides comprehensive Spotify integration for the YourDaddy AI Assistant, including:
- OAuth2 authentication
- Playback control (play, pause, next, previous)
- Track search and playback
- Playlist management
- Music recommendations
- Current playback status

## Setup Instructions

### 1. Create Spotify App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Log in with your Spotify account
3. Click "Create an App"
4. Fill in the app details:
   - App Name: YourDaddy Assistant
   - App Description: AI Assistant with music control
5. Click "Create"
6. In the app settings, add Redirect URI: `http://localhost:8888/callback`
7. Note your **Client ID** and **Client Secret**

### 2. Configure Credentials

**Option A: Environment Variables (Recommended)**

Add to your `.env` file:
```env
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
```

**Option B: Credentials File**

Create `spotify_credentials.json` in the project root:
```json
{
  "client_id": "your_client_id_here",
  "client_secret": "your_client_secret_here"
}
```

### 3. Install Dependencies

```bash
pip install spotipy
```

Or install from requirements.txt:
```bash
pip install -r requirements.txt
```

### 4. Authenticate

On first use, the application will:
1. Open your browser to Spotify's authorization page
2. Ask you to log in and authorize the app
3. Store authentication tokens locally at `~/.yourdaddy/.spotify_cache`

## API Functions

### Authentication

#### `SpotifyController.setup_spotify_auth()`
Initializes OAuth2 authentication with Spotify.

**Returns:** Status message indicating success or error

**Example:**
```python
from modules.music import SpotifyController

controller = SpotifyController()
result = controller.setup_spotify_auth()
print(result)  # "✅ Spotify authenticated as: YourName"
```

### Playback Control

#### `get_spotify_status() -> str`
Gets current playback status including track name, artist, and progress.

**Returns:** Formatted status string

**Example:**
```python
from modules.music import get_spotify_status

status = get_spotify_status()
print(status)
# Output: "🎵 ▶️ Playing: Bohemian Rhapsody by Queen (2:15/5:55)"
```

#### `spotify_play_pause() -> str`
Toggles between play and pause states.

**Returns:** Status message

**Example:**
```python
from modules.music import spotify_play_pause

result = spotify_play_pause()
print(result)  # "⏸️ Spotify paused" or "▶️ Spotify resumed"
```

#### `spotify_next_track() -> str`
Skips to the next track.

**Returns:** Status message with new track info

**Example:**
```python
from modules.music import spotify_next_track

result = spotify_next_track()
print(result)  # "⏭️ Next track: Take On Me by A-ha"
```

#### `spotify_previous_track() -> str`
Goes to the previous track.

**Returns:** Status message with track info

**Example:**
```python
from modules.music import spotify_previous_track

result = spotify_previous_track()
print(result)  # "⏮️ Previous track: Sweet Child O' Mine by Guns N' Roses"
```

### Search and Play

#### `search_and_play_spotify(query: str) -> str`
Searches for a track and plays it immediately.

**Parameters:**
- `query` (str): Search term (song name, artist, or combination)

**Returns:** Status message

**Example:**
```python
from modules.music import search_and_play_spotify

result = search_and_play_spotify("imagine dragons believer")
print(result)  # "🎵 Now playing: Believer by Imagine Dragons"
```

### Playlist Management

#### `create_spotify_playlist(name: str, description: str = "") -> str`
Creates a new private playlist.

**Parameters:**
- `name` (str): Playlist name
- `description` (str, optional): Playlist description

**Returns:** Status message with playlist URL

**Example:**
```python
from modules.music import create_spotify_playlist

result = create_spotify_playlist("My Favorites", "My favorite tracks")
print(result)
# Output: "✅ Created playlist: My Favorites\n🔗 https://open.spotify.com/playlist/..."
```

#### `add_to_spotify_playlist(playlist_name: str, track_query: str) -> str`
Adds a track to an existing playlist.

**Parameters:**
- `playlist_name` (str): Name of the playlist
- `track_query` (str): Search query for the track

**Returns:** Status message

**Example:**
```python
from modules.music import add_to_spotify_playlist

result = add_to_spotify_playlist("My Favorites", "radioactive imagine dragons")
print(result)
# Output: "✅ Added 'Radioactive' by Imagine Dragons to playlist 'My Favorites'"
```

#### `get_spotify_playlists() -> str`
Lists all user playlists.

**Returns:** Formatted list of playlists

**Example:**
```python
from modules.music import get_spotify_playlists

result = get_spotify_playlists()
print(result)
# Output:
# 🎵 Your Spotify Playlists:
# 1. My Favorites (25 tracks)
# 2. Workout Mix (40 tracks)
# 3. Chill Vibes (15 tracks)
```

### Recommendations

#### `get_music_recommendations(seed_type: str = "genre", seed_value: str = "pop", limit: int = 5) -> str`
Gets music recommendations based on a seed.

**Parameters:**
- `seed_type` (str): Type of seed - 'genre', 'artist', or 'track'
- `seed_value` (str): The seed value (genre name, artist name, or track name)
- `limit` (int): Number of recommendations (1-20)

**Returns:** Formatted list of recommendations

**Example:**
```python
from modules.music import get_music_recommendations

# By genre
result = get_music_recommendations("genre", "rock", 5)

# By artist
result = get_music_recommendations("artist", "The Beatles", 5)

# By track
result = get_music_recommendations("track", "Hotel California", 5)

print(result)
# Output:
# 🎵 Recommendations based on genre: rock
# 1. Stairway to Heaven by Led Zeppelin
# 2. Sweet Child O' Mine by Guns N' Roses
# 3. Smells Like Teen Spirit by Nirvana
# 4. Bohemian Rhapsody by Queen
# 5. November Rain by Guns N' Roses
```

## Voice Commands

The following voice commands are supported:

### Playback Control
- "play spotify" / "resume spotify"
- "pause spotify"
- "next song" / "skip song"
- "previous song" / "go back"

### Status
- "what's playing?" / "current song?"
- "spotify status"

### Search and Play
- "play [song name] on spotify"
- "play [artist name] on spotify"
- "search for [query] on spotify"

### Playlists
- "create playlist [name]"
- "show my playlists"
- "add this to [playlist name]"

### Recommendations
- "recommend [genre] music"
- "music like [artist/song]"

## Error Handling

All functions include comprehensive error handling and return user-friendly messages:

- **Not authenticated:** Prompts user to run authentication
- **No active device:** Informs user to start Spotify on a device
- **Search not found:** Provides clear "not found" message
- **API errors:** Returns descriptive error messages

## Token Management

- Tokens are automatically stored in `~/.yourdaddy/.spotify_cache`
- Tokens are automatically refreshed when expired
- No manual token management required

## Scopes

The following Spotify API scopes are requested:
- `user-read-playback-state` - Read current playback
- `user-modify-playback-state` - Control playback
- `user-read-currently-playing` - Read currently playing track
- `playlist-read-private` - Read user's playlists
- `playlist-modify-public` - Modify public playlists
- `playlist-modify-private` - Modify private playlists
- `user-library-read` - Read user's library
- `user-library-modify` - Modify user's library

## Troubleshooting

### "spotipy not installed"
```bash
pip install spotipy
```

### "Spotify not authenticated"
Run the setup function:
```python
from modules.music import SpotifyController
controller = SpotifyController()
controller.setup_spotify_auth()
```

### "No active device found"
Make sure Spotify is running on at least one device (desktop, mobile, web player).

### "Invalid credentials"
Check that your Client ID and Client Secret are correct in `.env` or `spotify_credentials.json`.

### Rate Limiting
Spotify API has rate limits. If you hit them, wait a few seconds before retrying.

## Testing

Run the unit tests:
```bash
python -m pytest tests/test_music.py -v
```

Or with coverage:
```bash
python -m pytest tests/test_music.py -v --cov=modules.music
```

## Architecture

### Singleton Pattern
The `SpotifyController` uses the singleton pattern to ensure only one instance exists, maintaining a single authenticated session.

### OAuth2 Flow
1. User credentials are loaded from environment or file
2. SpotifyOAuth handles authorization and token management
3. Tokens are cached locally
4. Tokens auto-refresh when expired

### Error Recovery
All functions gracefully handle:
- Missing authentication
- Network errors
- API errors
- Invalid inputs

## Future Enhancements

Potential future additions:
- Queue management
- Lyrics integration
- Audio analysis
- Collaborative playlists
- Podcast support
- Local file playback
- Smart shuffle based on mood
- Integration with other music services

## Support

For issues or questions:
1. Check the error message for guidance
2. Verify credentials are correct
3. Ensure Spotify is running
4. Check internet connection
5. Review Spotify API status

## License

This module is part of the YourDaddy AI Assistant project.
