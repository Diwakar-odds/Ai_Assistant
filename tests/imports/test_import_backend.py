
try:
    import ai_assistant.services.modern_web_backend
    print("Successfully imported ai_assistant.services.modern_web_backend")
except Exception as e:
    print(f"Failed to import: {e}")
    import traceback
    traceback.print_exc()
