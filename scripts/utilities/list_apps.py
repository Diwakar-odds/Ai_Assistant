# -*- coding: utf-8 -*-
"""List all discovered apps"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ai_assistant.modules.app_discovery import app_discovery

all_apps = app_discovery.get_all_apps()
print(f"\n[*] Found {len(all_apps)} apps on your system:\n")

# Sort and display
for i, (name, path) in enumerate(sorted(all_apps.items())[:30], 1):
    print(f"{i:2d}. {name}")
    
print(f"\n... and {len(all_apps) - 30} more apps")
print("\n[TIP] Your AI can open ANY of these apps!")
