"""
File Automation Module

Handles file system operations for the AI Assistant:
- Opening File Explorer at specific paths
- Finding files by name (fuzzy matching)
- Moving/Copying files
- Getting standard folders (Downloads, Documents, etc.)
"""

import os
import shutil
import subprocess
import logging
import time
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class FileAutomation:
    """
    Handles file system interactions and automation
    """
    
    def __init__(self):
        """Initialize file automation"""
        logger.info("📂 FileAutomation initialized")
        
    def get_standard_folder(self, folder_name: str) -> Optional[str]:
        """
        Get path to standard user folders
        
        Args:
            folder_name: Name of folder (downloads, documents, desktop, etc.)
            
        Returns:
            Absolute path or None
        """
        user_home = Path.home()
        folder_map = {
            'downloads': user_home / 'Downloads',
            'documents': user_home / 'Documents',
            'desktop': user_home / 'Desktop',
            'pictures': user_home / 'Pictures',
            'videos': user_home / 'Videos',
            'music': user_home / 'Music'
        }
        
        return str(folder_map.get(folder_name.lower())) if folder_name.lower() in folder_map else None

    def open_explorer(self, path: str = None) -> bool:
        """
        Open File Explorer at specific path
        
        Args:
            path: Path to open (defaults to Computer/This PC)
            
        Returns:
            Success status
        """
        try:
            if not path:
                # Open This PC
                subprocess.Popen('explorer /e,', shell=True)
                logger.info("📂 Opened File Explorer (This PC)")
                return True
                
            if not os.path.exists(path):
                logger.warning(f"⚠️ Path does not exist: {path}")
                # Try to resolve standard folder names
                std_path = self.get_standard_folder(path)
                if std_path and os.path.exists(std_path):
                    path = std_path
                else:
                    return False
            
            # Convert to Windows path style
            path = os.path.normpath(path)
            subprocess.Popen(f'explorer "{path}"', shell=True)
            logger.info(f"📂 Opened File Explorer at: {path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to open explorer: {e}")
            return False

    def find_file(self, filename: str, search_path: str = None, recursive: bool = True) -> Optional[str]:
        """
        Find a file by name
        
        Args:
            filename: Name of file to find (partial match supported)
            search_path: Directory to search in (default: user home)
            recursive: Whether to search subdirectories
            
        Returns:
            Path to found file or None
        """
        try:
            start_dir = search_path or str(Path.home())
            if not os.path.exists(start_dir):
                # Check if it's a standard folder name
                std_path = self.get_standard_folder(start_dir)
                if std_path:
                    start_dir = std_path
            
            logger.info(f"🔍 Searching for '{filename}' in '{start_dir}'...")
            
            # Walk through directories
            for root, dirs, files in os.walk(start_dir):
                for file in files:
                    # Simple case-insensitive partial match
                    if filename.lower() in file.lower():
                        full_path = os.path.join(root, file)
                        logger.info(f"✅ Found file: {full_path}")
                        return full_path
                
                if not recursive:
                    break
                    
            logger.warning(f"⚠️ File not found: {filename}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error searching for file: {e}")
            return None

    def move_file(self, src: str, dst_folder: str) -> bool:
        """
        Move a file to a destination folder
        
        Args:
            src: Source file path
            dst_folder: Destination folder path
            
        Returns:
            Success status
        """
        try:
            if not os.path.exists(src):
                logger.error(f"❌ Source file not found: {src}")
                return False
                
            # Resolve destination if it's a standard folder name
            std_dst = self.get_standard_folder(dst_folder)
            if std_dst:
                dst_folder = std_dst
                
            if not os.path.exists(dst_folder):
                os.makedirs(dst_folder, exist_ok=True)
                
            filename = os.path.basename(src)
            dst_path = os.path.join(dst_folder, filename)
            
            shutil.move(src, dst_path)
            logger.info(f"✅ Moved file to: {dst_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to move file: {e}")
            return False

    def copy_file(self, src: str, dst_folder: str) -> bool:
        """
        Copy a file to a destination folder
        
        Args:
            src: Source file path
            dst_folder: Destination folder path
            
        Returns:
            Success status
        """
        try:
            if not os.path.exists(src):
                logger.error(f"❌ Source file not found: {src}")
                return False
                
            # Resolve destination if it's a standard folder name
            std_dst = self.get_standard_folder(dst_folder)
            if std_dst:
                dst_folder = std_dst
                
            if not os.path.exists(dst_folder):
                os.makedirs(dst_folder, exist_ok=True)
                
            filename = os.path.basename(src)
            dst_path = os.path.join(dst_folder, filename)
            
            shutil.copy2(src, dst_path)
            logger.info(f"✅ Copied file to: {dst_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to copy file: {e}")
            return False
