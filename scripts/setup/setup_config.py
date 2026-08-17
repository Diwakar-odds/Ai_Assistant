#!/usr/bin/env python3
"""
Auto-Config Setup Script
Automatically copies .example files to actual config files if they don't exist.
This ensures the application works on first run without exposing personal data in git.
"""

import os
import shutil
from pathlib import Path

# Define config file mappings (example -> actual)
CONFIG_FILES = {
    'config/discovered_apps.json': None,  # Auto-generated, don't copy
    'config/app_usage.db': None,  # Auto-generated, don't copy
    'config/user_settings.json': 'config/user_settings.json.example',
    'config/multimodal_config.json': 'config/multimodal_config.json.example',
    'ai_assistant/config/contacts.json': 'ai_assistant/config/contacts.json.example',
}

def setup_config_files():
    """Copy example config files to actual config files if they don't exist."""
    root_dir = Path(__file__).parent
    copied = []
    skipped = []
    
    for target_file, example_file in CONFIG_FILES.items():
        target_path = root_dir / target_file
        
        # Skip auto-generated files
        if example_file is None:
            continue
            
        # Skip if target already exists
        if target_path.exists():
            skipped.append(target_file)
            continue
        
        example_path = root_dir / example_file
        
        # Check if example file exists
        if not example_path.exists():
            print(f"⚠️  Warning: Example file not found: {example_file}")
            continue
        
        # Create parent directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy example to actual
        shutil.copy2(example_path, target_path)
        copied.append(target_file)
        print(f"✅ Created: {target_file}")
    
    # Summary
    if copied:
        print(f"\n✨ Initialized {len(copied)} config file(s)")
    if skipped:
        print(f"ℹ️  Skipped {len(skipped)} existing file(s)")
    
    if not copied and not skipped:
        print("⚠️  No config files needed initialization")
    
    return len(copied)

if __name__ == "__main__":
    print("🔧 Setting up configuration files...")
    setup_config_files()
