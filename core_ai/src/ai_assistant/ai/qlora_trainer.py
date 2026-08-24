# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
QLoRA Trainer - Ultra-efficient fine-tuning for 8GB RAM systems
Uses 4-bit quantization + LoRA adapters to train on CPU with minimal memory
"""

import os
import json
import torch
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass

try:
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        BitsAndBytesConfig,
        DataCollatorForLanguageModeling
    )
    from datasets import Dataset
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    from peft import (
        LoraConfig,
        get_peft_model,
        prepare_model_for_kbit_training,
        TaskType
    )
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False


@dataclass
class TrainingConfig:
    """Configuration for QLoRA training optimized for 8GB RAM"""
    
    # Model settings
    model_name: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    use_4bit: bool = True
    
    # LoRA settings (only train small adapters, not full model)
    lora_r: int = 8  # Rank (lower = less memory, 8 is good for 8GB RAM)
    lora_alpha: int = 16  # Scaling factor
    lora_dropout: float = 0.05
    target_modules: List[str] = None  # Auto-detect
    
    # Training settings (ultra-conservative for 8GB RAM)
    batch_size: int = 1  # MUST be 1 for 8GB RAM
    gradient_accumulation_steps: int = 4  # Simulates batch_size=4
    learning_rate: float = 2e-4
    num_epochs: int = 3
    max_steps: int = -1  # Use epochs instead
    warmup_steps: int = 10
    
    # Memory optimization
    gradient_checkpointing: bool = True  # Saves memory at cost of speed
    fp16: bool = True  # Use half precision
    optim: str = "paged_adamw_8bit"  # Memory-efficient optimizer
    
    # Output
    output_dir: str = "models/local/fine_tuned"
    save_steps: int = 50
    logging_steps: int = 10
    
    def __post_init__(self):
        if self.target_modules is None:
            # Common LoRA targets for decoder-only models
            self.target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]


class QLoRATrainer:
    """
    Train tiny models with QLoRA on 8GB RAM systems
    Can run on CPU-only (slow but works)
    """
    
    def __init__(self, config: Optional[TrainingConfig] = None):
        """
        Initialize QLoRA trainer
        
        Args:
            config: Training configuration (uses defaults if None)
        """
        if not TRANSFORMERS_AVAILABLE or not PEFT_AVAILABLE:
            raise ImportError(
                "Required packages not installed.\n"
                "Run: pip install transformers peft datasets bitsandbytes accelerate"
            )
        
        self.config = config or TrainingConfig()
        
        # Paths
        self.base_dir = Path(__file__).parent.parent.parent
        self.models_dir = self.base_dir / 'models' / 'local'
        self.output_dir = self.base_dir / self.config.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Will be loaded during training
        self.model = None
        self.tokenizer = None
    
    def prepare_dataset(self, data: List[Dict[str, str]]) -> Dataset:
        """
        Prepare dataset for fine-tuning
        
        Args:
            data: List of dicts with 'instruction' and 'response' keys
                  Example: [{"instruction": "What is AI?", "response": "AI is..."}]
        
        Returns:
            Hugging Face Dataset object
        """
        # Format data for chat model
        formatted_data = []
        
        for item in data:
            # Create chat-style prompt
            text = f"<|user|>\n{item['instruction']}\n<|assistant|>\n{item['response']}\n"
            formatted_data.append({"text": text})
        
        # Create dataset
        dataset = Dataset.from_list(formatted_data)
        
        return dataset
    
    def load_training_data(self, data_path: str) -> Dataset:
        """
        Load training data from JSON file
        
        Format:
        [
            {"instruction": "question or command", "response": "answer"},
            ...
        ]
        """
        data_file = Path(data_path)
        
        if not data_file.exists():
            raise FileNotFoundError(f"Training data not found: {data_path}")
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📚 Loaded {len(data)} training examples from {data_path}")
        
        return self.prepare_dataset(data)
    
    def tokenize_dataset(self, dataset: Dataset, max_length: int = 512) -> Dataset:
        """Tokenize the dataset"""
        
        def tokenize_function(examples):
            # Tokenize with truncation and padding
            tokenized = self.tokenizer(
                examples["text"],
                truncation=True,
                max_length=max_length,
                padding="max_length",
                return_tensors=None
            )
            
            # For causal LM, labels are the same as input_ids
            tokenized["labels"] = tokenized["input_ids"].copy()
            
            return tokenized
        
        print("🔄 Tokenizing dataset...")
        tokenized_dataset = dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=dataset.column_names,
            desc="Tokenizing"
        )
        
        return tokenized_dataset
    
    def setup_model_and_tokenizer(self):
        """Load model with 4-bit quantization and prepare for LoRA training"""
        
        print(f"📥 Loading model: {self.config.model_name}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name,
            cache_dir=str(self.models_dir)
        )
        
        if not self.tokenizer.pad_token:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        
        # 4-bit quantization config (saves 75% memory)
        if self.config.use_4bit:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16
            )
            
            # Load base model
            model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                quantization_config=bnb_config,
                device_map="cpu",  # Force CPU for 1GB GPU
                cache_dir=str(self.models_dir),
                low_cpu_mem_usage=True,
                trust_remote_code=True
            )
        else:
            model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                device_map="cpu",
                cache_dir=str(self.models_dir),
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True,
                trust_remote_code=True
            )
        
        # Prepare model for k-bit training
        model = prepare_model_for_kbit_training(model)
        
        # Configure LoRA
        peft_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            target_modules=self.config.target_modules,
            bias="none"
        )
        
        # Add LoRA adapters
        model = get_peft_model(model, peft_config)
        
        # Print trainable parameters
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in model.parameters())
        trainable_percent = 100 * trainable_params / total_params
        
        logger.info(f"✅ Model prepared for training")
        print(f"   Trainable params: {trainable_params:,} ({trainable_percent:.2f}%)")
        print(f"   Total params: {total_params:,}")
        
        self.model = model
    
    def train(self, training_data_path: str, output_name: str = "custom_adapter"):
        """
        Fine-tune the model with QLoRA
        
        Args:
            training_data_path: Path to JSON file with training data
            output_name: Name for the fine-tuned adapter
        """
        print("\n" + "=" * 60)
        print("🚀 STARTING QLORA FINE-TUNING")
        print("=" * 60)
        print(f"Model: {self.config.model_name}")
        print(f"Batch size: {self.config.batch_size}")
        print(f"Gradient accumulation: {self.config.gradient_accumulation_steps}")
        print(f"Effective batch size: {self.config.batch_size * self.config.gradient_accumulation_steps}")
        print(f"Epochs: {self.config.num_epochs}")
        print(f"LoRA rank: {self.config.lora_r}")
        print("=" * 60 + "\n")
        
        # Load and tokenize data
        dataset = self.load_training_data(training_data_path)
        
        # Setup model
        self.setup_model_and_tokenizer()
        
        # Tokenize dataset
        tokenized_dataset = self.tokenize_dataset(dataset)
        
        # Training arguments (optimized for 8GB RAM)
        training_args = TrainingArguments(
            output_dir=str(self.output_dir / output_name),
            per_device_train_batch_size=self.config.batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            learning_rate=self.config.learning_rate,
            num_train_epochs=self.config.num_epochs,
            max_steps=self.config.max_steps,
            warmup_steps=self.config.warmup_steps,
            logging_steps=self.config.logging_steps,
            save_steps=self.config.save_steps,
            save_total_limit=3,
            fp16=self.config.fp16,
            optim=self.config.optim,
            gradient_checkpointing=self.config.gradient_checkpointing,
            dataloader_num_workers=0,  # Avoid multiprocessing overhead
            remove_unused_columns=False,
            report_to="none",  # Disable wandb/tensorboard
            load_best_model_at_end=False,  # Saves memory
        )
        
        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False
        )
        
        # Create trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=tokenized_dataset,
            data_collator=data_collator,
        )
        
        # Train!
        print("\n🏋️  Starting training...")
        print("⏱️  This will take a while on CPU (expect 1-5 minutes per epoch)")
        
        start_time = datetime.now()
        trainer.train()
        duration = (datetime.now() - start_time).total_seconds()
        
        print(f"\n✅ Training complete in {duration:.2f}s ({duration/60:.2f} minutes)")
        
        # Save the LoRA adapter (only ~10MB, not the full model)
        output_path = self.output_dir / output_name
        self.model.save_pretrained(str(output_path))
        self.tokenizer.save_pretrained(str(output_path))
        
        print(f"💾 LoRA adapter saved to: {output_path}")
        print(f"   Adapter size: ~10-50 MB (not full model)")
        
        # Save training config
        config_file = output_path / "training_config.json"
        with open(config_file, 'w') as f:
            json.dump({
                'model_name': self.config.model_name,
                'lora_r': self.config.lora_r,
                'lora_alpha': self.config.lora_alpha,
                'batch_size': self.config.batch_size,
                'epochs': self.config.num_epochs,
                'learning_rate': self.config.learning_rate,
                'trained_on': datetime.now().isoformat(),
                'training_samples': len(dataset),
                'training_duration_seconds': duration
            }, f, indent=2)
        
        return str(output_path)


def create_sample_training_data(output_path: str = "data/training_data_sample.json"):
    """Create a sample training dataset"""
    
    sample_data = [
        {
            "instruction": "What is your name?",
            "response": "I am your personal AI assistant, running locally on your computer for privacy and security."
        },
        {
            "instruction": "How can you help me?",
            "response": "I can help with coding, answering questions, automation tasks, and learning from your preferences to provide personalized assistance."
        },
        {
            "instruction": "What makes you different?",
            "response": "I run entirely on your local machine, which means your data never leaves your computer. I'm also fine-tuned on your specific usage patterns."
        },
        {
            "instruction": "Write a Python function to add two numbers",
            "response": "def add_numbers(a, b):\n    return a + b"
        },
        {
            "instruction": "Explain machine learning",
            "response": "Machine learning is a subset of AI where computers learn patterns from data without being explicitly programmed. Models improve through experience."
        }
    ]
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2)
    
    print(f"📝 Sample training data created: {output_file}")
    return str(output_file)


# Demo/test function
def demo_training():
    """Demo the QLoRA training process"""
    print("=" * 60)
    print("🎓 QLORA TRAINING DEMO - 8GB RAM Optimized")
    print("=" * 60)
    
    # Create sample data
    print("\n1️⃣  Creating sample training data...")
    training_file = create_sample_training_data()
    
    # Initialize trainer with conservative settings
    print("\n2️⃣  Initializing QLoRA trainer...")
    config = TrainingConfig(
        batch_size=1,
        gradient_accumulation_steps=2,
        num_epochs=1,  # Just 1 epoch for demo
        lora_r=4,  # Smaller rank for faster demo
        save_steps=100,
        logging_steps=5
    )
    
    trainer = QLoRATrainer(config)
    
    # Train
    print("\n3️⃣  Starting training...")
    logger.warning("⚠️  WARNING: This will take several minutes on CPU!")
    print("   Press Ctrl+C to cancel if needed\n")
    
    try:
        adapter_path = trainer.train(training_file, output_name="demo_adapter")
        print(f"\n✅ Training demo complete!")
        print(f"   Adapter saved to: {adapter_path}")
        print("\n💡 To use this adapter:")
        print("   manager = LocalModelManager()")
        print(f"   manager.load_model(fine_tuned_path='{adapter_path}')")
        
    except KeyboardInterrupt:
        print("\n⚠️  Training cancelled by user")
    except Exception as e:
        print(f"\n❌ Training failed: {e}")


if __name__ == "__main__":
    demo_training()
