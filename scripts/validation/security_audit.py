#!/usr/bin/env python3
"""
Security Audit Script
Checks for potential privacy and security issues in the repository.
Run this before committing to ensure no sensitive data is tracked.
"""

import subprocess
import sys
from pathlib import Path

# Patterns that should never be in tracked files
SENSITIVE_PATTERNS = [
    r'api_key.*=.*["\'][^"\']{20,}',  # API keys
    r'password.*=.*["\'][^"\']{8,}',  # Passwords
    r'secret.*=.*["\'][^"\']{16,}',   # Secrets
    r'token.*=.*["\'][^"\']{20,}',    # Tokens
    r'\+\d{10,}',                      # Phone numbers
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Email addresses (in data files)
]

# Files that should NOT be tracked
FORBIDDEN_FILES = [
    'config/discovered_apps.json',
    'config/app_usage.db',
    'config/user_settings.json',
    'config/multimodal_config.json',
    'ai_assistant/config/contacts.json',
    'config/app_integration.env',
]

# Directories that should NOT be tracked
FORBIDDEN_DIRS = [
    'data/',
    'user_data/',
    'logs/',
    'offline_cache/',
]

def run_command(cmd):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1

def check_tracked_files():
    """Check if any forbidden files are tracked."""
    print("🔍 Checking for tracked sensitive files...")
    
    output, code = run_command("git ls-files")
    if code != 0:
        print("❌ Error running git command")
        return False
    
    tracked_files = output.split('\n')
    issues = []
    
    # Check forbidden files
    for forbidden in FORBIDDEN_FILES:
        if forbidden in tracked_files:
            issues.append(f"❌ CRITICAL: {forbidden} is tracked in git!")
    
    # Check forbidden directories
    for forbidden_dir in FORBIDDEN_DIRS:
        matching = [f for f in tracked_files if f.startswith(forbidden_dir)]
        if matching:
            issues.append(f"❌ CRITICAL: {len(matching)} file(s) in {forbidden_dir} are tracked!")
            for f in matching[:5]:  # Show first 5
                issues.append(f"   - {f}")
    
    if issues:
        print("\n".join(issues))
        return False
    
    print("✅ No forbidden files tracked")
    return True

def check_sensitive_content():
    """Check for sensitive content in tracked files."""
    print("\n🔍 Checking for sensitive patterns in tracked code...")
    
    issues = []
    
    # Check Python files for hardcoded secrets
    output, code = run_command('git ls-files "*.py" | head -50')
    if code == 0 and output:
        py_files = output.split('\n')
        for pattern in SENSITIVE_PATTERNS[:4]:  # Check first 4 patterns (not emails/phones in code)
            cmd = f'git ls-files -z "*.py" | xargs -0 grep -E "{pattern}" 2>/dev/null | head -5'
            matches, _ = run_command(cmd)
            if matches:
                issues.append(f"⚠️  Warning: Potential secret pattern found in Python files")
                issues.append(f"   Pattern: {pattern}")
    
    if issues:
        print("\n".join(issues))
        print("\n⚠️  Review these matches manually - they may be false positives")
        return False
    
    print("✅ No obvious sensitive patterns found")
    return True

def check_large_files():
    """Check for large files that might be databases or models."""
    print("\n🔍 Checking for large files...")
    
    output, code = run_command("git ls-files | xargs -I {} stat -c '%s %n' {} 2>/dev/null | sort -rn | head -10")
    if code != 0:
        # Try Windows equivalent
        output, code = run_command("git ls-files")
        if code == 0:
            print("✅ File size check skipped (Windows)")
            return True
    
    if output:
        lines = output.split('\n')
        large_files = []
        for line in lines:
            if line.strip():
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    size, name = parts
                    size_mb = int(size) / (1024 * 1024)
                    if size_mb > 10:  # Files larger than 10MB
                        large_files.append(f"   {name}: {size_mb:.1f} MB")
        
        if large_files:
            print("⚠️  Large files found in repository:")
            print("\n".join(large_files))
            print("   Consider using Git LFS for large files")
            return False
    
    print("✅ No large files detected")
    return True

def check_gitignore():
    """Verify .gitignore contains all necessary entries."""
    print("\n🔍 Checking .gitignore completeness...")
    
    gitignore_path = Path('.gitignore')
    if not gitignore_path.exists():
        print("❌ CRITICAL: .gitignore file not found!")
        return False
    
    content = gitignore_path.read_text()
    
    required_entries = [
        '*.db',
        '*.env',
        'config/discovered_apps.json',
        'config/user_settings.json',
        'data/',
        'user_data/',
        'logs/',
    ]
    
    missing = []
    for entry in required_entries:
        if entry not in content:
            missing.append(entry)
    
    if missing:
        print("❌ Missing entries in .gitignore:")
        for entry in missing:
            print(f"   - {entry}")
        return False
    
    print("✅ .gitignore properly configured")
    return True

def check_example_files():
    """Verify all sensitive configs have .example templates."""
    print("\n🔍 Checking for .example template files...")
    
    required_examples = [
        ('config/user_settings.json', 'config/user_settings.json.example'),
        ('config/multimodal_config.json', 'config/multimodal_config.json.example'),
        ('ai_assistant/config/contacts.json', 'ai_assistant/config/contacts.json.example'),
    ]
    
    missing = []
    for actual, example in required_examples:
        example_path = Path(example)
        if not example_path.exists():
            missing.append(example)
    
    if missing:
        print("❌ Missing .example files:")
        for example in missing:
            print(f"   - {example}")
        return False
    
    print("✅ All .example template files present")
    return True

def main():
    """Run all security checks."""
    print("=" * 60)
    print("🔒 Security Audit - AI Assistant Repository")
    print("=" * 60 + "\n")
    
    checks = [
        check_gitignore(),
        check_example_files(),
        check_tracked_files(),
        check_sensitive_content(),
        check_large_files(),
    ]
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✅ All security checks passed!")
        print("=" * 60)
        return 0
    else:
        print("❌ Some security checks failed!")
        print("=" * 60)
        print("\n⚠️  Please fix the issues above before committing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
