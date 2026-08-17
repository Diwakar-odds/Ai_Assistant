#!/usr/bin/env python3
"""
Unicode Mojibake Fixer Utility.
Scans and repairs corrupted UTF-8 double-encoded sequences across all text files in the project.
"""

import os
import sys
from pathlib import Path

# Mapping of known mojibake corruptions to proper Unicode characters / emojis
MOJIBAKE_MAP = {
    "💾": "💾",
    "🔑": "🔑",
    "⚡": "⚡",
    "🔧": "🔧",
    "🔍": "🔍",
    "🎙️": "🎙️",
    "🌐": "🌐",
    "📡": "📡",
    "⚛️": "⚛️",
    "⚠️": "⚠️",
    "⚠️": "⚠️",
    "⚠️": "⚠️",
    "❌": "❌",
    "❌": "❌",
    "✅": "✅",
    "🚀": "🚀",
    "🤖": "🤖",
    "📌": "📌",
    "💡": "💡",
    "🧠": "🧠",
    "🤝": "🤝",
    "🏠": "🏠",
    "📋": "📋",
    "📜": "📜",
    "🔹": "🔹",
    "🔺": "🔺",
    "🔻": "🔻",
    "🌟": "🌟",
    "📊": "📊",
    "📚": "📚",
    "📄": "📄",
    "🌌": "🌌",
    "—": "—",
    "–": "–",
    "'": "'",
    """: '"',
    """: '"',
    "•": "•",
    "…": "…",
    "°": "°",
    "°": "°",
    "ÃƒÂ°Ã…Â¸"Ã‚Â¡": "📡",
    "📡": "📡",
}

EXTENSIONS = {'.py', '.ts', '.tsx', '.json', '.md', '.txt', '.html', '.css', '.ini'}
IGNORE_DIRS = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'dist', 'build', '.system_generated'}

def try_repair_mojibake(text: str) -> str:
    """Apply specific string replacements and automatic ftfy-style decoding."""
    # 1. First replace known explicit patterns
    for bad, good in MOJIBAKE_MAP.items():
        if bad in text:
            text = text.replace(bad, good)
            
    # 2. General encoding fix for remaining cases if detectable
    lines = text.split('\n')
    repaired_lines = []
    for line in lines:
        if 'Ã' in line or 'Â' in line:
            try:
                # Test if latin1 -> utf-8 recovers valid utf-8
                repaired = line.encode('latin1').decode('utf-8')
                repaired_lines.append(repaired)
            except (UnicodeEncodeError, UnicodeDecodeError):
                # Fallback: keep line with known map applied
                repaired_lines.append(line)
        else:
            repaired_lines.append(line)
            
    return '\n'.join(repaired_lines)

def process_file(file_path: Path) -> bool:
    """Check and fix encoding for a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        fixed_content = try_repair_mojibake(content)
        
        if fixed_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return False

def scan_and_fix(root_dir: Path):
    """Scan all files under root_dir and repair mojibake."""
    fixed_count = 0
    scanned_count = 0
    
    for path in root_dir.rglob('*'):
        if path.is_file() and path.suffix in EXTENSIONS:
            if any(part in IGNORE_DIRS for part in path.parts):
                continue
            scanned_count += 1
            if process_file(path):
                fixed_count += 1
                print(f"Fixed: {path.relative_to(root_dir)}")
                
    print(f"\nDone! Scanned {scanned_count} files, fixed {fixed_count} files.")

if __name__ == '__main__':
    project_root = Path(__file__).resolve().parent.parent.parent
    print(f"Scanning project for encoding issues: {project_root}")
    scan_and_fix(project_root)
