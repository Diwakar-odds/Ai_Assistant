"""
Unit tests for File Operations Module

Tests for:
- organize_files_by_type()
- find_duplicate_files()
- smart_file_search()
- batch_rename_files()
- create_backup_archive()
- analyze_directory_structure()
- sync_directories()
"""

import unittest
import os
import tempfile
import shutil
import time
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.file_ops import (
    organize_files_by_type,
    find_duplicate_files,
    remove_duplicate_files,
    create_backup_archive,
    smart_file_search,
    batch_rename_files,
    analyze_directory_structure,
    sync_directories
)


class TestFileOperations(unittest.TestCase):
    """Test suite for file operations module"""
    
    def setUp(self):
        """Set up test fixtures before each test"""
        # Create temporary test directory
        self.test_dir = tempfile.mkdtemp(prefix="file_ops_test_")
        self.addCleanup(self.cleanup_test_dir)
        
    def cleanup_test_dir(self):
        """Clean up test directory after test"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_file(self, filename, content="test content", subdir=None):
        """Helper to create a test file"""
        if subdir:
            dir_path = os.path.join(self.test_dir, subdir)
            os.makedirs(dir_path, exist_ok=True)
            file_path = os.path.join(dir_path, filename)
        else:
            file_path = os.path.join(self.test_dir, filename)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        return file_path
    
    # Test organize_files_by_type
    def test_organize_files_by_type_basic(self):
        """Test basic file organization by type"""
        # Create test files of different types
        self.create_test_file("photo1.jpg")
        self.create_test_file("document.pdf")
        self.create_test_file("music.mp3")
        self.create_test_file("video.mp4")
        self.create_test_file("code.py")
        
        # Organize files
        result = organize_files_by_type(self.test_dir, create_subfolders=True)
        
        # Verify results
        self.assertIn("Organized", result)
        self.assertIn("files", result)
        
        # Check folders were created
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Images")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Documents")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Audio")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Videos")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Code")))
        
        # Check files were moved
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Images", "photo1.jpg")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Documents", "document.pdf")))
    
    def test_organize_files_invalid_directory(self):
        """Test organize with non-existent directory"""
        result = organize_files_by_type("/nonexistent/path")
        self.assertIn("not found", result)
    
    def test_organize_files_with_duplicates(self):
        """Test organizing when destination already has files with same name"""
        # Create files
        self.create_test_file("photo.jpg")
        
        # Create Images folder and file with same name
        os.makedirs(os.path.join(self.test_dir, "Images"), exist_ok=True)
        self.create_test_file("photo.jpg", subdir="Images")
        
        # Organize should handle duplicate names
        result = organize_files_by_type(self.test_dir, create_subfolders=True)
        
        # Check that both files exist (one renamed)
        images_dir = os.path.join(self.test_dir, "Images")
        files = os.listdir(images_dir)
        self.assertTrue(any("photo" in f for f in files))
    
    # Test find_duplicate_files
    def test_find_duplicate_files_basic(self):
        """Test finding duplicate files"""
        # Create duplicate files
        content = "This is duplicate content"
        self.create_test_file("file1.txt", content)
        self.create_test_file("file2.txt", content)
        self.create_test_file("file3.txt", "Different content")
        
        result = find_duplicate_files(self.test_dir)
        
        self.assertIn("duplicate", result.lower())
        self.assertIn("file", result.lower())
    
    def test_find_duplicate_files_no_duplicates(self):
        """Test when no duplicates exist"""
        self.create_test_file("file1.txt", "Content 1")
        self.create_test_file("file2.txt", "Content 2")
        self.create_test_file("file3.txt", "Content 3")
        
        result = find_duplicate_files(self.test_dir)
        
        self.assertIn("No duplicate", result)
    
    def test_find_duplicate_files_with_subdirs(self):
        """Test finding duplicates in subdirectories"""
        content = "Duplicate content"
        self.create_test_file("file1.txt", content)
        self.create_test_file("file2.txt", content, subdir="subdir1")
        self.create_test_file("file3.txt", content, subdir="subdir2")
        
        result = find_duplicate_files(self.test_dir, include_subdirs=True)
        
        self.assertIn("duplicate", result.lower())
    
    def test_find_duplicate_files_invalid_directory(self):
        """Test find duplicates with invalid directory"""
        result = find_duplicate_files("/nonexistent/path")
        self.assertIn("not found", result)
    
    # Test remove_duplicate_files
    def test_remove_duplicate_files_dry_run(self):
        """Test removing duplicates in dry run mode"""
        content = "Duplicate"
        self.create_test_file("file1.txt", content)
        time.sleep(0.1)  # Ensure different timestamps
        self.create_test_file("file2.txt", content)
        
        result = remove_duplicate_files(self.test_dir, keep_oldest=True, dry_run=True)
        
        self.assertIn("Would remove", result)
        self.assertIn("DRY RUN", result)
        
        # Files should still exist
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "file1.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "file2.txt")))
    
    def test_remove_duplicate_files_actual(self):
        """Test actually removing duplicate files"""
        content = "Duplicate"
        self.create_test_file("file1.txt", content)
        time.sleep(0.1)
        self.create_test_file("file2.txt", content)
        
        result = remove_duplicate_files(self.test_dir, keep_oldest=True, dry_run=False)
        
        self.assertIn("Removing", result)
        
        # One file should be deleted
        files = os.listdir(self.test_dir)
        txt_files = [f for f in files if f.endswith('.txt')]
        self.assertEqual(len(txt_files), 1)
    
    # Test smart_file_search
    def test_smart_file_search_filename(self):
        """Test searching by filename"""
        self.create_test_file("report_2024.txt")
        self.create_test_file("report_2023.txt")
        self.create_test_file("document.txt")
        
        result = smart_file_search(self.test_dir, "report*", search_content=False)
        
        self.assertIn("Found", result)
        self.assertIn("report", result.lower())
    
    def test_smart_file_search_content(self):
        """Test searching file content"""
        self.create_test_file("file1.txt", "This file contains important data")
        self.create_test_file("file2.txt", "This is another file")
        self.create_test_file("file3.txt", "No match here")
        
        result = smart_file_search(self.test_dir, "important", search_content=True)
        
        self.assertIn("content matches", result.lower())
        self.assertIn("file1.txt", result)
    
    def test_smart_file_search_with_file_types(self):
        """Test searching with file type filter"""
        self.create_test_file("code.py", "def test(): pass")
        self.create_test_file("data.txt", "test data")
        self.create_test_file("doc.pdf")
        
        result = smart_file_search(self.test_dir, "test", search_content=True, file_types=['.py', '.txt'])
        
        # Should find .py and .txt but not .pdf
        self.assertIn("test", result.lower())
    
    def test_smart_file_search_invalid_directory(self):
        """Test search with invalid directory"""
        result = smart_file_search("/nonexistent/path", "test")
        self.assertIn("not found", result)
    
    # Test batch_rename_files
    def test_batch_rename_preview(self):
        """Test batch rename in preview mode"""
        self.create_test_file("old_1.txt")
        self.create_test_file("old_2.txt")
        self.create_test_file("old_3.txt")
        
        result = batch_rename_files(self.test_dir, "old_*.txt", "new_{n}", preview=True)
        
        self.assertIn("Preview", result)
        self.assertIn("old_1.txt", result)
        self.assertIn("new_001.txt", result)
        
        # Files should not be renamed
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "old_1.txt")))
    
    def test_batch_rename_actual(self):
        """Test actual batch renaming"""
        self.create_test_file("old_1.txt")
        self.create_test_file("old_2.txt")
        
        result = batch_rename_files(self.test_dir, "old_*.txt", "new_{n}", preview=False)
        
        self.assertIn("Successfully renamed", result)
        
        # Check files were renamed
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "new_001.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "new_002.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.test_dir, "old_1.txt")))
    
    def test_batch_rename_no_matches(self):
        """Test batch rename when no files match"""
        self.create_test_file("file.txt")
        
        result = batch_rename_files(self.test_dir, "nomatch*.txt", "new_{n}")
        
        self.assertIn("No files found", result)
    
    # Test create_backup_archive
    def test_create_backup_archive_zip(self):
        """Test creating zip backup"""
        self.create_test_file("file1.txt")
        self.create_test_file("file2.txt", subdir="subdir")
        
        result = create_backup_archive(self.test_dir, backup_name="test_backup", compression="zip")
        
        self.assertIn("Backup created", result)
        self.assertIn(".zip", result)
    
    def test_create_backup_archive_invalid_dir(self):
        """Test backup of non-existent directory"""
        result = create_backup_archive("/nonexistent/path")
        self.assertIn("not found", result)
    
    def test_create_backup_archive_unsupported_format(self):
        """Test unsupported compression format"""
        self.create_test_file("file.txt")
        
        result = create_backup_archive(self.test_dir, compression="rar")
        
        self.assertIn("Unsupported", result)
    
    # Test analyze_directory_structure
    def test_analyze_directory_structure_basic(self):
        """Test directory structure analysis"""
        # Create various files
        self.create_test_file("small.txt", "x")
        self.create_test_file("medium.txt", "x" * 1000)
        self.create_test_file("file.py")
        self.create_test_file("data.json")
        
        result = analyze_directory_structure(self.test_dir)
        
        self.assertIn("Directory Analysis", result)
        self.assertIn("Total Files:", result)
        self.assertIn("File Types:", result)
    
    def test_analyze_directory_structure_with_subdirs(self):
        """Test analysis with subdirectories"""
        self.create_test_file("file1.txt")
        self.create_test_file("file2.txt", subdir="sub1")
        self.create_test_file("file3.txt", subdir="sub2")
        
        result = analyze_directory_structure(self.test_dir, max_depth=2)
        
        self.assertIn("Total Directories:", result)
    
    def test_analyze_directory_structure_invalid_dir(self):
        """Test analysis of invalid directory"""
        result = analyze_directory_structure("/nonexistent/path")
        self.assertIn("not found", result)
    
    # Test sync_directories
    def test_sync_directories_basic(self):
        """Test basic directory synchronization"""
        # Create source files
        source_dir = os.path.join(self.test_dir, "source")
        dest_dir = os.path.join(self.test_dir, "dest")
        os.makedirs(source_dir)
        os.makedirs(dest_dir)
        
        self.create_test_file("file1.txt", subdir="source")
        self.create_test_file("file2.txt", subdir="source")
        
        result = sync_directories(source_dir, dest_dir, dry_run=True)
        
        self.assertIn("Directory Sync", result)
        self.assertIn("Actions to perform", result)
    
    def test_sync_directories_with_updates(self):
        """Test sync with file updates"""
        source_dir = os.path.join(self.test_dir, "source")
        dest_dir = os.path.join(self.test_dir, "dest")
        os.makedirs(source_dir)
        os.makedirs(dest_dir)
        
        # Create file in source
        source_file = self.create_test_file("file.txt", "new content", subdir="source")
        
        # Create older file in dest
        dest_file = os.path.join(dest_dir, "file.txt")
        with open(dest_file, 'w') as f:
            f.write("old content")
        
        # Make source file newer
        time.sleep(0.1)
        os.utime(source_file, None)
        
        result = sync_directories(source_dir, dest_dir, dry_run=True)
        
        self.assertIn("UPDATE", result)
    
    def test_sync_directories_invalid_source(self):
        """Test sync with invalid source directory"""
        dest_dir = os.path.join(self.test_dir, "dest")
        
        result = sync_directories("/nonexistent/source", dest_dir)
        
        self.assertIn("not found", result)
    
    def test_sync_directories_actual_sync(self):
        """Test actual synchronization"""
        source_dir = os.path.join(self.test_dir, "source")
        dest_dir = os.path.join(self.test_dir, "dest")
        os.makedirs(source_dir)
        
        self.create_test_file("file.txt", subdir="source")
        
        result = sync_directories(source_dir, dest_dir, dry_run=False)
        
        # File should be copied to destination
        self.assertTrue(os.path.exists(os.path.join(dest_dir, "file.txt")))


class TestFileOperationsSafety(unittest.TestCase):
    """Test suite for safety and edge cases"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp(prefix="file_ops_safety_")
        self.addCleanup(self.cleanup_test_dir)
    
    def cleanup_test_dir(self):
        """Clean up test directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_organize_empty_directory(self):
        """Test organizing an empty directory"""
        result = organize_files_by_type(self.test_dir)
        self.assertIn("0", result)
    
    def test_find_duplicates_single_file(self):
        """Test duplicate detection with single file"""
        with open(os.path.join(self.test_dir, "single.txt"), 'w') as f:
            f.write("content")
        
        result = find_duplicate_files(self.test_dir)
        self.assertIn("No duplicate", result)
    
    def test_search_empty_directory(self):
        """Test searching in empty directory"""
        result = smart_file_search(self.test_dir, "test")
        self.assertIn("No files found", result)
    
    def test_batch_rename_with_conflicts(self):
        """Test batch rename with naming conflicts"""
        # Create files that might conflict when renamed
        with open(os.path.join(self.test_dir, "file_1.txt"), 'w') as f:
            f.write("1")
        with open(os.path.join(self.test_dir, "file_2.txt"), 'w') as f:
            f.write("2")
        with open(os.path.join(self.test_dir, "new_001.txt"), 'w') as f:
            f.write("existing")
        
        result = batch_rename_files(self.test_dir, "file_*.txt", "new_{n}", preview=False)
        
        # Should handle conflict by adding suffix
        self.assertIn("renamed", result.lower())


def suite():
    """Create test suite"""
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestFileOperations))
    test_suite.addTest(unittest.makeSuite(TestFileOperationsSafety))
    return test_suite


if __name__ == '__main__':
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
