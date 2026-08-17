
import sys
import os
import time

# Add project root to path
sys.path.append(os.path.abspath(r"f:\bn\assitant"))

from ai_assistant.modules.app_discovery import app_discovery

print("--- Verifying Fixes ---")

# 1. Verify Exports (for Backend API)
try:
    from ai_assistant.modules.app_discovery import get_installed_apps, refresh_app_list
    print("✅ Successfully imported 'get_installed_apps' and 'refresh_app_list'")
except ImportError as e:
    print(f"❌ Failed to import aliases: {e}")

# 2. Verify WhatsApp Discovery (Direct Lookup)
print("\n--- Testing 'whatsapp' Discovery ---")
start_time = time.time()
path = app_discovery.find_app("whatsapp")
duration = time.time() - start_time
if path and "AppsFolder" in path:
    print(f"✅ Found WhatsApp: {path}")
    print(f"⏱️ Lookup Time: {duration:.4f}s (Should be < 0.01s for direct match)")
else:
    print(f"❌ Failed to find WhatsApp (Found: {path})")

# 3. Verify API Performance (get_apps_for_api)
print("\n--- Testing API App Loading Performance ---")
start_time = time.time()
apps = app_discovery.get_apps_for_api()
duration = time.time() - start_time
print(f"✅ Loaded {len(apps)} apps for API")
print(f"⏱️ Execution Time: {duration:.4f}s")
if duration > 1.0:
    print("⚠️ WARNING: API loading is still slow (> 1.0s)")
else:
    print("🚀 API loading is optimized!")

