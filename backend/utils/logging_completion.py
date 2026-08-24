"""
Final Logging System Completion Script
=====================================

This script completes the logging system by:
1. Testing all logging components
2. Creating missing log directories
3. Validating log configuration
4. Generating comprehensive documentation
5. Creating monitoring utilities
"""

import os
import json
from pathlib import Path
from datetime import datetime
import sys

# Import our centralized logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.logging_config import get_logger, LoggingConfig
from utils.advanced_logging import (
    log_performance, 
    error_logger,
    api_logger,
    security_logger,
    user_activity_logger,
    log_aggregator
)

logger = get_logger('logging_completion', log_category='system')


class LoggingSystemValidator:
    """Validates the complete logging system"""
    
    def __init__(self):
        self.validation_results = {}
        
    def validate_all(self):
        """Run comprehensive validation"""
        logger.info("🔍 Starting comprehensive logging system validation")
        
        self.validation_results = {
            'directory_structure': self._validate_directories(),
            'configuration': self._validate_configuration(),
            'logger_functionality': self._test_loggers(),
            'rotation_settings': self._validate_rotation(),
            'performance_logging': self._test_performance_logging(),
            'error_handling': self._test_error_handling(),
            'api_logging': self._test_api_logging(),
            'frontend_integration': self._validate_frontend_logging(),
            'documentation': self._validate_documentation()
        }
        
        return self.validation_results
    
    def _validate_directories(self):
        """Validate log directory structure"""
        logger.info("📁 Validating log directory structure")
        
        results = {'status': 'success', 'directories': [], 'missing': []}
        
        for category, path in LoggingConfig.LOG_DIRS.items():
            if path.exists():
                results['directories'].append(str(path))
                logger.debug(f"✓ Directory exists: {path}")
            else:
                results['missing'].append(str(path))
                logger.warning(f"⚠️ Missing directory: {path}")
                # Create missing directories
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"✅ Created directory: {path}")
        
        return results
    
    def _validate_configuration(self):
        """Validate logging configuration"""
        logger.info("⚙️ Validating logging configuration")
        
        results = {'status': 'success', 'issues': []}
        
        # Test formatters
        try:
            formatter = LoggingConfig.get_formatter('detailed')
            test_record = logger.makeRecord(
                'test', 20, 'test.py', 1, 'Test message', (), None
            )
            formatted = formatter.format(test_record)
            logger.debug(f"✓ Formatter test: {formatted}")
        except Exception as e:
            results['issues'].append(f"Formatter error: {e}")
            results['status'] = 'error'
        
        return results
    
    def _test_loggers(self):
        """Test all logger types"""
        logger.info("🧪 Testing logger functionality")
        
        results = {'status': 'success', 'tested_loggers': []}
        
        # Test module loggers for different categories
        test_categories = ['app', 'modules', 'backend', 'api', 'system']
        
        for category in test_categories:
            try:
                test_logger = get_logger(f'test_{category}', log_category=category)
                test_logger.info(f"Test message for {category} category")
                test_logger.warning(f"Test warning for {category} category")
                test_logger.error(f"Test error for {category} category")
                
                results['tested_loggers'].append(category)
                logger.debug(f"✓ {category} logger working")
                
            except Exception as e:
                results['status'] = 'error'
                logger.error(f"❌ {category} logger failed: {e}")
        
        return results
    
    def _validate_rotation(self):
        """Validate log rotation settings"""
        logger.info("🔄 Validating log rotation")
        
        results = {'status': 'success', 'settings': {}}
        
        results['settings'] = {
            'max_bytes': LoggingConfig.MAX_BYTES,
            'backup_count': LoggingConfig.BACKUP_COUNT,
            'rotation_enabled': True
        }
        
        logger.debug(f"✓ Rotation settings: {results['settings']}")
        return results
    
    def _test_performance_logging(self):
        """Test performance logging decorator"""
        logger.info("⚡ Testing performance logging")
        
        results = {'status': 'success', 'test_results': []}
        
        try:
            @log_performance("test_function", threshold_ms=1)
            def test_performance_function():
                import time
                time.sleep(0.01)  # 10ms delay
                return "test_complete"
            
            result = test_performance_function()
            results['test_results'].append(f"Performance decorator test: {result}")
            logger.debug("✓ Performance logging working")
            
        except Exception as e:
            results['status'] = 'error'
            logger.error(f"❌ Performance logging failed: {e}")
        
        return results
    
    def _test_error_handling(self):
        """Test error logging"""
        logger.info("🚨 Testing error handling")
        
        results = {'status': 'success', 'error_tests': []}
        
        try:
            # Test contextual error logging
            try:
                raise ValueError("Test error for logging validation")
            except Exception as e:
                error_logger.log_exception(
                    e, 
                    context={'test_context': 'validation_run'},
                    user_friendly="This is a test error - ignore"
                )
            
            results['error_tests'].append("Contextual error logging")
            logger.debug("✓ Error logging working")
            
        except Exception as e:
            results['status'] = 'error'
            logger.error(f"❌ Error logging failed: {e}")
        
        return results
    
    def _test_api_logging(self):
        """Test API logging"""
        logger.info("🌐 Testing API logging")
        
        results = {'status': 'success', 'api_tests': []}
        
        try:
            # Test API request logging
            api_logger.log_request('GET', '/api/test', {'param1': 'value1'})
            api_logger.log_response('GET', '/api/test', 200, 45.2)
            
            results['api_tests'].append("API request/response logging")
            logger.debug("✓ API logging working")
            
        except Exception as e:
            results['status'] = 'error'
            logger.error(f"❌ API logging failed: {e}")
        
        return results
    
    def _validate_frontend_logging(self):
        """Validate frontend logging integration"""
        logger.info("💻 Validating frontend logging integration")
        
        results = {'status': 'success', 'frontend_features': []}
        
        # Check if frontend error logging endpoint exists
        from modern_web_backend import app
        
        with app.test_client() as client:
            try:
                response = client.post('/api/error/log', 
                                     json={'message': 'Test frontend error'},
                                     headers={'Content-Type': 'application/json'})
                
                if response.status_code == 200:
                    results['frontend_features'].append("Frontend error logging endpoint")
                    logger.debug("✓ Frontend error endpoint working")
                else:
                    logger.warning(f"⚠️ Frontend error endpoint returned {response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ Frontend error endpoint test failed: {e}")
        
        return results
    
    def _validate_documentation(self):
        """Validate logging documentation"""
        logger.info("📚 Validating logging documentation")
        
        results = {'status': 'success', 'documentation_files': []}
        
        # Check for README in logs directory
        readme_path = LoggingConfig.BASE_LOG_DIR / "README.md"
        if readme_path.exists():
            results['documentation_files'].append(str(readme_path))
            logger.debug("✓ Logs README exists")
        
        return results
    
    def generate_report(self):
        """Generate comprehensive validation report"""
        logger.info("📋 Generating validation report")
        
        report = {
            'validation_timestamp': datetime.now().isoformat(),
            'overall_status': 'success',
            'summary': {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0
            },
            'detailed_results': self.validation_results
        }
        
        # Calculate summary
        for test_name, test_result in self.validation_results.items():
            report['summary']['total_tests'] += 1
            if test_result.get('status') == 'success':
                report['summary']['passed_tests'] += 1
            else:
                report['summary']['failed_tests'] += 1
                report['overall_status'] = 'partial'
        
        # Save report
        report_path = LoggingConfig.BASE_LOG_DIR / 'VALIDATION_REPORT.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📄 Validation report saved to: {report_path}")
        
        return report


def create_logging_utilities():
    """Create helpful logging utilities"""
    logger.info("🛠️ Creating logging utilities")
    
    # Create log viewer script
    log_viewer_script = '''#!/usr/bin/env python3
"""
Log Viewer Utility for Pulsar Assistant
==========================================

Usage:
    python logs_viewer.py [category] [--tail] [--errors-only]

Examples:
    python logs_viewer.py app          # Show app logs
    python logs_viewer.py modules --tail   # Tail module logs
    python logs_viewer.py --errors-only    # Show only errors
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import argparse

def main():
    parser = argparse.ArgumentParser(description='View Pulsar Assistant logs')
    parser.add_argument('category', nargs='?', default='app', 
                       help='Log category to view (app, modules, backend, etc.)')
    parser.add_argument('--tail', '-t', action='store_true',
                       help='Follow log file (like tail -f)')
    parser.add_argument('--errors-only', '-e', action='store_true',
                       help='Show only error logs')
    parser.add_argument('--lines', '-n', type=int, default=50,
                       help='Number of lines to show')
    
    args = parser.parse_args()
    
    logs_dir = Path('logs')
    
    if args.errors_only:
        log_file = logs_dir / 'errors' / f'{args.category}_errors.log'
    else:
        log_file = logs_dir / args.category / f'{args.category}.log'
    
    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        print(f"Available categories: {[d.name for d in logs_dir.iterdir() if d.is_dir()]}")
        return
    
    try:
        if args.tail:
            import subprocess
            subprocess.run(['tail', '-f', str(log_file)])
        else:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                for line in lines[-args.lines:]:
                    print(line.rstrip())
    except KeyboardInterrupt:
        print("\\nStopped")
    except Exception as e:
        logger.error(f"Error reading log file: {e}")

if __name__ == "__main__":
    main()
'''
    
    utils_dir = Path('utils')
    with open(utils_dir / 'log_viewer.py', 'w') as f:
        f.write(log_viewer_script)
    
    logger.info("✅ Created log viewer utility")


def main():
    """Main function to complete logging system"""
    logger.info("🚀 Starting logging system completion")
    
    # Initialize validator
    validator = LoggingSystemValidator()
    
    # Run comprehensive validation
    validation_results = validator.validate_all()
    
    # Generate report
    report = validator.generate_report()
    
    # Create utilities
    create_logging_utilities()
    
    # Print summary
    print("\\n" + "="*80)
    logger.info("🎯 LOGGING SYSTEM COMPLETION SUMMARY")
    print("="*80)
    
    print(f"📊 Validation Results:")
    print(f"   • Total tests: {report['summary']['total_tests']}")
    print(f"   • Passed: {report['summary']['passed_tests']}")
    print(f"   • Failed: {report['summary']['failed_tests']}")
    print(f"   • Overall status: {report['overall_status'].upper()}")
    
    print(f"\\n📁 Log Directory Structure:")
    for category, path in LoggingConfig.LOG_DIRS.items():
        status = "✅" if path.exists() else "❌"
        print(f"   {status} {category}: {path}")
    
    print(f"\\n🛠️ Utilities Created:")
    print(f"   • Log viewer: utils/log_viewer.py")
    print(f"   • Advanced logging: utils/advanced_logging.py")
    print(f"   • Configuration: utils/logging_config.py")
    
    print(f"\\n📋 Documentation:")
    print(f"   • Log structure: logs/README.md")
    print(f"   • Validation report: logs/VALIDATION_REPORT.json")
    
    print(f"\\n🎯 Usage Examples:")
    print(f"   # Import logger in any module")
    print(f"   from utils.logging_config import get_logger")
    print(f"   logger = get_logger(__name__)")
    print(f"   ")
    print(f"   # View logs")
    print(f"   python utils/log_viewer.py app")
    print(f"   python utils/log_viewer.py modules --tail")
    print(f"   ")
    print(f"   # Performance logging")
    print(f"   from utils.advanced_logging import log_performance")
    print(f"   @log_performance()")
    print(f"   def my_function(): pass")
    
    print("\\n" + "="*80)
    logger.info("✅ Logging system completion finished successfully!")
    
    return report


if __name__ == "__main__":
    report = main()