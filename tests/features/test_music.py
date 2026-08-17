"""
Unit tests for Music Module (Spotify Integration)
Tests Spotify OAuth authentication, playback controls, and playlist management
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules import music


class TestSpotifyController(unittest.TestCase):
    """Test SpotifyController class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Reset singleton instance for each test
        music.SpotifyController._instance = None
    
    @patch.dict(os.environ, {
        'SPOTIFY_CLIENT_ID': 'test_client_id',
        'SPOTIFY_CLIENT_SECRET': 'test_client_secret'
    })
    def test_spotify_controller_initialization(self):
        """Test SpotifyController initializes with environment variables"""
        controller = music.SpotifyController()
        self.assertEqual(controller.client_id, 'test_client_id')
        self.assertEqual(controller.client_secret, 'test_client_secret')
        self.assertEqual(controller.redirect_uri, 'http://localhost:8888/callback')
    
    def test_spotify_controller_singleton(self):
        """Test SpotifyController is a singleton"""
        controller1 = music.SpotifyController()
        controller2 = music.SpotifyController()
        self.assertIs(controller1, controller2)
    
    @patch('modules.music.SPOTIPY_AVAILABLE', False)
    def test_setup_auth_without_spotipy(self):
        """Test setup_spotify_auth when spotipy is not installed"""
        controller = music.SpotifyController()
        result = controller.setup_spotify_auth()
        self.assertIn("spotipy library not installed", result)
        self.assertIn("❌", result)
    
    @patch('modules.music.SPOTIPY_AVAILABLE', True)
    def test_setup_auth_missing_credentials(self):
        """Test setup_spotify_auth with missing credentials"""
        controller = music.SpotifyController()
        controller.client_id = None
        controller.client_secret = None
        
        result = controller.setup_spotify_auth()
        self.assertIn("credentials not configured", result)
        self.assertIn("developer.spotify.com", result)
    
    @patch('modules.music.SPOTIPY_AVAILABLE', True)
    @patch('modules.music.spotipy.Spotify')
    @patch('modules.music.SpotifyOAuth')
    @patch.dict(os.environ, {
        'SPOTIFY_CLIENT_ID': 'test_id',
        'SPOTIFY_CLIENT_SECRET': 'test_secret'
    })
    def test_setup_auth_success(self, mock_oauth, mock_spotify):
        """Test successful Spotify authentication"""
        # Mock the Spotify client
        mock_sp_instance = Mock()
        mock_sp_instance.current_user.return_value = {
            'display_name': 'Test User',
            'id': 'test_user_id'
        }
        mock_spotify.return_value = mock_sp_instance
        
        controller = music.SpotifyController()
        result = controller.setup_spotify_auth()
        
        self.assertIn("✅", result)
        self.assertIn("authenticated", result.lower())
        self.assertIn("Test User", result)


class TestSpotifyPlayback(unittest.TestCase):
    """Test Spotify playback functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        music.SpotifyController._instance = None
    
    @patch('modules.music.SPOTIPY_AVAILABLE', False)
    def test_get_status_without_spotipy(self):
        """Test get_spotify_status when spotipy is not installed"""
        result = music.get_spotify_status()
        self.assertIn("spotipy not installed", result)
        self.assertIn("❌", result)
    
    @patch('modules.music.SPOTIPY_AVAILABLE', True)
    @patch.object(music.SpotifyController, '_ensure_authenticated', return_value=False)
    def test_get_status_not_authenticated(self, mock_auth):
        """Test get_spotify_status when not authenticated"""
        result = music.get_spotify_status()
        self.assertIn("not authenticated", result)
    
    @patch('modules.music.SPOTIPY_AVAILABLE', True)
    @patch.object(music.SpotifyController, '_ensure_authenticated', return_value=True)
    @patch.object(music.SpotifyController, 'sp')
    def test_get_status_nothing_playing(self, mock_sp, mock_auth):
        """Test get_spotify_status when nothing is playing"""
        controller = music.SpotifyController()
        controller.sp = Mock()
        controller.sp.current_playback.return_value = None
        
        result = music.get_spotify_status()
        self.assertIn("No track currently playing", result)
    
    @patch('modules.music.SPOTIPY_AVAILABLE', True)
    @patch.object(music.SpotifyController, '_ensure_authenticated', return_value=True)
    def test_get_status_playing(self, mock_auth):
        """Test get_spotify_status when track is playing"""
        controller = music.SpotifyController()
        controller.sp = Mock()
        controller.sp.current_playback.return_value = {
            'item': {
                'name': 'Test Song',
                'artists': [{'name': 'Test Artist'}],
                'duration_ms': 180000
            },
            'is_playing': True,
            'progress_ms': 60000
        }
        
        result = music.get_spotify_status()
        self.assertIn("Test Song", result)
        self.assertIn("Test Artist", result)
        self.assertIn("Playing", result)
    
    @patch('modules.music.SPOTIPY_AVAILABLE', True)
    @patch.object(music.SpotifyController, '_ensure_authenticated', return_value=True)
    def test_play_pause_playing(self, mock_auth):
        """Test spotify_play_pause when currently playing"""
        controller = music.SpotifyController()
        controller.sp = Mock()
        controller.sp.current_playback.return_value = {
            'is_playing': True
        }
        
        result = music.spotify_play_pause()
        controller.sp.pause_playback.assert_called_once()
        self.assertIn("paused", result.lower())
    
    @patch('modules.music.SPOTIPY_AVAILABLE', True)
    @patch.object(music.SpotifyController, '_ensure_authenticated', return_value=True)
    def test_play_pause_paused(self, mock_auth):
        """Test spotify_play_pause when currently paused"""
        controller = music.SpotifyController()
        controller.sp = Mock()
        controller.sp.current_playback.return_value = {
            'is_playing': False
        }
        
        result = music.spotify_play_pause()
        controller.sp.start_playback.assert_called_once()
        self.assertIn("resumed", result.lower())


class TestSpotifySearch(unittest.TestCase):
    """Test Spotify search and play functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        music.SpotifyController._instance = None
    
    @patch('modules.music.SPOTIPY_AVAILABLE', True)
    @patch.object(music.SpotifyController, '_ensure_authenticated', return_value=True)
    def test_search_and_play_success(self, mock_auth):
        """Test successful search and play"""
        controller = music.SpotifyController()
        controller.sp = Mock()
        controller.sp.search.return_value = {
            'tracks': {
                'items': [{
                    'uri': 'spotify:track:123',
                    'name': 'Test Song',
                    'artists': [{'name': 'Test Artist'}]
                }]
            }
        }
        
        result = music.search_and_play_spotify('test query')
        controller.sp.start_playback.assert_called_once_with(uris=['spotify:track:123'])
        self.assertIn("Now playing", result)
        self.assertIn("Test Song", result)
    
    @patch('modules.music.SPOTIPY_AVAILABLE', True)
    @patch.object(music.SpotifyController, '_ensure_authenticated', return_value=True)
    def test_search_and_play_not_found(self, mock_auth):
        """Test search with no results"""
        controller = music.SpotifyController()
        controller.sp = Mock()
        controller.sp.search.return_value = {
            'tracks': {
                'items': []
            }
        }
        
        result = music.search_and_play_spotify('nonexistent song')
        self.assertIn("No tracks found", result)


class TestSpotifyPlaylists(unittest.TestCase):
    """Test Spotify playlist management"""
    
    def setUp(self):
        """Set up test fixtures"""
        music.SpotifyController._instance = None
    
    @patch('modules.music.SPOTIPY_AVAILABLE', True)
    @patch.object(music.SpotifyController, '_ensure_authenticated', return_value=True)
    def test_create_playlist_success(self, mock_auth):
        """Test successful playlist creation"""
        controller = music.SpotifyController()
        controller.sp = Mock()
        controller.sp.current_user.return_value = {'id': 'test_user'}
        controller.sp.user_playlist_create.return_value = {
            'name': 'Test Playlist',
            'external_urls': {'spotify': 'https://open.spotify.com/playlist/123'}
        }
        
        result = music.create_spotify_playlist('Test Playlist', 'Test Description')
        self.assertIn("Created playlist", result)
        self.assertIn("Test Playlist", result)
    
    @patch('modules.music.SPOTIPY_AVAILABLE', True)
    @patch.object(music.SpotifyController, '_ensure_authenticated', return_value=True)
    def test_get_playlists(self, mock_auth):
        """Test getting user playlists"""
        controller = music.SpotifyController()
        controller.sp = Mock()
        controller.sp.current_user_playlists.return_value = {
            'items': [
                {'name': 'Playlist 1', 'tracks': {'total': 10}},
                {'name': 'Playlist 2', 'tracks': {'total': 25}}
            ]
        }
        
        result = music.get_spotify_playlists()
        self.assertIn("Playlist 1", result)
        self.assertIn("Playlist 2", result)
        self.assertIn("10 tracks", result)


class TestSpotifyRecommendations(unittest.TestCase):
    """Test Spotify recommendations"""
    
    def setUp(self):
        """Set up test fixtures"""
        music.SpotifyController._instance = None
    
    @patch('modules.music.SPOTIPY_AVAILABLE', True)
    @patch.object(music.SpotifyController, '_ensure_authenticated', return_value=True)
    def test_recommendations_by_genre(self, mock_auth):
        """Test getting recommendations by genre"""
        controller = music.SpotifyController()
        controller.sp = Mock()
        controller.sp.recommendations.return_value = {
            'tracks': [
                {
                    'name': 'Recommended Song 1',
                    'artists': [{'name': 'Artist 1'}]
                },
                {
                    'name': 'Recommended Song 2',
                    'artists': [{'name': 'Artist 2'}]
                }
            ]
        }
        
        result = music.get_music_recommendations('genre', 'pop', 5)
        self.assertIn("Recommended Song 1", result)
        self.assertIn("Recommended Song 2", result)
        self.assertIn("pop", result.lower())


class TestVolumeControl(unittest.TestCase):
    """Test system volume control functions"""
    
    @patch('modules.music.AudioUtilities')
    @patch('modules.music.AudioEndpointVolume')
    def test_get_system_volume(self, mock_volume, mock_audio):
        """Test getting system volume"""
        # This test would need proper mocking of Windows audio APIs
        # For now, we'll skip it as it requires complex COM object mocking
        pass


if __name__ == '__main__':
    unittest.main()
