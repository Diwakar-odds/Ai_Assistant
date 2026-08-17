#!/usr/bin/env python3
"""
Comprehensive Project Dependency Analysis Tool
Analyzes missing dependencies, conflicts, and functional features
"""

import os
import sys
import ast
import re
import subprocess
import importlib
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

class DependencyAnalyzer:
    """Comprehensive dependency analysis for the AI Assistant project"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.requirements = {}
        self.imports_found = set()
        self.missing_dependencies = set()
        self.version_conflicts = []
        self.unused_dependencies = set()
        self.critical_features = {}
        self.optional_features = {}
        
        # Define known package mappings (import name -> pip package name)
        self.package_mappings = {
            'cv2': 'opencv-python',
            'PIL': 'Pillow',
            'sklearn': 'scikit-learn',
            'speech_recognition': 'SpeechRecognition',
            'pyttsx3': 'pyttsx3',
            'tkinter': 'built-in',  # Built into Python
            'customtkinter': 'customtkinter',
            'flask': 'Flask',
            'flask_socketio': 'Flask-SocketIO',
            'flask_cors': 'Flask-CORS',
            'flask_jwt_extended': 'Flask-JWT-Extended',
            'flask_limiter': 'Flask-Limiter',
            'socketio': 'python-socketio',
            'requests': 'requests',
            'numpy': 'numpy',
            'pandas': 'pandas',
            'matplotlib': 'matplotlib',
            'torch': 'torch',
            'tensorflow': 'tensorflow',
            'transformers': 'transformers',
            'openai': 'openai',
            'anthropic': 'anthropic',
            'langchain': 'langchain',
            'chromadb': 'chromadb',
            'faiss': 'faiss-cpu',
            'whisper': 'openai-whisper',
            'pyaudio': 'PyAudio',
            'sounddevice': 'sounddevice',
            'edge_tts': 'edge-tts',
            'gtts': 'gTTS',
            'pygame': 'pygame',
            'psutil': 'psutil',
            'win32gui': 'pywin32',
            'win32api': 'pywin32',
            'win32con': 'pywin32',
            'win32com': 'pywin32',
            'win32file': 'pywin32',
            'win32process': 'pywin32',
            'pywintypes': 'pywin32',
            'selenium': 'selenium',
            'beautifulsoup4': 'beautifulsoup4',
            'bs4': 'beautifulsoup4',
            'lxml': 'lxml',
            'pytesseract': 'pytesseract',
            'vosk': 'vosk',
            'spacy': 'spacy',
            'nltk': 'nltk',
            'dateutil': 'python-dateutil',
            'jwt': 'PyJWT',
            'yaml': 'PyYAML',
            'toml': 'toml',
            'dotenv': 'python-dotenv',
            'schedule': 'schedule',
            'streamlit': 'streamlit',
            'gradio': 'gradio',
            'dash': 'dash',
            'fastapi': 'fastapi',
            'uvicorn': 'uvicorn',
            'gunicorn': 'gunicorn',
            'celery': 'celery',
            'redis': 'redis',
            'sqlalchemy': 'SQLAlchemy',
            'pymongo': 'pymongo',
            'docker': 'docker',
            'kubernetes': 'kubernetes',
            'google': 'google-api-python-client',
            'googleapiclient': 'google-api-python-client',
            'azure': 'azure',
            'boto3': 'boto3',
            'paramiko': 'paramiko',
            'fabric': 'fabric',
            'watchdog': 'watchdog',
            'py4j': 'py4j'
        }
        
    def load_requirements_file(self, file_path: str = None) -> Dict[str, str]:
        """Load requirements from requirements.txt"""
        if file_path is None:
            file_path = self.project_root / "requirements.txt"
        
        requirements = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Parse package==version or package>=version etc.
                        match = re.match(r'^([a-zA-Z0-9_.-]+)([><=!~]+.*)?$', line)
                        if match:
                            package = match.group(1).lower()
                            version = match.group(2) if match.group(2) else ""
                            requirements[package] = version
        except FileNotFoundError:
            print(f"❌ Requirements file not found: {file_path}")
        
        return requirements
    
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the project"""
        python_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Skip common non-source directories
            dirs[:] = [d for d in dirs if d not in {
                '__pycache__', '.git', '.venv', 'venv', 'env', 
                'node_modules', '.pytest_cache', 'build', 'dist'
            }]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def extract_imports_from_file(self, file_path: Path) -> Set[str]:
        """Extract all imports from a Python file"""
        imports = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse AST to extract imports
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.add(node.module.split('.')[0])
            except SyntaxError:
                # Fallback to regex if AST parsing fails
                import_patterns = [
                    r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                    r'^from\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+import'
                ]
                
                for line in content.split('\n'):
                    line = line.strip()
                    for pattern in import_patterns:
                        match = re.match(pattern, line)
                        if match:
                            imports.add(match.group(1))
                            
        except Exception as e:
            print(f"⚠️ Error reading {file_path}: {e}")
        
        return imports
    
    def analyze_imports(self) -> Set[str]:
        """Analyze all imports in the project"""
        all_imports = set()
        python_files = self.find_python_files()
        
        print(f"🔍 Analyzing {len(python_files)} Python files...")
        
        for file_path in python_files:
            file_imports = self.extract_imports_from_file(file_path)
            all_imports.update(file_imports)
        
        # Filter out built-in modules
        stdlib_modules = {
            'os', 'sys', 'time', 'datetime', 'json', 'logging', 'threading',
            'subprocess', 'pathlib', 'collections', 'itertools', 'functools',
            'typing', 'abc', 'copy', 'pickle', 'tempfile', 'shutil', 'glob',
            'random', 'math', 'statistics', 'decimal', 'fractions', 'uuid',
            'hashlib', 'hmac', 'secrets', 'base64', 'binascii', 're', 'string',
            'textwrap', 'unicodedata', 'codecs', 'io', 'struct', 'difflib',
            'pprint', 'reprlib', 'enum', 'graphlib', 'types', 'weakref',
            'gc', 'inspect', 'importlib', 'warnings', 'contextlib', 'atexit',
            'traceback', 'socket', 'ssl', 'asyncio', 'concurrent', 'queue',
            'multiprocessing', 'signal', 'platform', 'ctypes', 'array',
            'sqlite3', 'csv', 'configparser', 'argparse', 'getopt', 'readline',
            'http', 'urllib', 'email', 'mimetypes', 'ftplib', 'imaplib',
            'poplib', 'smtplib', 'telnetlib', 'xmlrpc', 'html', 'xml',
            # Additional built-in modules
            'ast', 'unittest', 'cProfile', 'pstats', 'dataclasses', 'fnmatch',
            'shlex', 'tarfile', 'zipfile', 'wave', 'webbrowser', 'winreg',
            'tkinter', 'line_profiler', 'memory_profiler', 'inotify'
        }
        
        # Remove built-in modules and local modules
        external_imports = set()
        for imp in all_imports:
            if imp not in stdlib_modules and not imp.startswith('test_'):
                # Check if it's not a local module
                if not (self.project_root / f"{imp}.py").exists() and \
                   not (self.project_root / imp).is_dir() and \
                   not (self.project_root / "modules" / f"{imp}.py").exists():
                    external_imports.add(imp)
        
        return external_imports
    
    def check_installed_packages(self) -> Dict[str, str]:
        """Check what packages are currently installed"""
        installed = {}
        
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=freeze'], 
                                  capture_output=True, text=True, check=True)
            
            for line in result.stdout.strip().split('\n'):
                if '==' in line:
                    package, version = line.split('==', 1)
                    installed[package.lower()] = version
                    
        except subprocess.CalledProcessError as e:
            print(f"❌ Error checking installed packages: {e}")
        
        return installed
    
    def find_missing_dependencies(self, imports: Set[str], installed: Dict[str, str]) -> Set[str]:
        """Find dependencies that are imported but not installed"""
        missing = set()
        
        for imp in imports:
            # Get the pip package name
            package_name = self.package_mappings.get(imp, imp)
            
            # Skip built-in packages
            if package_name == 'built-in':
                continue
            
            # Check if installed
            if package_name.lower() not in installed:
                # Also check the original import name
                if imp.lower() not in installed:
                    missing.add(imp)
        
        return missing
    
    def analyze_feature_coverage(self) -> Dict[str, Dict]:
        """Analyze which features are available based on dependencies"""
        features = {
            'voice_recognition': {
                'packages': ['speech_recognition', 'pyaudio', 'whisper', 'vosk'],
                'status': 'unknown',
                'missing': [],
                'description': 'Voice input and speech recognition'
            },
            'text_to_speech': {
                'packages': ['pyttsx3', 'edge_tts', 'gtts'],
                'status': 'unknown',
                'missing': [],
                'description': 'Text-to-speech synthesis'
            },
            'gui_interface': {
                'packages': ['tkinter', 'customtkinter'],
                'status': 'unknown',
                'missing': [],
                'description': 'Graphical user interface'
            },
            'web_interface': {
                'packages': ['flask', 'flask_socketio', 'flask_cors'],
                'status': 'unknown',
                'missing': [],
                'description': 'Web-based interface'
            },
            'llm_integration': {
                'packages': ['openai', 'anthropic', 'transformers', 'langchain'],
                'status': 'unknown',
                'missing': [],
                'description': 'Large Language Model integration'
            },
            'computer_vision': {
                'packages': ['cv2', 'PIL', 'pytesseract'],
                'status': 'unknown',
                'missing': [],
                'description': 'Image and video processing'
            },
            'automation': {
                'packages': ['selenium', 'pyautogui', 'win32gui'],
                'status': 'unknown',
                'missing': [],
                'description': 'Task automation and control'
            },
            'data_processing': {
                'packages': ['numpy', 'pandas', 'matplotlib'],
                'status': 'unknown',
                'missing': [],
                'description': 'Data analysis and visualization'
            },
            'machine_learning': {
                'packages': ['sklearn', 'torch', 'tensorflow'],
                'status': 'unknown',
                'missing': [],
                'description': 'Machine learning capabilities'
            },
            'audio_processing': {
                'packages': ['sounddevice', 'pygame', 'librosa'],
                'status': 'unknown',
                'missing': [],
                'description': 'Audio processing and playback'
            },
            'web_scraping': {
                'packages': ['requests', 'beautifulsoup4', 'selenium'],
                'status': 'unknown',
                'missing': [],
                'description': 'Web scraping and data extraction'
            },
            'database_support': {
                'packages': ['sqlalchemy', 'pymongo', 'redis'],
                'status': 'unknown',
                'missing': [],
                'description': 'Database connectivity'
            },
            'cloud_integration': {
                'packages': ['boto3', 'azure', 'google'],
                'status': 'unknown',
                'missing': [],
                'description': 'Cloud services integration'
            }
        }
        
        installed = self.check_installed_packages()
        
        for feature_name, feature_info in features.items():
            available_packages = []
            missing_packages = []
            
            for package in feature_info['packages']:
                pip_package = self.package_mappings.get(package, package)
                if pip_package == 'built-in' or pip_package.lower() in installed:
                    available_packages.append(package)
                else:
                    missing_packages.append(package)
            
            feature_info['missing'] = missing_packages
            feature_info['available'] = available_packages
            
            if len(available_packages) == len(feature_info['packages']):
                feature_info['status'] = 'complete'
            elif available_packages:
                feature_info['status'] = 'partial'
            else:
                feature_info['status'] = 'missing'
        
        return features
    
    def check_version_conflicts(self, requirements: Dict[str, str], installed: Dict[str, str]) -> List[Dict]:
        """Check for version conflicts between requirements and installed packages"""
        conflicts = []
        
        for package, req_version in requirements.items():
            if package in installed:
                installed_version = installed[package]
                if req_version and not self._version_satisfies(installed_version, req_version):
                    conflicts.append({
                        'package': package,
                        'required': req_version,
                        'installed': installed_version,
                        'severity': 'warning'
                    })
        
        return conflicts
    
    def _version_satisfies(self, installed: str, required: str) -> bool:
        """Check if installed version satisfies requirement"""
        # Simple version checking - in practice you'd want to use packaging.specifiers
        try:
            from packaging import version, specifiers
            spec = specifiers.SpecifierSet(required)
            return version.parse(installed) in spec
        except ImportError:
            # Fallback to simple string comparison if packaging not available
            if required.startswith('=='):
                return installed == required[2:]
            elif required.startswith('>='):
                # Very basic comparison - not accurate for all cases
                return True
            else:
                return True
    
    def generate_report(self) -> Dict:
        """Generate comprehensive dependency analysis report"""
        print("🔍 Starting comprehensive dependency analysis...")
        
        # Load requirements
        self.requirements = self.load_requirements_file()
        print(f"📋 Found {len(self.requirements)} packages in requirements.txt")
        
        # Analyze imports
        self.imports_found = self.analyze_imports()
        print(f"📦 Found {len(self.imports_found)} external imports")
        
        # Check installed packages
        installed = self.check_installed_packages()
        print(f"✅ Found {len(installed)} installed packages")
        
        # Find missing dependencies
        self.missing_dependencies = self.find_missing_dependencies(self.imports_found, installed)
        
        # Check version conflicts
        self.version_conflicts = self.check_version_conflicts(self.requirements, installed)
        
        # Analyze feature coverage
        self.critical_features = self.analyze_feature_coverage()
        
        # Find unused dependencies
        required_packages = set(self.requirements.keys())
        mapped_imports = {self.package_mappings.get(imp, imp).lower() for imp in self.imports_found}
        self.unused_dependencies = required_packages - mapped_imports
        
        return {
            'summary': {
                'total_requirements': len(self.requirements),
                'total_imports': len(self.imports_found),
                'missing_dependencies': len(self.missing_dependencies),
                'version_conflicts': len(self.version_conflicts),
                'unused_dependencies': len(self.unused_dependencies)
            },
            'missing_dependencies': sorted(list(self.missing_dependencies)),
            'version_conflicts': self.version_conflicts,
            'unused_dependencies': sorted(list(self.unused_dependencies)),
            'feature_analysis': self.critical_features,
            'imports_found': sorted(list(self.imports_found)),
            'requirements': self.requirements,
            'installed_packages': installed
        }
    
    def print_report(self, report: Dict):
        """Print formatted analysis report"""
        print("\n" + "="*80)
        print("🤖 AI ASSISTANT - DEPENDENCY ANALYSIS REPORT")
        print("="*80)
        
        summary = report['summary']
        print(f"\n📊 SUMMARY:")
        print(f"   Total Requirements: {summary['total_requirements']}")
        print(f"   External Imports:   {summary['total_imports']}")
        print(f"   Missing Deps:       {summary['missing_dependencies']}")
        print(f"   Version Conflicts:  {summary['version_conflicts']}")
        print(f"   Unused Deps:        {summary['unused_dependencies']}")
        
        # Missing Dependencies
        if report['missing_dependencies']:
            print(f"\n❌ MISSING DEPENDENCIES ({len(report['missing_dependencies'])}):")
            for dep in report['missing_dependencies']:
                pip_package = self.package_mappings.get(dep, dep)
                print(f"   • {dep} → pip install {pip_package}")
        else:
            print(f"\n✅ NO MISSING DEPENDENCIES")
        
        # Version Conflicts
        if report['version_conflicts']:
            print(f"\n⚠️ VERSION CONFLICTS ({len(report['version_conflicts'])}):")
            for conflict in report['version_conflicts']:
                print(f"   • {conflict['package']}: required{conflict['required']} vs installed={conflict['installed']}")
        else:
            print(f"\n✅ NO VERSION CONFLICTS")
        
        # Feature Analysis
        print(f"\n🎯 FEATURE ANALYSIS:")
        complete_features = []
        partial_features = []
        missing_features = []
        
        for feature_name, feature_info in report['feature_analysis'].items():
            status = feature_info['status']
            if status == 'complete':
                complete_features.append(feature_name)
            elif status == 'partial':
                partial_features.append((feature_name, feature_info))
            else:
                missing_features.append((feature_name, feature_info))
        
        print(f"   ✅ Complete: {len(complete_features)}")
        for feature in complete_features:
            print(f"      • {feature}")
        
        if partial_features:
            print(f"   ⚠️ Partial: {len(partial_features)}")
            for feature_name, feature_info in partial_features:
                missing = ', '.join(feature_info['missing'])
                print(f"      • {feature_name} (missing: {missing})")
        
        if missing_features:
            print(f"   ❌ Missing: {len(missing_features)}")
            for feature_name, feature_info in missing_features:
                missing = ', '.join(feature_info['missing'])
                print(f"      • {feature_name} (needs: {missing})")
        
        # Unused Dependencies
        if report['unused_dependencies']:
            print(f"\n🗑️ POTENTIALLY UNUSED DEPENDENCIES ({len(report['unused_dependencies'])}):")
            for dep in report['unused_dependencies']:
                print(f"   • {dep}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        
        if report['missing_dependencies']:
            print(f"   1. Install missing dependencies:")
            print(f"      pip install " + " ".join([
                self.package_mappings.get(dep, dep) for dep in report['missing_dependencies']
            ]))
        
        if missing_features:
            print(f"   2. Consider installing optional features:")
            for feature_name, feature_info in missing_features:
                packages = [self.package_mappings.get(pkg, pkg) for pkg in feature_info['missing']]
                print(f"      # {feature_info['description']}")
                print(f"      pip install " + " ".join(packages))
        
        if report['unused_dependencies']:
            print(f"   3. Consider removing unused dependencies from requirements.txt")
        
        print("="*80)

def main():
    """Main function to run dependency analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze project dependencies')
    parser.add_argument('--project', '-p', help='Project root directory', default='.')
    parser.add_argument('--output', '-o', help='Output JSON file')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode')
    
    args = parser.parse_args()
    
    analyzer = DependencyAnalyzer(args.project)
    report = analyzer.generate_report()
    
    if not args.quiet:
        analyzer.print_report(report)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n💾 Report saved to: {args.output}")

if __name__ == "__main__":
    main()