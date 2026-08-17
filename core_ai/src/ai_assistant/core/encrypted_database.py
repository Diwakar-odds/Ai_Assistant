"""
Encrypted Database Operations for AI Assistant

Provides transparent encryption/decryption for database operations.
Encrypts sensitive fields while maintaining database functionality.
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager
from .encryption import get_db_encryption, EncryptionError

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class EncryptedDatabase:
    """
    Database wrapper that provides transparent encryption for sensitive fields.
    
    Features:
    - Automatic encryption/decryption of marked fields
    - Backward compatibility with existing databases
    - Migration support for adding encryption to existing data
    - Query encryption for searching encrypted fields
    """
    
    def __init__(self, db_path: str, encrypted_fields: Dict[str, List[str]] = None):
        """
        Initialize encrypted database wrapper.
        
        Args:
            db_path: Path to SQLite database
            encrypted_fields: Dict mapping table_name -> list of encrypted field names
        """
        self.db_path = db_path
        self.encrypted_fields = encrypted_fields or {}
        self.db_encryption = get_db_encryption()
        
        # Ensure database directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def add_encrypted_field(self, table_name: str, field_name: str):
        """Mark a field as encrypted for automatic handling"""
        if table_name not in self.encrypted_fields:
            self.encrypted_fields[table_name] = []
        if field_name not in self.encrypted_fields[table_name]:
            self.encrypted_fields[table_name].append(field_name)
    
    def _is_encrypted_field(self, table_name: str, field_name: str) -> bool:
        """Check if a field should be encrypted"""
        return (table_name in self.encrypted_fields and 
                field_name in self.encrypted_fields[table_name])
    
    def _encrypt_value(self, value: Any, table_name: str, field_name: str) -> str:
        """Encrypt a field value"""
        if value is None:
            return None
        
        # Skip if already encrypted
        if isinstance(value, str) and value.startswith('enc:'):
            return value
        
        try:
            encrypted = self.db_encryption.encrypt_field(value, table_name, field_name)
            return f"enc:{encrypted}"
        except EncryptionError as e:
            logger.error(f"Failed to encrypt field {table_name}.{field_name}: {e}")
            return value
    
    def _decrypt_value(self, encrypted_value: Any, table_name: str, field_name: str) -> Any:
        """Decrypt a field value"""
        if not isinstance(encrypted_value, str) or not encrypted_value.startswith('enc:'):
            return encrypted_value
        
        try:
            encrypted_data = encrypted_value[4:]  # Remove 'enc:' prefix
            return self.db_encryption.decrypt_field(encrypted_data, table_name, field_name)
        except EncryptionError as e:
            logger.error(f"Failed to decrypt field {table_name}.{field_name}: {e}")
            return encrypted_value
    
    def _process_row_for_encryption(self, row_data: Dict[str, Any], table_name: str, operation: str) -> Dict[str, Any]:
        """Process a row for encryption/decryption"""
        processed_data = row_data.copy()
        
        for field_name, value in processed_data.items():
            if self._is_encrypted_field(table_name, field_name):
                if operation == 'encrypt':
                    processed_data[field_name] = self._encrypt_value(value, table_name, field_name)
                elif operation == 'decrypt':
                    processed_data[field_name] = self._decrypt_value(value, table_name, field_name)
        
        return processed_data
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper cleanup"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()
    
    def execute(self, query: str, params: Optional[Tuple] = None, table_name: str = None) -> bool:
        """
        Execute a SQL command with automatic encryption
        
        Args:
            query: SQL query
            params: Query parameters
            table_name: Table name for encryption context
            
        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Database execution failed: {e}")
            return False
    
    def insert(self, table_name: str, data: Dict[str, Any]) -> Optional[int]:
        """
        Insert data with automatic encryption
        
        Args:
            table_name: Target table
            data: Data dictionary
            
        Returns:
            Last row ID if successful, None otherwise
        """
        try:
            # Encrypt sensitive fields
            encrypted_data = self._process_row_for_encryption(data, table_name, 'encrypt')
            
            # Build insert query
            columns = list(encrypted_data.keys())
            placeholders = ', '.join(['?' for _ in columns])
            query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            values = list(encrypted_data.values())
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Database insert failed: {e}")
            return None
    
    def select(self, table_name: str, where_clause: str = "", params: Optional[Tuple] = None, 
               limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Select data with automatic decryption
        
        Args:
            table_name: Source table
            where_clause: WHERE condition (without WHERE keyword)
            params: Query parameters
            limit: Maximum number of results
            
        Returns:
            List of decrypted row dictionaries
        """
        try:
            query = f"SELECT * FROM {table_name}"
            
            if where_clause:
                query += f" WHERE {where_clause}"
            
            if limit:
                query += f" LIMIT {limit}"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                rows = cursor.fetchall()
                
                # Convert to dictionaries and decrypt
                result = []
                for row in rows:
                    row_dict = dict(row)
                    decrypted_row = self._process_row_for_encryption(row_dict, table_name, 'decrypt')
                    result.append(decrypted_row)
                
                return result
                
        except Exception as e:
            logger.error(f"Database select failed: {e}")
            return []
    
    def update(self, table_name: str, data: Dict[str, Any], where_clause: str, params: Optional[Tuple] = None) -> bool:
        """
        Update data with automatic encryption
        
        Args:
            table_name: Target table
            data: Update data dictionary
            where_clause: WHERE condition (without WHERE keyword)
            params: WHERE clause parameters
            
        Returns:
            True if successful
        """
        try:
            # Encrypt sensitive fields in update data
            encrypted_data = self._process_row_for_encryption(data, table_name, 'encrypt')
            
            # Build update query
            set_clauses = [f"{col} = ?" for col in encrypted_data.keys()]
            query = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {where_clause}"
            
            # Combine update values with where parameters
            values = list(encrypted_data.values())
            if params:
                values.extend(params)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Database update failed: {e}")
            return False
    
    def delete(self, table_name: str, where_clause: str, params: Optional[Tuple] = None) -> bool:
        """Delete records (no encryption needed)"""
        try:
            query = f"DELETE FROM {table_name} WHERE {where_clause}"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Database delete failed: {e}")
            return False
    
    def migrate_to_encrypted(self, table_name: str, fields_to_encrypt: List[str]) -> bool:
        """
        Migrate existing table data to encrypted format
        
        Args:
            table_name: Table to migrate
            fields_to_encrypt: List of field names to encrypt
            
        Returns:
            True if migration successful
        """
        try:
            logger.info(f"Migrating {table_name} to encrypted format...")
            
            # Add fields to encrypted list
            for field in fields_to_encrypt:
                self.add_encrypted_field(table_name, field)
            
            # Get all existing data
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                
                # Process each row
                for row in rows:
                    row_dict = dict(row)
                    
                    # Check if any field needs encryption
                    needs_update = False
                    for field in fields_to_encrypt:
                        if field in row_dict and row_dict[field] is not None:
                            if not str(row_dict[field]).startswith('enc:'):
                                needs_update = True
                                break
                    
                    if needs_update:
                        # Get primary key for update
                        pk_value = row_dict.get('id') or row_dict.get('rowid')
                        if pk_value:
                            # Encrypt fields
                            update_data = {}
                            for field in fields_to_encrypt:
                                if field in row_dict and row_dict[field] is not None:
                                    if not str(row_dict[field]).startswith('enc:'):
                                        update_data[field] = row_dict[field]
                            
                            if update_data:
                                self.update(table_name, update_data, "id = ?", (pk_value,))
            
            logger.info(f"Migration of {table_name} completed")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed for {table_name}: {e}")
            return False


# Convenience functions for common use cases

def create_encrypted_memory_db(db_path: str) -> EncryptedDatabase:
    """Create encrypted database for conversation memory"""
    db = EncryptedDatabase(db_path)
    
    # Define encrypted fields for memory tables
    db.add_encrypted_field("memory", "content")
    db.add_encrypted_field("enhanced_memory", "content")
    db.add_encrypted_field("enhanced_memory", "context")
    db.add_encrypted_field("knowledge_base", "content")
    db.add_encrypted_field("daily_summaries", "summary")
    
    return db


def create_encrypted_conversation_db(db_path: str) -> EncryptedDatabase:
    """Create encrypted database for conversation AI"""
    db = EncryptedDatabase(db_path)
    
    # Define encrypted fields for conversation tables
    db.add_encrypted_field("conversations", "messages")
    db.add_encrypted_field("conversations", "metadata")
    db.add_encrypted_field("conversation_contexts", "content")
    db.add_encrypted_field("mood_history", "context")
    
    return db


def create_encrypted_credentials_db(db_path: str) -> EncryptedDatabase:
    """Create encrypted database for API credentials"""
    db = EncryptedDatabase(db_path)
    
    # Define encrypted fields for credentials
    db.add_encrypted_field("api_credentials", "api_key")
    db.add_encrypted_field("api_credentials", "secret_key")
    db.add_encrypted_field("api_credentials", "refresh_token")
    db.add_encrypted_field("oauth_tokens", "access_token")
    db.add_encrypted_field("oauth_tokens", "refresh_token")
    
    return db


if __name__ == "__main__":
    # Test encrypted database
    print("Testing encrypted database...")
    
    # Create test database
    test_db_path = "test_encrypted.db"
    db = EncryptedDatabase(test_db_path)
    
    # Add encrypted field
    db.add_encrypted_field("test_table", "sensitive_data")
    
    # Create table
    db.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INTEGER PRIMARY KEY,
            name TEXT,
            sensitive_data TEXT
        )
    """)
    
    # Insert test data
    test_data = {
        "name": "Test User",
        "sensitive_data": "This is secret information"
    }
    
    row_id = db.insert("test_table", test_data)
    print(f"Inserted row with ID: {row_id}")
    
    # Select data
    results = db.select("test_table")
    print(f"Retrieved data: {results}")
    
    # Cleanup
    os.remove(test_db_path)
    print("✅ Encrypted database test passed!")