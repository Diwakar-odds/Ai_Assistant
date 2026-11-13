"""
Auto-Update System for AI Assistant Windows App

Features:
- Check for updates from GitHub Releases
- Download and install updates automatically
- Backup current version before updating
- Rollback on failed updates
- Show update notifications to users
"""

import os
import sys
import json
import shutil
import tempfile
import zipfile
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests library not available - updates disabled")


class Version:
    """Semantic version comparison"""
    
    def __init__(self, version_string: str):
        # Parse "v1.2.3" or "1.2.3"
        version_string = version_string.lstrip('v')
        parts = version_string.split('.')
        self.major = int(parts[0]) if len(parts) > 0 else 0
        self.minor = int(parts[1]) if len(parts) > 1 else 0
        self.patch = int(parts[2]) if len(parts) > 2 else 0
    
    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def __gt__(self, other):
        if self.major != other.major:
            return self.major > other.major
        if self.minor != other.minor:
            return self.minor > other.minor
        return self.patch > other.patch
    
    def __eq__(self, other):
        return (self.major == other.major and 
                self.minor == other.minor and 
                self.patch == other.patch)


class AutoUpdater:
    """Automatic update checker and installer"""
    
    def __init__(self, 
                 current_version: str = "1.0.0",
                 github_repo: str = "yourusername/ai-assistant",
                 update_channel: str = "stable"):
        """
        Initialize auto-updater
        
        Args:
            current_version: Current app version (e.g., "1.0.0")
            github_repo: GitHub repository in format "owner/repo"
            update_channel: "stable" or "beta"
        """
        self.current_version = Version(current_version)
        self.github_repo = github_repo
        self.update_channel = update_channel
        
        # Paths
        self.app_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path.cwd()
        self.update_dir = self.app_dir / "updates"
        self.backup_dir = self.app_dir / "backups"
        self.config_file = self.app_dir / "update_config.json"
        
        # Create directories
        self.update_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Load config
        self.config = self._load_config()
        
        # Update state
        self.latest_version: Optional[Version] = None
        self.update_available = False
        self.download_url: Optional[str] = None
        self.release_notes: Optional[str] = None
    
    def _load_config(self) -> Dict:
        """Load update configuration"""
        default_config = {
            "auto_check": True,
            "auto_download": False,
            "auto_install": False,
            "check_interval_hours": 24,
            "last_check": None,
            "update_channel": self.update_channel,
            "ignored_version": None
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    default_config.update(config)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        
        return default_config
    
    def _save_config(self):
        """Save update configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def should_check_for_updates(self) -> bool:
        """Check if it's time to check for updates"""
        if not self.config["auto_check"]:
            return False
        
        last_check = self.config.get("last_check")
        if not last_check:
            return True
        
        try:
            last_check_time = datetime.fromisoformat(last_check)
            hours_since_check = (datetime.now() - last_check_time).total_seconds() / 3600
            return hours_since_check >= self.config["check_interval_hours"]
        except:
            return True
    
    def check_for_updates(self) -> Tuple[bool, Optional[str]]:
        """
        Check for updates from GitHub Releases
        
        Returns:
            (update_available, version_string)
        """
        if not REQUESTS_AVAILABLE:
            return False, None
        
        try:
            # GitHub Releases API
            api_url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
            
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            release_data = response.json()
            
            # Parse version
            tag_name = release_data.get("tag_name", "")
            self.latest_version = Version(tag_name)
            
            # Check if newer
            if self.latest_version > self.current_version:
                # Check if ignored
                ignored = self.config.get("ignored_version")
                if ignored and Version(ignored) == self.latest_version:
                    logger.info(f"Update {self.latest_version} is ignored by user")
                    return False, None
                
                self.update_available = True
                self.release_notes = release_data.get("body", "No release notes available")
                
                # Find download URL for Windows
                for asset in release_data.get("assets", []):
                    if "windows" in asset["name"].lower() and asset["name"].endswith(".zip"):
                        self.download_url = asset["browser_download_url"]
                        break
                
                logger.info(f"Update available: {self.latest_version}")
                self._save_config()
                return True, str(self.latest_version)
            else:
                logger.info(f"Already on latest version: {self.current_version}")
                return False, None
        
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
            return False, None
        
        finally:
            # Update last check time
            self.config["last_check"] = datetime.now().isoformat()
            self._save_config()
    
    def download_update(self, callback=None) -> Optional[Path]:
        """
        Download update ZIP file
        
        Args:
            callback: Optional callback(bytes_downloaded, total_bytes)
            
        Returns:
            Path to downloaded file or None
        """
        if not self.download_url:
            logger.error("No download URL available")
            return None
        
        try:
            # Download with progress
            response = requests.get(self.download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # Save to temp file
            temp_file = self.update_dir / f"update-{self.latest_version}.zip"
            
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if callback:
                            callback(downloaded, total_size)
            
            logger.info(f"Downloaded update to: {temp_file}")
            return temp_file
        
        except Exception as e:
            logger.error(f"Failed to download update: {e}")
            return None
    
    def install_update(self, update_file: Path) -> bool:
        """
        Install downloaded update
        
        Args:
            update_file: Path to update ZIP file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup of current version
            backup_name = f"backup-{self.current_version}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            backup_path = self.backup_dir / backup_name
            
            logger.info(f"Creating backup: {backup_path}")
            shutil.copytree(self.app_dir, backup_path, 
                          ignore=shutil.ignore_patterns('updates', 'backups', 'logs', '*.log'))
            
            # Extract update
            logger.info(f"Extracting update: {update_file}")
            with zipfile.ZipFile(update_file, 'r') as zip_ref:
                # Extract to temp location first
                temp_extract = tempfile.mkdtemp()
                zip_ref.extractall(temp_extract)
                
                # Find the actual app folder inside ZIP
                extracted_folders = list(Path(temp_extract).iterdir())
                if len(extracted_folders) == 1 and extracted_folders[0].is_dir():
                    update_source = extracted_folders[0]
                else:
                    update_source = Path(temp_extract)
                
                # Copy files (skip running exe)
                for item in update_source.rglob('*'):
                    if item.is_file():
                        relative_path = item.relative_to(update_source)
                        target = self.app_dir / relative_path
                        
                        # Skip locked files (running .exe)
                        if target.name == Path(sys.executable).name:
                            continue
                        
                        # Create parent dirs
                        target.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Copy file
                        shutil.copy2(item, target)
                
                # Cleanup
                shutil.rmtree(temp_extract)
            
            logger.info("Update installed successfully!")
            
            # Create restart script
            restart_script = self.app_dir / "restart_after_update.bat"
            with open(restart_script, 'w') as f:
                f.write(f"""@echo off
timeout /t 2 /nobreak > nul
start "" "{sys.executable}"
del "%~f0"
""")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to install update: {e}")
            
            # Try to restore backup
            if backup_path.exists():
                logger.info("Restoring from backup...")
                try:
                    shutil.copytree(backup_path, self.app_dir, dirs_exist_ok=True)
                    logger.info("Backup restored successfully")
                except Exception as restore_error:
                    logger.error(f"Failed to restore backup: {restore_error}")
            
            return False
    
    def ignore_version(self, version: str):
        """Ignore a specific version"""
        self.config["ignored_version"] = version
        self._save_config()
    
    def get_update_info(self) -> Dict:
        """Get current update information"""
        return {
            "current_version": str(self.current_version),
            "latest_version": str(self.latest_version) if self.latest_version else None,
            "update_available": self.update_available,
            "release_notes": self.release_notes,
            "download_url": self.download_url,
            "auto_check": self.config["auto_check"],
            "auto_download": self.config["auto_download"],
            "auto_install": self.config["auto_install"]
        }
    
    def check_for_updates_async(self, callback):
        """Check for updates in background thread"""
        def _check():
            update_available, version = self.check_for_updates()
            callback(update_available, version)
        
        thread = threading.Thread(target=_check, daemon=True)
        thread.start()


# Singleton instance
_updater_instance: Optional[AutoUpdater] = None

def get_updater(current_version: str = "1.0.0", 
                github_repo: str = "yourusername/ai-assistant") -> AutoUpdater:
    """Get singleton updater instance"""
    global _updater_instance
    if _updater_instance is None:
        _updater_instance = AutoUpdater(current_version, github_repo)
    return _updater_instance
