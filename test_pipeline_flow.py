import sys
import os
import json
from pathlib import Path

# Add core_ai/src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'core_ai', 'src'))

from ai_assistant.nlp.unified_intent_classifier import UnifiedIntentClassifier
from ai_assistant.core.chain_of_actions_manager import ChainOfActionsManager

def run_backend_test():
    print("🚀 Starting Backend Pipeline Test...")
    
    print("\n[1] Initializing Unified Intent Classifier...")
    try:
        classifier = UnifiedIntentClassifier()
        classifier_available = True
    except Exception as e:
        print(f"Failed to initialize UnifiedIntentClassifier: {e}")
        classifier_available = False
        
    print("\n[2] Initializing Chain of Actions Manager...")
    try:
        chain_manager = ChainOfActionsManager()
        chain_manager_available = True
    except Exception as e:
        print(f"Failed to initialize ChainOfActionsManager: {e}")
        chain_manager_available = False

    # Test Commands based on commands_dataset.csv
    test_commands = [
        "chrome khol do",          # open_app
        "laptop band kar do",      # shutdown
        "wifi band kar de",        # toggle_wifi
        "volume full kar",         # set_volume
        "website laga youtube.com",# open_website
        "screen pe kya hai",       # read_screen
        "folder saaf kar downloads"# organize_files
    ]

    print("\n" + "="*50)
    print("🧪 RUNNING COMMAND TESTS")
    print("="*50)

    for cmd in test_commands:
        print(f"\n🗣️ Testing Command: '{cmd}'")
        
        if classifier_available:
            intent_res = classifier.classify(cmd)
            print(f"  -> [UnifiedClassifier] Identified Intent: {intent_res.intent}")
            print(f"  -> [UnifiedClassifier] Extracted Entities: {intent_res.entities}")
            print(f"  -> [UnifiedClassifier] Confidence: {intent_res.confidence}")
            
            if chain_manager_available and intent_res.intent and intent_res.intent != "unknown":
                print(f"  -> [ChainOfActions] Processing intent: {intent_res.intent}")
                try:
                    # In a real run, ChainOfActionsManager might need 'action' inside entities or direct mapping
                    # We can use execute_intent if it exists, or generate_chain
                    if hasattr(chain_manager, 'execute_intent'):
                        res = chain_manager.execute_intent(intent_res.intent, intent_res.entities)
                        print(f"  -> [ChainOfActions] Output: {res}")
                    elif hasattr(chain_manager, 'process_intent'):
                        res = chain_manager.process_intent(intent_res.intent, intent_res.entities)
                        print(f"  -> [ChainOfActions] Output: {res}")
                    else:
                        print(f"  -> [ChainOfActions] Output: Sent to chain (simulation)")
                except Exception as e:
                    print(f"  -> [ChainOfActions] Error: {e}")

if __name__ == "__main__":
    run_backend_test()
