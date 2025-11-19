"""
Script to update all logging.info/error/warning calls to use logger instance
This helps migrate from global logging to centralized logging system
"""

import os
import re
from pathlib import Path

def update_logging_calls(file_path: str):
    """Update logging calls in a file"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if file already uses centralized logging
    if 'from utils.logging_config import get_logger' in content:
        print(f"✓ {file_path} already uses centralized logging")
        return False
    
    # Skip if no logging calls
    if not re.search(r'logging\.(info|error|warning|debug|critical)', content):
        return False
    
    original_content = content
    
    # Replace logging.info with logger.info, etc.
    content = re.sub(r'\blogging\.info\(', 'logger.info(', content)
    content = re.sub(r'\blogging\.error\(', 'logger.error(', content)
    content = re.sub(r'\blogging\.warning\(', 'logger.warning(', content)
    content = re.sub(r'\blogging\.debug\(', 'logger.debug(', content)
    content = re.sub(r'\blogging\.critical\(', 'logger.critical(', content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✓ Updated logging calls in {file_path}")
        return True
    
    return False

def main():
    """Update all module files"""
    modules_dir = Path('F:/bn/assitant/modules')
    
    print("Updating logging calls in module files...\n")
    
    updated_count = 0
    for py_file in modules_dir.glob('*.py'):
        if py_file.name == '__init__.py':
            continue
        
        if update_logging_calls(str(py_file)):
            updated_count += 1
    
    print(f"\n✅ Updated {updated_count} module files")

if __name__ == "__main__":
    main()
