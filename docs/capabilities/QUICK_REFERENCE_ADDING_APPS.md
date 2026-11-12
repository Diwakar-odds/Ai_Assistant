# Quick Reference: Adding More Apps to Intent Recognizer

## How to Add New Apps

Edit `ai_assistant/ai/intent_recognizer.py` and add to the `app_aliases` dictionary:

```python
self.app_aliases = {
    # ... existing apps ...
    
    # Add your new app here:
    'your_app': ['your_app', 'your app', 'ur app', 'alias1', 'alias2'],
}
```

### Examples:

```python
# Adobe Acrobat
'acrobat': ['acrobat', 'adobe acrobat', 'pdf reader', 'acrobat reader'],

# PyCharm
'pycharm': ['pycharm', 'py charm', 'pycharm ide'],

# IntelliJ IDEA
'intellij': ['intellij', 'intelli j', 'idea'],

# Android Studio
'android_studio': ['android studio', 'android', 'as'],

# Slack
'slack': ['slack', 'slak'],

# Notion
'notion': ['notion', 'notes'],

# Figma
'figma': ['figma', 'design'],
```

## How to Add Hindi/Hinglish Variations

Add Hindi equivalents to your app aliases:

```python
'whatsapp': [
    'whatsapp', 
    'whats app',
    'wa',
    'whatsap',
    # Hindi variations
    'व्हाट्सएप',  # If using Hindi script
],
```

## How to Test New Apps

Run the test script:

```bash
cd f:\bn\assitant
python test_intent_recognizer.py
```

Or create a quick test:

```python
from ai_assistant.ai.intent_recognizer import IntentRecognizer

recognizer = IntentRecognizer()

# Test your new app
tests = [
    "open your_app",
    "your_app kholo",
    "ur app open karo",
]

for cmd in tests:
    result = recognizer.parse_command(cmd)
    print(f"{cmd} -> {result['app_name']}")
```

## Common App Categories

### Browsers
```python
'chrome': ['chrome', 'google chrome', 'browser'],
'firefox': ['firefox', 'fire fox', 'mozilla'],
'edge': ['edge', 'microsoft edge'],
'brave': ['brave', 'brave browser'],
```

### Communication
```python
'whatsapp': ['whatsapp', 'whats app', 'wa'],
'telegram': ['telegram', 'tele', 'tg'],
'discord': ['discord', 'disc'],
'slack': ['slack', 'slak'],
'teams': ['teams', 'microsoft teams', 'ms teams'],
'zoom': ['zoom', 'zoom meeting'],
```

### Development
```python
'vscode': ['vscode', 'vs code', 'visual studio code', 'code'],
'pycharm': ['pycharm', 'py charm'],
'sublime': ['sublime', 'sublime text'],
'atom': ['atom', 'atom editor'],
'notepad++': ['notepad++', 'notepad plus plus', 'npp'],
```

### Office
```python
'word': ['word', 'ms word', 'microsoft word', 'document'],
'excel': ['excel', 'ms excel', 'spreadsheet'],
'powerpoint': ['powerpoint', 'ppt', 'presentation'],
'outlook': ['outlook', 'email', 'mail'],
```

### Media
```python
'spotify': ['spotify', 'music', 'spot'],
'vlc': ['vlc', 'vlc player', 'video player'],
'obs': ['obs', 'obs studio'],
'itunes': ['itunes', 'apple music'],
```

### Design/Creative
```python
'photoshop': ['photoshop', 'ps', 'adobe photoshop'],
'illustrator': ['illustrator', 'ai', 'adobe illustrator'],
'figma': ['figma', 'design'],
'canva': ['canva'],
```

### Gaming
```python
'steam': ['steam', 'steam app'],
'discord': ['discord', 'disc'],
'epic': ['epic', 'epic games'],
```

## Pro Tips

1. **Common misspellings**: Add common typos
   ```python
   'whatsapp': ['whatsapp', 'whatsap', 'whatapp', 'watsapp']
   ```

2. **Short forms**: Add abbreviations
   ```python
   'telegram': ['telegram', 'tele', 'tg', 'tel']
   ```

3. **Spaces**: Handle both with and without spaces
   ```python
   'youtube': ['youtube', 'you tube', 'yt']
   ```

4. **Language mixing**: Add Hinglish versions
   ```python
   'music': ['music', 'gaana', 'song', 'songs']
   ```

## Dynamic Addition (In Code)

You can also add apps dynamically without editing the file:

```python
from ai_assistant.core.core import get_intent_recognizer

recognizer = get_intent_recognizer()
if recognizer:
    # Add new app at runtime
    recognizer.add_app_alias('my_app', ['my app', 'myapp', 'ma'])
```

This is useful for user-specific customizations!
