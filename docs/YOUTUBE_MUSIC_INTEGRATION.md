# YouTube Music Integration

YouTube Music has been integrated as an alternative to Spotify. You can now search and play music from YouTube Music.

## Installation

The `ytmusicapi` package is already installed. No API keys required for basic functionality!

## Features

### 1. Search YouTube Music
```python
from modules.music import search_youtube_music

# Search for songs
result = search_youtube_music("Shape of You Ed Sheeran", limit=5)
print(result)
```

### 2. Play Music (Opens in Browser)
```python
from modules.music import play_youtube_music

# Play a song
result = play_youtube_music("Bohemian Rhapsody Queen")
print(result)
```

### 3. Get Your Playlists (Requires Authentication)
```python
from modules.music import get_ytmusic_playlists

# Get playlists
result = get_ytmusic_playlists()
print(result)
```

## Authentication (Optional)

For basic search and play features, **no authentication is needed**. The integration works out of the box!

For accessing your personal playlists and library, you need to authenticate:

### Method 1: Browser Headers (Easiest)
1. Open YouTube Music in your browser
2. Open Developer Tools (F12)
3. Go to Network tab
4. Click on any request to `music.youtube.com`
5. Copy the request headers
6. Run: `ytmusicapi browser`
7. Paste the headers when prompted
8. Move the generated file to: `C:\Users\YourName\.yourdaddy\ytmusic_oauth.json`

### Method 2: OAuth (More Secure)
1. Run: `ytmusicapi oauth`
2. Follow the browser prompts to authenticate
3. Move the generated file to: `C:\Users\YourName\.yourdaddy\ytmusic_oauth.json`

## Usage in Voice Commands

You can now use voice commands like:
- "Play Despacito on YouTube Music"
- "Search for songs by Adele on YouTube Music"
- "Show my YouTube Music playlists"

## Comparison: Spotify vs YouTube Music

| Feature | Spotify | YouTube Music |
|---------|---------|---------------|
| API Keys Required | ✅ Yes | ❌ No (for basic features) |
| Playback Control | ✅ Yes (via API) | ❌ Browser only |
| Search & Play | ✅ Yes | ✅ Yes |
| Library Access | ✅ Yes (with auth) | ✅ Yes (with auth) |
| Free Tier | ✅ Yes | ✅ Yes |
| Setup Complexity | Medium | Easy |

## Advantages of YouTube Music

1. **No API Key Required** - Works immediately without any setup
2. **Larger Music Library** - Includes official releases, covers, remixes, live performances
3. **Free** - No premium subscription needed for basic features
4. **Simple Setup** - Just install and use

## Backend API Endpoints

The following endpoints are available in `modern_web_backend.py`:

- `POST /api/music/ytmusic/search` - Search YouTube Music
- `POST /api/music/ytmusic/play` - Play a song
- `GET /api/music/ytmusic/playlists` - Get user playlists

## Example Usage

```python
# Import the music module
from modules import music

# Search for music
results = music.search_youtube_music("Imagine Dragons", limit=5)
print(results)

# Play a specific song
result = music.play_youtube_music("Thunder Imagine Dragons")
print(result)
```

## Notes

- Music playback opens in your default browser
- No background playback control (unlike Spotify API)
- For full playback control, consider using browser automation or keeping the tab open
- Perfect for quick music searches and playing songs without complex API setup
