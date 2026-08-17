"""Script to remove Ollama references from modern_web_backend.py"""
import re

file_path = 'f:/bn/assitant/ai_assistant/services/modern_web_backend.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find and replace the ollama conditional
old_pattern = r'if provider == "ollama":\s+print\(f"[^"]+Using your local \{model\} model"\)\s+elif provider in \["openai", "gemini"\]:\s+print\(f"[^"]+Using online \{provider\} API"\)'
new_code = 'print(f"\\u2705 Using online {provider} API ({model})")'

content = re.sub(old_pattern, new_code, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated modern_web_backend.py")
