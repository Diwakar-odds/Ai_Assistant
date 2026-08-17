"""Fix memory.py to be a clean re-export module"""

content = '''# Memory Management Module
"""
Re-export from canonical location to avoid code duplication.
The actual implementation is in ai_assistant.modules.memory
"""

# Re-export everything from the canonical module
from ai_assistant.modules.memory import (
    ConnectionPool,
    get_db_connection,
    get_db_transaction,
    setup_memory,
    save_to_memory,
    get_memory,
    search_memory,
    get_conversation_summary,
    save_knowledge,
    get_knowledge,
    determine_importance,
    categorize_content,
    generate_summary,
)

__all__ = [
    'ConnectionPool',
    'get_db_connection',
    'get_db_transaction',
    'setup_memory',
    'save_to_memory',
    'get_memory',
    'search_memory',
    'get_conversation_summary',
    'save_knowledge',
    'get_knowledge',
    'determine_importance',
    'categorize_content',
    'generate_summary',
]
'''

file_path = 'f:/bn/assitant/ai_assistant/ai/memory.py'

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ Fixed {file_path}")
print(f"   File size: {len(content)} bytes")
