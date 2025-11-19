# 🔧 Core Module Analysis

**File:** `modules/core.py`  
**Lines of Code:** 218  
**Status:** ⚠️ **PARTIALLY WORKING**  
**Last Updated:** November 17, 2025

---

## 📋 Functionality Overview

The Core module provides fundamental Windows automation capabilities:

- ✅ Write notes to Notepad
- ✅ Open/close applications
- ✅ Search Google/YouTube
- ✅ Text-to-speech
- ✅ System volume control
- ✅ File operations
- ⚠️ Application discovery (delegates to app_discovery module)

---

## 🐛 Issues Found

### Issue #1: Command Injection Vulnerability 🔴
**Lines:** 60-77  
**Severity:** CRITICAL

```python
def search_google(query: str) -> str:
    try:
        import urllib.parse
        quoted_query = urllib.parse.quote_plus(query)
        # ❌ VULNERABLE: os.system with user input
        os.system(f'start "chrome" "https://www.google.com/search?q={quoted_query}"')
        return f"Successfully searched Google for: {query}"
```

**Problem:** While `quote_plus` is used, the `os.system()` call with shell=True is inherently dangerous.

**Attack Example:**
```python
query = 'test" && calc.exe #'
# Becomes: start "chrome" "https://www.google.com/search?q=test" && calc.exe #"
```

**Fix:**
```python
import subprocess
import urllib.parse

def search_google(query: str) -> str:
    """Searches for a query on Google - SECURE"""
    try:
        if not query or len(query) > 500:
            return "Invalid query"
        
        quoted_query = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={quoted_query}"
        
        # Use subprocess without shell
        if os.name == 'nt':  # Windows
            subprocess.Popen(['cmd', '/c', 'start', '', url], shell=False)
        else:
            subprocess.Popen(['xdg-open', url], shell=False)
        
        return f"Successfully searched Google for: {query}"
    except Exception as e:
        return f"Error: {e}"
```

**Same Issue in:**
- `search_youtube()` line 70-77
- `open_settings_page()` line 53

---

### Issue #2: Volume Control - Limited Error Handling
**Lines:** 121-137  
**Severity:** MODERATE

```python
def set_system_volume(level: int) -> str:
    try:
        if not (0 <= level <= 100):
            return "Error: Volume must be between 0 and 100."
            
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        scalar_level = level / 100.0
        volume.SetMasterVolumeLevelScalar(scalar_level, None)
        return f"Successfully set volume to {level}%."
    except Exception as e:
        return f"Error setting volume: {e}"  # ❌ Generic error
```

**Problems:**
1. No check if audio devices exist
2. Works only on Windows
3. Requires `pycaw` library (not always installed)
4. Error message too generic

**Fix:**
```python
def set_system_volume(level: int) -> str:
    """Sets system volume with comprehensive error handling"""
    try:
        # Validate input
        if not isinstance(level, int):
            return "Error: Volume level must be an integer"
        if not (0 <= level <= 100):
            return "Error: Volume must be between 0 and 100"
        
        # Check platform
        if os.name != 'nt':
            return "Error: Volume control only supported on Windows"
        
        # Import dependencies
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        except ImportError:
            return "Error: pycaw library not installed. Run: pip install pycaw"
        
        # Get audio device
        devices = AudioUtilities.GetSpeakers()
        if not devices:
            return "Error: No audio output devices found"
        
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        # Set volume
        scalar_level = level / 100.0
        volume.SetMasterVolumeLevelScalar(scalar_level, None)
        
        return f"✅ Volume set to {level}%"
    except Exception as e:
        logging.error(f"Volume control error: {e}")
        return f"Error: Could not set volume - {type(e).__name__}"
```

---

### Issue #3: Notepad Automation - Fragile Window Handling
**Lines:** 25-44  
**Severity:** MODERATE

```python
def write_a_note(message: str) -> str:
    try:
        app = Application(backend="uia").start("notepad.exe")
        main_window = app.window(title="Untitled - Notepad")  # ❌ Hardcoded title
        main_window.wait("ready", timeout=5)
        main_window.child_window(title="Text Editor", control_type="Edit").type_keys(message, with_spaces=True)
        time.sleep(1) 
        main_window.close()
        # ❌ Assumes "Don't Save" button exists with exact title
        app.window(title="Notepad", control_type="Window").wait("ready", timeout=2)
        app.window(title="Notepad").child_window(title="Don't Save", control_type="Button").click()
```

**Problems:**
1. Window titles are language-dependent (breaks in non-English Windows)
2. No retry logic if window not found
3. Hard timeout values
4. May fail on fast/slow systems

**Fix:**
```python
def write_a_note(message: str) -> str:
    """Writes note to Notepad - IMPROVED VERSION"""
    try:
        # Start Notepad
        app = Application(backend="uia").start("notepad.exe")
        
        # Wait for window (more flexible matching)
        main_window = None
        for attempt in range(3):
            try:
                main_window = app.window(title_re=".*Notepad.*")
                main_window.wait("ready", timeout=3)
                break
            except Exception:
                time.sleep(1)
        
        if not main_window:
            return "Error: Could not find Notepad window"
        
        # Type message
        edit_control = main_window.child_window(control_type="Edit")
        edit_control.set_text(message)
        
        # Close without saving
        time.sleep(0.5)
        main_window.close()
        
        # Handle save dialog (try multiple button names)
        try:
            save_dialog = app.window(title_re=".*Notepad.*", control_type="Window")
            save_dialog.wait("ready", timeout=2)
            
            # Try different button names (language-independent approach)
            button_found = False
            for button_name in ["Don't Save", "N", "&N", "No guardar", "Não salvar"]:
                try:
                    button = save_dialog.child_window(title=button_name, control_type="Button")
                    button.click()
                    button_found = True
                    break
                except:
                    continue
            
            if not button_found:
                # Fallback: press 'N' key
                save_dialog.type_keys('n')
        except:
            pass  # Window might have closed already
        
        return f"✅ Successfully wrote '{message[:50]}...' to Notepad"
    except Exception as e:
        logging.error(f"Notepad automation error: {e}")
        return f"Error controlling Notepad: {type(e).__name__}"
```

---

### Issue #4: Application Opening - No Validation
**Lines:** 47-51  
**Severity:** LOW

```python
def open_application(app_name: str) -> str:
    """Opens any application on the computer using intelligent discovery."""
    print(f"--- 'Hands' (open_application) activated. App: {app_name} ---")
    
    # Use the smart application discovery system
    return smart_open_application(app_name)
```

**Problems:**
1. No input validation
2. Delegates entirely to `smart_open_application` (good design, but no fallback)
3. No check if app_name is empty
4. Debug print statements in production code

**Fix:**
```python
def open_application(app_name: str) -> str:
    """Opens application with validation"""
    # Validate input
    if not app_name or not isinstance(app_name, str):
        return "Error: Invalid application name"
    
    app_name = app_name.strip()
    if len(app_name) < 2:
        return "Error: Application name too short"
    if len(app_name) > 100:
        return "Error: Application name too long"
    
    logging.info(f"Opening application: {app_name}")
    
    try:
        return smart_open_application(app_name)
    except Exception as e:
        logging.error(f"Application opening failed: {e}")
        return f"Error: Could not open {app_name}"
```

---

### Issue #5: PDF Generation - Optional Dependency Not Handled
**Lines:** 185-203  
**Severity:** LOW

```python
# Import at top of file
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    REPORTLAB_INSTALLED = True
except ImportError:
    REPORTLAB_INSTALLED = False

def write_to_file(filename: str, content: str) -> str:
    # ...
    if filename.lower().endswith('.pdf'):
        if not REPORTLAB_INSTALLED:
            return "Error: To save PDFs, I need the 'reportlab' library..."
```

**Problem:** Good pattern, but user needs to know this before trying.

**Improvement:**
```python
def get_supported_formats() -> dict:
    """Return dict of supported file formats and their availability"""
    return {
        'txt': {'supported': True, 'description': 'Plain text'},
        'md': {'supported': True, 'description': 'Markdown'},
        'pdf': {
            'supported': REPORTLAB_INSTALLED,
            'description': 'PDF document',
            'install': 'pip install reportlab' if not REPORTLAB_INSTALLED else None
        }
    }

def write_to_file(filename: str, content: str) -> str:
    """Creates a file with validation"""
    if not filename or not content:
        return "Error: Filename and content required"
    
    # Get file extension
    ext = filename.split('.')[-1].lower() if '.' in filename else 'txt'
    
    # Check support
    formats = get_supported_formats()
    if ext not in formats:
        return f"Error: Unsupported format '.{ext}'. Supported: {', '.join(formats.keys())}"
    
    if not formats[ext]['supported']:
        return f"Error: {formats[ext]['install']}"
    
    # ... rest of implementation
```

---

## ⚠️ Vulnerabilities Summary

| Vulnerability | Severity | Fix Priority |
|--------------|----------|--------------|
| Command Injection (search functions) | 🔴 Critical | P0 |
| Command Injection (settings) | 🔴 Critical | P0 |
| Input Validation | 🟡 Medium | P2 |

---

## 📊 Code Quality Assessment

### Strengths ✅
- Clear function names and docstrings
- Good separation of concerns
- Handles Windows-specific functionality well
- Uses type hints

### Weaknesses ❌
- Debug print statements in production code
- Inconsistent error handling patterns
- Some hardcoded values (window titles, timeouts)
- No logging framework used
- No input validation on most functions

### Technical Debt 📝
- Should use logging instead of print
- Need consistent error return format
- Add retry logic to automation functions
- Make language-agnostic (i18n)

---

## 🧪 Testing Status

**Current Coverage:** 0%  
**Tests Exist:** NO  
**Required Tests:** 15+

### Critical Tests Needed
1. `test_write_a_note()` - Mock pywinauto
2. `test_open_application()` - Mock subprocess
3. `test_search_google_injection()` - Security test
4. `test_search_youtube_injection()` - Security test
5. `test_volume_control_bounds()` - Edge cases
6. `test_write_to_file_pdf()` - With/without reportlab

---

## 🔧 Required Fixes - Priority Order

### P0 - Critical (Fix This Week)
1. ✅ Fix command injection in `search_google()`
2. ✅ Fix command injection in `search_youtube()`
3. ✅ Fix command injection in `open_settings_page()`
4. ✅ Add input validation to all functions

**Time Estimate:** 3-4 hours

### P1 - High (Fix Next Week)
5. Improve Notepad automation (language-agnostic)
6. Add comprehensive error handling
7. Replace print with logging
8. Add retry logic to automation functions

**Time Estimate:** 6-8 hours

### P2 - Medium (Fix This Month)
9. Create test suite
10. Add support for non-Windows platforms
11. Improve PDF generation
12. Add file format validation

**Time Estimate:** 12-16 hours

---

## ✨ Enhancement Opportunities

### 1. Configuration System
```python
# core_config.py
@dataclass
class CoreConfig:
    default_browser: str = "chrome"
    automation_timeout: int = 5
    retry_attempts: int = 3
    enable_logging: bool = True
```

### 2. Platform Abstraction
```python
class PlatformAutomation:
    @staticmethod
    def open_url(url: str):
        if os.name == 'nt':
            subprocess.Popen(['start', '', url], shell=True)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', url])
        else:
            subprocess.Popen(['xdg-open', url])
```

### 3. Async Operations
```python
import asyncio

async def write_a_note_async(message: str):
    """Non-blocking note writing"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, write_a_note, message)
```

---

## 📝 Recommendations

### Immediate
1. Apply security fixes for command injection
2. Add input validation
3. Set up logging framework

### Short Term
1. Create comprehensive test suite
2. Improve error handling consistency
3. Add retry mechanisms

### Long Term
1. Support multiple platforms
2. Add async/await support
3. Implement plugin system for extensibility

---

## 🔗 Dependencies

### Required
- `pywinauto==0.6.9` - Windows automation
- `pywin32==311` - Windows API
- `pyttsx3==2.90` - Text-to-speech
- `pycaw` - Volume control
- `comtypes==1.4.13` - COM automation

### Optional
- `reportlab` - PDF generation

### Conflicts
- None identified

---

**Analysis Complete**  
**Next Module:** [Memory Module →](MEMORY_MODULE.md)
