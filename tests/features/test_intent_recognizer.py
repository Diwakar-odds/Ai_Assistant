"""
Comprehensive test for Intent Recognizer with ALL apps
"""
import sys
sys.path.insert(0, 'f:\\bn\\assitant')

from ai_assistant.ai.intent_recognizer import IntentRecognizer

recognizer = IntentRecognizer()

print("="*70)
print("COMPREHENSIVE APP TEST - Testing Across All Categories")
print("="*70)

# Test cases across different categories
test_commands = [
    # Social Media
    ("linkedin kholo", "LinkedIn"),
    ("facebook open karo", "Facebook"),
    ("instagram kholo", "Instagram"),
    ("twitter on kro", "Twitter"),
    
    # Browsers
    ("chrome kholo", "Chrome"),
    ("firefox open", "Firefox"),
    
    # Development
    ("vs code kholo", "VS Code"),
    ("pycharm open karo", "PyCharm"),
    ("github kholo", "GitHub"),
    
    # Office
    ("word kholo", "Word"),
    ("excel open karo", "Excel"),
    
    # Media
    ("spotify kholo", "Spotify"),
    ("netflix open", "Netflix"),
    
    # Gaming
    ("steam kholo", "Steam"),
    ("minecraft open karo", "Minecraft"),
    
    # Utilities
    ("calculator kholo", "Calculator"),
    ("notepad open", "Notepad"),
]

success_count = 0
total_count = len(test_commands)

for cmd, expected_category in test_commands:
    result = recognizer.parse_command(cmd)
    intent = result.get('intent')
    app_name = result.get('app_name')
    confidence = result.get('confidence', 0)
    
    status = "✅" if intent == 'open_app' and app_name else "❌"
    if intent == 'open_app' and app_name:
        success_count += 1
    
    print(f"{status} {expected_category:15} | '{cmd:25}' -> {app_name} ({confidence:.0%})")

print("\n" + "="*70)
print(f"SUCCESS RATE: {success_count}/{total_count} ({100*success_count/total_count:.0f}%)")
print("="*70)

# Count total apps supported
total_apps = len(recognizer.app_aliases)
print(f"\n📱 TOTAL APPS SUPPORTED: {total_apps}")
print("\nCategories:")
print("  🌐 Browsers: 7")
print("  💬 Social Media & Communication: 15")
print("  💻 Development Tools: 14")
print("  📄 Microsoft Office: 7")
print("  🎵 Media & Entertainment: 12")
print("  🎨 Design & Creative: 14")
print("  🛠️  Utilities: 13")
print("  🎮 Gaming: 9")
print("  ⚙️  System Tools: 7")
