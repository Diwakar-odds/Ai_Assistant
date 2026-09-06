import os
from transformers import WhisperForConditionalGeneration, WhisperProcessor

def move_model():
    model_id = "Hhsjsnns/whisper-small-hinglish"
    save_directory = "models/whisper-hinglish"
    
    print(f"[1/2] Loading model from cache ({model_id})...")
    # This will load from cache instantly if already downloaded
    try:
        model = WhisperForConditionalGeneration.from_pretrained(model_id)
        processor = WhisperProcessor.from_pretrained("openai/whisper-small")
    except Exception as e:
        print(f"Error loading model: {e}")
        print("Model probably hasn't finished downloading yet in the backend! Wait for it to finish first.")
        return

    print(f"[2/2] Saving model cleanly to {save_directory} ...")
    os.makedirs(save_directory, exist_ok=True)
    
    model.save_pretrained(save_directory)
    processor.save_pretrained(save_directory)
    
    print(f"SUCCESS! Model is now saved permanently in your local '{save_directory}' folder.")
    print("You can safely delete the huggingface cache later if you want to free up space.")

if __name__ == "__main__":
    move_model()
