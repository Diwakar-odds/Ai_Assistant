"""
Clean legacy hardcoded developer paths (e.g. c:\\users\\hp\\...) from tests and scripts
"""

import os
import re

files_to_clean = [
    "scripts/create_dummy_video.py",
    "scripts/debug_moviepy.py",
    "scripts/analysis/analyze_video.py",
    "tests/test_creative_agent.py",
    "tests/test_expert_profiles.py",
    "tests/test_filmora.py",
    "tests/test_gui.py",
    "tests/test_orchestrator.py",
    "tests/test_training.py",
    "tests/test_video.py",
    "tests/test_visual_verification.py",
]

pattern = re.compile(
    r"^\s*sys\.path\.append\(r?[\"\']c:\\\\users\\\\hp\\\\appdata\\\\roaming\\\\python\\\\python39\\\\site-packages[\"\']\)\s*\n?",
    re.MULTILINE | re.IGNORECASE,
)

for f in files_to_clean:
    if os.path.exists(f):
        with open(f, "r", encoding="utf-8") as inf:
            content = inf.read()
        new_content = pattern.sub("", content)
        if f.endswith("analyze_video.py"):
            new_content = new_content.replace(
                r'captures_dir = r"c:\Users\hp\Videos\Captures"',
                'captures_dir = os.path.expandvars(r"%USERPROFILE%\\Videos\\Captures")'
            )
        if new_content != content:
            with open(f, "w", encoding="utf-8") as outf:
                outf.write(new_content)
            print("Cleaned:", f)
