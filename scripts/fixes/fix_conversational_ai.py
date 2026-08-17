"""Fix conversational_ai.py to be a clean re-export module"""

content = '''# Advanced Conversational AI Module
"""
Re-export from canonical location to avoid code duplication.
The actual implementation is in ai_assistant.modules.conversational_ai
"""

# Re-export everything from the canonical module
from ai_assistant.modules.conversational_ai import (
    ConversationState,
    MoodType,
    ConversationContext,
    AdvancedConversationalAI,
)

__all__ = [
    'ConversationState',
    'MoodType', 
    'ConversationContext',
    'AdvancedConversationalAI',
]
'''

file_path = 'f:/bn/assitant/ai_assistant/ai/conversational_ai.py'

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ Fixed {file_path}")
print(f"   File size: {len(content)} bytes (should be ~400)")
