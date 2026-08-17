import os
import json
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class OfflineCommandPredictor:
    def __init__(self):
        self.model_dir = os.path.join(os.path.dirname(__file__), "offline_command_model")
        self.mapping_file = os.path.join(self.model_dir, "label_mapping.json")
        
        if not os.path.exists(self.model_dir) or not os.path.exists(self.mapping_file):
            raise FileNotFoundError(f"Offline model not found at {self.model_dir}. Please run train_model.py first.")
            
        print("Loading offline command model into memory...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_dir)
        self.model.eval() # Set to evaluation mode
        
        with open(self.mapping_file, "r") as f:
            # json saves keys as strings, we need to map string indices to intent names
            self.labels_mapping = json.load(f)
            
    def predict(self, text: str) -> str:
        """
        Takes a natural language command (English, Hindi, or Bhojpuri) 
        and returns the corresponding INTENT tag.
        """
        # Tokenize the input text
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=64)
        
        # Predict
        with torch.no_grad():
            outputs = self.model(**inputs)
            
        logits = outputs.logits
        predicted_class_id = logits.argmax().item()
        
        # Look up the intent string
        intent = self.labels_mapping[str(predicted_class_id)]
        return intent

if __name__ == "__main__":
    try:
        predictor = OfflineCommandPredictor()
        print("\n--- Offline Tri-Lingual Assistant ---")
        print("Type a command in English, Hindi, or Bhojpuri (or 'exit' to quit).")
        
        while True:
            user_input = input("\nCommand: ")
            if user_input.lower() in ['exit', 'quit']:
                break
                
            predicted_intent = predictor.predict(user_input)
            print(f"-> Predicted Intent: {predicted_intent}")
            
            # Here you would route to your actual assistant logic, for example:
            if predicted_intent == "SYSTEM_SHUTDOWN":
                print("   [Action] Triggering system shutdown logic...")
            elif predicted_intent == "OPEN_BROWSER":
                print("   [Action] Launching Chrome...")
                
    except FileNotFoundError as e:
        print(e)
