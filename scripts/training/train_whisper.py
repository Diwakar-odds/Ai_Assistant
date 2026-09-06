import os
import torch
import warnings
warnings.filterwarnings("ignore")

from datasets import load_dataset, Audio
from transformers import (
    WhisperFeatureExtractor,
    WhisperTokenizer,
    WhisperProcessor,
    WhisperForConditionalGeneration,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer
)
from peft import prepare_model_for_kbit_training, LoraConfig, get_peft_model
from dataclasses import dataclass
from typing import Any, Dict, List, Union

# ============================================================================
# WHISPER QLoRA TRAINER 
# Fine-tunes the openai/whisper-small model using 8-bit quantization and LoRA
# ============================================================================

MODEL_ID = "openai/whisper-small"
DATASET_DIR = "data/training/whisper_audio_dataset_cloned"
OUTPUT_DIR = "models/whisper_bhojpuri_lora"

print("🚀 Initializing Whisper QLoRA Trainer...")

# 1. Load Feature Extractor, Tokenizer and Processor
feature_extractor = WhisperFeatureExtractor.from_pretrained(MODEL_ID)
tokenizer = WhisperTokenizer.from_pretrained(MODEL_ID, language="Hindi", task="transcribe")
processor = WhisperProcessor.from_pretrained(MODEL_ID, language="Hindi", task="transcribe")

# 2. Load the Dataset from local directory
print(f"Loading dataset from {DATASET_DIR}...")
try:
    # Requires metadata.csv and audio files in the folder
    dataset = load_dataset("audiofolder", data_dir=DATASET_DIR)
except Exception as e:
    print(f"❌ Error loading dataset: {e}")
    print("Please make sure you have run generate_audio_dataset.py first!")
    exit(1)

# Cast audio column to 16kHz
dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))

# 3. Data Preparation Function
def prepare_dataset(batch):
    # Process audio
    audio = batch["audio"]
    batch["input_features"] = feature_extractor(audio["array"], sampling_rate=audio["sampling_rate"]).input_features[0]
    # Process text
    batch["labels"] = tokenizer(batch["transcription"]).input_ids
    return batch

print("Processing dataset features (this might take a few minutes)...")
dataset = dataset.map(prepare_dataset, remove_columns=dataset.column_names["train"], num_proc=2)

# 4. Data Collator
@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    processor: Any

    def __call__(self, features: List[Dict[str, Union[List[int], torch.Tensor]]]) -> Dict[str, torch.Tensor]:
        input_features = [{"input_features": feature["input_features"]} for feature in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")
        
        label_features = [{"input_ids": feature["labels"]} for feature in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")
        
        # Replace padding with -100 to ignore loss correctly
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)
        
        # If bos token is appended in previous tokenization step, cut it off
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]
            
        batch["labels"] = labels
        return batch

data_collator = DataCollatorSpeechSeq2SeqWithPadding(processor=processor)

# 5. Load Model in 8-bit using BitsAndBytes
print("Loading Whisper model in 8-bit precision...")
model = WhisperForConditionalGeneration.from_pretrained(
    MODEL_ID, 
    load_in_8bit=True, 
    device_map="auto"
)

# Whisper specific configuration
model.config.forced_decoder_ids = None
model.config.suppress_tokens = []

# Prepare for INT8 Training
model = prepare_model_for_kbit_training(model)

# 6. Apply LoRA (Low-Rank Adaptation)
config = LoraConfig(
    r=32, 
    lora_alpha=64, 
    target_modules=["q_proj", "v_proj"], 
    lora_dropout=0.05, 
    bias="none"
)

model = get_peft_model(model, config)
model.print_trainable_parameters()

# 7. Define Training Arguments
training_args = Seq2SeqTrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=8,
    gradient_accumulation_steps=2,
    learning_rate=1e-3,
    warmup_steps=50,
    max_steps=500, # 500 steps is good for a quick fine-tune demonstration
    gradient_checkpointing=True,
    fp16=True,
    evaluation_strategy="steps",
    per_device_eval_batch_size=8,
    predict_with_generate=True,
    generation_max_length=225,
    save_steps=100,
    eval_steps=100,
    logging_steps=25,
    report_to=["tensorboard"],
    load_best_model_at_end=True,
    metric_for_best_model="wer",
    greater_is_better=False,
    push_to_hub=False,
)

# 8. Evaluation Metric (WER)
import evaluate
metric = evaluate.load("wer")
def compute_metrics(pred):
    pred_ids = pred.predictions
    label_ids = pred.label_ids
    label_ids[label_ids == -100] = tokenizer.pad_token_id
    pred_str = tokenizer.batch_decode(pred_ids, skip_special_tokens=True)
    label_str = tokenizer.batch_decode(label_ids, skip_special_tokens=True)
    wer = 100 * metric.compute(predictions=pred_str, references=label_str)
    return {"wer": wer}

# 9. Initialize Trainer
trainer = Seq2SeqTrainer(
    args=training_args,
    model=model,
    train_dataset=dataset["train"],
    eval_dataset=dataset["train"], # Ideally should be a test split, using train for simplicity
    data_collator=data_collator,
    compute_metrics=compute_metrics,
    tokenizer=processor.feature_extractor,
)

# 10. TRAIN!
print("🔥 STARTING QLORA TRAINING 🔥")
trainer.train()

print(f"✅ Training complete! Saving LoRA weights to {OUTPUT_DIR}...")
model.save_pretrained(OUTPUT_DIR)
processor.save_pretrained(OUTPUT_DIR)
print("Done! Next step: Convert the model to CTranslate2 format.")
