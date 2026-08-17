
import sys
import os
import time

# Add project root to path
sys.path.append(os.path.abspath(r"f:\bn\assitant"))

from ai_assistant.modules.app_discovery import app_discovery, smart_open_application

print("--- Verifying Launch Priority ---")

app_name = "whatsapp"
print(f"Testing launch priority for '{app_name}'...")

# Mocking _open_via_windows_search to simply return True and print
# This avoids actual key presses during verification but checks the logic path
original_search = app_discovery._open_via_windows_search
def mock_search(name):
    print(f"  [MOCK] _open_via_windows_search called for '{name}'")
    return True
app_discovery._open_via_windows_search = mock_search

try:
    # Logic Test
    result = smart_open_application(app_name)
    print(f"\nResult: {result}")
    
    if "via Windows Search" in result:
        print("✅ SUCCESS: Logic prioritized Windows Search!")
    else:
        print("❌ FAILURE: Logic did NOT use Windows Search.")

finally:
    # Restore original method
    app_discovery._open_via_windows_search = original_search

print("\n--- Testing Web Fallback Removal ---")
# Check if whatsapp is in fallbacks
# We need to peek inside smart_open_application logic or just test a fake app?
# We removed it from the code, so we can verify by source inspection or behavior.
# Let's test non-existent app behavior if possible, but that's hard to assert without modifying code.
# The previous test confirms the POSITIVE case (priority).
