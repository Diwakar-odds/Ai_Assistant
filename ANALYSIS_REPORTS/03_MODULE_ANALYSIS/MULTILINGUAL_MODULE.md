# 🌍 Multilingual Module Analysis

**File:** `modules/multilingual.py`, `setup_multilingual.py`  
**Lines of Code:** 423  
**Status:** ⚠️ **PARTIALLY WORKING**  
**Test Coverage:** 0%  
**Last Updated:** November 17, 2025

---

## 📋 Functionality Overview

### Purpose
Provides multi-language support for the assistant with:
- Speech recognition in multiple languages
- Language-specific command processing
- Translation capabilities
- Multilingual text-to-speech

### Supported Languages
```python
SUPPORTED_LANGUAGES = {
    'english': 'en-US',
    'hindi': 'hi-IN',
    'spanish': 'es-ES',
    'french': 'fr-FR',
    'german': 'de-DE',
    'japanese': 'ja-JP',
    'chinese': 'zh-CN'
}
```

---

## 🐛 Issues Found

### Issue #1: Database Not Created on Init 🔴
**File:** `modules/multilingual.py`  
**Lines:** 28-35  
**Severity:** HIGH

```python
def __init__(self):
    self.db_path = "data/multilingual.db"
    self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
    # ❌ No database/table creation logic
    # ❌ Fails if data/ folder doesn't exist
    # ❌ No schema initialization
```

**Error when running:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'data/multilingual.db'
```

**Fix - Add Database Initialization:**

```python
import os
import sqlite3
from pathlib import Path

class MultilingualModule:
    def __init__(self):
        """Initialize multilingual module with database"""
        # Ensure data directory exists
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        self.db_path = data_dir / "multilingual.db"
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # Initialize database schema
        self._init_database()
        
        self.current_language = 'english'
        self.recognizer = sr.Recognizer()
    
    def _init_database(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Language preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS language_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                language_code TEXT NOT NULL,
                language_name TEXT NOT NULL,
                is_active INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Translation cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS translation_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_text TEXT NOT NULL,
                source_lang TEXT NOT NULL,
                target_lang TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_text, source_lang, target_lang)
            )
        """)
        
        # Command translations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS command_translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                english_command TEXT NOT NULL,
                language_code TEXT NOT NULL,
                translated_command TEXT NOT NULL,
                UNIQUE(english_command, language_code)
            )
        """)
        
        # Insert default language if table is empty
        cursor.execute("SELECT COUNT(*) as count FROM language_preferences")
        if cursor.fetchone()['count'] == 0:
            cursor.execute("""
                INSERT INTO language_preferences (language_code, language_name, is_active)
                VALUES ('en-US', 'English', 1)
            """)
        
        self.conn.commit()
        cursor.close()
```

---

### Issue #2: Vosk Model Loading Not Checked 🔴
**File:** `modules/multilingual.py`  
**Lines:** 45-60  
**Severity:** HIGH

```python
def load_vosk_model(self, language='en-US'):
    """Load Vosk speech recognition model"""
    model_path = f"model/vosk-model-small-{self._get_language_code(language)}"
    
    # ❌ No check if model exists
    # ❌ No error handling
    # ❌ Downloads not implemented
    
    self.vosk_model = Model(model_path)
    return True
```

**Error when model missing:**
```
FileNotFoundError: model/vosk-model-small-hi-0.22 not found
```

**Fix - Add Model Validation:**

```python
import os
import urllib.request
import zipfile

class MultilingualModule:
    VOSK_MODELS = {
        'en-US': {
            'name': 'vosk-model-small-en-us-0.15',
            'url': 'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip'
        },
        'hi-IN': {
            'name': 'vosk-model-small-hi-0.22',
            'url': 'https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip'
        },
        'es-ES': {
            'name': 'vosk-model-small-es-0.42',
            'url': 'https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip'
        }
    }
    
    def load_vosk_model(self, language='en-US'):
        """Load Vosk speech recognition model"""
        try:
            if language not in self.VOSK_MODELS:
                print(f"⚠️ No Vosk model available for {language}")
                return False
            
            model_info = self.VOSK_MODELS[language]
            model_path = f"model/{model_info['name']}"
            
            # Check if model exists
            if not os.path.exists(model_path):
                print(f"📥 Model not found. Downloading {model_info['name']}...")
                self._download_vosk_model(language, model_info)
            
            # Load model
            from vosk import Model
            self.vosk_model = Model(model_path)
            print(f"✅ Loaded Vosk model for {language}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load Vosk model: {e}")
            return False
    
    def _download_vosk_model(self, language, model_info):
        """Download Vosk model if not present"""
        try:
            model_dir = Path("model")
            model_dir.mkdir(exist_ok=True)
            
            zip_path = model_dir / f"{model_info['name']}.zip"
            
            # Download
            print(f"Downloading from {model_info['url']}...")
            urllib.request.urlretrieve(model_info['url'], zip_path)
            
            # Extract
            print(f"Extracting {zip_path}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(model_dir)
            
            # Clean up zip file
            zip_path.unlink()
            
            print(f"✅ Model downloaded and extracted successfully")
            
        except Exception as e:
            raise Exception(f"Failed to download model: {e}")
```

---

### Issue #3: Translation API Not Implemented 🔴
**File:** `modules/multilingual.py`  
**Lines:** 125-135  
**Severity:** HIGH

```python
def translate_text(self, text, target_language):
    """Translate text to target language"""
    # ❌ NOT IMPLEMENTED
    # Returns input text unchanged
    return text
```

**Fix - Implement Translation:**

```python
from googletrans import Translator, LANGUAGES

class MultilingualModule:
    def __init__(self):
        # ...
        self.translator = Translator()
        self.translation_cache = {}  # In-memory cache
    
    def translate_text(self, text, target_language, source_language='auto'):
        """Translate text to target language with caching"""
        try:
            # Check cache first
            cache_key = f"{text}:{source_language}:{target_language}"
            if cache_key in self.translation_cache:
                return self.translation_cache[cache_key]
            
            # Check database cache
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT translated_text FROM translation_cache
                WHERE source_text = ? AND source_lang = ? AND target_lang = ?
            """, (text, source_language, target_language))
            
            row = cursor.fetchone()
            if row:
                translated = row['translated_text']
                self.translation_cache[cache_key] = translated
                return translated
            
            # Translate using Google Translate
            result = self.translator.translate(
                text,
                src=source_language,
                dest=target_language
            )
            
            translated = result.text
            
            # Cache in memory
            self.translation_cache[cache_key] = translated
            
            # Cache in database
            cursor.execute("""
                INSERT INTO translation_cache 
                (source_text, source_lang, target_lang, translated_text)
                VALUES (?, ?, ?, ?)
            """, (text, source_language, target_language, translated))
            self.conn.commit()
            
            cursor.close()
            return translated
            
        except Exception as e:
            print(f"Translation error: {e}")
            return text  # Return original on error
    
    def get_available_languages(self):
        """Get list of available translation languages"""
        return LANGUAGES
```

---

### Issue #4: No Text-to-Speech for Non-English 🟡
**File:** `modules/multilingual.py`  
**Lines:** 178-190  
**Severity:** MODERATE

```python
def speak(self, text, language='en-US'):
    """Speak text in specified language"""
    try:
        engine = pyttsx3.init()
        # ❌ Doesn't change voice based on language
        # ❌ Only uses default English voice
        engine.say(text)
        engine.runAndWait()
    except:
        pass
```

**Fix - Language-Specific TTS:**

```python
import pyttsx3

class MultilingualModule:
    def __init__(self):
        # ...
        self.tts_engine = pyttsx3.init()
        self.tts_voices = self._get_available_voices()
    
    def _get_available_voices(self):
        """Map languages to available TTS voices"""
        voices = self.tts_engine.getProperty('voices')
        
        language_voices = {}
        for voice in voices:
            # Extract language from voice ID
            if 'english' in voice.name.lower() or 'en' in voice.id.lower():
                language_voices['en-US'] = voice.id
            elif 'hindi' in voice.name.lower() or 'hi' in voice.id.lower():
                language_voices['hi-IN'] = voice.id
            elif 'spanish' in voice.name.lower() or 'es' in voice.id.lower():
                language_voices['es-ES'] = voice.id
            # Add more mappings...
        
        return language_voices
    
    def speak(self, text, language='en-US'):
        """Speak text in specified language"""
        try:
            # Set voice for language
            if language in self.tts_voices:
                self.tts_engine.setProperty('voice', self.tts_voices[language])
            else:
                print(f"⚠️ No voice available for {language}, using default")
            
            # Set rate and volume
            self.tts_engine.setProperty('rate', 150)
            self.tts_engine.setProperty('volume', 0.9)
            
            # Speak
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
            
        except Exception as e:
            print(f"TTS error: {e}")
    
    def list_available_voices(self):
        """List all available TTS voices"""
        voices = self.tts_engine.getProperty('voices')
        return [{
            'id': voice.id,
            'name': voice.name,
            'languages': voice.languages
        } for voice in voices]
```

---

### Issue #5: Command Translation Not Working 🟡
**File:** `modules/multilingual.py`  
**Lines:** 210-230  
**Severity:** MODERATE

```python
def translate_command(self, command, from_language, to_language='english'):
    """Translate command from one language to English"""
    # ❌ Uses simple dictionary lookup only
    # ❌ Doesn't handle variations or synonyms
    # ❌ Very limited command set
    
    command_translations = {
        'hindi': {
            'समय बताओ': 'what is the time',
            'नोट लिखो': 'write a note',
        }
    }
    
    return command_translations.get(from_language, {}).get(command, command)
```

**Fix - Better Command Translation:**

```python
class MultilingualModule:
    def __init__(self):
        # ...
        self._load_command_translations()
    
    def _load_command_translations(self):
        """Load command translations from database"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM command_translations")
        rows = cursor.fetchall()
        
        self.command_translations = {}
        for row in rows:
            lang = row['language_code']
            if lang not in self.command_translations:
                self.command_translations[lang] = {}
            
            self.command_translations[lang][row['translated_command']] = row['english_command']
        
        cursor.close()
    
    def translate_command(self, command, from_language, to_language='en-US'):
        """Translate command with fuzzy matching"""
        if from_language == to_language:
            return command
        
        command_lower = command.lower().strip()
        
        # Try exact match first
        if from_language in self.command_translations:
            if command_lower in self.command_translations[from_language]:
                return self.command_translations[from_language][command_lower]
        
        # Try fuzzy matching
        best_match = self._fuzzy_match_command(command_lower, from_language)
        if best_match:
            return best_match
        
        # Fallback to text translation
        return self.translate_text(command, 'en', from_language[:2])
    
    def _fuzzy_match_command(self, command, language):
        """Find best matching command using fuzzy matching"""
        from difflib import get_close_matches
        
        if language not in self.command_translations:
            return None
        
        commands = list(self.command_translations[language].keys())
        matches = get_close_matches(command, commands, n=1, cutoff=0.8)
        
        if matches:
            return self.command_translations[language][matches[0]]
        
        return None
    
    def add_command_translation(self, english_command, language_code, translated_command):
        """Add new command translation"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO command_translations
            (english_command, language_code, translated_command)
            VALUES (?, ?, ?)
        """, (english_command, language_code, translated_command))
        self.conn.commit()
        cursor.close()
        
        # Update in-memory cache
        self._load_command_translations()
```

---

## 🧪 Testing Requirements

**Current Tests:** 0  
**Required Tests:** 15+

```python
# test_multilingual.py
import pytest
from modules.multilingual import MultilingualModule

@pytest.fixture
def ml_module():
    module = MultilingualModule()
    yield module
    module.conn.close()

def test_database_initialization(ml_module):
    """Test database is created with correct schema"""
    cursor = ml_module.conn.cursor()
    
    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    assert 'language_preferences' in tables
    assert 'translation_cache' in tables
    assert 'command_translations' in tables

def test_translation(ml_module):
    """Test text translation"""
    text = "Hello, how are you?"
    translated = ml_module.translate_text(text, 'es')
    
    assert translated != text
    assert len(translated) > 0

def test_translation_cache(ml_module):
    """Test translation caching works"""
    text = "Test phrase"
    
    # First translation
    result1 = ml_module.translate_text(text, 'fr')
    
    # Second translation (should be cached)
    result2 = ml_module.translate_text(text, 'fr')
    
    assert result1 == result2

def test_command_translation(ml_module):
    """Test command translation"""
    # Add test command
    ml_module.add_command_translation(
        "what is the time",
        "hi-IN",
        "समय क्या है"
    )
    
    result = ml_module.translate_command("समय क्या है", "hi-IN")
    assert result == "what is the time"

def test_vosk_model_check(ml_module):
    """Test Vosk model availability check"""
    # Should return True for English (model exists)
    result = ml_module.load_vosk_model('en-US')
    assert result == True

def test_available_languages(ml_module):
    """Test getting available languages"""
    languages = ml_module.get_available_languages()
    assert 'en' in languages
    assert 'es' in languages
    assert 'hi' in languages

def test_tts_voices(ml_module):
    """Test TTS voice listing"""
    voices = ml_module.list_available_voices()
    assert len(voices) > 0
    assert 'id' in voices[0]
    assert 'name' in voices[0]

def test_fuzzy_command_matching(ml_module):
    """Test fuzzy matching for commands"""
    ml_module.add_command_translation(
        "what is the weather",
        "en-US",
        "what's the weather"
    )
    
    # Should match despite slight difference
    result = ml_module.translate_command("whats the weather", "en-US")
    assert result == "what is the weather"
```

---

## 📊 Feature Completeness

| Feature | Status | Priority |
|---------|--------|----------|
| Database initialization | ❌ Broken | P0 |
| Vosk model loading | ⚠️ No validation | P0 |
| Text translation | ❌ Not implemented | P0 |
| Command translation | ⚠️ Basic only | P1 |
| Language-specific TTS | ❌ Not implemented | P1 |
| Translation caching | ❌ Not implemented | P1 |
| Fuzzy command matching | ❌ Not implemented | P2 |
| Model auto-download | ❌ Not implemented | P2 |

---

## 🔧 Fix Priority

### P0 - Critical (Week 1)
- [ ] Fix database initialization (2 hours)
- [ ] Add Vosk model validation (1 hour)
- [ ] Implement text translation (3 hours)
- [ ] Add error handling (1 hour)

### P1 - High (Week 2)
- [ ] Implement translation caching (2 hours)
- [ ] Add language-specific TTS (3 hours)
- [ ] Improve command translation (2 hours)
- [ ] Write tests (4 hours)

### P2 - Medium (Week 3)
- [ ] Add fuzzy command matching (2 hours)
- [ ] Implement model auto-download (3 hours)
- [ ] Add language detection (1 hour)
- [ ] Performance optimization (2 hours)

**Total Effort:** 15-20 hours

---

## 📚 Dependencies

```python
# Add to requirements.txt
googletrans==4.0.0-rc1  # For translation
vosk==0.3.45            # For speech recognition
pyttsx3==2.90           # For text-to-speech
```

---

**Priority:** 🟡 P1  
**Status:** Partially working, needs implementation  
**Impact:** Medium - affects international users

**Next Report:** [Multimodal Module →](MULTIMODAL_MODULE.md)
