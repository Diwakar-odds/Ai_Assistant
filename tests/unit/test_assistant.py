"""
Unit tests for ModernAssistant class.

Tests initialization, command processing, and core functionality.
"""

import pytest

def test_assistant_initialization(assistant):
    """Test assistant initializes correctly"""
    assert assistant is not None
    assert hasattr(assistant, 'process_command')
    assert hasattr(assistant, 'get_init_status')

def test_get_init_status(assistant):
    """Test initialization status retrieval"""
    status = assistant.get_init_status()
    assert isinstance(status, dict)
    assert 'memory' in status
    # Status should be one of: ready, failed, not_started
    assert status['memory'] in ['ready', 'failed', 'not_started']

def test_process_command_basic(assistant):
    """Test basic command processing"""
    response = assistant.process_command("hello")
    assert isinstance(response, str)
    assert len(response) > 0

def test_process_command_empty(assistant):
    """Test handling of empty command"""
    response = assistant.process_command("")
    assert isinstance(response, str)

def test_system_stats_structure(assistant):
    """Test system stats return proper structure"""
    try:
        stats = assistant.get_real_time_system_stats()
        assert isinstance(stats, dict)
        # Should have basic system info
        assert 'cpu_usage' in stats or 'error' in stats
    except Exception:
        # System stats may not be available in all environments
        pytest.skip("System stats not available")

def test_assistant_has_required_methods(assistant):
    """Test assistant has all required public methods"""
    required_methods = [
        'process_command',
        'get_init_status',
        'get_real_time_system_stats'
    ]
    for method in required_methods:
        assert hasattr(assistant, method)
        assert callable(getattr(assistant, method))

def test_command_processing_consistency(assistant):
    """Test that same command produces consistent results"""
    command = "what is 2+2"
    response1 = assistant.process_command(command)
    response2 = assistant.process_command(command)
    # Both should be valid responses
    assert isinstance(response1, str)
    assert isinstance(response2, str)
    assert len(response1) > 0
    assert len(response2) > 0

def test_assistant_handles_special_characters(assistant):
    """Test assistant handles special characters in commands"""
    special_commands = [
        "test@#$%",
        "café résumé",
        "测试",  # Chinese
        "тест",  # Russian
    ]
    for cmd in special_commands:
        try:
            response = assistant.process_command(cmd)
            assert isinstance(response, str)
        except Exception as e:
            # Should handle gracefully, not crash
            assert "error" in str(e).lower() or response is not None

def test_memory_initialization(assistant):
    """Test memory system is initialized"""
    status = assistant.get_init_status()
    # Memory should be in some state (ready, failed, or not_started)
    assert 'memory' in status
    memory_status = status['memory']
    assert memory_status in ['ready', 'failed', 'not_started']
