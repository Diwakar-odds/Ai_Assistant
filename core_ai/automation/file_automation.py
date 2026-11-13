"""
File Automation Module

Handles file system operations for the AI Assistant:
- Opening File Explorer at specific paths
- Finding files by name (fuzzy matching)
- Moving/Copying files
- Getting standard folders (Downloads, Documents, etc.)
"""

import os
import re
import shutil
import subprocess
import logging
import time
import difflib
import string
import ctypes
from typing import Optional, List, Dict, Any, Tuple
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
                subprocess.Popen(['explorer.exe', '/e,'], shell=False)
                logger.info("📂 Opened File Explorer (This PC)")
                return True

            resolved = self.resolve_folder_path(path)
            if not resolved or not os.path.exists(resolved):
                logger.warning(f"⚠️ Path could not be resolved or does not exist: {path}")
                return False

            # Convert to Windows path style
            norm_target = os.path.normpath(resolved)
            subprocess.Popen(['explorer.exe', norm_target], shell=False)
            logger.info(f"📂 Opened File Explorer at: {norm_target}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to open explorer: {e}")
            return False

    def resolve_folder_path(self, raw_path: str):
        """
        Resolve colloquial, drive-letter, or fuzzy folder names into real filesystem paths.
        Supports:
          - 'disk d', 'd drive', 'drive d', 'd:' -> 'D:\\'
          - 'resume folder in disk d', 'locate to resume in drive d' -> 'D:\\Resume'
          - 'resume', 'resume folder', 'resume naam ka folder' -> searches D:\\, C:\\, user dirs
        """
        if not raw_path or not str(raw_path).strip():
            return None

        cleaned = str(raw_path).strip().strip('"\'')

        # 1. Exact existing path
        if os.path.exists(cleaned):
            return os.path.normpath(cleaned)

        # 2. Standard user home directories
        std = self.get_standard_folder(cleaned)
        if std and os.path.exists(std):
            return os.path.normpath(std)

        # 3. Pure drive letter expressions: 'disk d', 'd drive', 'drive d', 'disk c', 'd:'
        drive_pure_m = re.match(
            r'^\s*(?:disk\s+([a-zA-Z])|drive\s+([a-zA-Z])|([a-zA-Z])\s+(?:disk|drive)|([a-zA-Z]):?/?\\?)\s*$',
            cleaned,
            re.IGNORECASE,
        )
        if drive_pure_m:
            letter = (drive_pure_m.group(1) or drive_pure_m.group(2) or drive_pure_m.group(3) or drive_pure_m.group(4)).upper()
            drive_root = f"{letter}:\\"
            if os.path.exists(drive_root):
                return os.path.normpath(drive_root)

        # 4. Extract folder name and target drive from compound expressions
        target_folder = None
        target_drive = None

        m_compound = re.search(
            r'(?:locate\s+to\s+)?(?:the\s+)?(?P<folder>.+?)\s+(?:folder|directory)?\s*(?:in|on|under|inside)\s+(?:disk|drive)\s+(?P<drive>[a-zA-Z])\b',
            cleaned,
            re.IGNORECASE,
        )
        if m_compound:
            target_folder = m_compound.group("folder").strip()
            target_drive = m_compound.group("drive").upper()
        else:
            m_hindi = re.search(
                r'(?:disk|drive)\s+(?P<drive>[a-zA-Z])\s+(?:mein?|pe|par|in)\s+(?P<folder>.+)',
                cleaned,
                re.IGNORECASE,
            )
            if m_hindi:
                target_folder = m_hindi.group("folder").strip()
                target_drive = m_hindi.group("drive").upper()

        if target_folder:
            target_folder = re.sub(r'\b(?:folder|directory|naam\s+ka\s+folder)\b', '', target_folder, flags=re.IGNORECASE).strip()

        if target_drive and target_folder:
            drive_root = f"{target_drive}:\\"
            direct_cand = os.path.join(drive_root, target_folder)
            if os.path.exists(direct_cand):
                return os.path.normpath(direct_cand)

            if os.path.exists(drive_root):
                try:
                    for entry in os.scandir(drive_root):
                        if entry.is_dir() and entry.name.lower() == target_folder.lower():
                            return os.path.normpath(entry.path)
                except Exception:
                    pass

                try:
                    for root, dirs, _ in os.walk(drive_root):
                        rel = os.path.relpath(root, drive_root)
                        depth = len(rel.split(os.sep)) if rel != '.' else 0
                        if depth >= 2:
                            dirs.clear()
                            continue
                        for d in dirs:
                            if d.lower() == target_folder.lower():
                                return os.path.normpath(os.path.join(root, d))
                except Exception:
                    pass

        # 5. Generic folder name search without explicit drive
        clean_name = re.sub(
            r'^\s*(?:locate\s+to|navigate\s+to|open|browse|find|locate|search\s+for|dhundo)\s+(?:the\s+)?',
            '',
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        clean_name = re.sub(
            r'\s*(?:naam\s+ka\s+folder|folder|directory|dhundo|kholo|batao|open|locate)\s*$',
            '',
            clean_name,
            flags=re.IGNORECASE,
        ).strip()

        if clean_name:
            user_home = Path.home()
            candidates = [
                os.path.join("D:\\", clean_name),
                os.path.join("C:\\", clean_name),
                str(user_home / clean_name),
                str(user_home / "Documents" / clean_name),
                str(user_home / "Desktop" / clean_name),
                str(user_home / "Downloads" / clean_name),
            ]
            for cand in candidates:
                if os.path.exists(cand) and os.path.isdir(cand):
                    return os.path.normpath(cand)

            for drive in ["D:\\", "C:\\"]:
                if os.path.exists(drive):
                    try:
                        for entry in os.scandir(drive):
                            if entry.is_dir() and entry.name.lower() == clean_name.lower():
                                return os.path.normpath(entry.path)
                    except Exception:
                        pass

        return None

    def list_folder_contents(self, path: str, max_items: int = 20):
        """List entries in a directory."""
        try:
            resolved = self.resolve_folder_path(path) or path
            if not os.path.exists(resolved) or not os.path.isdir(resolved):
                return []
            return sorted(os.listdir(resolved))[:max_items]
        except Exception as e:
            logger.error(f"Error listing folder contents: {e}")
            return []

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

    def create_folder(self, folder_name: str, dst_folder: str = "desktop") -> bool:
        """
        Create a new folder at a destination
        
        Args:
            folder_name: Name of the new folder
            dst_folder: Destination path or standard folder name (default: desktop)
            
        Returns:
            Success status
        """
        try:
            # Resolve destination if it's a standard folder name
            std_dst = self.get_standard_folder(dst_folder)
            if std_dst:
                dst_folder = std_dst
                
            if not os.path.exists(dst_folder):
                # If destination doesn't exist, we'll try to create it anyway
                os.makedirs(dst_folder, exist_ok=True)
                
            new_path = os.path.join(dst_folder, folder_name)
            os.makedirs(new_path, exist_ok=True)
            logger.info(f"✅ Created folder: {new_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create folder: {e}")
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

    def get_dynamic_project_roots(self) -> List[str]:
        """
        Dynamically discover project folders across all logical system drives
        and user directories with zero hardcoded paths or usernames.
        """
        roots: List[str] = []
        seen = set()

        def add_if_exists(p: str):
            if p and p not in seen and os.path.isdir(p):
                seen.add(p)
                roots.append(p)

        # 1. Inspect all logical drives on the system (C:, D:, E:, etc.)
        try:
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drive = f"{letter}:\\"
                    for folder_name in ("Projects", "projects", "Workspace", "workspaces", "dev", "Dev", "Code", "code"):
                        add_if_exists(os.path.join(drive, folder_name))
                bitmask >>= 1
        except Exception as e:
            logger.debug(f"Logical drive enumeration skipped: {e}")

        # 2. Inspect standard user profile directories
        user_prof = os.environ.get("USERPROFILE") or str(Path.home())
        for folder_name in ("Projects", "projects", "Desktop", "Documents", "Workspace", "workspaces", "dev", "Code"):
            add_if_exists(os.path.join(user_prof, folder_name))

        # 3. Inspect parent directory of the current workspace
        try:
            cwd = os.getcwd()
            parent_dir = os.path.dirname(os.path.abspath(cwd))
            add_if_exists(parent_dir)
        except Exception:
            pass

        return roots

    def list_known_projects(self) -> List[Dict[str, str]]:
        """Scan and index all project folders across dynamic roots."""
        projects: List[Dict[str, str]] = []
        seen_paths = set()

        for root in self.get_dynamic_project_roots():
            try:
                with os.scandir(root) as it:
                    for entry in it:
                        if entry.is_dir() and not entry.name.startswith("."):
                            full_path = os.path.abspath(entry.path)
                            if full_path not in seen_paths:
                                seen_paths.add(full_path)
                                projects.append({
                                    "name": entry.name,
                                    "path": full_path,
                                    "parent": root,
                                })
            except Exception as e:
                logger.debug(f"Error scanning project root {root}: {e}")

        return projects

    def find_project_path(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Find best matching project directory for a given query string.
        Returns (project_name, full_path) or None.
        """
        if not query:
            return None

        s = str(query).lower().strip()
        s = s.replace("_", " ").replace("-", " ")
        s = s.replace("assitant", "assistant")
        clean_q = " ".join(s.split())

        all_projects = self.list_known_projects()
        if not all_projects:
            cwd = os.getcwd()
            if clean_q in os.path.basename(cwd).lower():
                return os.path.basename(cwd), cwd
            return None

        # Tier 1: Exact or normalized match
        for p in all_projects:
            norm_name = p["name"].lower().replace("_", " ").replace("-", " ").strip()
            if norm_name == clean_q or p["name"].lower() == query.lower().strip():
                return p["name"], p["path"]

        # Tier 2: Substring inclusion
        for p in all_projects:
            norm_name = p["name"].lower().replace("_", " ").replace("-", " ").strip()
            if clean_q in norm_name or norm_name in clean_q:
                return p["name"], p["path"]

        # Tier 3: Fuzzy matching
        best_match = None
        best_score = 0.0
        for p in all_projects:
            norm_name = p["name"].lower().replace("_", " ").replace("-", " ").strip()
            score = difflib.SequenceMatcher(None, clean_q, norm_name).ratio()
            if score > best_score:
                best_score = score
                best_match = p

        if best_match and best_score >= 0.60:
            logger.info(f"Fuzzy matched project '{query}' -> '{best_match['name']}' (score: {best_score:.2f})")
            return best_match["name"], best_match["path"]

        return None

    def get_ide_executable(self, ide: str) -> Optional[str]:
        """Dynamically resolve IDE executable without hardcoded usernames or paths."""
        target = str(ide or "").lower().strip()
        
        if "antigravity" in target:
            which_p = shutil.which("antigravity")
            if which_p and os.path.isfile(which_p):
                return which_p
            try:
                import psutil
                for proc in psutil.process_iter(["name", "exe"]):
                    if (proc.info.get("name") or "").lower() == "antigravity.exe":
                        exe = proc.info.get("exe")
                        if exe and os.path.isfile(exe):
                            return exe
            except Exception:
                pass
            for pat in [
                r"%LOCALAPPDATA%\Programs\antigravity\Antigravity.exe",
                r"%PROGRAMFILES%\Antigravity\Antigravity.exe",
                r"%PROGRAMFILES(X86)%\Antigravity\Antigravity.exe",
            ]:
                res = os.path.expandvars(pat)
                if os.path.isfile(res):
                    return res

        elif any(v in target for v in ("vscode", "vs code", "code")):
            which_p = shutil.which("code")
            if which_p and os.path.isfile(which_p):
                return which_p
            try:
                import psutil
                for proc in psutil.process_iter(["name", "exe"]):
                    if (proc.info.get("name") or "").lower() == "code.exe":
                        exe = proc.info.get("exe")
                        if exe and os.path.isfile(exe):
                            return exe
            except Exception:
                pass
            for pat in [
                r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
                r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd",
                r"%PROGRAMFILES%\Microsoft VS Code\Code.exe",
            ]:
                res = os.path.expandvars(pat)
                if os.path.isfile(res):
                    return res

        return None

    def open_project(self, project_path: str, ide: str = "antigravity") -> Dict[str, Any]:
        """
        Open a project workspace in Antigravity, VS Code, or both.
        """
        if not os.path.exists(project_path) or not os.path.isdir(project_path):
            return {
                "success": False,
                "error": f"Project path does not exist: {project_path}",
            }

        norm_ide = str(ide or "antigravity").lower().strip()
        launched = []
        errors = []

        if norm_ide in ("antigravity", "both", "dono", "all"):
            ag_exe = self.get_ide_executable("antigravity")
            if not ag_exe:
                errors.append("Antigravity executable not found on system.")
            else:
                try:
                    logger.info(f"🚀 Opening Antigravity at: {project_path}")
                    subprocess.Popen([ag_exe, project_path], shell=False)
                    launched.append("Antigravity")
                except Exception as e:
                    errors.append(f"Failed to open Antigravity: {e}")

        if norm_ide in ("vscode", "vs code", "code", "both", "dono", "all"):
            code_exe = self.get_ide_executable("vscode")
            if not code_exe:
                errors.append("VS Code executable not found on system.")
            else:
                try:
                    logger.info(f"🚀 Opening VS Code at: {project_path}")
                    subprocess.Popen([code_exe, project_path], shell=True)
                    launched.append("VS Code")
                except Exception as e:
                    errors.append(f"Failed to open VS Code: {e}")

        success = len(launched) > 0
        return {
            "success": success,
            "launched": launched,
            "project_path": project_path,
            "errors": errors if errors else None,
            "message": (
                f"Successfully opened {os.path.basename(project_path)} in {' & '.join(launched)}"
                if success else
                f"Failed to open project: {'; '.join(errors)}"
            )
        }
