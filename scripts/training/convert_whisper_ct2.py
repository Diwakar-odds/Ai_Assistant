import os
import subprocess
from transformers import WhisperForConditionalGeneration
from peft import PeftModel

# ============================================================================
# WHISPER CTRANSLATE2 CONVERTER
# Merges LoRA weights and converts the model to CTranslate2 (Faster-Whisper) format
# ============================================================================

BASE_MODEL_ID = "openai/whisper-small"
LORA_ADAPTER_DIR = "models/whisper_bhojpuri_lora"
MERGED_OUTPUT_DIR = "models/whisper_bhojpuri_merged"
CT2_OUTPUT_DIR = "models/my_bhojpuri_whisper_ct2"

def main():
    print("🚀 Starting Whisper Model Conversion...")
    
    # Step 1: Check if LoRA model exists
    if not os.path.exists(LORA_ADAPTER_DIR):
        print(f"❌ Error: LoRA adapter not found at {LORA_ADAPTER_DIR}")
        print("Please run train_whisper.py first!")
        return

    # Step 2: Load base model and merge with LoRA weights
    print(f"Loading base model {BASE_MODEL_ID}...")
    base_model = WhisperForConditionalGeneration.from_pretrained(BASE_MODEL_ID, device_map="cpu")
    
    print(f"Loading LoRA weights from {LORA_ADAPTER_DIR}...")
    peft_model = PeftModel.from_pretrained(base_model, LORA_ADAPTER_DIR)
    
    print("Merging weights (this may take a moment)...")
    merged_model = peft_model.merge_and_unload()
    
    print(f"Saving merged model to {MERGED_OUTPUT_DIR}...")
    merged_model.save_pretrained(MERGED_OUTPUT_DIR)
    
    # We also need the processor/tokenizer to be copied over
    from transformers import WhisperProcessor
    processor = WhisperProcessor.from_pretrained(BASE_MODEL_ID, language="Hindi", task="transcribe")
    processor.save_pretrained(MERGED_OUTPUT_DIR)
    print("✅ Merging complete!")

    # Step 3: Convert merged model to CTranslate2 format for Faster-Whisper
    print("\n⚡ Converting to CTranslate2 (Faster-Whisper) format...")
    try:
        subprocess.run(["ct2-transformers-converter", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        print("❌ ct2-transformers-converter not found.")
        print("Installing it now... (pip install ctranslate2)")
        subprocess.run(["pip", "install", "ctranslate2"], check=True)
        
    cmd = [
        "ct2-transformers-converter",
        "--model", MERGED_OUTPUT_DIR,
        "--output_dir", CT2_OUTPUT_DIR,
        "--quantization", "int8", # Same quantization used in assistant.py
        "--force"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    
    if result.returncode == 0:
        print(f"\n🎉 SUCCESS! Your local Bhojpuri Whisper model is ready!")
        print(f"Location: {CT2_OUTPUT_DIR}")
        print("To use it, update core_ai/src/ai_assistant/core/assistant.py line 586:")
        print(f'WhisperModel("{CT2_OUTPUT_DIR}", device="cpu", compute_type="int8")')
    else:
        print("\n❌ Conversion failed. Check the error message above.")

if __name__ == "__main__":
    main()
