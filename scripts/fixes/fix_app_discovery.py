"""Fix app_discovery.py to be a clean re-export module with proper fallback"""

content = '''"""
App Discovery Module - Re-export
Re-export from canonical location to avoid code duplication.
The comprehensive implementation is in ai_assistant.modules.app_discovery
"""

# Re-export from the main modules implementation
try:
    from ai_assistant.modules.app_discovery import (
        AppDiscovery,
        smart_open_application,
        discover_applications,
        refresh_app_database,
        list_installed_apps,
    )
    
    __all__ = [
        'AppDiscovery',
        'smart_open_application',
        'discover_applications',
        'refresh_app_database',
        'list_installed_apps',
    ]
except ImportError:
    # Fallback if modules.app_discovery is not available
    import os
    import json
    import subprocess
    import logging
    from typing import Dict, List, Optional
    
    logger = logging.getLogger(__name__)
    APP_DB_FILE = 'apps.json'
    
    def list_installed_apps() -> List[str]:
        """Returns a list of all indexed application names."""
        try:
            if os.path.exists(APP_DB_FILE):
                with open(APP_DB_FILE, 'r') as f:
                    apps = json.load(f)
                return list(apps.keys())
        except Exception:
            pass
        return []
    
    def refresh_app_database() -> str:
        """Force rescan of installed applications."""
        return discover_applications()
    
    def discover_applications() -> str:
        """Scans Windows Start Menu for .lnk shortcuts."""
        logger.info("Scanning for applications...")
        apps = {}
        
        paths = [
            os.path.join(os.environ.get('APPDATA', ''), r'Microsoft\\Windows\\Start Menu\\Programs'),
            os.path.join(os.environ.get('PROGRAMDATA', ''), r'Microsoft\\Windows\\Start Menu\\Programs')
        ]

        for path in paths:
            if os.path.exists(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith('.lnk'):
                            name = file[:-4].lower()
                            full_path = os.path.join(root, file)
                            apps[name] = full_path
        
        try:
            with open(APP_DB_FILE, 'w') as f:
                json.dump(apps, f, indent=4)
            return f"Scan complete. Found {len(apps)} applications."
        except Exception as e:
            logger.error(f"Error saving app database: {e}")
            return f"Error saving app list: {e}"
    
    def smart_open_application(app_name: str) -> str:
        """Smartly opens an application."""
        app_name = app_name.lower().strip()
        
        apps = {}
        if os.path.exists(APP_DB_FILE):
            try:
                with open(APP_DB_FILE, 'r') as f:
                    apps = json.load(f)
            except:
                pass
        
        if not apps:
            discover_applications()
            if os.path.exists(APP_DB_FILE):
                try:
                    with open(APP_DB_FILE, 'r') as f:
                        apps = json.load(f)
                except:
                    pass

        target_path = None
        
        if app_name in apps:
            target_path = apps[app_name]
        
        if not target_path:
            for name, path in apps.items():
                if app_name in name:
                    target_path = path
                    break
        
        if target_path:
            try:
                os.startfile(target_path)
                return f"Opening {app_name}..."
            except Exception as e:
                return f"Found {app_name} but failed to open: {e}"
        
        try:
            subprocess.Popen(f"start {app_name}", shell=True)
            return f"Attempting to open {app_name} via system command..."
        except Exception as e:
            return f"Could not find or open {app_name}. Error: {e}"
    
    __all__ = [
        'smart_open_application',
        'discover_applications',
        'refresh_app_database',
        'list_installed_apps',
    ]
'''

file_path = 'f:/bn/assitant/ai_assistant/core/app_discovery.py'

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ Fixed {file_path}")
print(f"   File size: {len(content)} bytes")
