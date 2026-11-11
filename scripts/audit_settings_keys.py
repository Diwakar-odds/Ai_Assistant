import sys
import json
import re
from pathlib import Path

# Enforce UTF-8
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

backend_dir = Path('backend')
core_ai_dir = Path('core_ai')

py_files = list(backend_dir.rglob('*.py')) + list(core_ai_dir.rglob('*.py'))

code_corpus = {}
for p in py_files:
    try:
        code_corpus[str(p)] = p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        pass

sys.path.insert(0, str(Path('backend').resolve()))
from settings_manager import DEFAULTS, _SETTINGS_FILE

print("=" * 80)
print("  🔍 AUDITING SETTINGS KEYS: FRONTEND / DEFAULTS vs BACKEND CODEBASE")
print("=" * 80)

def search_key_in_code(key):
    pattern = re.compile(rf"['\"]{re.escape(key)}['\"]")
    matches = []
    for path, code in code_corpus.items():
        if 'settings_manager.py' in path or 'test' in path or 'mock' in path:
            continue
        if pattern.search(code):
            matches.append(path)
    return matches

def audit_dict(d, prefix=""):
    items = []
    for k, v in d.items():
        full_path = f"{prefix}.{k}" if prefix else k
        matches = search_key_in_code(k)
        items.append((full_path, k, len(matches), matches))
        if isinstance(v, dict):
            items.extend(audit_dict(v, full_path))
    return items

audit_results = audit_dict(DEFAULTS)

used_count = 0
unused_count = 0

for full_path, key, count, matches in audit_results:
    if count > 0:
        used_count += 1
        sample = Path(matches[0]).name
        if len(matches) > 1:
            sample += f" (+{len(matches)-1} more)"
        print(f"  ✅ {full_path:<40} -> FOUND in {count} files (e.g. {sample})")
    else:
        unused_count += 1
        print(f"  ⚠️  {full_path:<40} -> NOT referenced by name in backend/core_ai!")

print("\n" + "=" * 80)
print(f"  Summary: {used_count} settings actively referenced | {unused_count} potentially unreferenced")
print("=" * 80)
