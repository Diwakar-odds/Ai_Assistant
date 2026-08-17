"""Script to fix encoding and remove Ollama from services/modern_web_backend.py"""

file_path = 'f:/bn/assitant/ai_assistant/services/modern_web_backend.py'

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace the problematic section
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Check if this is the start of the section to replace
    if 'if provider == "ollama":' in line:
        # Skip the next lines (local model, elif, online api)
        # and replace with simple online-only code
        new_lines.append('                print(f"✅ Using online {provider} API ({model})")\n')
        # Skip: ollama line, local model line, elif line, online api line
        i += 4
        continue
    
    new_lines.append(line)
    i += 1

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Fixed services/modern_web_backend.py")
