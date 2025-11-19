# Test Real-time Chat Commands
"""
Quick test script to demonstrate all the new chat capabilities
"""

print("🤖 YourDaddy Assistant - Real-time Command Test")
print("=" * 60)
print("\n✅ Your assistant can now handle these commands:\n")

commands = [
    ("Opening Apps", [
        "open chrome",
        "open calculator",
        "open notepad",
        "open spotify",
        "launch word"
    ]),
    ("Opening Websites", [
        "open google.com",
        "open youtube.com",
        "open github.com"
    ]),
    ("Closing Apps", [
        "close chrome",
        "close notepad",
        "quit spotify"
    ]),
    ("Google Search", [
        "google python tutorial",
        "search for best restaurants",
        "find weather forecast"
    ]),
    ("Playing Music", [
        "play believer",
        "play shape of you",
        "play music by coldplay"
    ]),
    ("Creating Documents", [
        "create a powerpoint",
        "make a ppt",
        "create a document",
        "open word document"
    ]),
    ("Volume Control", [
        "volume up",
        "volume down",
        "volume 50",
        "mute volume"
    ]),
    ("System Settings", [
        "open settings",
        "open wifi settings",
        "open bluetooth settings",
        "open display settings",
        "open sound settings"
    ]),
    ("Math & Info", [
        "what is 10 times 5",
        "calculate 100 plus 50",
        "what is pie value",
        "what time is it",
        "what date is today"
    ])
]

for category, cmds in commands:
    print(f"\n📌 {category}:")
    for cmd in cmds:
        print(f"   • \"{cmd}\"")

print("\n" + "=" * 60)
print("🚀 Start the backend and try these commands in the chat!")
print("   Run: python modern_web_backend.py")
print("=" * 60)
