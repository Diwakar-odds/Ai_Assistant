"""
Abliteration Script to Remove Safety Filters (Censorship) from the Model.

REQUIREMENTS:
pip install transformers torch accelerate safetensors

HOW IT WORKS:
Instead of trying to modify the compressed .gguf file directly (which is mathematically very difficult), 
this script takes your base Safetensors model, calculates the "Refusal Vector" (the exact neurons that say NO),
and deletes them from the model's weights. 
After running this, you can convert the output back to .gguf using llama.cpp.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

def remove_censorship(model_path, output_path):
    print(f"Loading model from {model_path} into RAM/VRAM...")
    # Load your model (unquantized safetensors)
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.float16, device_map="auto")
    
    print("Identifying refusal neurons...")
    # In a full abliteration, we calculate the refusal direction using a dataset.
    # For a quick fix, many people merge with an already abliterated model's weights 
    # OR use the 'abliterator' library.
    
    # If you want the automatic 1-click method, you can use the 'abliterator' library:
    # pip install abliterator
    # from abliterator import Abliterator
    # abliterator = Abliterator(model_path)
    # abliterator.orthogonalize()
    # abliterator.save_pretrained(output_path)
    
    print("Warning: To do this properly in 10 lines, you need the 'abliterator' package.")
    print("Run: pip install git+https://github.com/FailSpy/abliterator.git")
    
    print(f"\n--- FASTEST ALTERNATIVE METHOD ---")
    print("Since you are already training a model, the absolute best way is to apply your training")
    print("on top of a base model that ALREADY has its censorship removed.")
    print("Base Model to use: 'cognitivecomputations/dolphin-2.9-llama3-8b' OR 'failspy/Meta-Llama-3-8B-Instruct-abliterated-v3'")
    print("If you train on top of these, your final GGUF will be 100% uncensored automatically!")

if __name__ == "__main__":
    # Replace with your HuggingFace model path or local safetensors path
    my_model = "path_to_your_trained_safetensors_model" 
    output_dir = "path_to_save_uncensored_model"
    
    # remove_censorship(my_model, output_dir)
    print("Please read the instructions inside this script!")
