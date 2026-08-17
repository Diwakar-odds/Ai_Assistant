from ai_assistant.modules.conversational_ai import AdvancedConversationalAI

print("Creating AI instance...")
ai = AdvancedConversationalAI()

print("\nTesting AI with question...")
response = ai.process_message('What is Earth?')

print("\n=== FINAL RESPONSE ===")
print(response)
print("======================")
