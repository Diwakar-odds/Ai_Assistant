"""
Script to replace print statements with proper logging calls
Systematically updates the entire codebase for consistent logging
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple

class PrintToLoggerConverter:
    """Converts print statements to logger calls throughout the project"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.conversion_map = {
            # Error/warning patterns
            r'print\(f?"❌.*?\)': ('logger.error', 'ERROR'),
            r'print\(f?"⚠️.*?\)': ('logger.warning', 'WARNING'),
            r'print\(f?"ERROR.*?\)': ('logger.error', 'ERROR'),
            r'print\(f?"Warning.*?\)': ('logger.warning', 'WARNING'),
            r'print\(f?"FAILED.*?\)': ('logger.error', 'ERROR'),
            
            # Success patterns
            r'print\(f?"✅.*?\)': ('logger.info', 'INFO'),
            r'print\(f?"OK.*?\)': ('logger.info', 'INFO'),
            r'print\(f?"SUCCESS.*?\)': ('logger.info', 'INFO'),
            
            # Info patterns
            r'print\(f?"🔍.*?\)': ('logger.info', 'INFO'),
            r'print\(f?"📁.*?\)': ('logger.info', 'INFO'),
            r'print\(f?"🎯.*?\)': ('logger.info', 'INFO'),
            
            # Debug patterns (for testing/development files)
            r'print\(f?"Test.*?\)': ('logger.debug', 'DEBUG'),
            r'print\(f?"Debug.*?\)': ('logger.debug', 'DEBUG'),
        }
        
        self.files_updated = []
        self.total_conversions = 0
        
    def convert_project(self):
        """Convert all Python files in the project"""
        print("🔧 Converting print statements to logger calls...")
        
        for py_file in self.project_root.rglob('*.py'):
            if self._should_skip_file(py_file):
                continue
                
            if self._convert_file(py_file):
                self.files_updated.append(py_file)
        
        print(f"✅ Conversion complete!")
        print(f"   Files updated: {len(self.files_updated)}")
        print(f"   Total conversions: {self.total_conversions}")
        
        return self.files_updated
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            '.git', '__pycache__', '.venv', 'node_modules',
            'utils/logging_config.py',  # Skip our logging config
            'utils/advanced_logging.py',  # Skip our advanced logging
            'utils/update_logging.py'   # Skip logging utilities
        ]
        
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _convert_file(self, file_path: Path) -> bool:
        """Convert a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            conversions_in_file = 0
            
            # Check if file already uses centralized logging
            has_centralized_logging = 'from utils.logging_config import get_logger' in content
            
            # Add centralized logging if needed and file has print statements
            if not has_centralized_logging and 'print(' in content:
                # Determine log category based on file location
                if 'modules/' in str(file_path):
                    log_category = 'modules'
                elif 'backend' in file_path.name or 'web' in file_path.name:
                    log_category = 'backend'
                elif 'test' in file_path.name:
                    log_category = 'tests'
                else:
                    log_category = 'app'
                
                # Add imports after the last import line
                lines = content.split('\\n')
                import_lines = []
                other_lines = []
                found_imports = False
                
                for line in lines:
                    if line.startswith(('import ', 'from ')) and not found_imports:
                        import_lines.append(line)
                    elif line.startswith(('import ', 'from ')):
                        import_lines.append(line)
                    else:
                        if import_lines and not found_imports:
                            found_imports = True
                        other_lines.append(line)
                
                if import_lines:
                    # Insert our logging import
                    import_lines.extend([
                        '',
                        '# Setup centralized logging',
                        'from utils.logging_config import get_logger',
                        f'logger = get_logger(__name__, log_category="{log_category}")'
                    ])
                    content = '\\n'.join(import_lines + [''] + other_lines)
                else:
                    # No imports found, add at the top
                    content = ('# Setup centralized logging\\n'
                             'from utils.logging_config import get_logger\\n'
                             f'logger = get_logger(__name__, log_category="{log_category}")\\n'
                             '\\n' + content)
            
            # Convert print statements to logger calls
            for pattern, (logger_method, level) in self.conversion_map.items():
                matches = list(re.finditer(pattern, content, re.IGNORECASE | re.DOTALL))
                for match in matches:
                    old_print = match.group(0)
                    # Extract the content inside print()
                    print_content = old_print[old_print.find('(')+1:old_print.rfind(')')]
                    new_logger_call = f'{logger_method}({print_content})'
                    content = content.replace(old_print, new_logger_call, 1)
                    conversions_in_file += 1
            
            # Convert remaining generic print statements
            remaining_prints = list(re.finditer(r'print\\(([^)]+)\\)', content))
            for match in remaining_prints:
                old_print = match.group(0)
                print_content = match.group(1)
                
                # Determine appropriate log level based on content
                if any(keyword in print_content.lower() for keyword in ['error', 'fail', 'exception']):
                    new_call = f'logger.error({print_content})'
                elif any(keyword in print_content.lower() for keyword in ['warn', 'caution']):
                    new_call = f'logger.warning({print_content})'
                elif any(keyword in print_content.lower() for keyword in ['debug', 'test']):
                    new_call = f'logger.debug({print_content})'
                else:
                    new_call = f'logger.info({print_content})'
                
                content = content.replace(old_print, new_call, 1)
                conversions_in_file += 1
            
            # Write back if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.total_conversions += conversions_in_file
                print(f"   ✓ {file_path.relative_to(self.project_root)} ({conversions_in_file} conversions)")
                return True
            
            return False
            
        except Exception as e:
            print(f"   ✗ Error processing {file_path}: {e}")
            return False


def main():
    """Run the conversion"""
    converter = PrintToLoggerConverter('F:/bn/assitant')
    updated_files = converter.convert_project()
    
    if updated_files:
        print(f"\\n📋 Updated files:")
        for file_path in updated_files:
            print(f"   • {file_path.relative_to(Path('F:/bn/assitant'))}")
    
    print(f"\\n🎯 Next steps:")
    print(f"   1. Test the application to ensure logging works correctly")
    print(f"   2. Review log files in logs/ directory")
    print(f"   3. Adjust log levels if needed")

if __name__ == "__main__":
    main()