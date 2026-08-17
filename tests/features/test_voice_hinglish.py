"""
Unit tests for voice recognition and Hinglish command processing.
Tests modules/multilingual.py voice functions and modules/core.py Hinglish processing.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules import multilingual, core


class TestVoskModelLoading(unittest.TestCase):
    """Test Vosk model loading functionality."""
    
    @patch('modules.multilingual.os.path.exists')
    @patch('modules.multilingual.Model')
    def test_load_vosk_models_success(self, mock_model, mock_exists):
        """Test successful loading of Vosk models."""
        mock_exists.return_value = True
        mock_model.return_value = MagicMock()
        
        # Reset the singleton
        multilingual.MultilingualSupport._instance = None
        support = multilingual.MultilingualSupport()
        
        models = support._load_vosk_models()
        
        self.assertIsNotNone(models.get('en'))
        self.assertIsNotNone(models.get('hi'))
        self.assertEqual(mock_model.call_count, 2)
    
    @patch('modules.multilingual.os.path.exists')
    def test_load_vosk_models_missing(self, mock_exists):
        """Test loading when Vosk models are missing."""
        mock_exists.return_value = False
        
        # Reset the singleton
        multilingual.MultilingualSupport._instance = None
        support = multilingual.MultilingualSupport()
        
        models = support._load_vosk_models()
        
        self.assertEqual(models, {})


class TestVoiceListenLoop(unittest.TestCase):
    """Test voice_listen_loop function."""
    
    @patch('modules.multilingual.VOSK_AVAILABLE', False)
    def test_voice_listen_loop_no_vosk(self):
        """Test voice_listen_loop when Vosk is not available."""
        result = multilingual.voice_listen_loop(use_vosk=True)
        self.assertIn("Vosk library not available", result)
    
    def test_voice_listen_loop_invalid_language(self):
        """Test voice_listen_loop with invalid language parameter."""
        result = multilingual.voice_listen_loop(language='invalid')
        self.assertIn("Invalid language", result)
    
    @patch('modules.multilingual.threading.Thread')
    def test_voice_listen_loop_starts_thread(self, mock_thread):
        """Test that voice_listen_loop starts a thread."""
        mock_callback = Mock()
        mock_stop_event = Mock()
        
        result = multilingual.voice_listen_loop(
            callback_function=mock_callback,
            stop_event=mock_stop_event,
            use_vosk=False
        )
        
        self.assertIn("started", result.lower())
        mock_thread.assert_called_once()


class TestVoiceListenLoopGoogle(unittest.TestCase):
    """Test Google Speech Recognition voice loop."""
    
    @patch('modules.multilingual.sr')
    @patch('modules.multilingual.MultilingualSupport')
    def test_voice_listen_loop_google_recognition(self, mock_support_class, mock_sr):
        """Test Google voice recognition loop."""
        # Setup mocks
        mock_recognizer = MagicMock()
        mock_sr.Recognizer.return_value = mock_recognizer
        mock_sr.Microphone.return_value.__enter__ = MagicMock()
        
        # Mock the listen method
        mock_audio = MagicMock()
        mock_recognizer.listen.return_value = mock_audio
        mock_recognizer.recognize_google.return_value = "hey assistant play music"
        
        # Mock stop event to stop after one iteration
        mock_stop_event = MagicMock()
        mock_stop_event.is_set.side_effect = [False, True]
        
        # Mock callback
        mock_callback = Mock()
        
        # Mock support instance
        mock_support = MagicMock()
        mock_support_class.return_value = mock_support
        mock_support.speak_multilingual.return_value = None
        
        # Call the function
        multilingual._voice_listen_loop_google(
            mock_callback,
            ['hey assistant'],
            'en',
            mock_stop_event
        )
        
        # Verify callback was called
        mock_callback.assert_called_once()


class TestVoiceListenLoopVosk(unittest.TestCase):
    """Test Vosk offline voice recognition loop."""
    
    @patch('modules.multilingual.VOSK_AVAILABLE', True)
    @patch('modules.multilingual.pyaudio')
    @patch('modules.multilingual.KaldiRecognizer')
    @patch('modules.multilingual.MultilingualSupport')
    def test_voice_listen_loop_vosk_recognition(self, mock_support_class, mock_recognizer_class, mock_pyaudio, ):
        """Test Vosk voice recognition loop."""
        # Setup mocks
        mock_support = MagicMock()
        mock_support_class.return_value = mock_support
        mock_support.vosk_models = {'en': MagicMock()}
        mock_support.speak_multilingual.return_value = None
        
        # Mock PyAudio
        mock_audio = MagicMock()
        mock_pyaudio.PyAudio.return_value = mock_audio
        mock_stream = MagicMock()
        mock_audio.open.return_value = mock_stream
        mock_stream.read.return_value = b'audio_data'
        
        # Mock recognizer
        mock_recognizer = MagicMock()
        mock_recognizer_class.return_value = mock_recognizer
        mock_recognizer.AcceptWaveform.return_value = True
        mock_recognizer.Result.return_value = json.dumps({'text': 'hey assistant test command'})
        
        # Mock stop event to stop after one iteration
        mock_stop_event = MagicMock()
        mock_stop_event.is_set.side_effect = [False, True]
        
        # Mock callback
        mock_callback = Mock()
        
        # Call the function
        multilingual._voice_listen_loop_vosk(
            mock_callback,
            ['hey assistant'],
            'en',
            mock_stop_event
        )
        
        # Verify callback was called with the command text
        mock_callback.assert_called_once()


class TestTestVoiceRecognition(unittest.TestCase):
    """Test test_voice_recognition function."""
    
    @patch('modules.multilingual.VOSK_AVAILABLE', True)
    @patch('modules.multilingual.pyaudio')
    @patch('modules.multilingual.KaldiRecognizer')
    @patch('modules.multilingual.MultilingualSupport')
    def test_voice_recognition_test_function(self, mock_support_class, mock_recognizer_class, mock_pyaudio):
        """Test the test_voice_recognition function."""
        # Setup mocks
        mock_support = MagicMock()
        mock_support_class.return_value = mock_support
        mock_support.vosk_models = {'en': MagicMock()}
        mock_support.speak_multilingual.return_value = None
        
        # Mock PyAudio
        mock_audio = MagicMock()
        mock_pyaudio.PyAudio.return_value = mock_audio
        mock_stream = MagicMock()
        mock_audio.open.return_value = mock_stream
        mock_stream.read.return_value = b'audio_data'
        
        # Mock recognizer
        mock_recognizer = MagicMock()
        mock_recognizer_class.return_value = mock_recognizer
        mock_recognizer.AcceptWaveform.side_effect = [True, False]
        mock_recognizer.Result.return_value = json.dumps({'text': 'test speech'})
        mock_recognizer.FinalResult.return_value = json.dumps({'text': ''})
        
        # Call function
        result = multilingual.test_voice_recognition(duration=1, language='en')
        
        self.assertIn("Testing voice recognition", result)


class TestHinglishVolumeCommands(unittest.TestCase):
    """Test Hinglish volume control commands."""
    
    def test_volume_up_command(self):
        """Test volume up in Hinglish."""
        test_commands = [
            "volume badhao",
            "awaaz badha do",
            "sound zyada karo",
            "volume up karo"
        ]
        
        for command in test_commands:
            with patch('modules.core.AudioUtilities'):
                result = core.process_hinglish_command(command)
                self.assertEqual(result['detected_command'], 'volume_up')
    
    def test_volume_down_command(self):
        """Test volume down in Hinglish."""
        test_commands = [
            "volume kam karo",
            "awaaz ghata do",
            "sound down karo"
        ]
        
        for command in test_commands:
            with patch('modules.core.AudioUtilities'):
                result = core.process_hinglish_command(command)
                self.assertEqual(result['detected_command'], 'volume_down')
    
    def test_mute_command(self):
        """Test mute in Hinglish."""
        test_commands = [
            "volume mute karo",
            "awaaz band karo",
            "sound chup karo"
        ]
        
        for command in test_commands:
            with patch('modules.core.AudioUtilities'):
                result = core.process_hinglish_command(command)
                self.assertEqual(result['detected_command'], 'mute')
    
    def test_set_volume_level(self):
        """Test setting specific volume level."""
        test_commands = [
            "volume 50 karo",
            "awaaz pachaas set karo"
        ]
        
        with patch('modules.core.AudioUtilities'):
            result = core.process_hinglish_command(test_commands[0])
            self.assertEqual(result['detected_command'], 'set_volume')
            self.assertEqual(result['parameters']['level'], 50)


class TestHinglishPhoneCommands(unittest.TestCase):
    """Test Hinglish phone calling commands."""
    
    def test_call_with_phone_number(self):
        """Test phone call with number."""
        result = core.process_hinglish_command("9876543210 ko call karo")
        
        self.assertEqual(result['detected_command'], 'make_call')
        self.assertIn('phone_number', result['parameters'])
        self.assertIn('9876543210', result['parameters']['phone_number'])
    
    def test_call_with_contact_name(self):
        """Test phone call with contact name."""
        result = core.process_hinglish_command("raj ko call karo")
        
        self.assertEqual(result['detected_command'], 'make_call')
        self.assertIn('contact_name', result['parameters'])
        self.assertEqual(result['parameters']['contact_name'], 'raj')
    
    def test_call_stub_function(self):
        """Test phone call stub function directly."""
        result = core.make_phone_call(contact_name="John")
        
        self.assertIn("stub", result.lower())
        self.assertIn("John", result)


class TestHinglishAppCommands(unittest.TestCase):
    """Test Hinglish app opening commands."""
    
    @patch('modules.core.smart_open_application')
    def test_open_app_hinglish(self, mock_open):
        """Test opening apps with Hinglish commands."""
        mock_open.return_value = "Opening Chrome"
        
        test_commands = [
            "chrome kholo",
            "notepad open karo",
            "calculator chalu karo"
        ]
        
        for command in test_commands:
            result = core.process_hinglish_command(command)
            self.assertEqual(result['detected_command'], 'open_app')
            self.assertIn('app_name', result['parameters'])


class TestHinglishSearchCommands(unittest.TestCase):
    """Test Hinglish search commands."""
    
    @patch('modules.core.search_google')
    def test_google_search_hinglish(self, mock_search):
        """Test Google search with Hinglish."""
        mock_search.return_value = "Searching Google"
        
        result = core.process_hinglish_command("google me weather dhundo")
        
        self.assertEqual(result['detected_command'], 'search_google')
        self.assertIn('query', result['parameters'])
    
    @patch('modules.core.search_youtube')
    def test_youtube_search_hinglish(self, mock_search):
        """Test YouTube search with Hinglish."""
        mock_search.return_value = "Searching YouTube"
        
        result = core.process_hinglish_command("youtube pe songs dhundo")
        
        self.assertEqual(result['detected_command'], 'search_youtube')
        self.assertIn('query', result['parameters'])


class TestExtractNumber(unittest.TestCase):
    """Test number extraction from text."""
    
    def test_extract_digit(self):
        """Test extracting digits."""
        self.assertEqual(core.extract_number("volume 50"), 50)
        self.assertEqual(core.extract_number("set to 75 percent"), 75)
    
    def test_extract_english_words(self):
        """Test extracting English number words."""
        self.assertEqual(core.extract_number("volume fifty"), 50)
        self.assertEqual(core.extract_number("set to twenty"), 20)
    
    def test_extract_hindi_words(self):
        """Test extracting Hindi number words."""
        self.assertEqual(core.extract_number("volume pachaas"), 50)
        self.assertEqual(core.extract_number("set to bees"), 20)
    
    def test_no_number(self):
        """Test when no number is present."""
        self.assertIsNone(core.extract_number("volume up"))
        self.assertIsNone(core.extract_number("just text"))


class TestVolumeControlFunctions(unittest.TestCase):
    """Test volume control functions."""
    
    @patch('modules.core.AudioUtilities')
    def test_set_system_volume(self, mock_audio_utils):
        """Test setting system volume."""
        mock_volume = MagicMock()
        mock_audio_utils.GetSpeakers.return_value.Activate.return_value = mock_volume
        
        result = core.set_system_volume(50)
        
        self.assertIn("50", result)
        self.assertIn("Success", result)
    
    @patch('modules.core.AudioUtilities')
    def test_volume_up(self, mock_audio_utils):
        """Test volume up function."""
        mock_volume_interface = MagicMock()
        mock_volume_interface.GetMasterVolumeLevelScalar.return_value = 0.5
        mock_audio_utils.GetSpeakers.return_value.Activate.return_value = mock_volume_interface
        
        result = core.volume_up(10)
        
        self.assertIn("60", result)
        mock_volume_interface.SetMasterVolumeLevelScalar.assert_called_once()
    
    @patch('modules.core.AudioUtilities')
    def test_volume_down(self, mock_audio_utils):
        """Test volume down function."""
        mock_volume_interface = MagicMock()
        mock_volume_interface.GetMasterVolumeLevelScalar.return_value = 0.5
        mock_audio_utils.GetSpeakers.return_value.Activate.return_value = mock_volume_interface
        
        result = core.volume_down(10)
        
        self.assertIn("40", result)
        mock_volume_interface.SetMasterVolumeLevelScalar.assert_called_once()
    
    @patch('modules.core.AudioUtilities')
    def test_mute_volume(self, mock_audio_utils):
        """Test mute function."""
        mock_volume_interface = MagicMock()
        mock_audio_utils.GetSpeakers.return_value.Activate.return_value = mock_volume_interface
        
        result = core.mute_volume()
        
        self.assertIn("muted", result.lower())
        mock_volume_interface.SetMute.assert_called_once_with(1, None)
    
    @patch('modules.core.AudioUtilities')
    def test_unmute_volume(self, mock_audio_utils):
        """Test unmute function."""
        mock_volume_interface = MagicMock()
        mock_audio_utils.GetSpeakers.return_value.Activate.return_value = mock_volume_interface
        
        result = core.unmute_volume()
        
        self.assertIn("unmuted", result.lower())
        mock_volume_interface.SetMute.assert_called_once_with(0, None)


if __name__ == '__main__':
    unittest.main()
