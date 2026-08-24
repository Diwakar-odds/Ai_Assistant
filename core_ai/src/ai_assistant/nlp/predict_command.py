import os
import json
from pathlib import Path

# We will lazily load llama_cpp to avoid errors if it's not installed yet
try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False


class OfflineCommandPredictor:
    def __init__(self):
        try:
            from src.ai_assistant.ai.gguf_model_manager import gguf_manager
        except ImportError:
            from ai_assistant.ai.gguf_model_manager import gguf_manager
        
        if not LLAMA_AVAILABLE:
            raise ImportError("llama-cpp-python is not installed. Please run: pip install llama-cpp-python")
            
        # Use the singleton manager to ensure the 4.6GB model is loaded exactly once
        self.llm = gguf_manager.get_model()
            
    def predict(self, text: str) -> str:
        """
        Takes a natural language command (English, Hindi, or Bhojpuri) 
        and returns the corresponding INTENT tag.
        """
        messages = [
            {"role": "system", "content": "You are an AI assistant intent classifier. Reply with exactly one of the known INTENT tags (e.g. SYSTEM_SHUTDOWN, OPEN_BROWSER, PLAY_MUSIC) and nothing else."},
            {"role": "user", "content": text}
        ]
        
        # We can use the chat_completion API
        response = self.llm.create_chat_completion(
            messages=messages,
            max_tokens=15,      # We only need a short intent string
            temperature=0.1     # Low temperature for deterministic classification
        )
        
        # Extract the text
        intent = response['choices'][0]['message']['content'].strip()
        
        # Clean up any markdown or quotes just in case
        intent = intent.replace('`', '').replace('"', '').replace("'", "").strip()
        
        return intent

if __name__ == "__main__":
    try:
        predictor = OfflineCommandPredictor()
        print("\n\n# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

--- Offline Tri-Lingual Assistant (Llama 3.1 8B GGUF) ---")
        print("Type a command in English, Hindi, or Bhojpuri (or 'exit' to quit).")
        
        while True:
            user_input = input("\nCommand: ")
            if user_input.lower() in ['exit', 'quit']:
                break
                
            predicted_intent = predictor.predict(user_input)
            print(f"-> Predicted Intent: {predicted_intent}")
                
    except Exception as e:
        logger.error(f"Error: {e}")
