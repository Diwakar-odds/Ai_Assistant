"""Fix llm_provider.py to be a clean re-export module"""

content = '''#!/usr/bin/env python3
"""
LLM Provider Abstraction Layer - Re-export Module
Re-export from canonical location to avoid code duplication.
The actual implementation is in ai_assistant.modules.llm_provider
"""

# Re-export everything from the canonical module
from ai_assistant.modules.llm_provider import (
    LLMProvider,
    OpenAIProvider,
    GeminiProvider,
    LocalLLMProvider,
    OfflineProvider,
    LLMFactory,
)

__all__ = [
    'LLMProvider',
    'OpenAIProvider',
    'GeminiProvider',
    'LocalLLMProvider',
    'OfflineProvider',
    'LLMFactory',
]
'''

file_path = 'f:/bn/assitant/ai_assistant/ai/llm_provider.py'

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ Fixed {file_path}")
print(f"   File size: {len(content)} bytes")
