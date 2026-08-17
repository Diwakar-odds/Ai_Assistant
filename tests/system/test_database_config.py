"""
Test suite for database configuration module.
"""

import pytest
from pathlib import Path
import shutil
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_assistant import database_config


class TestDatabaseConfig:
    """Tests for database configuration module."""
    
    def test_get_db_path(self):
        """Test getting database path."""
        path = database_config.get_db_path('memory')
        assert isinstance(path, Path)
        assert path.name == 'memory.db'
        assert 'data' in str(path)
    
    def test_get_db_path_invalid(self):
        """Test getting path for invalid database."""
        with pytest.raises(KeyError):
            database_config.get_db_path('invalid_db')
    
    def test_get_db_path_str(self):
        """Test getting database path as string."""
        path_str = database_config.get_db_path_str('memory')
        assert isinstance(path_str, str)
        assert path_str.endswith('memory.db')
    
    def test_list_databases(self):
        """Test listing all databases."""
        dbs = database_config.list_databases()
        assert isinstance(dbs, dict)
        assert 'memory' in dbs
        assert 'chat_history' in dbs
        assert len(dbs) > 0
    
    def test_database_exists(self):
        """Test checking if database exists."""
        # This will depend on whether databases have been created
        result = database_config.database_exists('memory')
        assert isinstance(result, bool)
    
    def test_get_database_size(self):
        """Test getting database size."""
        size = database_config.get_database_size('memory')
        assert isinstance(size, int)
        assert size >= 0


@pytest.mark.integration
class TestDatabaseMigration:
    """Integration tests for database migration."""
    
    def test_migrate_legacy_databases(self, tmp_path, monkeypatch):
        """Test migrating legacy databases."""
        # Mock the project root to use tmp_path
        monkeypatch.setattr(database_config, 'PROJECT_ROOT', tmp_path)
        monkeypatch.setattr(database_config, 'DATA_DIR', tmp_path / 'data')
        
        # Create a fake legacy database
        legacy_db = tmp_path / 'memory.db'
        legacy_db.write_text('fake database content')
        
        # Run migration
        migrated = database_config.migrate_legacy_databases()
        
        # Check that database was migrated
        assert len(migrated) > 0 or not legacy_db.exists()
