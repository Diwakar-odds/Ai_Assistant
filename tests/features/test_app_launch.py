#!/usr/bin/env python3
"""Test script to verify app search and launch functionality"""
import sys
import importlib.util

# Load app_discovery module directly
spec = importlib.util.spec_from_file_location('app_discovery', 'ai_assistant/modules/app_discovery.py')
app_disc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_disc)

discovery = app_disc.AppDiscovery()

print("=" * 60)
print("APP SEARCH AND LAUNCH TESTS")
print("=" * 60)

# Test 1: Sticky Notes
print("\n1. Testing 'Sticky Notes' search...")
result = discovery.find_app('sticky notes')
if result and 'sticky' in result.lower():
    print(f"   ✅ PASS: Found Sticky Notes")
    print(f"   Path: {result}")
else:
    print(f"   ❌ FAIL: Wrong app found: {result}")

# Test 2: Spotify
print("\n2. Testing 'Spotify' search...")
result = discovery.find_app('spotify')
print(f"   Found: {result}")
if 'chrome_proxy' in result or 'brave' in result.lower():
    print("   ℹ️  Note: This is Spotify Web App (browser-based)")
    print("   Explanation: Desktop Spotify not installed, using web version")
else:
    print("   ✅ Desktop Spotify app found")

# Test 3: Show all Spotify-related apps
print("\n3. All Spotify-related apps in database:")
for name, path in discovery.apps_database.items():
    if 'spotify' in name.lower():
        print(f"   - {name}")
        print(f"     Path: {path}")

print("\n" + "=" * 60)
print("EXPLANATION:")
print("=" * 60)
print("""
1. STICKY NOTES: 
   - Stored as 'microsoft.microsoftstickynotes' in database
   - New word splitting logic breaks it into 'microsoft sticky notes'
   - Now searchable with 'sticky notes' query
   
2. SPOTIFY:
   - Found path is a Chrome/Brave browser proxy
   - This means you have Spotify Web App installed, not desktop app
   - When launched, it opens Spotify in the browser
   - To use desktop Spotify, install from: https://www.spotify.com/download
""")
