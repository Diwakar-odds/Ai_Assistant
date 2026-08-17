"""Quick dependency check"""
import sys

packages = {
    'numpy': 'NumPy',
    'sklearn': 'scikit-learn', 
    'scipy': 'SciPy',
    'networkx': 'NetworkX',
    'torch': 'PyTorch',
    'sentence_transformers': 'Sentence Transformers'
}

print("Checking dependencies...\n")
installed = []
missing = []

for package, name in packages.items():
    try:
        __import__(package)
        installed.append(f"✅ {name}")
        print(f"✅ {name}")
    except ImportError:
        missing.append(f"❌ {name}")
        print(f"❌ {name}")

print(f"\n{'='*50}")
print(f"Installed: {len(installed)}/{len(packages)}")
print(f"Missing: {len(missing)}/{len(packages)}")

if missing:
    print(f"\nTo install missing packages:")
    print(f"pip install " + " ".join([p.split()[1].lower().replace('-', '_') if len(p.split()) > 1 else '' for p in missing]))
