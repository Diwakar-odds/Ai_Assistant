import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
import shutil
from pathlib import Path

# Remove stray files in root
for p in Path('.').glob('*'):
    if p.is_file() and (p.name == 'hii.ts' or 'Projects' in p.name or 'd\uf03a' in p.name or 'README.md' in p.name and len(p.name) > 10):
        try:
            p.unlink()
            print("Removed stray file successfully")
        except Exception as e:
            print(f"Error removing file: {e}")

# Create experimental directory
ai_dir = Path('core_ai/src/ai_assistant/ai')
exp_dir = ai_dir / 'experimental'
exp_dir.mkdir(parents=True, exist_ok=True)

exp_files = [
    'federated_learning.py',
    'graph_neural_networks.py',
    'qlora_trainer.py',
    'causal_inference.py',
    'contrastive_learning.py'
]

for name in exp_files:
    src = ai_dir / name
    if src.exists():
        dst = exp_dir / name
        shutil.copy2(src, dst)
        print(f"Moved {name} to experimental/")
        with open(src, 'w', encoding='utf-8') as f:
            f.write(f'"""\nExperimental Module Proxy: {name}\nThis module has been relocated to ai_assistant.ai.experimental.{name[:-3]}\n"""\n\nfrom ai_assistant.ai.experimental.{name[:-3]} import *\n')

print("Experimental reorganization complete.")
