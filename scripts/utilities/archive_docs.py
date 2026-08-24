import os
import shutil
from pathlib import Path

docs_dir = Path("docs")
archive_dir = docs_dir / "archive"
archive_dir.mkdir(parents=True, exist_ok=True)

to_archive = [
    'VOICE_FIX_APPLIED.md', 'VOICE_FIX_COMPLETE.md', 'WEBSOCKET_FIX.md',
    'FIX_APPLIED.md', 'FIX_ALL_ISSUES.md', 'FULL_SESSION_KNOWLEDGE_DUMP.md',
    'ONLINE_ONLY_MODE_COMPLETE.md', 'SECURE_APP_INTEGRATION_COMPLETE.md',
    'PIN_AUTHENTICATION_COMPLETE.md', 'IMPLEMENTATION_COMPLETE.md',
    'IMPLEMENTATION_COMPLETE_SUMMARY.md', 'INTEGRATION_COMPLETE.md',
    'ACTIVATION_COMPLETE.md', 'CORRECTED_LEARNING_ASSESSMENT.md',
    'TEST_RESULTS.md', 'VERIFICATION_CHECKLIST.md', 'VOICE_TESTING_GUIDE_OLD.md',
    'REACT_MOBILE_SUMMARY.md', 'MOBILE_README.md', 'WINDOWS_APP_README.md',
    'PYTHON_311_UPGRADE.md', 'PROJECT_CONTEXT_HANDOVER.md', 'APP_DISCOVERY_ISSUES_ANALYSIS.md',
    'APP_DISCOVERY_LAZY_LOADING.md', 'OPTIMIZATION_SUMMARY.md', 'ONLINE_LEARNING_TEST_RESULTS.md'
]

moved = 0
for name in to_archive:
    src = docs_dir / name
    if src.exists():
        shutil.move(str(src), str(archive_dir / name))
        moved += 1

print(f"Archived {moved} files to docs/archive/")
