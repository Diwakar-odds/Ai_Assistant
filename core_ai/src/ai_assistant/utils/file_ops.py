# Advanced File Operations Module for YourDaddy Assistant
"""
Advanced file management and organization functionality:
- Intelligent file organization and sorting
- Duplicate file detection and management
- File compression and archiving
- Advanced search and filtering
- File synchronization between directories
- Batch file operations
- File metadata analysis
- Automated backup management
"""

import os
import shutil
import zipfile
import hashlib
import json
import datetime
import fnmatch
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import subprocess

class FileOperationsManager:
    """
    Advanced file operations manager with intelligent features
    """
    
    def __init__(self):
        self.operations_log = []
        self.backup_dir = os.path.expanduser("~/YourDaddy_Backups")
        self.ensure_backup_dir()
    
    def ensure_backup_dir(self):
        """Ensure backup directory exists"""
        os.makedirs(self.backup_dir, exist_ok=True)

def organize_files_by_type(directory: str, create_subfolders: bool = True) -> str:
    """
    Organize files in a directory by their type/extension
    Args:
        directory: Target directory to organize
        create_subfolders: Whether to create subfolders for each type
    """
    try:
        if not os.path.exists(directory):
            return f"❌ Directory not found: {directory}"
        
        file_types = {
            'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg', '.webp'],
            'Videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
            'Audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
            'Documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.pages'],
            'Spreadsheets': ['.xls', '.xlsx', '.csv', '.ods', '.numbers'],
            'Presentations': ['.ppt', '.pptx', '.odp', '.key'],
            'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
            'Code': ['.py', '.js', '.html', '.css', '.cpp', '.java', '.php', '.rb'],
            'Executables': ['.exe', '.msi', '.deb', '.dmg', '.pkg', '.app']
        }
        
        organized_count = 0
        created_folders = []
        
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            # Skip directories
            if os.path.isdir(file_path):
                continue
            
            file_ext = os.path.splitext(filename)[1].lower()
            moved = False
            
            # Find appropriate category
            for category, extensions in file_types.items():
                if file_ext in extensions:
                    if create_subfolders:
                        category_dir = os.path.join(directory, category)
                        os.makedirs(category_dir, exist_ok=True)
                        
                        if category not in created_folders:
                            created_folders.append(category)
                        
                        dest_path = os.path.join(category_dir, filename)
                        # Handle duplicate names
                        if os.path.exists(dest_path):
                            base, ext = os.path.splitext(filename)
                            counter = 1
                            while os.path.exists(dest_path):
                                new_name = f"{base}_{counter}{ext}"
                                dest_path = os.path.join(category_dir, new_name)
                                counter += 1
                        
                        shutil.move(file_path, dest_path)
                        organized_count += 1
                        moved = True
                        break
            
            # Files with no category go to 'Other'
            if not moved and create_subfolders:
                other_dir = os.path.join(directory, 'Other')
                os.makedirs(other_dir, exist_ok=True)
                if 'Other' not in created_folders:
                    created_folders.append('Other')
                
                dest_path = os.path.join(other_dir, filename)
                if not os.path.exists(dest_path):
                    shutil.move(file_path, dest_path)
                    organized_count += 1
        
        result = f"🗂️ Organized {organized_count} files into {len(created_folders)} categories"
        if created_folders:
            result += f"\n📁 Created folders: {', '.join(created_folders)}"
        
        return result
        
    except PermissionError:
        return "❌ Permission denied. Run as administrator or check file permissions."
    except Exception as e:
        return f"❌ Organization error: {str(e)}"

def find_duplicate_files(directory: str, include_subdirs: bool = True) -> str:
    """
    Find duplicate files in a directory based on file content hash
    Args:
        directory: Directory to scan for duplicates
        include_subdirs: Whether to include subdirectories
    """
    try:
        if not os.path.exists(directory):
            return f"❌ Directory not found: {directory}"
        
        file_hashes = {}
        duplicates = []
        total_files = 0
        total_size_saved = 0
        
        # Walk through directory
        for root, dirs, files in os.walk(directory):
            if not include_subdirs and root != directory:
                continue
            
            for filename in files:
                file_path = os.path.join(root, filename)
                
                try:
                    # Calculate file hash
                    hash_md5 = hashlib.md5()
                    with open(file_path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hash_md5.update(chunk)
                    
                    file_hash = hash_md5.hexdigest()
                    file_size = os.path.getsize(file_path)
                    
                    if file_hash in file_hashes:
                        # Duplicate found
                        duplicates.append({
                            'original': file_hashes[file_hash]['path'],
                            'duplicate': file_path,
                            'size': file_size,
                            'hash': file_hash
                        })
                        total_size_saved += file_size
                    else:
                        file_hashes[file_hash] = {
                            'path': file_path,
                            'size': file_size
                        }
                    
                    total_files += 1
                    
                except (PermissionError, FileNotFoundError):
                    continue
        
        if duplicates:
            result = f"🔍 Found {len(duplicates)} duplicate files from {total_files} scanned\n"
            result += f"💾 Potential space savings: {total_size_saved / (1024*1024):.1f} MB\n\n"
            
            # Show first 5 duplicates as examples
            for i, dup in enumerate(duplicates[:5]):
                size_mb = dup['size'] / (1024*1024)
                result += f"📄 Duplicate {i+1}: {os.path.basename(dup['duplicate'])} ({size_mb:.1f} MB)\n"
                result += f"   Original: {dup['original']}\n"
                result += f"   Copy: {dup['duplicate']}\n\n"
            
            if len(duplicates) > 5:
                result += f"... and {len(duplicates) - 5} more duplicates found."
            
            # Save detailed report
            report_path = os.path.join(directory, f"duplicate_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(report_path, 'w') as f:
                json.dump(duplicates, f, indent=2)
            
            result += f"\n📋 Detailed report saved: {report_path}"
            
        else:
            result = f"✅ No duplicate files found in {total_files} scanned files"
        
        return result
        
    except Exception as e:
        return f"❌ Duplicate detection error: {str(e)}"

def remove_duplicate_files(directory: str, keep_oldest: bool = True, dry_run: bool = True) -> str:
    """
    Remove duplicate files, keeping either oldest or newest
    Args:
        directory: Directory to clean
        keep_oldest: If True, keep oldest files; if False, keep newest
        dry_run: If True, only show what would be deleted without actually deleting
    """
    try:
        if not os.path.exists(directory):
            return f"❌ Directory not found: {directory}"
        
        # First find duplicates
        file_hashes = {}
        duplicates_to_remove = []
        
        for root, dirs, files in os.walk(directory):
            for filename in files:
                file_path = os.path.join(root, filename)
                
                try:
                    # Calculate file hash and modification time
                    hash_md5 = hashlib.md5()
                    with open(file_path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hash_md5.update(chunk)
                    
                    file_hash = hash_md5.hexdigest()
                    mod_time = os.path.getmtime(file_path)
                    file_size = os.path.getsize(file_path)
                    
                    if file_hash in file_hashes:
                        # Duplicate found - decide which to keep
                        existing_time = file_hashes[file_hash]['mod_time']
                        
                        if keep_oldest:
                            if mod_time > existing_time:
                                # Current file is newer, mark for deletion
                                duplicates_to_remove.append(file_path)
                            else:
                                # Current file is older, mark existing for deletion
                                duplicates_to_remove.append(file_hashes[file_hash]['path'])
                                file_hashes[file_hash] = {
                                    'path': file_path,
                                    'mod_time': mod_time,
                                    'size': file_size
                                }
                        else:
                            if mod_time < existing_time:
                                # Current file is older, mark for deletion
                                duplicates_to_remove.append(file_path)
                            else:
                                # Current file is newer, mark existing for deletion
                                duplicates_to_remove.append(file_hashes[file_hash]['path'])
                                file_hashes[file_hash] = {
                                    'path': file_path,
                                    'mod_time': mod_time,
                                    'size': file_size
                                }
                    else:
                        file_hashes[file_hash] = {
                            'path': file_path,
                            'mod_time': mod_time,
                            'size': file_size
                        }
                        
                except (PermissionError, FileNotFoundError):
                    continue
        
        if not duplicates_to_remove:
            return "✅ No duplicate files found to remove"
        
        total_size_freed = sum(os.path.getsize(path) for path in duplicates_to_remove if os.path.exists(path))
        
        result = f"🗑️ {'Would remove' if dry_run else 'Removing'} {len(duplicates_to_remove)} duplicate files\n"
        result += f"💾 Space {'would be' if dry_run else ''} freed: {total_size_freed / (1024*1024):.1f} MB\n\n"
        
        removed_count = 0
        for file_path in duplicates_to_remove:
            if os.path.exists(file_path):
                if not dry_run:
                    try:
                        os.remove(file_path)
                        removed_count += 1
                    except (PermissionError, FileNotFoundError):
                        continue
                else:
                    removed_count += 1
                
                result += f"{'Would delete' if dry_run else 'Deleted'}: {file_path}\n"
                
                # Limit output to first 10 files
                if removed_count >= 10:
                    remaining = len(duplicates_to_remove) - 10
                    if remaining > 0:
                        result += f"... and {remaining} more files\n"
                    break
        
        if dry_run:
            result += "\n⚠️  This was a DRY RUN. Set dry_run=False to actually delete files."
        
        return result
        
    except Exception as e:
        return f"❌ Duplicate removal error: {str(e)}"

def create_backup_archive(source_dir: str, backup_name: str = None, compression: str = "zip") -> str:
    """
    Create a compressed backup archive of a directory
    Args:
        source_dir: Directory to backup
        backup_name: Custom backup name (optional)
        compression: Compression format (zip, tar)
    """
    try:
        if not os.path.exists(source_dir):
            return f"❌ Source directory not found: {source_dir}"
        
        # Generate backup name
        if not backup_name:
            dir_name = os.path.basename(source_dir.rstrip(os.sep))
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{dir_name}_backup_{timestamp}"
        
        backup_manager = FileOperationsManager()
        
        if compression == "zip":
            archive_path = os.path.join(backup_manager.backup_dir, f"{backup_name}.zip")
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, source_dir)
                        zipf.write(file_path, arcname)
            
        elif compression == "tar":
            import tarfile
            archive_path = os.path.join(backup_manager.backup_dir, f"{backup_name}.tar.gz")
            
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(source_dir, arcname=os.path.basename(source_dir))
        
        else:
            return f"❌ Unsupported compression format: {compression}"
        
        archive_size = os.path.getsize(archive_path) / (1024*1024)
        
        return f"📦 Backup created successfully!\n🗂️ Archive: {archive_path}\n💾 Size: {archive_size:.1f} MB"
        
    except Exception as e:
        return f"❌ Backup creation error: {str(e)}"

def smart_file_search(directory: str, pattern: str, search_content: bool = False, file_types: List[str] = None) -> str:
    """
    Advanced file search with content search and filtering
    Args:
        directory: Directory to search in
        pattern: Search pattern (filename or content)
        search_content: Whether to search file contents
        file_types: List of file extensions to include
    """
    try:
        if not os.path.exists(directory):
            return f"❌ Directory not found: {directory}"
        
        found_files = []
        content_matches = []
        
        for root, dirs, files in os.walk(directory):
            for filename in files:
                file_path = os.path.join(root, filename)
                file_ext = os.path.splitext(filename)[1].lower()
                
                # Filter by file type if specified
                if file_types and file_ext not in file_types:
                    continue
                
                # Check filename match
                if fnmatch.fnmatch(filename.lower(), pattern.lower()) or pattern.lower() in filename.lower():
                    file_size = os.path.getsize(file_path)
                    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    found_files.append({
                        'path': file_path,
                        'size': file_size,
                        'modified': mod_time.strftime('%Y-%m-%d %H:%M')
                    })
                
                # Search file content if requested
                if search_content and file_ext in ['.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv']:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if pattern.lower() in content.lower():
                                # Find line numbers
                                lines = content.split('\n')
                                matching_lines = []
                                for i, line in enumerate(lines, 1):
                                    if pattern.lower() in line.lower():
                                        matching_lines.append(f"Line {i}: {line.strip()[:100]}")
                                        if len(matching_lines) >= 3:  # Limit to 3 matches per file
                                            break
                                
                                content_matches.append({
                                    'path': file_path,
                                    'matches': matching_lines
                                })
                                
                    except (UnicodeDecodeError, PermissionError, FileNotFoundError):
                        continue
        
        # Format results
        result = ""
        
        if found_files:
            result += f"📁 Found {len(found_files)} files matching filename pattern:\n\n"
            for i, file_info in enumerate(found_files[:10]):  # Show first 10
                size_str = f"{file_info['size']} bytes"
                if file_info['size'] > 1024*1024:
                    size_str = f"{file_info['size']/(1024*1024):.1f} MB"
                elif file_info['size'] > 1024:
                    size_str = f"{file_info['size']/1024:.1f} KB"
                
                result += f"{i+1}. {os.path.basename(file_info['path'])}\n"
                result += f"   📍 {file_info['path']}\n"
                result += f"   📊 {size_str} | Modified: {file_info['modified']}\n\n"
            
            if len(found_files) > 10:
                result += f"... and {len(found_files) - 10} more files\n\n"
        
        if content_matches:
            result += f"📄 Found {len(content_matches)} files with content matches:\n\n"
            for i, match in enumerate(content_matches[:5]):  # Show first 5
                result += f"{i+1}. {os.path.basename(match['path'])}\n"
                result += f"   📍 {match['path']}\n"
                for line_match in match['matches']:
                    result += f"   🔍 {line_match}\n"
                result += "\n"
            
            if len(content_matches) > 5:
                result += f"... and {len(content_matches) - 5} more files with matches\n"
        
        if not found_files and not content_matches:
            result = f"🔍 No files found matching pattern: {pattern}"
        
        return result
        
    except Exception as e:
        return f"❌ Search error: {str(e)}"

def batch_rename_files(directory: str, pattern: str, replacement: str, preview: bool = True) -> str:
    """
    Batch rename files using pattern matching
    Args:
        directory: Directory containing files to rename
        pattern: Pattern to match (supports wildcards)
        replacement: New name pattern (use {n} for numbers)
        preview: If True, show preview without renaming
    """
    try:
        if not os.path.exists(directory):
            return f"❌ Directory not found: {directory}"
        
        files_to_rename = []
        
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            if os.path.isfile(file_path) and fnmatch.fnmatch(filename, pattern):
                files_to_rename.append(filename)
        
        if not files_to_rename:
            return f"🔍 No files found matching pattern: {pattern}"
        
        rename_operations = []
        
        for i, filename in enumerate(files_to_rename):
            # Generate new filename
            new_name = replacement.replace("{n}", str(i+1).zfill(3))
            
            # Keep file extension if not specified in replacement
            if not os.path.splitext(new_name)[1] and os.path.splitext(filename)[1]:
                new_name += os.path.splitext(filename)[1]
            
            old_path = os.path.join(directory, filename)
            new_path = os.path.join(directory, new_name)
            
            rename_operations.append({
                'old': filename,
                'new': new_name,
                'old_path': old_path,
                'new_path': new_path
            })
        
        result = f"{'Preview of' if preview else 'Performing'} batch rename operation:\n\n"
        
        renamed_count = 0
        for operation in rename_operations:
            if not preview:
                try:
                    # Check if destination already exists
                    if os.path.exists(operation['new_path']):
                        base, ext = os.path.splitext(operation['new'])
                        counter = 1
                        while os.path.exists(operation['new_path']):
                            new_name = f"{base}_{counter}{ext}"
                            operation['new_path'] = os.path.join(directory, new_name)
                            operation['new'] = new_name
                            counter += 1
                    
                    os.rename(operation['old_path'], operation['new_path'])
                    renamed_count += 1
                except (PermissionError, FileNotFoundError) as e:
                    result += f"❌ Failed to rename {operation['old']}: {str(e)}\n"
                    continue
            else:
                renamed_count += 1
            
            result += f"{operation['old']} → {operation['new']}\n"
        
        result += f"\n{'Would rename' if preview else 'Successfully renamed'} {renamed_count} files"
        
        if preview:
            result += "\n⚠️  This was a PREVIEW. Set preview=False to actually rename files."
        
        return result
        
    except Exception as e:
        return f"❌ Batch rename error: {str(e)}"

def analyze_directory_structure(directory: str, max_depth: int = 3) -> str:
    """
    Analyze directory structure and provide insights
    Args:
        directory: Directory to analyze
        max_depth: Maximum depth to analyze
    """
    try:
        if not os.path.exists(directory):
            return f"❌ Directory not found: {directory}"
        
        analysis = {
            'total_files': 0,
            'total_dirs': 0,
            'total_size': 0,
            'file_types': {},
            'large_files': [],
            'empty_dirs': [],
            'old_files': []
        }
        
        current_time = time.time()
        one_year_ago = current_time - (365 * 24 * 60 * 60)
        
        for root, dirs, files in os.walk(directory):
            # Check depth
            depth = root[len(directory):].count(os.sep)
            if depth >= max_depth:
                dirs.clear()  # Don't go deeper
                continue
            
            analysis['total_dirs'] += len(dirs)
            
            # Check for empty directories
            if not dirs and not files:
                analysis['empty_dirs'].append(root)
            
            for filename in files:
                file_path = os.path.join(root, filename)
                
                try:
                    file_size = os.path.getsize(file_path)
                    mod_time = os.path.getmtime(file_path)
                    
                    analysis['total_files'] += 1
                    analysis['total_size'] += file_size
                    
                    # Track file types
                    ext = os.path.splitext(filename)[1].lower()
                    if ext:
                        analysis['file_types'][ext] = analysis['file_types'].get(ext, 0) + 1
                    else:
                        analysis['file_types']['no_extension'] = analysis['file_types'].get('no_extension', 0) + 1
                    
                    # Track large files (>100MB)
                    if file_size > 100 * 1024 * 1024:
                        analysis['large_files'].append({
                            'path': file_path,
                            'size': file_size
                        })
                    
                    # Track old files (>1 year)
                    if mod_time < one_year_ago:
                        analysis['old_files'].append({
                            'path': file_path,
                            'age_days': int((current_time - mod_time) / (24 * 60 * 60))
                        })
                        
                except (PermissionError, FileNotFoundError):
                    continue
        
        # Format results
        result = f"📊 Directory Analysis: {directory}\n"
        result += "=" * 50 + "\n\n"
        
        # Basic stats
        total_size_gb = analysis['total_size'] / (1024**3)
        result += f"📁 Total Directories: {analysis['total_dirs']}\n"
        result += f"📄 Total Files: {analysis['total_files']}\n"
        result += f"💾 Total Size: {total_size_gb:.2f} GB\n\n"
        
        # File types
        if analysis['file_types']:
            result += "📋 File Types:\n"
            sorted_types = sorted(analysis['file_types'].items(), key=lambda x: x[1], reverse=True)
            for ext, count in sorted_types[:10]:
                ext_display = ext if ext != 'no_extension' else '(no extension)'
                result += f"   {ext_display}: {count} files\n"
            result += "\n"
        
        # Large files
        if analysis['large_files']:
            result += "🐘 Large Files (>100MB):\n"
            analysis['large_files'].sort(key=lambda x: x['size'], reverse=True)
            for large_file in analysis['large_files'][:5]:
                size_gb = large_file['size'] / (1024**3)
                filename = os.path.basename(large_file['path'])
                result += f"   {filename}: {size_gb:.2f} GB\n"
            result += "\n"
        
        # Empty directories
        if analysis['empty_dirs']:
            result += f"📂 Empty Directories: {len(analysis['empty_dirs'])}\n"
            for empty_dir in analysis['empty_dirs'][:5]:
                result += f"   {empty_dir}\n"
            if len(analysis['empty_dirs']) > 5:
                result += f"   ... and {len(analysis['empty_dirs']) - 5} more\n"
            result += "\n"
        
        # Old files
        if analysis['old_files']:
            result += f"🗓️ Old Files (>1 year): {len(analysis['old_files'])}\n"
            analysis['old_files'].sort(key=lambda x: x['age_days'], reverse=True)
            for old_file in analysis['old_files'][:5]:
                years = old_file['age_days'] / 365
                filename = os.path.basename(old_file['path'])
                result += f"   {filename}: {years:.1f} years old\n"
            result += "\n"
        
        return result
        
    except Exception as e:
        return f"❌ Analysis error: {str(e)}"

def sync_directories(source_dir: str, dest_dir: str, delete_extra: bool = False, dry_run: bool = True) -> str:
    """
    Synchronize two directories (one-way sync from source to destination)
    Args:
        source_dir: Source directory
        dest_dir: Destination directory
        delete_extra: Whether to delete files in destination that don't exist in source
        dry_run: If True, only show what would be done
    """
    try:
        if not os.path.exists(source_dir):
            return f"❌ Source directory not found: {source_dir}"
        
        os.makedirs(dest_dir, exist_ok=True)
        
        sync_actions = []
        
        # Walk source directory
        for root, dirs, files in os.walk(source_dir):
            rel_path = os.path.relpath(root, source_dir)
            dest_root = os.path.join(dest_dir, rel_path) if rel_path != '.' else dest_dir
            
            # Create directories
            if not os.path.exists(dest_root):
                sync_actions.append(f"CREATE DIR: {dest_root}")
                if not dry_run:
                    os.makedirs(dest_root, exist_ok=True)
            
            # Copy/update files
            for filename in files:
                source_file = os.path.join(root, filename)
                dest_file = os.path.join(dest_root, filename)
                
                need_copy = False
                action = ""
                
                if not os.path.exists(dest_file):
                    need_copy = True
                    action = f"COPY: {filename}"
                else:
                    # Compare modification times
                    source_mtime = os.path.getmtime(source_file)
                    dest_mtime = os.path.getmtime(dest_file)
                    
                    if source_mtime > dest_mtime:
                        need_copy = True
                        action = f"UPDATE: {filename}"
                
                if need_copy:
                    sync_actions.append(action)
                    if not dry_run:
                        try:
                            shutil.copy2(source_file, dest_file)
                        except (PermissionError, FileNotFoundError):
                            sync_actions.append(f"ERROR: Could not copy {filename}")
        
        # Delete extra files if requested
        if delete_extra:
            for root, dirs, files in os.walk(dest_dir):
                rel_path = os.path.relpath(root, dest_dir)
                source_root = os.path.join(source_dir, rel_path) if rel_path != '.' else source_dir
                
                for filename in files:
                    source_file = os.path.join(source_root, filename)
                    dest_file = os.path.join(root, filename)
                    
                    if not os.path.exists(source_file):
                        sync_actions.append(f"DELETE: {filename}")
                        if not dry_run:
                            try:
                                os.remove(dest_file)
                            except (PermissionError, FileNotFoundError):
                                pass
        
        result = f"🔄 Directory Sync: {source_dir} → {dest_dir}\n"
        result += "=" * 50 + "\n\n"
        
        if sync_actions:
            result += f"{'Actions to perform' if dry_run else 'Actions performed'}: {len(sync_actions)}\n\n"
            
            # Group actions by type
            creates = [a for a in sync_actions if a.startswith('CREATE')]
            copies = [a for a in sync_actions if a.startswith('COPY')]
            updates = [a for a in sync_actions if a.startswith('UPDATE')]
            deletes = [a for a in sync_actions if a.startswith('DELETE')]
            errors = [a for a in sync_actions if a.startswith('ERROR')]
            
            if creates:
                result += f"📁 Directories to create: {len(creates)}\n"
            if copies:
                result += f"📄 Files to copy: {len(copies)}\n"
            if updates:
                result += f"🔄 Files to update: {len(updates)}\n"
            if deletes:
                result += f"🗑️ Files to delete: {len(deletes)}\n"
            if errors:
                result += f"❌ Errors encountered: {len(errors)}\n"
            
            result += "\n"
            
            # Show detailed actions (first 20)
            for action in sync_actions[:20]:
                result += f"   {action}\n"
            
            if len(sync_actions) > 20:
                result += f"   ... and {len(sync_actions) - 20} more actions\n"
            
            if dry_run:
                result += "\n⚠️  This was a DRY RUN. Set dry_run=False to perform actual sync."
        else:
            result += "✅ Directories are already in sync"
        
        return result
        
    except Exception as e:
        return f"❌ Sync error: {str(e)}"

# Export all functions for the main application
__all__ = [
    'organize_files_by_type', 'find_duplicate_files', 'remove_duplicate_files',
    'create_backup_archive', 'smart_file_search', 'batch_rename_files', 
    'analyze_directory_structure', 'sync_directories'
]