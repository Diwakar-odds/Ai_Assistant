import json
import gzip
import os
import random
import torch
import sys
from tqdm import tqdm

# ============================================================================
# VOICE CLONING AUDIO SYNTHESIS: Whisper Training Dataset Builder
# Generates audio files for a subset of the text corpus using XTTS-v2 
# (Clones the user's voice to create a perfectly personalized dataset)
# ============================================================================

try:
    from TTS.api import TTS
except ImportError:
    print("❌ Error: The 'TTS' library is not installed.")
    print("Please install it by running: pip install TTS")
    sys.exit(1)

CORPUS_FILE = "data/training/hinglish_stt_corpus_v1.jsonl.gz"
OUTPUT_DIR = "data/training/whisper_audio_dataset_cloned"
VOICE_SAMPLE = "data/training/my_voice_sample.wav"
NUM_SAMPLES = 1000  # Reduced to 1,000 for XTTS as it is computationally heavy

def main():
    print("🚀 Starting Voice Cloning Dataset Synthesis (XTTS-v2)")
    
    if not os.path.exists(VOICE_SAMPLE):
        print(f"❌ Error: Voice sample not found at {VOICE_SAMPLE}")
        print("Please record a 15-second clean audio sample of you speaking Hindi/Hinglish")
        print(f"and save it as {VOICE_SAMPLE} before running this script.")
        sys.exit(1)
        
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Initialize XTTS Model
    print("Loading XTTS-v2 model (this may take a minute and download ~2GB of weights)...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    
    # 2. Load Text Corpus
    print(f"Loading corpus from {CORPUS_FILE}...")
    corpus = []
    with gzip.open(CORPUS_FILE, 'rt', encoding='utf-8') as f:
        for line in f:
            corpus.append(json.loads(line))
            
    # Shuffle and select a subset
    random.shuffle(corpus)
    selected_subset = corpus[:NUM_SAMPLES]
    
    print(f"Synthesizing {NUM_SAMPLES} audio files using your cloned voice...")
    
    metadata = []
    
    # 3. Generate Audio
    for i, row in enumerate(tqdm(selected_subset)):
        text = row["text"]
        filename = f"sample_{i:05d}.wav"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        try:
            # XTTS supports "hi" (Hindi) and "en" (English)
            tts.tts_to_file(
                text=text,
                speaker_wav=VOICE_SAMPLE,
                language="hi",
                file_path=filepath
            )
            
            # Save metadata format suitable for HuggingFace datasets
            metadata.append({
                "file_name": filename,
                "transcription": text
            })
        except Exception as e:
            print(f"⚠️ Error generating file {filename}: {e}")
            
    # Write metadata.csv
    import csv
    metadata_path = os.path.join(OUTPUT_DIR, "metadata.csv")
    with open(metadata_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["file_name", "transcription"])
        writer.writeheader()
        writer.writerows(metadata)
        
    print(f"✅ Finished! Custom cloned audio dataset saved to {OUTPUT_DIR}")
    print("Next step: Upload this folder to Kaggle/Colab and run the train_whisper.py script!")

if __name__ == "__main__":
    main()
