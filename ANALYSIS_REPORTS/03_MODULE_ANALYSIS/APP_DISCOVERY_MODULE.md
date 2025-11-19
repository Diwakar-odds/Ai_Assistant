# 🔍 App Discovery Module Analysis

**File:** `modules/app_discovery.py`  
**Lines:** 189  
**Status:** ✅ **WORKING**  
**Test Coverage:** 0%  
**Last Updated:** November 17, 2025

---

## 📋 Functionality

### Purpose
Scans and discovers installed Windows applications

### Features
- ✅ Scans common install directories
- ✅ Finds .exe files
- ✅ Caches discovered apps to JSON
- ⚠️ No Start Menu scanning
- ⚠️ No registry scanning

---

## 🐛 Issues Found

### Issue #1: Performance - No Concurrent Scanning 🟡
**Lines:** 78-95  
**Severity:** MODERATE

```python
def scan_directories(self):
    """Scan directories for apps"""
    for directory in self.search_paths:
        if os.path.exists(directory):
            for root, dirs, files in os.walk(directory):
                # ❌ Sequential scanning - very slow
                for file in files:
                    if file.endswith('.exe'):
                        self.apps.append({
                            'name': file,
                            'path': os.path.join(root, file)
                        })
```

**Fix - Add Parallel Scanning:**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

def scan_directories(self):
    """Scan directories in parallel"""
    apps_lock = threading.Lock()
    
    def scan_directory(directory):
        local_apps = []
        if os.path.exists(directory):
            for root, dirs, files in os.walk(directory):
                # Skip system directories
                dirs[:] = [d for d in dirs if d not in ['System32', 'WinSxS']]
                
                for file in files:
                    if file.endswith('.exe'):
                        local_apps.append({
                            'name': file,
                            'path': os.path.join(root, file)
                        })
        return local_apps
    
    # Scan in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(scan_directory, d): d for d in self.search_paths}
        
        for future in as_completed(futures):
            try:
                apps = future.result()
                with apps_lock:
                    self.apps.extend(apps)
            except Exception as e:
                print(f"Error scanning directory: {e}")
```

### Issue #2: No Start Menu or Registry Scanning 🟡
**Severity:** MODERATE

```python
# Currently only scans file system
# ❌ Misses apps in Start Menu
# ❌ Misses apps in registry
```

**Fix - Add Start Menu Scanning:**
```python
import winreg

def scan_start_menu(self):
    """Scan Start Menu for applications"""
    start_menu_paths = [
        os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
        os.path.join(os.environ['ProgramData'], 'Microsoft', 'Windows', 'Start Menu', 'Programs')
    ]
    
    for base_path in start_menu_paths:
        if os.path.exists(base_path):
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.endswith('.lnk'):
                        # Parse shortcut
                        shortcut_path = os.path.join(root, file)
                        target_path = self._get_shortcut_target(shortcut_path)
                        
                        if target_path and target_path.endswith('.exe'):
                            self.apps.append({
                                'name': file.replace('.lnk', ''),
                                'path': target_path,
                                'source': 'start_menu'
                            })

def scan_registry(self):
    """Scan Windows Registry for installed apps"""
    registry_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    ]
    
    for path in registry_paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
            
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)
                    
                    try:
                        name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                        exe_path = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                        
                        if exe_path and '.exe' in exe_path:
                            self.apps.append({
                                'name': name,
                                'path': exe_path.split(',')[0],  # Remove icon index
                                'source': 'registry'
                            })
                    except:
                        pass
                    
                    winreg.CloseKey(subkey)
                except:
                    continue
            
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Registry scan error: {e}")
```

### Issue #3: No Duplicate Filtering 🟡
**Severity:** LOW

```python
# Currently can add same app multiple times
```

**Fix:**
```python
def deduplicate_apps(self):
    """Remove duplicate apps"""
    seen = set()
    unique_apps = []
    
    for app in self.apps:
        # Normalize path
        path = os.path.normpath(app['path']).lower()
        
        if path not in seen:
            seen.add(path)
            unique_apps.append(app)
    
    self.apps = unique_apps
    print(f"Found {len(self.apps)} unique applications")
```

---

## 🔧 Fix Priority

### P1 - High (Week 1) - 4 hours
- [ ] Add parallel scanning (2 hours)
- [ ] Add Start Menu scanning (1 hour)
- [ ] Add duplicate filtering (30 min)
- [ ] Add progress reporting (30 min)

### P2 - Medium (Week 2) - 3 hours
- [ ] Add registry scanning (2 hours)
- [ ] Write tests (1 hour)

**Total:** 7 hours

---

**Priority:** 🟡 P1  
**Impact:** Performance & completeness

**Next:** [System Module →](SYSTEM_MODULE.md)
