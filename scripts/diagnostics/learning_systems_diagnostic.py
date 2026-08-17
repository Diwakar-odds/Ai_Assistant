#!/usr/bin/env python3
"""
Learning Systems Diagnostic Tool
Checks health and status of all 27+ learning systems

Usage:
    python scripts/diagnostics/learning_systems_diagnostic.py
"""

import sys
import os
from pathlib import Path
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import importlib.util

# Add project to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class LearningSystemsDiagnostic:
    """Comprehensive diagnostic for all learning systems"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'systems': {},
            'dependencies': {},
            'databases': {},
            'imports': {},
            'integration': {},
            'overall_health': 0
        }
        
    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text:^80}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")
    
    def print_status(self, name: str, status: str, details: str = ""):
        """Print status line with color coding"""
        if status == "OK":
            color = Colors.GREEN
            symbol = "✅"
        elif status == "WARNING":
            color = Colors.YELLOW
            symbol = "⚠️"
        elif status == "ERROR":
            color = Colors.RED
            symbol = "❌"
        else:
            color = Colors.BLUE
            symbol = "ℹ️"
        
        print(f"{symbol} {color}{name:.<50}{Colors.RESET} {status:>10}")
        if details:
            print(f"   {Colors.CYAN}└─ {details}{Colors.RESET}")
    
    def check_dependencies(self):
        """Check critical dependencies"""
        self.print_header("CHECKING DEPENDENCIES")
        
        dependencies = {
            'numpy': 'Core ML operations',
            'scikit-learn': 'ML algorithms',
            'torch': 'Neural networks',
            'tensorflow': 'Deep learning',
            'sentence-transformers': 'Embeddings',
            'transformers': 'HuggingFace models',
            'faiss-cpu': 'Vector search (RAG)',
            'chromadb': 'Vector database',
            'networkx': 'Graph operations',
            'google-generativeai': 'Gemini API',
            'openai': 'OpenAI API'
        }
        
        for pkg, purpose in dependencies.items():
            try:
                spec = importlib.util.find_spec(pkg.replace('-', '_'))
                if spec is not None:
                    self.print_status(pkg, "OK", purpose)
                    self.results['dependencies'][pkg] = {'status': 'installed', 'purpose': purpose}
                else:
                    self.print_status(pkg, "ERROR", f"Missing - needed for {purpose}")
                    self.results['dependencies'][pkg] = {'status': 'missing', 'purpose': purpose}
            except (ImportError, ValueError):
                self.print_status(pkg, "ERROR", f"Missing - needed for {purpose}")
                self.results['dependencies'][pkg] = {'status': 'missing', 'purpose': purpose}
    
    def check_learning_system_imports(self):
        """Check if learning systems can be imported"""
        self.print_header("CHECKING LEARNING SYSTEM IMPORTS")
        
        systems = {
            'advanced_feedback_learning': 'ai_assistant.ai.advanced_feedback_learning',
            'enhanced_learning': 'ai_assistant.ai.enhanced_learning',
            'graph_neural_networks': 'ai_assistant.ai.graph_neural_networks',
            'historical_rag': 'ai_assistant.ai.historical_rag',
            'intelligent_responder': 'ai_assistant.ai.intelligent_responder',
            'active_learning': 'ai_assistant.ai.active_learning',
            'smart_command_prediction': 'ai_assistant.ai.smart_command_prediction',
            'context_aware_response': 'ai_assistant.ai.context_aware_response',
            'adaptive_voice': 'ai_assistant.ai.adaptive_voice',
            'workflow_recommender': 'ai_assistant.ai.workflow_recommender',
            'anomaly_detection': 'ai_assistant.ai.anomaly_detection',
            'behavior_clustering': 'ai_assistant.ai.behavior_clustering',
            'conversation_clustering': 'ai_assistant.ai.conversation_clustering',
            'command_sequences': 'ai_assistant.ai.command_sequences',
            'command_predictor': 'ai_assistant.ai.command_predictor',
            'llm_bandit': 'ai_assistant.ai.llm_bandit',
            'causal_inference': 'ai_assistant.ai.causal_inference',
            'query_cache': 'ai_assistant.ai.query_cache',
            'explainability': 'ai_assistant.ai.explainability',
            'meta_learning': 'ai_assistant.ai.meta_learning',
            'federated_learning': 'ai_assistant.ai.federated_learning',
            'self_supervised_learning': 'ai_assistant.ai.self_supervised_learning',
            'full_rl_system': 'ai_assistant.ai.full_rl_system',
            'model_compression': 'ai_assistant.ai.model_compression',
            'multimodal_learning': 'ai_assistant.ai.multimodal_learning',
            'domain_embeddings': 'ai_assistant.ai.domain_embeddings',
            'network_aware_llm': 'ai_assistant.ai.network_aware_llm'
        }
        
        for name, module_path in systems.items():
            try:
                module = importlib.import_module(module_path)
                self.print_status(name, "OK", f"Module: {module_path}")
                self.results['systems'][name] = {'status': 'importable', 'module': module_path}
            except ImportError as e:
                self.print_status(name, "ERROR", f"Import failed: {str(e)[:60]}")
                self.results['systems'][name] = {'status': 'import_error', 'error': str(e)}
            except Exception as e:
                self.print_status(name, "WARNING", f"Other error: {str(e)[:60]}")
                self.results['systems'][name] = {'status': 'other_error', 'error': str(e)}
    
    def check_databases(self):
        """Check learning system databases"""
        self.print_header("CHECKING LEARNING DATABASES")
        
        db_paths = {
            'memory.db': 'Main conversation memory',
            'enhanced_learning.db': 'Enhanced learning system',
            'data/historical_rag.db': 'Historical RAG',
            'data/active_learning.db': 'Active learning',
            'data/feedback.db': 'User feedback',
            'data/knowledge_graph.db': 'Knowledge graph',
            'data/behavior_clustering.db': 'Behavior patterns',
            'data/conversation_clustering.db': 'Conversation clusters',
            'data/query_cache.db': 'Query cache'
        }
        
        for db_file, purpose in db_paths.items():
            db_path = project_root / db_file
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    # Get table count
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    table_count = len(tables)
                    
                    # Get total row count across all tables
                    total_rows = 0
                    for table in tables:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                            total_rows += cursor.fetchone()[0]
                        except:
                            pass
                    
                    conn.close()
                    
                    status = "OK" if total_rows > 0 else "WARNING"
                    details = f"{table_count} tables, {total_rows} total rows - {purpose}"
                    self.print_status(db_file, status, details)
                    
                    self.results['databases'][db_file] = {
                        'status': 'exists',
                        'tables': table_count,
                        'rows': total_rows,
                        'purpose': purpose
                    }
                except Exception as e:
                    self.print_status(db_file, "ERROR", f"Database error: {str(e)[:50]}")
                    self.results['databases'][db_file] = {'status': 'error', 'error': str(e)}
            else:
                self.print_status(db_file, "WARNING", f"Not found - {purpose}")
                self.results['databases'][db_file] = {'status': 'not_found', 'purpose': purpose}
    
    def check_integration_status(self):
        """Check integration in main assistant"""
        self.print_header("CHECKING ASSISTANT INTEGRATION")
        
        assistant_path = project_root / 'ai_assistant' / 'core' / 'assistant.py'
        
        if not assistant_path.exists():
            self.print_status("assistant.py", "ERROR", "Main assistant file not found")
            return
        
        with open(assistant_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for learning router import
        checks = {
            'Learning Router Import': 'from auto_learning_router import LearningDataRouter' in content or 
                                     'from ai_assistant.integrations.learning_integration import LearningAssistant' in content,
            'Learning Router Usage': 'learning_router.route_conversation' in content,
            'Historical RAG Import': 'historical_rag' in content.lower(),
            'Enhanced Learning Import': 'EnhancedLearning' in content,
            'Feedback Collection': 'feedback' in content.lower(),
            'Memory Integration': 'save_to_memory' in content,
            'Conversational AI': 'conversational_ai' in content
        }
        
        for check_name, exists in checks.items():
            if exists:
                self.print_status(check_name, "OK", "Found in assistant.py")
                self.results['integration'][check_name] = True
            else:
                self.print_status(check_name, "WARNING", "Not found in assistant.py")
                self.results['integration'][check_name] = False
    
    def check_learning_router_location(self):
        """Check learning router file location"""
        self.print_header("CHECKING LEARNING ROUTER LOCATION")
        
        possible_paths = [
            'scripts/learning/auto_learning_router.py',
            'ai_assistant/integrations/learning_integration.py',
            'auto_learning_router.py'
        ]
        
        for path_str in possible_paths:
            path = project_root / path_str
            if path.exists():
                self.print_status(path_str, "OK", "File exists")
                
                # Check if it's in the right location for import
                if 'scripts' in path_str:
                    self.print_status("Import Path", "WARNING", 
                                    "Router in scripts/ - should be in ai_assistant/")
                else:
                    self.print_status("Import Path", "OK", "Proper location for import")
            else:
                self.print_status(path_str, "WARNING", "Not found")
    
    def check_data_availability(self):
        """Check if learning systems have training data"""
        self.print_header("CHECKING TRAINING DATA AVAILABILITY")
        
        # Check memory database
        memory_db = project_root / 'memory.db'
        if memory_db.exists():
            try:
                conn = sqlite3.connect(str(memory_db))
                cursor = conn.cursor()
                
                # Check memory table
                cursor.execute("SELECT COUNT(*) FROM memory")
                memory_count = cursor.fetchone()[0]
                
                # Check enhanced_memory if exists
                try:
                    cursor.execute("SELECT COUNT(*) FROM enhanced_memory")
                    enhanced_count = cursor.fetchone()[0]
                except:
                    enhanced_count = 0
                
                conn.close()
                
                total = memory_count + enhanced_count
                if total > 100:
                    self.print_status("Conversation History", "OK", 
                                    f"{total} conversations available for learning")
                elif total > 0:
                    self.print_status("Conversation History", "WARNING", 
                                    f"Only {total} conversations - need more data")
                else:
                    self.print_status("Conversation History", "WARNING", 
                                    "No conversation data for training")
            except Exception as e:
                self.print_status("Conversation History", "ERROR", str(e))
        else:
            self.print_status("Conversation History", "WARNING", "No memory database found")
    
    def generate_health_score(self):
        """Calculate overall health score"""
        scores = {
            'dependencies_ok': 0,
            'systems_ok': 0,
            'databases_ok': 0,
            'integration_ok': 0
        }
        
        # Count OK dependencies
        for dep, info in self.results['dependencies'].items():
            if info['status'] == 'installed':
                scores['dependencies_ok'] += 1
        
        # Count importable systems
        for sys, info in self.results['systems'].items():
            if info['status'] == 'importable':
                scores['systems_ok'] += 1
        
        # Count existing databases with data
        for db, info in self.results['databases'].items():
            if info['status'] == 'exists' and info.get('rows', 0) > 0:
                scores['databases_ok'] += 1
        
        # Count active integrations
        for integration, active in self.results['integration'].items():
            if active:
                scores['integration_ok'] += 1
        
        total_deps = len(self.results['dependencies'])
        total_systems = len(self.results['systems'])
        total_dbs = len(self.results['databases'])
        total_integrations = len(self.results['integration'])
        
        # Weighted score
        health_score = (
            (scores['dependencies_ok'] / max(total_deps, 1)) * 30 +
            (scores['systems_ok'] / max(total_systems, 1)) * 40 +
            (scores['databases_ok'] / max(total_dbs, 1)) * 15 +
            (scores['integration_ok'] / max(total_integrations, 1)) * 15
        )
        
        return health_score, scores
    
    def print_summary(self):
        """Print diagnostic summary"""
        self.print_header("DIAGNOSTIC SUMMARY")
        
        health_score, scores = self.generate_health_score()
        self.results['overall_health'] = health_score
        self.results['score_breakdown'] = scores
        
        # Overall health
        if health_score >= 80:
            color = Colors.GREEN
            status = "EXCELLENT"
        elif health_score >= 60:
            color = Colors.YELLOW
            status = "GOOD"
        elif health_score >= 40:
            color = Colors.YELLOW
            status = "NEEDS ATTENTION"
        else:
            color = Colors.RED
            status = "CRITICAL"
        
        print(f"\n{color}{Colors.BOLD}Overall Health Score: {health_score:.1f}/100 ({status}){Colors.RESET}\n")
        
        # Breakdown
        print(f"📦 Dependencies: {scores['dependencies_ok']}/{len(self.results['dependencies'])} installed")
        print(f"🧠 Learning Systems: {scores['systems_ok']}/{len(self.results['systems'])} importable")
        print(f"💾 Databases: {scores['databases_ok']}/{len(self.results['databases'])} with data")
        print(f"🔗 Integrations: {scores['integration_ok']}/{len(self.results['integration'])} active")
        
        # Critical issues
        print(f"\n{Colors.BOLD}Critical Issues:{Colors.RESET}")
        issues = []
        
        for dep, info in self.results['dependencies'].items():
            if info['status'] == 'missing' and dep in ['faiss-cpu', 'chromadb', 'sentence-transformers']:
                issues.append(f"❌ Missing critical dependency: {dep}")
        
        for sys, info in self.results['systems'].items():
            if info['status'] != 'importable' and sys in ['historical_rag', 'advanced_feedback_learning']:
                issues.append(f"❌ Cannot import critical system: {sys}")
        
        if not self.results['integration'].get('Learning Router Import', False):
            issues.append("❌ Learning router not properly imported")
        
        if issues:
            for issue in issues:
                print(f"  {issue}")
        else:
            print(f"  {Colors.GREEN}✅ No critical issues found{Colors.RESET}")
        
        # Recommendations
        print(f"\n{Colors.BOLD}Recommendations:{Colors.RESET}")
        
        # Check missing dependencies
        missing_deps = [dep for dep, info in self.results['dependencies'].items() 
                       if info['status'] == 'missing']
        if missing_deps:
            print(f"  1. Install missing dependencies:")
            print(f"     pip install {' '.join(missing_deps)}")
        
        # Check import path
        if 'Learning Router Import' in self.results['integration'] and not self.results['integration']['Learning Router Import']:
            print(f"  2. Fix learning router import path in assistant.py")
        
        # Check data
        has_data = any(db.get('rows', 0) > 0 for db in self.results['databases'].values())
        if not has_data:
            print(f"  3. Populate databases with conversation data")
        
        print()
    
    def save_report(self):
        """Save diagnostic report to JSON"""
        report_dir = project_root / 'logs' / 'diagnostics'
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = report_dir / f'learning_diagnostic_{timestamp}.json'
        
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"{Colors.GREEN}📄 Detailed report saved: {report_path}{Colors.RESET}\n")
        
        return report_path
    
    def run(self):
        """Run full diagnostic"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}")
        print("╔═══════════════════════════════════════════════════════════════════════════════╗")
        print("║                   LEARNING SYSTEMS DIAGNOSTIC TOOL                            ║")
        print("║                        YourDaddy AI Assistant                                 ║")
        print("╚═══════════════════════════════════════════════════════════════════════════════╝")
        print(f"{Colors.RESET}")
        
        self.check_dependencies()
        self.check_learning_system_imports()
        self.check_databases()
        self.check_integration_status()
        self.check_learning_router_location()
        self.check_data_availability()
        self.print_summary()
        
        report_path = self.save_report()
        
        return self.results


if __name__ == "__main__":
    diagnostic = LearningSystemsDiagnostic()
    results = diagnostic.run()
    
    # Exit with appropriate code
    health_score = results['overall_health']
    if health_score >= 80:
        sys.exit(0)  # Success
    elif health_score >= 40:
        sys.exit(1)  # Warning
    else:
        sys.exit(2)  # Critical
