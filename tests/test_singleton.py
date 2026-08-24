#!/usr/bin/env python
"""Quick test to verify singleton pattern works"""
import sys
import os

# Suppress warnings
os.environ['PYTHONWARNINGS'] = 'ignore'

print("Testing session_init singleton pattern...", flush=True)

# Import multiple times
import utils.session_init as s1
sid1 = s1.session_id
print(f"Import 1: {sid1}", flush=True)

import utils.session_init as s2  
sid2 = s2.session_id
print(f"Import 2: {sid2}", flush=True)

# Result
if sid1 == sid2:
    print("✅ SUCCESS: Singleton working - no duplicate sessions", flush=True)
    pass
else:
    print("❌ FAIL: Different session IDs", flush=True)
    pass
