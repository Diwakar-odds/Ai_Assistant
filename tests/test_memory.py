import sys
import os
import shutil

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_assistant.core.memory_manager import MemoryManager

def test_memory():
    print("Testing Memory Manager...")
    
    # Use a temp file
    test_path = "workspace/test_memory.json"
    if os.path.exists(test_path):
        os.remove(test_path)
        
    mm = MemoryManager(storage_path=test_path)
    
    # Test Set/Get
    print("Set 'user_name' = 'Alice'")
    mm.set("user_name", "Alice")
    
    val = mm.get("user_name")
    if val == "Alice":
        print("✅ Get Success")
    else:
        print(f"❌ Get Failed. Got: {val}")
        
    # Test Persistence
    print("Testing Persistence...")
    mm2 = MemoryManager(storage_path=test_path)
    val2 = mm2.get("user_name")
    if val2 == "Alice":
        print("✅ Persistence Success")
    else:
        print(f"❌ Persistence Failed. Got: {val2}")
        
    # Test Clear
    mm2.clear()
    if not mm2.list_keys():
        print("✅ Clear Success")
        
    # Cleanup
    if os.path.exists(test_path):
        os.remove(test_path)

if __name__ == "__main__":
    test_memory()
