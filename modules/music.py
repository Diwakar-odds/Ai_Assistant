# Music Control Module for YourDaddy Assistant
"""
Advanced music control functionality supporting:
- Spotify integration with OAuth authentication
- YouTube Music integration
- Local media player control (Windows Media Player, VLC, etc.)
- System volume control
- Playlist management
- Voice commands for music control
"""

import subprocess
import os
import json
import webbrowser
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import psutil

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False
    print("WARNING: spotipy not installed. Spotify features will be disabled.")
    print("Install with: pip install spotipy")

try:
    from ytmusicapi import YTMusic
    YTMUSIC_AVAILABLE = True
except ImportError:
    YTMUSIC_AVAILABLE = False
    print("WARNING: ytmusicapi not installed. YouTube Music features will be disabled.")
    print("Install with: pip install ytmusicapi")

class SpotifyController:
    """
    Spotify Web API integration with proper OAuth2 authentication
    """
    
    _instance = None  # Singleton instance
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SpotifyController, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        self.client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = "http://localhost:8888/callback"
        self.scope = " ".join([
            "user-read-playback-state",
            "user-modify-playback-state",
            "user-read-currently-playing",
            "playlist-read-private",
            "playlist-modify-public",
            "playlist-modify-private",
            "user-library-read",
            "user-library-modify"
        ])
        
        # Cache path for token storage
        self.cache_path = Path.home() / ".yourdaddy" / ".spotify_cache"
        self.sp = None
        self._initialized = True
        
    def setup_spotify_auth(self) -> str:
        """
        Set up Spotify API authentication using OAuth2
        Returns status message
        """
        if not SPOTIPY_AVAILABLE:
            return "❌ spotipy library not installed. Install with: pip install spotipy"
            
        try:
            # Check for credentials
            if not self.client_id or not self.client_secret:
                # Try to load from credentials file
                creds_file = Path("spotify_credentials.json")
                if creds_file.exists():
                    with open(creds_file, 'r') as f:
                        creds = json.load(f)
                        self.client_id = creds.get('client_id')
                        self.client_secret = creds.get('client_secret')
                
                if not self.client_id or not self.client_secret:
                    return """❌ Spotify credentials not configured.

Setup Steps:
1. Go to https://developer.spotify.com/dashboard/
2. Create an app or use an existing one
3. Add redirect URI: http://localhost:8888/callback
4. Copy Client ID and Client Secret

Option A - Use .env file (Recommended):
   Add these lines to .env file:
   SPOTIFY_CLIENT_ID=your_client_id_here
   SPOTIFY_CLIENT_SECRET=your_client_secret_here

Option B - Use credentials file:
   Create spotify_credentials.json:
   {
     "client_id": "your_client_id_here",
     "client_secret": "your_client_secret_here"
   }
"""
            
            # Create cache directory
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize OAuth
            auth_manager = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=self.scope,
                cache_path=str(self.cache_path),
                open_browser=True
            )
            
            # Create Spotify client
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            
            # Test authentication
            user = self.sp.current_user()
            username = user.get('display_name', user.get('id', 'User'))
            return f"✅ Spotify authenticated as: {username}"
            
        except Exception as e:
            self.sp = None
            return f"❌ Spotify authentication failed: {str(e)}"
    
    def _ensure_authenticated(self) -> bool:
        """Ensure we have valid authentication"""
        if not SPOTIPY_AVAILABLE:
            return False
            
        if self.sp is None:
            result = self.setup_spotify_auth()
            if "❌" in result:
                return False
        return True

class YouTubeMusicController:
    """
    YouTube Music integration using ytmusicapi
    """
    
    _instance = None  # Singleton instance
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(YouTubeMusicController, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.ytmusic = None
        self.auth_file = Path.home() / ".yourdaddy" / "ytmusic_oauth.json"
        self._initialized = True
        
    def setup_ytmusic_auth(self) -> str:
        """
        Set up YouTube Music authentication
        """
        if not YTMUSIC_AVAILABLE:
            return "❌ ytmusicapi not installed. Install with: pip install ytmusicapi"
            
        try:
            # Try to load existing auth
            if self.auth_file.exists():
                self.ytmusic = YTMusic(str(self.auth_file))
                return "✅ YouTube Music authenticated (using saved credentials)"
            else:
                # Setup OAuth
                self.auth_file.parent.mkdir(parents=True, exist_ok=True)
                
                # For OAuth, we need to run the setup
                return """🎵 YouTube Music Setup Required:

Run this command in terminal:
ytmusicapi oauth

This will:
1. Open a browser for Google authentication
2. Save credentials to headers_auth.json

Then move the file to: {str(self.auth_file)}

Or use browser authentication (simpler):
ytmusicapi browser

This will guide you to copy request headers from your browser."""
                
        except Exception as e:
            return f"❌ YouTube Music setup error: {str(e)}"
    
    def _ensure_authenticated(self) -> bool:
        """Ensure we have valid authentication"""
        if not YTMUSIC_AVAILABLE:
            return False
            
        if self.ytmusic is None:
            if self.auth_file.exists():
                try:
                    self.ytmusic = YTMusic(str(self.auth_file))
                    return True
                except:
                    return False
            return False
        return True

def search_youtube_music(query: str, limit: int = 5) -> str:
    """
    Search for songs on YouTube Music
    """
    if not YTMUSIC_AVAILABLE:
        return "❌ ytmusicapi not installed. Install with: pip install ytmusicapi"
        
    try:
        controller = YouTubeMusicController()
        if not controller._ensure_authenticated():
            # Try unauthenticated mode
            try:
                controller.ytmusic = YTMusic()
            except:
                return "🎵 YouTube Music not authenticated. Please run setup first."
        
        results = controller.ytmusic.search(query, filter="songs", limit=limit)
        
        if not results:
            return f"🔍 No results found for: {query}"
        
        output = f"🎵 YouTube Music results for '{query}':\n\n"
        for i, track in enumerate(results, 1):
            title = track.get('title', 'Unknown')
            artists = ', '.join([a['name'] for a in track.get('artists', [])])
            duration = track.get('duration', 'Unknown')
            output += f"{i}. {title}\n   by {artists} ({duration})\n"
        
        return output.strip()
        
    except Exception as e:
        return f"❌ YouTube Music search error: {str(e)}"

def play_youtube_music(query: str) -> str:
    """
    Play a song on YouTube Music (opens in browser)
    """
    if not YTMUSIC_AVAILABLE:
        return "❌ ytmusicapi not installed. Install with: pip install ytmusicapi"
        
    try:
        controller = YouTubeMusicController()
        if not controller._ensure_authenticated():
            # Try unauthenticated mode
            try:
                controller.ytmusic = YTMusic()
            except:
                return "🎵 YouTube Music not authenticated. Please run setup first."
        
        # Search for the song
        results = controller.ytmusic.search(query, filter="songs", limit=1)
        
        if not results:
            return f"🔍 No results found for: {query}"
        
        track = results[0]
        video_id = track.get('videoId')
        title = track.get('title', 'Unknown')
        artists = ', '.join([a['name'] for a in track.get('artists', [])])
        
        if video_id:
            # Open in browser
            url = f"https://music.youtube.com/watch?v={video_id}"
            webbrowser.open(url)
            return f"🎵 Opening in browser: {title} by {artists}"
        else:
            return "❌ Could not get video ID"
        
    except Exception as e:
        return f"❌ YouTube Music play error: {str(e)}"

def get_ytmusic_playlists() -> str:
    """
    Get user's YouTube Music playlists
    """
    if not YTMUSIC_AVAILABLE:
        return "❌ ytmusicapi not installed. Install with: pip install ytmusicapi"
        
    try:
        controller = YouTubeMusicController()
        if not controller._ensure_authenticated():
            return "🎵 YouTube Music not authenticated. Authentication required for playlists."
        
        playlists = controller.ytmusic.get_library_playlists(limit=50)
        
        if not playlists:
            return "🎵 No playlists found"
        
        result = "🎵 Your YouTube Music Playlists:\n\n"
        for i, playlist in enumerate(playlists, 1):
            title = playlist.get('title', 'Unknown')
            count = playlist.get('count', '?')
            result += f"{i}. {title} ({count} songs)\n"
        
        return result.strip()
        
    except Exception as e:
        return f"❌ Error getting playlists: {str(e)}"


    """
    Get current Spotify playback status
    """
    if not SPOTIPY_AVAILABLE:
        return "❌ spotipy not installed. Install with: pip install spotipy"
        
    try:
        controller = SpotifyController()
        if not controller._ensure_authenticated():
            return "🎵 Spotify not authenticated. Please run setup first."
            
        playback = controller.sp.current_playback()
        
        if not playback or not playback.get('item'):
            return "🎵 Spotify: No track currently playing"
        
        track = playback['item']
        artists = ', '.join([artist['name'] for artist in track['artists']])
        is_playing = playback['is_playing']
        progress_ms = playback['progress_ms']
        duration_ms = track['duration_ms']
        
        # Format time
        progress_sec = progress_ms // 1000
        duration_sec = duration_ms // 1000
        progress_str = f"{progress_sec//60}:{progress_sec%60:02d}"
        duration_str = f"{duration_sec//60}:{duration_sec%60:02d}"
        
        status = "▶️ Playing" if is_playing else "⏸️ Paused"
        
        return f"🎵 {status}: {track['name']} by {artists} ({progress_str}/{duration_str})"
        
    except Exception as e:
        return f"❌ Error getting Spotify status: {str(e)}"

def get_spotify_status() -> str:
    """
    Get current Spotify playback status
    Alias for _get_current_spotify_track() for backward compatibility
    
    Returns:
        Status string with current track info
    """
    return _get_current_spotify_track()

def spotify_play_pause() -> str:
    """
    Toggle Spotify play/pause
    """
    if not SPOTIPY_AVAILABLE:
        return "❌ spotipy not installed. Install with: pip install spotipy"
        
    try:
        controller = SpotifyController()
        if not controller._ensure_authenticated():
            return "🎵 Spotify not authenticated. Please run setup first."
            
        playback = controller.sp.current_playback()
        
        if not playback:
            return "🎵 No active Spotify device found. Please start Spotify."
        
        if playback['is_playing']:
            controller.sp.pause_playback()
            return "⏸️ Spotify paused"
        else:
            controller.sp.start_playback()
            return "▶️ Spotify resumed"
            
    except Exception as e:
        return f"❌ Spotify control error: {str(e)}"

def spotify_next_track() -> str:
    """
    Skip to next track on Spotify
    """
    if not SPOTIPY_AVAILABLE:
        return "❌ spotipy not installed. Install with: pip install spotipy"
        
    try:
        controller = SpotifyController()
        if not controller._ensure_authenticated():
            return "🎵 Spotify not authenticated. Please run setup first."
            
        controller.sp.next_track()
        
        # Wait a moment and get new track info
        import time
        time.sleep(0.5)
        playback = controller.sp.current_playback()
        
        if playback and playback.get('item'):
            track = playback['item']
            return f"⏭️ Next track: {track['name']} by {track['artists'][0]['name']}"
        else:
            return "⏭️ Skipped to next track"
            
    except Exception as e:
        return f"❌ Spotify skip error: {str(e)}"

def spotify_previous_track() -> str:
    """
    Go to previous track on Spotify
    """
    if not SPOTIPY_AVAILABLE:
        return "❌ spotipy not installed. Install with: pip install spotipy"
        
    try:
        controller = SpotifyController()
        if not controller._ensure_authenticated():
            return "🎵 Spotify not authenticated. Please run setup first."
            
        controller.sp.previous_track()
        
        # Wait a moment and get new track info
        import time
        time.sleep(0.5)
        playback = controller.sp.current_playback()
        
        if playback and playback.get('item'):
            track = playback['item']
            return f"⏮️ Previous track: {track['name']} by {track['artists'][0]['name']}"
        else:
            return "⏮️ Went to previous track"
            
    except Exception as e:
        return f"❌ Spotify previous error: {str(e)}"

def search_and_play_spotify(query: str) -> str:
    """
    Search for music on Spotify and play it
    Args:
        query: Search term (song, artist, album)
    """
    if not SPOTIPY_AVAILABLE:
        return "❌ spotipy not installed. Install with: pip install spotipy"
        
    try:
        controller = SpotifyController()
        if not controller._ensure_authenticated():
            return "🎵 Spotify not authenticated. Please run setup first."
            
        # Search for tracks
        results = controller.sp.search(q=query, type='track', limit=1)
        tracks = results.get('tracks', {}).get('items', [])
        
        if not tracks:
            return f"🔍 No tracks found for: {query}"
        
        track = tracks[0]
        track_uri = track['uri']
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        
        # Play the track
        controller.sp.start_playback(uris=[track_uri])
        
        return f"🎵 Now playing: {track_name} by {artist_name}"
        
    except Exception as e:
        return f"❌ Spotify search/play error: {str(e)}"

def get_media_players() -> List[str]:
    """
    Get list of running media players
    """
    try:
        media_players = []
        common_players = [
            'spotify.exe', 'vlc.exe', 'wmplayer.exe', 'itunes.exe',
            'musicbee.exe', 'foobar2000.exe', 'winamp.exe', 'aimp.exe'
        ]
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name'].lower()
                if proc_name in common_players:
                    media_players.append(proc.info['name'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return media_players
    except Exception as e:
        return [f"Error detecting players: {str(e)}"]

def control_media_player(action: str, player: str = "any") -> str:
    """
    Control local media players using Windows media keys
    Args:
        action: play_pause, next, previous, volume_up, volume_down
        player: specific player or "any"
    """
    try:
        import keyboard
        
        # Map actions to Windows media key codes
        key_mappings = {
            'play_pause': 'play/pause media',
            'next': 'next track',
            'previous': 'previous track',
            'volume_up': 'volume up',
            'volume_down': 'volume down'
        }
        
        if action in key_mappings:
            keyboard.send(key_mappings[action])
            return f"🎵 Sent {action} command to media player"
        else:
            return f"❌ Unknown action: {action}"
            
    except ImportError:
        # Fallback to sending keystrokes using subprocess
        try:
            key_codes = {
                'play_pause': 'F13',  # Media play/pause
                'next': 'F14',        # Media next
                'previous': 'F15',    # Media previous
            }
            
            if action in key_codes:
                # Use PowerShell to send media keys
                ps_cmd = f"""
                Add-Type -AssemblyName System.Windows.Forms
                [System.Windows.Forms.SendKeys]::SendWait('{{F13}}')
                """
                subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True)
                return f"🎵 Sent {action} command via PowerShell"
            else:
                return f"❌ Action not supported: {action}"
                
        except Exception as e:
            return f"❌ Media control error: {str(e)}"
    except Exception as e:
        return f"❌ Media control error: {str(e)}"

def get_system_volume() -> str:
    """
    Get current system volume level
    """
    try:
        from pycaw.pycaw import AudioUtilities, AudioSession, AudioEndpointVolume
        from comtypes import CLSCTX_ALL
        
        # Get default audio device
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(AudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = AudioEndpointVolume(interface)
        
        # Get volume level (0.0 to 1.0)
        current_volume = volume.GetMasterScalarVolume()
        volume_percent = int(current_volume * 100)
        
        is_muted = volume.GetMute()
        status = "🔇 Muted" if is_muted else f"🔊 {volume_percent}%"
        
        return f"🎵 System Volume: {status}"
        
    except ImportError:
        return "❌ pycaw library required for volume control. Install with: pip install pycaw"
    except Exception as e:
        return f"❌ Volume check error: {str(e)}"

def set_system_volume(level: int) -> str:
    """
    Set system volume level
    Args:
        level: Volume level (0-100)
    """
    try:
        from pycaw.pycaw import AudioUtilities, AudioEndpointVolume
        from comtypes import CLSCTX_ALL
        
        # Validate level
        level = max(0, min(100, level))
        
        # Get default audio device
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(AudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = AudioEndpointVolume(interface)
        
        # Set volume level (convert to 0.0-1.0 range)
        volume.SetMasterScalarVolume(level / 100.0, None)
        
        return f"🔊 System volume set to {level}%"
        
    except ImportError:
        return "❌ pycaw library required for volume control. Install with: pip install pycaw"
    except Exception as e:
        return f"❌ Volume control error: {str(e)}"

def create_spotify_playlist(name: str, description: str = "") -> str:
    """
    Create a new Spotify playlist
    Args:
        name: Playlist name
        description: Playlist description (optional)
    """
    if not SPOTIPY_AVAILABLE:
        return "❌ spotipy not installed. Install with: pip install spotipy"
        
    try:
        controller = SpotifyController()
        if not controller._ensure_authenticated():
            return "🎵 Spotify not authenticated. Please run setup first."
            
        # Get user ID
        user = controller.sp.current_user()
        user_id = user['id']
        
        # Create playlist
        playlist = controller.sp.user_playlist_create(
            user=user_id,
            name=name,
            public=False,
            description=description
        )
        
        playlist_url = playlist['external_urls']['spotify']
        return f"✅ Created playlist: {name}\n🔗 {playlist_url}"
        
    except Exception as e:
        return f"❌ Playlist creation error: {str(e)}"

def add_to_spotify_playlist(playlist_name: str, track_query: str) -> str:
    """
    Add a track to a Spotify playlist
    Args:
        playlist_name: Name of the playlist
        track_query: Search query for the track to add
    """
    if not SPOTIPY_AVAILABLE:
        return "❌ spotipy not installed. Install with: pip install spotipy"
        
    try:
        controller = SpotifyController()
        if not controller._ensure_authenticated():
            return "🎵 Spotify not authenticated. Please run setup first."
        
        # Search for the track
        results = controller.sp.search(q=track_query, type='track', limit=1)
        tracks = results.get('tracks', {}).get('items', [])
        
        if not tracks:
            return f"🔍 No tracks found for: {track_query}"
        
        track = tracks[0]
        track_uri = track['uri']
        track_name = track['name']
        artist_name = track['artists'][0]['name']
        
        # Get user's playlists
        playlists = controller.sp.current_user_playlists(limit=50)
        target_playlist = None
        
        for playlist in playlists['items']:
            if playlist['name'].lower() == playlist_name.lower():
                target_playlist = playlist
                break
        
        if not target_playlist:
            return f"❌ Playlist '{playlist_name}' not found"
        
        # Add track to playlist
        controller.sp.playlist_add_items(target_playlist['id'], [track_uri])
        
        return f"✅ Added '{track_name}' by {artist_name} to playlist '{playlist_name}'"
        
    except Exception as e:
        return f"❌ Error adding track to playlist: {str(e)}"

def get_music_recommendations(seed_type: str = "genre", seed_value: str = "pop", limit: int = 5) -> str:
    """
    Get music recommendations from Spotify
    Args:
        seed_type: 'genre', 'artist', or 'track'
        seed_value: The seed value (genre name, artist name, or track name)
        limit: Number of recommendations (1-20)
    """
    if not SPOTIPY_AVAILABLE:
        return "❌ spotipy not installed. Install with: pip install spotipy"
        
    try:
        controller = SpotifyController()
        if not controller._ensure_authenticated():
            return "🎵 Spotify not authenticated. Please run setup first."
        
        limit = max(1, min(20, limit))  # Clamp between 1 and 20
        
        # Build recommendation parameters
        kwargs = {'limit': limit}
        
        if seed_type == 'genre':
            kwargs['seed_genres'] = [seed_value.lower()]
        elif seed_type == 'artist':
            # Search for artist
            results = controller.sp.search(q=seed_value, type='artist', limit=1)
            artists = results.get('artists', {}).get('items', [])
            if not artists:
                return f"🔍 Artist not found: {seed_value}"
            kwargs['seed_artists'] = [artists[0]['id']]
        elif seed_type == 'track':
            # Search for track
            results = controller.sp.search(q=seed_value, type='track', limit=1)
            tracks = results.get('tracks', {}).get('items', [])
            if not tracks:
                return f"🔍 Track not found: {seed_value}"
            kwargs['seed_tracks'] = [tracks[0]['id']]
        else:
            return f"❌ Invalid seed type: {seed_type}. Use 'genre', 'artist', or 'track'"
        
        # Get recommendations
        recommendations = controller.sp.recommendations(**kwargs)
        tracks = recommendations.get('tracks', [])
        
        if not tracks:
            return f"🎵 No recommendations found for {seed_type}: {seed_value}"
        
        # Format recommendations
        result = f"🎵 Recommendations based on {seed_type}: {seed_value}\n\n"
        for i, track in enumerate(tracks, 1):
            track_name = track['name']
            artist_name = track['artists'][0]['name']
            result += f"{i}. {track_name} by {artist_name}\n"
        
        return result.strip()
        
    except Exception as e:
        return f"❌ Recommendations error: {str(e)}"

def get_spotify_playlists() -> str:
    """
    Get user's Spotify playlists
    """
    if not SPOTIPY_AVAILABLE:
        return "❌ spotipy not installed. Install with: pip install spotipy"
        
    try:
        controller = SpotifyController()
        if not controller._ensure_authenticated():
            return "🎵 Spotify not authenticated. Please run setup first."
        
        playlists = controller.sp.current_user_playlists(limit=50)
        
        if not playlists or not playlists.get('items'):
            return "🎵 No playlists found"
        
        result = "🎵 Your Spotify Playlists:\n\n"
        for i, playlist in enumerate(playlists['items'], 1):
            name = playlist['name']
            track_count = playlist['tracks']['total']
            result += f"{i}. {name} ({track_count} tracks)\n"
        
        return result.strip()
        
    except Exception as e:
        return f"❌ Error getting playlists: {str(e)}"

# Export all functions for the main application
__all__ = [
    'SpotifyController',
    'YouTubeMusicController',
    'get_spotify_status', 
    'spotify_play_pause', 
    'spotify_next_track', 
    'spotify_previous_track', 
    'search_and_play_spotify',
    'create_spotify_playlist',
    'add_to_spotify_playlist',
    'get_music_recommendations',
    'get_spotify_playlists',
    'search_youtube_music',
    'play_youtube_music',
    'get_ytmusic_playlists',
    'get_media_players',
    'control_media_player', 
    'get_system_volume', 
    'set_system_volume'
]