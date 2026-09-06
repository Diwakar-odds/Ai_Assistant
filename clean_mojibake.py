import re, glob
files = glob.glob(r'd:/Projects/Ai_Assistant/backend/**/*.py', recursive=True) + glob.glob(r'd:/Projects/Ai_Assistant/core_ai/**/*.py', recursive=True)
count = 0

def clean_mojibake(text):
    # Typical mojibake sequences
    bad_chars = ['Ã', '¢', 'Å', '¡', 'Â', '¯', '¸', '°', 'Ÿ', '’', 'œ', '”', 'œ', 'µ', '“', '§', 'Š', '™', 'â', '€', '¢', 'ð', '¿', '½', '', 'ï']
    for c in bad_chars:
        text = text.replace(c, '')
    return text

for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
            
        new_content = clean_mojibake(content)
        
        if new_content != content:
            with open(f, 'w', encoding='utf-8') as file:
                file.write(new_content)
            count += 1
            print(f'Cleaned {f}')
    except Exception as e:
        pass

print(f'Total cleaned: {count}')
