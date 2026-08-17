# Dynamic Application Discovery Module
"""
This module scans the system to discover all installed applications
and provides intelligent app launching based on voice commands.
"""

import os
import winreg
import json
import webbrowser
import time
import subprocess
import glob
import json
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
from pathlib import Path
import time
import sqlite3
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

class AppDiscovery:
    def __init__(self):
        # Get the project root directory (2 levels up from this file)
        project_root = Path(__file__).parent.parent.parent
        config_dir = project_root / "config"
        
        # Ensure config directory exists
        config_dir.mkdir(exist_ok=True)
        
        # Set paths relative to config directory
        self.apps_cache_file = str(config_dir / "discovered_apps.json")
        self.usage_db_file = str(config_dir / "app_usage.db")
        self.apps_database = {}
        self._is_refreshing = False
        self._last_refresh_time = None
        
        # Load cache first for fast startup
        self.load_cache()
        self._init_usage_database()
        
        # DON'T start background refresh at startup - defer until first use
        # This saves 10-20 seconds at server startup
        # self._start_background_refresh()  # Disabled for performance
    
    def scan_installed_applications(self) -> Dict[str, str]:
        """
        Scan apps from EXACT same sources as Windows Settings > Apps & Features.
        This is the definitive list of installed applications on Windows.
        
        Discovery Sources (same as Settings):
        1. Registry Uninstall keys (Desktop apps)
        2. AppX/MSIX packages (Store/Modern apps)
        
        WHY THIS IS THE BEST APPROACH:
        - Shows exact same apps as Settings > Apps & Features
        - No missing apps or extra hidden apps
        - Official Windows application registry
        - What users expect to see
        """
        print("âš™ï¸ Scanning from Windows Settings > Apps & Features sources...")
        apps = {}
        
        # Method 1: Registry Uninstall Keys (Desktop Apps)
        print("  📋 Reading Registry Uninstall Keys (Desktop Apps)...")
        apps.update(self._scan_apps_and_features_registry())
        
        # Method 2: AppX Packages (Microsoft Store Apps)
        print("  ðŸª Reading AppX Packages (Store Apps)...")
        apps.update(self._scan_appx_packages())
        
        # Method 3: Start Menu Shortcuts (PWAs and Utilities)
        apps.update(self._scan_start_menu_shortcuts())
        
        # Save to cache
        self.apps_database = apps
        self.save_cache()
        
        print(f"✅ Discovery complete! Found {len(apps)} apps (same as Settings).")
        return apps
    
    # REMOVED: PowerShell Get-StartApps - not needed, using Windows Settings > Apps & Features sources
    
    def _scan_apps_and_features_registry(self) -> Dict[str, str]:
        r"""
        Scan Registry Uninstall keys - EXACT same source as Settings > Apps & Features.
        This finds all desktop applications installed via installers.
        
        Registry Locations (same as Windows Settings uses):
        - HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall (64-bit apps)
        - HKLM\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall (32-bit apps)
        - HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall (user apps)
        """
        apps = {}
        
        # Registry paths that Settings > Apps & Features reads from
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        
        for root_key, reg_path in registry_paths:
            try:
                with winreg.OpenKey(root_key, reg_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    # Read DisplayName - this is what shows in Settings
                                    display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                    
                                    # Skip if no name or it's an update/component
                                    if not display_name or any(skip in display_name.lower() for skip in 
                                        ['update', 'hotfix', 'security update', 'kb']):
                                        continue
                                    
                                    # Try to get SystemComponent flag - if 1, it's hidden from Settings
                                    try:
                                        system_component = winreg.QueryValueEx(subkey, "SystemComponent")[0]
                                        if system_component == 1:
                                            continue  # Skip system components
                                    except FileNotFoundError:
                                        pass  # No SystemComponent key means it's visible
                                    
                                    # Try to get ParentKeyName - if exists, it's a sub-component
                                    try:
                                        parent = winreg.QueryValueEx(subkey, "ParentKeyName")[0]
                                        if parent:
                                            continue  # Skip sub-components
                                    except FileNotFoundError:
                                        pass
                                    
                                    # Store the app name (we use Windows Search to launch, so path doesn't matter)
                                    app_key = display_name.lower().strip()
                                    if app_key and app_key not in apps:
                                        apps[app_key] = display_name  # Store display name as "path"
                                        
                                except (FileNotFoundError, OSError):
                                    continue
                        except OSError:
                            continue
            except Exception as e:
                continue  # Skip if can't access registry path
        
        return apps
    
    def _scan_appx_packages(self) -> Dict[str, str]:
        """
        Scan AppX/MSIX packages - Microsoft Store apps (same as Settings > Apps & Features).
        Uses PowerShell Get-AppxPackage which is what Windows Settings uses internally.
        """
        apps = {}
        try:
            # PowerShell command to get AppX packages (same as Settings uses)
            cmd = 'powershell -NoProfile -NonInteractive -Command "Get-AppxPackage | Where-Object {$_.Name -notlike \"*DeletedAllUserPackages*\" -and $_.SignatureKind -eq \"Store\"} | Select-Object Name,PackageFamilyName | ConvertTo-Json"'
            
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    
                    # Handle single item vs list
                    if isinstance(data, dict):
                        data = [data]
                    
                    for item in data:
                        if 'Name' in item:
                            # Extract friendly name from package name
                            name = item['Name']
                            
                            # Convert package name to friendly display name
                            # e.g., "Microsoft.WindowsCalculator" -> "Calculator"
                            friendly_name = name.split('.')[-1] if '.' in name else name
                            
                            # Remove common suffixes
                            friendly_name = friendly_name.replace('App', '').replace('UWP', '').strip()
                            
                            if friendly_name and len(friendly_name) > 2:
                                app_key = friendly_name.lower()
                                if app_key not in apps:
                                    apps[app_key] = friendly_name
                                    
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"  âš ï¸ AppX scan failed: {e}")
        
        return apps
    
    def _scan_start_menu_shortcuts(self) -> Dict[str, str]:
        """
        Scan Start Menu for .lnk shortcuts (Desktop apps, PWAs, Utility shortcuts).
        This is critical for finding Brave/Chrome/Edge Apps (YouTube, Spotify, etc.)
        that might not appear in the Registry or have different internal names.
        """
        apps = {}
        
        # Standard Start Menu locations
        paths = [
            os.path.join(os.environ.get('APPDATA', ''), r'Microsoft\Windows\Start Menu\Programs'),
            os.path.join(os.environ.get('PROGRAMDATA', ''), r'Microsoft\Windows\Start Menu\Programs')
        ]
        
        print("  📂 Scanning Start Menu shortcuts...")
        for path in paths:
            if os.path.exists(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith('.lnk'):
                            # Use filename as app name (e.g., "YouTube.lnk" -> "youtube")
                            name = file[:-4]
                            
                            # Clean up name (remove " - Shortcut", etc.)
                            name = name.replace(" - Shortcut", "")
                            
                            full_path = os.path.join(root, file)
                            app_key = name.lower().strip()
                            
                            # Don't overwrite existing registry entries unless it's a specific PWA
                            # This allows "YouTube" from Brave to override generic entries
                            if app_key not in apps:
                                apps[app_key] = full_path
                                
        return apps
    
    def save_cache(self):
        """Save discovered apps to cache file"""
        try:
            with open(self.apps_cache_file, 'w') as f:
                json.dump(self.apps_database, f, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def load_cache(self):
        """Load discovered apps from cache file"""
        try:
            if os.path.exists(self.apps_cache_file):
                with open(self.apps_cache_file, 'r') as f:
                    data = json.load(f)
                    
                # Handle different cache formats
                if isinstance(data, dict):
                    if 'applications' in data:
                        # New complex format - extract app data
                        self.apps_database = {}
                        for app in data['applications']:
                            app_name = app['name'].lower().replace(' ', '_')
                            self.apps_database[app_name] = app['path']
                    else:
                        # Old simple format - use as is
                        self.apps_database = data
                else:
                    self.apps_database = {}
        except Exception as e:
            print(f"Error loading cache: {e}")
            self.apps_database = {}
    
    def _start_background_refresh(self):
        """Start background thread to refresh app list (lazy load)"""
        if self._is_refreshing or (self._last_refresh_time and 
            (datetime.now() - self._last_refresh_time).seconds < 300):  # 5 min cache
            return  # Already refreshing or recently refreshed
        
        import threading
        thread = threading.Thread(target=self._background_refresh, daemon=True)
        thread.start()
    
    def start_delayed_refresh(self, delay_seconds: int = 30):
        """Start background refresh after a delay (for post-startup refresh)"""
        import threading
        import time
        
        def delayed_refresh():
            print(f"â° Scheduled app refresh will start in {delay_seconds} seconds...")
            time.sleep(delay_seconds)
            if not self._is_refreshing:
                print("🔄 Starting scheduled background app refresh...")
                self._background_refresh()
        
        thread = threading.Thread(target=delayed_refresh, daemon=True)
        thread.start()
        print(f"✅ Delayed app refresh scheduled ({delay_seconds}s after startup)")
    
    def _background_refresh(self):
        """Background refresh of app database"""
        try:
            self._is_refreshing = True
            print("🔄 Background app refresh started...")
            
            # Scan for apps
            new_apps = self.scan_installed_applications()
            
            # Update timestamp
            from datetime import datetime
            self._last_refresh_time = datetime.now()
            
            print(f"✅ Background refresh complete! Found {len(new_apps)} apps")
            
            # Notify frontend via WebSocket if available
            try:
                from flask import current_app
                if current_app and hasattr(current_app, 'extensions'):
                    socketio = current_app.extensions.get('socketio')
                    if socketio:
                        socketio.emit('apps_discovered', {
                            'count': len(new_apps),
                            'timestamp': datetime.now().isoformat(),
                            'message': f'Discovered {len(new_apps)} applications'
                        })
                        print("ðŸ“¡ Sent apps_discovered event to frontend")
            except (RuntimeError, ImportError) as e:
                # Not running in Flask context or socketio not available
                print(f"â„¹ï¸ WebSocket notification skipped: {e}")
                
        except Exception as e:
            print(f"âš ï¸ Background refresh failed: {e}")
        finally:
            self._is_refreshing = False
    
    def _init_usage_database(self):
        """Initialize SQLite database for tracking app usage."""
        try:
            with sqlite3.connect(self.usage_db_file) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS app_launches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        app_name TEXT NOT NULL,
                        app_path TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN DEFAULT 1
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_app_launches_name 
                    ON app_launches(app_name)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_app_launches_timestamp 
                    ON app_launches(timestamp DESC)
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS app_frequency (
                        app_name TEXT PRIMARY KEY,
                        launch_count INTEGER DEFAULT 0,
                        last_launched DATETIME,
                        avg_daily_launches REAL DEFAULT 0.0
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        action_type TEXT NOT NULL,
                        chosen_app TEXT NOT NULL,
                        chosen_method TEXT NOT NULL,
                        use_count INTEGER DEFAULT 1,
                        last_used DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY(action_type, chosen_app)
                    )
                """)
                
                conn.commit()
        except Exception as e:
            print(f"Error initializing usage database: {e}")
    
    def track_app_launch(self, app_name: str, app_path: str = "", success: bool = True):
        """Track an application launch for usage statistics."""
        try:
            with sqlite3.connect(self.usage_db_file) as conn:
                # Record launch
                conn.execute("""
                    INSERT INTO app_launches (app_name, app_path, success)
                    VALUES (?, ?, ?)
                """, (app_name, app_path, success))
                
                # Update frequency table
                conn.execute("""
                    INSERT INTO app_frequency (app_name, launch_count, last_launched)
                    VALUES (?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(app_name) DO UPDATE SET
                        launch_count = launch_count + 1,
                        last_launched = CURRENT_TIMESTAMP
                """, (app_name,))
                
                conn.commit()
        except Exception as e:
            print(f"Error tracking app launch: {e}")
    
    def get_most_used_apps(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most frequently used applications."""
        try:
            with sqlite3.connect(self.usage_db_file) as conn:
                cursor = conn.execute("""
                    SELECT app_name, launch_count
                    FROM app_frequency
                    ORDER BY launch_count DESC
                    LIMIT ?
                """, (limit,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Error getting most used apps: {e}")
            return []
    
    def get_recent_apps(self, limit: int = 10) -> List[Tuple[str, str]]:
        """Get recently launched applications."""
        try:
            with sqlite3.connect(self.usage_db_file) as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT app_name, MAX(timestamp) as last_time
                    FROM app_launches
                    WHERE success = 1
                    GROUP BY app_name
                    ORDER BY last_time DESC
                    LIMIT ?
                """, (limit,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Error getting recent apps: {e}")
            return []
    
    def get_preferred_app_for_action(self, action_type: str) -> Optional[Tuple[str, str]]:
        """Get user's most preferred app and method for an action."""
        try:
            with sqlite3.connect(self.usage_db_file) as conn:
                cursor = conn.execute("""
                    SELECT chosen_app, chosen_method
                    FROM user_preferences
                    WHERE action_type = ?
                    ORDER BY use_count DESC, last_used DESC
                    LIMIT 1
                """, (action_type,))
                row = cursor.fetchone()
                if row:
                    return (row[0], row[1])
                return None
        except Exception as e:
            print(f"Error getting preference: {e}")
            return None

    def record_action_preference(self, action_type: str, chosen_app: str, method: str):
        """Record which app/method user chose for an action."""
        try:
            with sqlite3.connect(self.usage_db_file) as conn:
                conn.execute("""
                    INSERT INTO user_preferences (action_type, chosen_app, chosen_method, use_count, last_used)
                    VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(action_type, chosen_app) DO UPDATE SET
                        chosen_method = excluded.chosen_method,
                        use_count = use_count + 1,
                        last_used = CURRENT_TIMESTAMP
                """, (action_type, chosen_app, method))
                conn.commit()
        except Exception as e:
            print(f"Error recording preference: {e}")

    def try_windows_search(self, app_name: str) -> bool:
        """Use Windows search bar (Win+S) as last resort."""
        if not PYAUTOGUI_AVAILABLE:
            return False
        try:
            print(f"  🔍 Trying Windows Search Bar for: {app_name}")
            pyautogui.hotkey('win', 's')
            time.sleep(0.5)
            pyautogui.typewrite(app_name, interval=0.05)
            time.sleep(1)
            pyautogui.press('enter')
            return True
        except Exception as e:
            print(f"Error with Windows Search: {e}")
            return False
    
    def _split_camel_case(self, text: str) -> str:
        """Split camelCase and PascalCase words with spaces."""
        import re
        # Insert space before capital letters (except at start)
        result = re.sub(r'(?<!^)(?=[A-Z])', ' ', text)
        result = result.lower()
        
        # Also try to split known compound words in lowercase
        # This handles cases like "microsoftstickynotes" -> "microsoft sticky notes"
        compound_patterns = [
            (r'microsoft', 'microsoft '),
            (r'sticky', ' sticky '),
            (r'notes', ' notes '),
            (r'google', 'google '),
            (r'chrome', ' chrome '),
            (r'spotify', ' spotify '),
            (r'adobe', 'adobe '),
            (r'reader', ' reader '),
            (r'player', ' player '),
            (r'media', ' media '),
            (r'video', ' video '),
            (r'music', ' music '),
        ]
        
        for pattern, replacement in compound_patterns:
            result = re.sub(pattern, replacement, result)
        
        # Clean up extra spaces
        result = ' '.join(result.split())
        return result
    
    def find_app(self, app_name: str) -> str:
        """Find application by name using advanced fuzzy matching with usage-based ranking."""
        app_name_lower = app_name.lower().strip()
        
        # Normalize the search query (remove special chars, handle spaces)
        normalized_query = app_name_lower.replace('.', ' ').replace('_', ' ').replace('-', ' ')
        
        # Get usage statistics for ranking boost
        # Optimization: Don't fetch if no matches found yet
        
        # 0. DIRECT LOOKUP CHECK (Fastest)
        if normalized_query in self.apps_database:
             return self.apps_database[normalized_query]
        
        # 1. Direct Lookup (Legacy/Mapped names)
        # Check standard app names that might not be normalized
        if app_name_lower in self.apps_database:
            return self.apps_database[app_name_lower]
        if app_name in self.apps_database:
            return self.apps_database[app_name]

        # Get usage statistics for ranking boost
        most_used = {name.lower(): count for name, count in self.get_most_used_apps(100)}
        
        matches = []
        
        for db_name, db_path in self.apps_database.items():
            # Normalize database name for comparison
            # First split camelCase, then replace special chars
            normalized_db_name = self._split_camel_case(db_name)
            normalized_db_name = normalized_db_name.replace('.', ' ').replace('_', ' ').replace('-', ' ')
            
            score = self._calculate_match_score(normalized_query, normalized_db_name, most_used.get(db_name, 0))
            if score > 0:
                matches.append((score, db_name, db_path))
        
        if not matches:
            return ""
        
        # Sort by score (highest first)
        matches.sort(reverse=True, key=lambda x: x[0])
        
        # Only return if the score is good enough (minimum threshold of 30)
        best_match = matches[0]
        if best_match[0] >= 30:  # score threshold
            return best_match[2]
        else:
            return ""  # No good match found
    
    def _calculate_match_score(self, query: str, app_name: str, usage_count: int = 0) -> int:
        """Calculate match score for fuzzy search with usage-based ranking."""
        score = 0
        
        # Exact match (highest priority)
        if query == app_name:
            score += 100
        
        # Direct substring match
        if query in app_name:
            score += 50
            # Boost if match is at the start
            if app_name.startswith(query):
                score += 20
        
        # Reverse substring match
        if app_name in query:
            score += 40
        
        # Word-based matching - check if ALL query words are present
        query_words = set(query.split())
        app_words = set(app_name.split())
        
        # Check if all query words exist in app name (important for multi-word searches)
        if query_words and query_words.issubset(app_words):
            score += 80  # High score for containing all words
        
        # Some query words present (partial match)
        common_words = query_words & app_words
        if common_words and not query_words.issubset(app_words):
            score += len(common_words) * 10
        
        # Character-level fuzzy matching (Levenshtein-like)
        if score == 0:  # Only if no other matches
            similarity = self._string_similarity(query, app_name)
            if similarity > 0.7:
                score += int(similarity * 20)
        
        # Boost by usage frequency (logarithmic scale)
        if usage_count > 0:
            import math
            score += int(math.log(usage_count + 1) * 5)
        
        return score
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity (0.0 to 1.0) using simple approach."""
        if not s1 or not s2:
            return 0.0
        
        # Convert to sets of character bigrams
        def get_bigrams(s):
            return set(s[i:i+2] for i in range(len(s) - 1))
        
        bigrams1 = get_bigrams(s1)
        bigrams2 = get_bigrams(s2)
        
        if not bigrams1 or not bigrams2:
            return 0.0
        
        intersection = len(bigrams1 & bigrams2)
        union = len(bigrams1 | bigrams2)
        
        return intersection / union if union > 0 else 0.0
    
    def search_apps(self, query: str, limit: int = 10) -> List[Tuple[str, str, int]]:
        """Search for apps with scoring and ranking."""
        query_lower = query.lower().strip()
        most_used = {name.lower(): count for name, count in self.get_most_used_apps(100)}
        
        matches = []
        for db_name, db_path in self.apps_database.items():
            score = self._calculate_match_score(query_lower, db_name, most_used.get(db_name, 0))
            if score > 0:
                matches.append((db_name, db_path, score))
        
        # Sort by score and return top matches
        matches.sort(reverse=True, key=lambda x: x[2])
        return matches[:limit]
    
    def get_all_apps(self) -> Dict[str, str]:
        """Get all discovered applications"""
        return self.apps_database
    
    def get_apps_for_api(self) -> List[Dict[str, str]]:
        """Get applications formatted for API responses"""
        apps_list = []
        
        # Performance Optimization: Query usage stats ONCE before the loop
        most_used = dict(self.get_most_used_apps(200)) # Increased limit to catch more
        
        for app_name, app_path in self.apps_database.items():
            usage_count = most_used.get(app_name, 0)
            
            # Categorize app
            category = self._categorize_app(app_name)
            
            apps_list.append({
                "name": app_name.replace('_', ' ').title(),
                "path": app_path,
                "category": category,
                "usage": usage_count,
                "description": self._generate_description(app_name)
            })
        
        # Sort by usage count
        apps_list.sort(key=lambda x: x['usage'], reverse=True)
        return apps_list
    
    def _categorize_app(self, app_name: str) -> str:
        """Categorize application by name"""
        app_lower = app_name.lower()
        
        # Browsers
        if any(word in app_lower for word in ['chrome', 'firefox', 'edge', 'browser', 'brave', 'opera', 'safari']):
            return "Browser"
        
        # Productivity
        elif any(word in app_lower for word in ['notepad', 'word', 'excel', 'powerpoint', 'office', 'sticky', 'onenote', 'notion', 'evernote', 'pdf', 'reader']):
            return "Productivity"
        
        # Development
        elif any(word in app_lower for word in ['code', 'visual', 'studio', 'terminal', 'cmd', 'powershell', 'git', 'python', 'node', 'docker', 'postman', 'insomnia', 'database', 'sql', 'mongodb']):
            return "Development"
        
        # Media
        elif any(word in app_lower for word in ['vlc', 'media', 'music', 'video', 'spotify', 'youtube', 'netflix', 'player', 'winamp', 'audacity']):
            return "Media"
        
        # Communication
        elif any(word in app_lower for word in ['mail', 'discord', 'slack', 'teams', 'zoom', 'skype', 'telegram', 'whatsapp', 'messenger']):
            return "Communication"
        
        # Graphics & Design
        elif any(word in app_lower for word in ['paint', 'photoshop', 'gimp', 'inkscape', 'illustrator', 'blender', 'figma', 'canva', '3d']):
            return "Graphics"
        
        # Games
        elif any(word in app_lower for word in ['game', 'steam', 'epic', 'xbox', 'play', 'minecraft', 'roblox']):
            return "Games"
        
        # Utilities
        elif any(word in app_lower for word in ['calculator', 'notepad', 'control', 'task', 'manager', 'settings', 'cleaner', 'winrar', '7zip', 'zip']):
            return "System Tools"
        
        # Security
        elif any(word in app_lower for word in ['antivirus', 'defender', 'malware', 'security', 'vpn']):
            return "Security"
        
        # Default
        else:
            return "Other"
    
    def _generate_description(self, app_name: str) -> str:
        """Generate description for application"""
        descriptions = {
            'chrome': 'Google Chrome web browser',
            'firefox': 'Mozilla Firefox web browser',
            'edge': 'Microsoft Edge web browser',
            'notepad': 'Simple text editor',
            'calculator': 'Windows calculator utility',
            'paint': 'Microsoft Paint image editor',
            'word': 'Microsoft Word document editor',
            'excel': 'Microsoft Excel spreadsheet application',
            'powerpoint': 'Microsoft PowerPoint presentation software',
            'code': 'Visual Studio Code editor',
            'terminal': 'Command line interface',
            'cmd': 'Command prompt',
            'powershell': 'PowerShell command interface',
            'vlc': 'VLC multimedia player',
            'spotify': 'Music streaming application',
            'discord': 'Voice and text communication platform',
            'control': 'Windows Control Panel',
            'task_manager': 'Windows Task Manager',
            'file_explorer': 'Windows File Explorer'
        }
        
        app_lower = app_name.lower().replace(' ', '_')
        return descriptions.get(app_lower, f"{app_name.replace('_', ' ').title()} application")

    def refresh_database(self) -> int:
        """Refresh the applications database"""
        old_count = len(self.apps_database)
        self.scan_installed_applications()
        new_count = len(self.apps_database)
        return new_count - old_count# Global instance
app_discovery = AppDiscovery()

def discover_applications() -> str:
    """Main function to discover all applications"""
    try:
        # Trigger background refresh if not already started
        if not app_discovery._is_refreshing and app_discovery._last_refresh_time is None:
            app_discovery._start_background_refresh()
        
        apps = app_discovery.scan_installed_applications()
        return f"Successfully discovered {len(apps)} applications on your system."
    except Exception as e:
        return f"Error during application discovery: {e}"

def smart_open_application(app_name: str, action_type: str = 'open_app') -> str:
    """Intelligently open any application by name with usage tracking.
    Supports precise methods: Native Windows Apps, Web Apps, Windows Search.
    """
    print(f"🚀 Smart app launcher: Looking for '{app_name}'...")
    
    # Trigger background refresh on first app access (lazy load)
    if not app_discovery._is_refreshing and app_discovery._last_refresh_time is None:
        app_discovery._start_background_refresh()
    
    # Validate app_name to prevent injection
    if len(app_name) > 200:
        return "❌ Application name is too long"
    
    # Normalize app name using Intent Recognizer
    original_app_name = app_name
    try:
        from ai_assistant.ai.intent_recognizer import IntentRecognizer
        recognizer = IntentRecognizer()
        app_name = recognizer.normalize_app_name(app_name)
        if app_name != original_app_name:
            print(f"[Intent Recognizer] Normalized '{original_app_name}' -> '{app_name}'")
    except Exception as e:
        print(f"[Intent Recognizer] Not available in smart_open_application: {e}")
    
    # Check preferences (learned behavior)
    pref = app_discovery.get_preferred_app_for_action(action_type)
    if pref and original_app_name.lower().strip() in ["play music", "music", "play"]:
        # If generic action and we have a preference, try it
        app_name = pref[0]
        print(f"  💡 Using learned preference for {action_type}: {app_name}")

    # First, try to find in discovered apps
    app_path = app_discovery.find_app(app_name)
    
    if app_path:
        try:
            # METHOD 1: NATIVE WINDOWS APP OR SHORTCUT (.exe / .lnk)
            # This is reliable for Desktop apps and PWAs found in Start Menu
            if os.path.exists(app_path):
                print(f"  🚀 Launching Native Windows App directly: {app_path}")
                # Use subprocess shell start to robustly handle .lnk files and PWAs (like Brave)
                import subprocess
                subprocess.Popen(f'start "" "{app_path}"', shell=True)
                app_discovery.track_app_launch(app_name, app_path, success=True)
                app_discovery.record_action_preference(action_type, app_name, 'native')
                return f"✅ Opened Native App: {app_name}"
            # Fallback for Windows App protocols/commands (like Calculator UWP)
            else:
                import subprocess
                subprocess.Popen(app_path, shell=True)
                app_discovery.track_app_launch(app_name, app_path, success=True)
                app_discovery.record_action_preference(action_type, app_name, 'native')
                return f"✅ Opened Web/Windows App using Shell: {app_name}"
        except Exception as e:
            print(f"  ❌ Launch failed: {e}")
            app_discovery.track_app_launch(app_name, app_path, success=False)
            return f"❌ Failed to launch {app_name}: {e}"
    else:
        # If not found natively, try web fallbacks
        web_fallbacks = {
            'youtube': 'https://www.youtube.com',
            'youtube music': 'https://music.youtube.com',
            'spotify': 'https://open.spotify.com',
            'discord': 'https://discord.com/app',
            'slack': 'https://app.slack.com',
            'zoom': 'https://zoom.us/join',
            'teams': 'https://teams.microsoft.com',
            'netflix': 'https://www.netflix.com',
            'prime video': 'https://www.primevideo.com',
            'facebook': 'https://www.facebook.com',
            'instagram': 'https://www.instagram.com',
            'twitter': 'https://twitter.com',
            'x': 'https://twitter.com',
            'whatsapp': 'https://web.whatsapp.com',
            'telegram': 'https://web.telegram.org',
            'github': 'https://github.com',
            'chatgpt': 'https://chat.openai.com',
            'claude': 'https://claude.ai',
            'bard': 'https://bard.google.com',
            'gemini': 'https://gemini.google.com'
        }
        
        app_lower = app_name.lower().strip()
        
        # METHOD 1: WEB APP (Fallback)
        for key, url in web_fallbacks.items():
            if key in app_lower:
                try:
                    import webbrowser
                    print(f"  🌐 Launching Web App fallback: {url}")
                    webbrowser.open(url)
                    app_discovery.track_app_launch(app_name, url, success=True)
                    app_discovery.record_action_preference(action_type, app_name, 'web')
                    return f"✅ Opened Web App: {app_name}"
                except Exception as e:
                    app_discovery.track_app_launch(app_name, url, success=False)
                    return f"❌ Failed to open Web App {app_name}: {e}"
        
        # METHOD 3: Windows Search Bar (Last Resort)
        if app_discovery.try_windows_search(app_name):
            app_discovery.track_app_launch(app_name, "windows_search", success=True)
            app_discovery.record_action_preference(action_type, app_name, 'windows_search')
            return f"✅ Attempted to open '{app_name}' using Windows Search"

        app_discovery.track_app_launch(app_name, "", success=False)
        return f"❌ App '{app_name}' not found locally and no Web App equivalent exists."


def refresh_app_database() -> str:
    """Refresh the application database"""
    try:
        new_apps = app_discovery.refresh_database()
        total_apps = len(app_discovery.get_all_apps())
        return f"Database refreshed! Found {new_apps} new apps. Total: {total_apps} applications."
    except Exception as e:
        return f"Error refreshing database: {e}"

def list_installed_apps() -> str:
    """List all discovered applications"""
    apps = app_discovery.get_all_apps()
    if not apps:
        return "No applications discovered yet. Run application discovery first."
    
    app_list = "\n".join([f"â€¢ {name.title()}" for name in sorted(apps.keys())][:50])  # Limit to 50
    total = len(apps)
    
    return f"Found {total} applications (showing first 50):\n{app_list}"

def get_apps_for_web() -> List[Dict[str, str]]:
    """Get applications formatted for web API responses"""
    # Return cached data immediately (non-blocking)
    # Auto-refresh happens in background after server startup
    apps = app_discovery.get_apps_for_api()
    
    if len(apps) == 0:
        print("â„¹ï¸ No apps in cache - user can click refresh or wait for auto-refresh")
    else:
        print(f"ðŸ“¦ Returning {len(apps)} cached apps to API")
    
    return apps

def get_app_usage_stats() -> str:
    """Get application usage statistics."""
    most_used = app_discovery.get_most_used_apps(10)
    recent = app_discovery.get_recent_apps(10)
    
    report = "ðŸ“Š APPLICATION USAGE STATISTICS\n"
    report += "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n\n"
    
    report += "ðŸ”¥ MOST USED APPS:\n"
    for i, (app_name, count) in enumerate(most_used, 1):
        report += f"{i}. {app_name.title()}: {count} launches\n"
    
    report += "\nâ° RECENTLY USED:\n"
    for i, (app_name, last_time) in enumerate(recent, 1):
        report += f"{i}. {app_name.title()} (Last: {last_time})\n"
    
    return report

# EXPORT ALIASES for backend compatibility
get_installed_apps = get_apps_for_web
refresh_app_list = refresh_app_database

def start_periodic_refresh(interval_hours: int = 168):  # 168 hours = 1 week
    """Start periodic background refresh (runs in separate thread)"""
    import threading
    import time
    
    def periodic_refresh_loop():
        while True:
            try:
                time.sleep(interval_hours * 3600)  # Convert hours to seconds
                if not app_discovery._is_refreshing:
                    print(f"ðŸ“… Weekly scheduled refresh starting...")
                    app_discovery._background_refresh()
            except Exception as e:
                print(f"âš ï¸ Periodic refresh error: {e}")
    
    thread = threading.Thread(target=periodic_refresh_loop, daemon=True)
    thread.start()
    print(f"✅ Periodic app refresh enabled (every {interval_hours} hours)")

def start_auto_refresh_after_startup(delay_seconds: int = 30):
    """Convenience function to start delayed refresh after server startup"""
    app_discovery.start_delayed_refresh(delay_seconds)

def search_apps_by_name(query: str) -> str:
    """Search for applications by name."""
    results = app_discovery.search_apps(query, limit=10)
    
    if not results:
        return f"No applications found matching '{query}'"
    
    report = f"ðŸ” SEARCH RESULTS for '{query}':\n"
    for i, (name, path, score) in enumerate(results, 1):
        report += f"{i}. {name.title()} (Score: {score})\n   Path: {path}\n"
    
    return report

# =============================================================================
# Section 2: Taskbar Detection (from taskbar_detection.py)
# =============================================================================
# Taskbar and Running Applications Detection Module
"""
This module provides capabilities to detect and analyze the Windows taskbar,
including running applications, taskbar icons, and system tray information.
"""

import os
try:
    import psutil
except ImportError:
    psutil = None
import time
from typing import Dict, List, Tuple, Optional, Any
try:
    from PIL import Image, ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL not available. Visual taskbar detection disabled.")
import json
from datetime import datetime

try:
    import win32gui
    import win32con
    import win32process
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("Warning: win32gui not available. Some taskbar detection features will be limited.")

# Import multimodal capabilities for visual analysis
try:
    from ai_assistant.vision.multimodal import MultiModalAI
    MULTIMODAL_AVAILABLE = True
except ImportError:
    MULTIMODAL_AVAILABLE = False
    print("Warning: Multimodal AI not available for visual taskbar analysis.")

class TaskbarDetector:
    """Detects and analyzes Windows taskbar and running applications."""
    
    def __init__(self):
        self.multimodal = None
        if MULTIMODAL_AVAILABLE:
            try:
                self.multimodal = MultiModalAI()
            except Exception as e:
                print(f"Warning: Could not initialize MultiModalAI: {e}")
    
    def get_running_applications(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get detailed information about all running applications.
        
        Returns:
            Dictionary with application information including PIDs, names, and window titles
        """
        print("ðŸ” Detecting running applications...")
        
        applications = {
            "processes": [],
            "windows": [],
            "summary": {}
        }
        
        # Get process information
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent', 'create_time']):
            try:
                proc_info = proc.info
                proc_info['memory_mb'] = proc_info['memory_info'].rss / 1024 / 1024
                proc_info['running_time'] = time.time() - proc_info['create_time']
                del proc_info['memory_info']  # Remove the original object
                applications["processes"].append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Get window information if win32gui is available
        if WIN32_AVAILABLE:
            applications["windows"] = self._get_window_information()
        
        # Create summary
        applications["summary"] = {
            "total_processes": len(applications["processes"]),
            "total_windows": len(applications["windows"]),
            "timestamp": datetime.now().isoformat()
        }
        
        return applications
    
    def _get_window_information(self) -> List[Dict[str, Any]]:
        """Get information about all visible windows using win32gui."""
        windows = []
        
        def enum_window_callback(hwnd, _):
            if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
                try:
                    window_text = win32gui.GetWindowText(hwnd)
                    class_name = win32gui.GetClassName(hwnd)
                    
                    # Skip empty titles and certain system windows
                    if window_text and class_name not in ['Shell_TrayWnd', 'DV2ControlHost']:
                        # Get process information
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            proc = psutil.Process(pid)
                            process_name = proc.name()
                        except:
                            process_name = "Unknown"
                            pid = 0
                        
                        # Get window position
                        try:
                            rect = win32gui.GetWindowRect(hwnd)
                            position = {
                                "left": rect[0],
                                "top": rect[1], 
                                "right": rect[2],
                                "bottom": rect[3],
                                "width": rect[2] - rect[0],
                                "height": rect[3] - rect[1]
                            }
                        except:
                            position = {}
                        
                        windows.append({
                            "hwnd": hwnd,
                            "title": window_text,
                            "class_name": class_name,
                            "process_name": process_name,
                            "pid": pid,
                            "position": position,
                            "is_minimized": win32gui.IsIconic(hwnd),
                            "is_maximized": win32gui.IsZoomed(hwnd)
                        })
                except Exception as e:
                    pass  # Skip windows we can't access
        
        try:
            win32gui.EnumWindows(enum_window_callback, None)
        except Exception as e:
            print(f"Error enumerating windows: {e}")
        
        return windows
    
    def get_taskbar_apps_visual(self) -> Dict[str, Any]:
        """
        Use computer vision to analyze the taskbar and identify apps.
        
        Returns:
            Visual analysis of the taskbar including app icons and running applications
        """
        if not self.multimodal:
            return {"error": "Visual analysis not available - Multimodal AI not initialized"}
        
        print("ðŸ‘ï¸ Analyzing taskbar visually...")
        
        try:
            # Capture the screen
            screenshot = self.multimodal.capture_screen()
            if not screenshot:
                return {"error": "Failed to capture screenshot"}
            
            # Analyze the taskbar area specifically
            taskbar_prompt = """
            Analyze this Windows desktop screenshot and identify:
            
            1. TASKBAR LOCATION: Where is the taskbar located (bottom, top, left, right)?
            
            2. TASKBAR APPS: List all application icons visible in the taskbar, including:
               - App names (if identifiable from icons)
               - Whether apps appear to be running (highlighted/active)
               - Order from left to right
            
            3. SYSTEM TRAY: Describe what's visible in the system tray area (right side of taskbar):
               - System icons (clock, notifications, etc.)
               - Running background applications
               - Network/battery/volume indicators
            
            4. OPEN WINDOWS: Describe any open application windows visible on the desktop
            
            5. START MENU: Is the Start menu open or closed?
            
            Format your response clearly with each section labeled.
            """
            
            analysis = self.multimodal.analyze_image(screenshot, taskbar_prompt)
            
            return {
                "visual_analysis": analysis.get("analysis", ""),
                "timestamp": analysis.get("timestamp"),
                "method": "computer_vision",
                "screenshot_captured": True
            }
            
        except Exception as e:
            return {"error": f"Visual analysis failed: {str(e)}"}
    
    def get_taskbar_region_analysis(self) -> Dict[str, Any]:
        """
        Capture and analyze just the taskbar region for more focused results.
        
        Returns:
            Focused analysis of the taskbar area only
        """
        if not self.multimodal:
            return {"error": "Visual analysis not available"}
            
        if not PIL_AVAILABLE:
            return {"error": "PIL not available for screen capture"}
        
        print("ðŸ” Analyzing taskbar region specifically...")
        
        try:
            # Get screen dimensions
            screen = ImageGrab.grab()
            screen_width, screen_height = screen.size
            
            # Assume taskbar is at bottom (most common) - adjust if needed
            taskbar_height = 48  # Standard Windows taskbar height
            taskbar_region = (0, screen_height - taskbar_height, screen_width, screen_height)
            
            # Capture taskbar region
            taskbar_screenshot = self.multimodal.capture_screen(taskbar_region)
            if not taskbar_screenshot:
                return {"error": "Failed to capture taskbar region"}
            
            taskbar_prompt = """
            This is a cropped image of just the Windows taskbar. Please identify:
            
            1. All application icons from left to right
            2. Which apps appear to be running (active/highlighted)
            3. System tray contents on the right side
            4. Start button state
            5. Any other taskbar elements visible
            
            Be specific about what you can see and the order of elements.
            """
            
            analysis = self.multimodal.analyze_image(taskbar_screenshot, taskbar_prompt)
            
            return {
                "taskbar_analysis": analysis.get("analysis", ""),
                "region_captured": taskbar_region,
                "timestamp": analysis.get("timestamp"),
                "method": "focused_region_analysis"
            }
            
        except Exception as e:
            return {"error": f"Taskbar region analysis failed: {str(e)}"}
    
    def get_complete_desktop_analysis(self) -> Dict[str, Any]:
        """
        Provide a complete analysis combining process detection and visual analysis.
        
        Returns:
            Comprehensive desktop and taskbar analysis
        """
        print("ðŸ–¥ï¸ Performing complete desktop analysis...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "process_analysis": {},
            "visual_analysis": {},
            "taskbar_analysis": {},
            "summary": {}
        }
        
        # Get running applications via process detection
        try:
            results["process_analysis"] = self.get_running_applications()
        except Exception as e:
            results["process_analysis"] = {"error": str(e)}
        
        # Get visual analysis of entire desktop
        try:
            results["visual_analysis"] = self.get_taskbar_apps_visual()
        except Exception as e:
            results["visual_analysis"] = {"error": str(e)}
        
        # Get focused taskbar analysis
        try:
            results["taskbar_analysis"] = self.get_taskbar_region_analysis()
        except Exception as e:
            results["taskbar_analysis"] = {"error": str(e)}
        
        # Create summary
        process_count = len(results["process_analysis"].get("processes", []))
        window_count = len(results["process_analysis"].get("windows", []))
        
        results["summary"] = {
            "total_running_processes": process_count,
            "total_visible_windows": window_count,
            "visual_analysis_success": "visual_analysis" in results["visual_analysis"],
            "taskbar_analysis_success": "taskbar_analysis" in results["taskbar_analysis"],
            "detection_methods": ["process_enumeration"]
        }
        
        if WIN32_AVAILABLE:
            results["summary"]["detection_methods"].append("win32_windows")
        
        if self.multimodal:
            results["summary"]["detection_methods"].append("computer_vision")
        
        return results
    
    def find_specific_app_in_taskbar(self, app_name: str) -> Dict[str, Any]:
        """
        Look for a specific application in the taskbar.
        
        Args:
            app_name: Name of the application to find
            
        Returns:
            Information about whether the app is found and its status
        """
        print(f"ðŸ” Looking for '{app_name}' in taskbar...")
        
        # Check running processes first
        app_found_in_processes = False
        matching_processes = []
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if app_name.lower() in proc.info['name'].lower():
                    matching_processes.append(proc.info)
                    app_found_in_processes = True
            except:
                continue
        
        # Visual search if available
        visual_result = {}
        if self.multimodal:
            try:
                visual_prompt = f"""
                Look at this Windows desktop screenshot and determine:
                
                1. Is there an icon for "{app_name}" in the taskbar?
                2. If yes, does it appear to be running (highlighted/active)?
                3. Is there an open window for this application?
                4. Where exactly do you see it?
                
                Be specific about what you observe.
                """
                
                visual_result = self.multimodal.answer_visual_question(visual_prompt)
                
            except Exception as e:
                visual_result = {"error": str(e)}
        
        return {
            "app_name": app_name,
            "found_in_processes": app_found_in_processes,
            "matching_processes": matching_processes,
            "visual_search_result": visual_result,
            "timestamp": datetime.now().isoformat()
        }

# Convenience functions for easy access
def detect_taskbar_apps() -> str:
    """
    Main function to detect and describe taskbar applications.
    
    Returns:
        Human-readable description of taskbar contents
    """
    detector = TaskbarDetector()
    analysis = detector.get_complete_desktop_analysis()
    
    # Format results for human reading
    report_lines = []
    report_lines.append("ðŸ“Š TASKBAR & RUNNING APPS ANALYSIS")
    report_lines.append("=" * 50)
    
    # Process information
    if "process_analysis" in analysis and "summary" in analysis["process_analysis"]:
        summary = analysis["process_analysis"]["summary"]
        report_lines.append(f"🔄 Total Running Processes: {summary.get('total_processes', 0)}")
        report_lines.append(f"📦Ÿ Visible Windows: {summary.get('total_windows', 0)}")
    
    # Visual analysis
    if "visual_analysis" in analysis and "visual_analysis" in analysis["visual_analysis"]:
        report_lines.append("\nðŸ‘ï¸ VISUAL TASKBAR ANALYSIS:")
        report_lines.append(analysis["visual_analysis"]["visual_analysis"])
    
    # Focused taskbar analysis  
    if "taskbar_analysis" in analysis and "taskbar_analysis" in analysis["taskbar_analysis"]:
        report_lines.append("\nðŸŽ¯ FOCUSED TASKBAR ANALYSIS:")
        report_lines.append(analysis["taskbar_analysis"]["taskbar_analysis"])
    
    # Running processes summary
    if "process_analysis" in analysis and "processes" in analysis["process_analysis"]:
        processes = analysis["process_analysis"]["processes"]
        # Show top processes by memory usage
        top_processes = sorted(processes, key=lambda x: x.get('memory_mb', 0), reverse=True)[:10]
        
        report_lines.append("\nðŸ’¾ TOP MEMORY-USING PROCESSES:")
        for proc in top_processes:
            name = proc.get('name', 'Unknown')[:20].ljust(20)
            memory = f"{proc.get('memory_mb', 0):.1f}MB".rjust(10)
            report_lines.append(f"  â€¢ {name} {memory}")
    
    return "\n".join(report_lines)

def can_see_taskbar() -> str:
    """
    Check if the assistant can see and analyze the taskbar.
    
    Returns:
        Capability report
    """
    detector = TaskbarDetector()
    
    capabilities = []
    limitations = []
    
    # Check process detection
    capabilities.append("✅ Process Detection - I can see all running processes")
    
    # Check Windows API access
    if WIN32_AVAILABLE:
        capabilities.append("✅ Window Detection - I can see window titles and states")
    else:
        limitations.append("âŒ Win32 API - Limited window information available")
    
    # Check visual analysis
    if detector.multimodal:
        capabilities.append("✅ Visual Analysis - I can see and analyze your screen/taskbar")
        capabilities.append("✅ Icon Recognition - I can identify app icons in the taskbar")
    else:
        limitations.append("âŒ Computer Vision - Cannot visually analyze taskbar")
    
    report = []
    report.append("ðŸ” TASKBAR DETECTION CAPABILITIES")
    report.append("=" * 40)
    report.append("\nWhat I CAN do:")
    report.extend(capabilities)
    
    if limitations:
        report.append("\nLimitations:")
        report.extend(limitations)
    
    report.append(f"\nDetection Methods Available: {len(capabilities)}/3")
    
    return "\n".join(report)
