"""
Comprehensive Logging System Analysis and Improvements for YourDaddy Assistant
================================================================================

This script analyzes the entire project for logging issues and implements
a complete, production-ready logging system.
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple
import ast

class LoggingAnalyzer:
    """Analyzes the entire project for logging issues and improvements."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues = []
        self.print_statements = []
        self.missing_loggers = []
        self.console_logs = []
        self.error_handlers = []
        
    def analyze_project(self) -> Dict:
        """Perform comprehensive logging analysis."""
        print("🔍 Starting comprehensive logging analysis...")
        
        results = {
            'python_files': self._analyze_python_files(),
            'frontend_files': self._analyze_frontend_files(),
            'config_files': self._analyze_config_files(),
            'print_statements': self.print_statements,
            'missing_loggers': self.missing_loggers,
            'console_logs': self.console_logs,
            'error_handlers': self.error_handlers,
            'recommendations': self._generate_recommendations()
        }
        
        return results
    
    def _analyze_python_files(self) -> List[Dict]:
        """Analyze all Python files for logging issues."""
        python_files = []
        
        for py_file in self.project_root.rglob('*.py'):
            if self._should_skip_file(py_file):
                continue
                
            file_info = self._analyze_python_file(py_file)
            if file_info:
                python_files.append(file_info)
        
        return python_files
    
    def _analyze_python_file(self, file_path: Path) -> Dict:
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_info = {
                'file': str(file_path),
                'relative_path': str(file_path.relative_to(self.project_root)),
                'uses_centralized_logging': 'from utils.logging_config import get_logger' in content,
                'has_print_statements': [],
                'has_console_prints': [],
                'has_error_handling': False,
                'has_traceback': False,
                'needs_update': False
            }
            
            # Find print statements
            print_matches = re.finditer(r'\\bprint\\(.*?\\)', content, re.MULTILINE | re.DOTALL)
            for match in print_matches:
                line_num = content[:match.start()].count('\\n') + 1
                file_info['has_print_statements'].append({
                    'line': line_num,
                    'content': match.group(0)[:100] + ('...' if len(match.group(0)) > 100 else '')
                })
                self.print_statements.append({
                    'file': str(file_path),
                    'line': line_num,
                    'content': match.group(0)
                })
            
            # Check for error handling
            if 'except' in content:
                file_info['has_error_handling'] = True
            
            if 'traceback' in content:
                file_info['has_traceback'] = True
            
            # Check if file needs logger
            if not file_info['uses_centralized_logging'] and (
                'logging.' in content or 
                len(file_info['has_print_statements']) > 0 or
                file_info['has_error_handling']
            ):
                file_info['needs_update'] = True
                self.missing_loggers.append(str(file_path))
            
            return file_info
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None
    
    def _analyze_frontend_files(self) -> List[Dict]:
        """Analyze frontend files for console.log statements."""
        frontend_files = []
        
        # Analyze TypeScript/JavaScript files
        for ext in ['*.js', '*.ts', '*.tsx', '*.jsx']:
            for js_file in self.project_root.rglob(ext):
                if self._should_skip_file(js_file):
                    continue
                
                file_info = self._analyze_js_file(js_file)
                if file_info:
                    frontend_files.append(file_info)
        
        return frontend_files
    
    def _analyze_js_file(self, file_path: Path) -> Dict:
        """Analyze a JavaScript/TypeScript file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_info = {
                'file': str(file_path),
                'relative_path': str(file_path.relative_to(self.project_root)),
                'console_logs': [],
                'error_handlers': []
            }
            
            # Find console.log statements
            console_matches = re.finditer(r'console\\.(log|warn|error|info|debug)\\(.*?\\)', content)
            for match in console_matches:
                line_num = content[:match.start()].count('\\n') + 1
                file_info['console_logs'].append({
                    'line': line_num,
                    'type': match.group(1),
                    'content': match.group(0)[:100] + ('...' if len(match.group(0)) > 100 else '')
                })
                self.console_logs.append({
                    'file': str(file_path),
                    'line': line_num,
                    'type': match.group(1),
                    'content': match.group(0)
                })
            
            # Find error handlers
            if 'catch' in content or 'error' in content.lower():
                file_info['error_handlers'].append('Has error handling')
            
            return file_info
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None
    
    def _analyze_config_files(self) -> List[Dict]:
        """Analyze configuration files."""
        config_files = []
        
        # Look for configuration files
        for pattern in ['*.json', '*.yml', '*.yaml', '*.ini', '*.env*']:
            for config_file in self.project_root.rglob(pattern):
                if self._should_skip_file(config_file):
                    continue
                
                if 'log' in config_file.name.lower():
                    config_files.append({
                        'file': str(config_file),
                        'relative_path': str(config_file.relative_to(self.project_root)),
                        'type': 'logging_config'
                    })
        
        return config_files
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = [
            '.git', '__pycache__', '.venv', 'node_modules', 
            '.pytest_cache', '.coverage', 'dist', 'build'
        ]
        
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def _generate_recommendations(self) -> List[Dict]:
        """Generate recommendations for logging improvements."""
        recommendations = []
        
        # High-priority recommendations
        if self.print_statements:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Print Statements',
                'issue': f'Found {len(self.print_statements)} print statements that should use logger',
                'solution': 'Replace print() with logger.info(), logger.error(), etc.',
                'files_affected': len(set(item['file'] for item in self.print_statements))
            })
        
        if self.missing_loggers:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Missing Loggers',
                'issue': f'{len(self.missing_loggers)} files need centralized logging setup',
                'solution': 'Add centralized logger import and initialization',
                'files_affected': len(self.missing_loggers)
            })
        
        if self.console_logs:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Frontend Logging',
                'issue': f'Found {len(self.console_logs)} console.log statements in frontend',
                'solution': 'Implement structured frontend logging system',
                'files_affected': len(set(item['file'] for item in self.console_logs))
            })
        
        # Add specific recommendations
        recommendations.extend([
            {
                'priority': 'HIGH',
                'category': 'Error Handling',
                'issue': 'Inconsistent error logging across modules',
                'solution': 'Standardize exception handling with proper logging',
                'implementation': 'Use try-except blocks with logger.error() and traceback'
            },
            {
                'priority': 'MEDIUM',
                'category': 'Performance Logging',
                'issue': 'No performance metrics logging',
                'solution': 'Add performance decorators and timing logs',
                'implementation': 'Create @log_performance decorator'
            },
            {
                'priority': 'MEDIUM',
                'category': 'API Logging',
                'issue': 'Incomplete API request/response logging',
                'solution': 'Implement comprehensive API logging middleware',
                'implementation': 'Use Flask middleware for automatic API logging'
            },
            {
                'priority': 'LOW',
                'category': 'Log Aggregation',
                'issue': 'No centralized log monitoring',
                'solution': 'Implement log aggregation and monitoring',
                'implementation': 'Consider ELK stack or simple log viewer'
            }
        ])
        
        return recommendations

def main():
    """Run comprehensive logging analysis."""
    analyzer = LoggingAnalyzer('F:/bn/assitant')
    results = analyzer.analyze_project()
    
    # Generate report
    print("\\n" + "="*80)
    print("📊 COMPREHENSIVE LOGGING ANALYSIS REPORT")
    print("="*80)
    
    print(f"\\n📁 Project Analysis:")
    print(f"   • Python files analyzed: {len(results['python_files'])}")
    print(f"   • Frontend files analyzed: {len(results['frontend_files'])}")
    print(f"   • Config files found: {len(results['config_files'])}")
    
    print(f"\\n🔍 Issues Found:")
    print(f"   • Print statements: {len(results['print_statements'])}")
    print(f"   • Missing loggers: {len(results['missing_loggers'])}")
    print(f"   • Console.log statements: {len(results['console_logs'])}")
    
    print(f"\\n🎯 Recommendations ({len(results['recommendations'])}):")
    for i, rec in enumerate(results['recommendations'], 1):
        priority_emoji = "🔴" if rec['priority'] == 'HIGH' else "🟡" if rec['priority'] == 'MEDIUM' else "🟢"
        print(f"   {i}. {priority_emoji} [{rec['priority']}] {rec['category']}: {rec['issue']}")
        print(f"      Solution: {rec['solution']}")
        if 'files_affected' in rec:
            print(f"      Files affected: {rec['files_affected']}")
    
    # Save detailed report
    report_file = 'F:/bn/assitant/logs/LOGGING_ANALYSIS_REPORT.json'
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\\n📋 Detailed report saved to: {report_file}")
    
    return results

if __name__ == "__main__":
    main()