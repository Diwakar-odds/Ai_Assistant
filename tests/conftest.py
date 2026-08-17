"""
Pytest configuration and shared fixtures for testing.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "core_ai" / "src"))
sys.path.insert(0, str(project_root / "backend"))

@pytest.fixture
def assistant():
    """Create ModernAssistant instance for testing"""
    from ai_assistant.core.assistant import ModernAssistant
    return ModernAssistant()

@pytest.fixture
def app_client():
    """Create Flask test client"""
    import os
    os.environ['TESTING'] = 'true'
    os.environ['ADMIN_PASSWORD'] = 'changeme123'
    os.environ['ADMIN_PIN'] = '123456'
    os.environ['GEMINI_API_KEY'] = 'dummy_key_for_testing'
    
    # Import after setting env var
    from modern_web_backend import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def auth_headers(app_client):
    """Get authentication headers for testing"""
    # Login and get token
    response = app_client.post('/api/auth/login', json={'pin': '1234'})
    if response.status_code == 200:
        data = response.get_json()
        token = data.get('access_token')
        return {'Authorization': f'Bearer {token}'}
    return {}

# --- Pipeline Testing Framework Setup ---

import json
import os
from datetime import datetime

# Global store for test results
pipeline_results = []

def pytest_addoption(parser):
    parser.addoption(
        "--pipeline-report", action="store_true", default=False, help="Generate pipeline test report"
    )

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()
    
    # We only care about the actual test run (not setup/teardown)
    if rep.when == "call" and hasattr(item, "callspec"):
        # This is a parametrized test
        if "cmd_data" in item.callspec.params:
            cmd_data = item.callspec.params["cmd_data"]
            result = {
                "test_name": item.name,
                "command": cmd_data["text"],
                "category": cmd_data["category"],
                "language": cmd_data["language"],
                "status": "passed" if rep.passed else "failed" if rep.failed else "skipped",
                "error": str(rep.longrepr) if rep.failed else None
            }
            pipeline_results.append(result)

def pytest_sessionfinish(session, exitstatus):
    if session.config.getoption("--pipeline-report") or True:
        report_dir = os.path.join(os.path.dirname(__file__), "output")
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, "pipeline_test_report.json")
        
        # Calculate summary statistics
        summary = {
            "total": len(pipeline_results),
            "passed": sum(1 for r in pipeline_results if r["status"] == "passed"),
            "failed": sum(1 for r in pipeline_results if r["status"] == "failed"),
            "timestamp": datetime.now().isoformat(),
            "by_category": {},
            "by_language": {}
        }
        
        for r in pipeline_results:
            cat = r["category"]
            lang = r["language"]
            
            if cat not in summary["by_category"]:
                summary["by_category"][cat] = {"total": 0, "passed": 0}
            summary["by_category"][cat]["total"] += 1
            if r["status"] == "passed":
                summary["by_category"][cat]["passed"] += 1
                
            if lang not in summary["by_language"]:
                summary["by_language"][lang] = {"total": 0, "passed": 0}
            summary["by_language"][lang]["total"] += 1
            if r["status"] == "passed":
                summary["by_language"][lang]["passed"] += 1
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "summary": summary,
                "results": pipeline_results
            }, f, indent=2)
            
        print(f"\n[Pipeline Test Report] generated at: {report_path}")
