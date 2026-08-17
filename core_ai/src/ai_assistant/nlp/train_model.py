import os
import pandas as pd
import torch
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

def main():
    # 1. Load Dataset
    data_path = os.path.join(os.path.dirname(__file__), "commands_dataset.csv")
    if not os.path.exists(data_path):
        print(f"Error: Dataset not found at {data_path}. Run generate_dataset.py first.")
        return

    df = pd.read_csv(data_path)
    
    # Encode Intents to numeric labels
    label_encoder = LabelEncoder()
    df["label"] = label_encoder.fit_transform(df["intent"])
    
    # Save the label mapping for inference later
    labels_mapping = dict(zip(label_encoder.transform(label_encoder.classes_), label_encoder.classes_))
    print(f"Detected Intents: {labels_mapping}")

    # Split into train and evaluation
    train_df, eval_df = train_test_split(df, test_size=0.1, random_state=42)

    # Convert to HuggingFace Dataset
    train_dataset = Dataset.from_pandas(train_df)
    eval_dataset = Dataset.from_pandas(eval_df)

    # 2. Load Tokenizer and Model
    # Using a public multilingual model
    model_name = "distilbert-base-multilingual-cased"
    print(f"Loading Tokenizer and Model: {model_name}...")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, 
        num_labels=len(label_encoder.classes_)
    )

    # 3. Tokenize Dataset
    def tokenize_function(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=64)

    train_tokenized = train_dataset.map(tokenize_function, batched=True)
    eval_tokenized = eval_dataset.map(tokenize_function, batched=True)

    # 4. Define Training Arguments
    output_dir = os.path.join(os.path.dirname(__file__), "offline_command_model")
    
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        logging_dir='./logs',
        load_best_model_at_end=True,
    )

    # 5. Train Model
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_tokenized,
        eval_dataset=eval_tokenized,
    )

    print("Starting fine-tuning... This may take a few minutes on CPU, or seconds on GPU.")
    trainer.train()

    # 6. Save Final Model and Tokenizer
    print(f"Training complete. Saving model to {output_dir}")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    # Save label encoder classes
    import json
    with open(os.path.join(output_dir, "label_mapping.json"), "w") as f:
        json.dump(labels_mapping, f)
        
    print("Model saved successfully. You can now run offline inference!")

if __name__ == "__main__":
    main()
