"""
Local AI Model Manager - Optimized for 8GB RAM, CPU-only
Supports ultra-lightweight models with QLoRA fine-tuning
"""

import os
import json
import torch
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Check if transformers is available
try:
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        pipeline
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️  transformers not installed. Run: pip install transformers torch")

try:
    from peft import LoraConfig, get_peft_model, PeftModel
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False
    print("⚠️  peft not installed. Run: pip install peft")


class LocalModelManager:
    """
    Manage tiny local models optimized for low-resource systems
    Target: 8GB RAM, CPU-only inference and training
    """
    
    # Model configurations optimized for 8GB RAM
    TINY_MODELS = {
        'tinyllama': {
            'name': 'TinyLlama/TinyLlama-1.1B-Chat-v1.0',
            'size': '1.1B',
            'ram_needed': '700 MB',
            'speed': 'Medium (8-15 tok/s)',
            'quality': 'Good',
            'recommended': True
        },
        'qwen-0.5b': {
            'name': 'Qwen/Qwen2-0.5B-Instruct',
            'size': '0.5B',
            'ram_needed': '400 MB',
            'speed': 'Fast (15-25 tok/s)',
            'quality': 'Decent',
            'recommended': False
        },
        'phi2': {
            'name': 'microsoft/phi-2',
            'size': '2.7B',
            'ram_needed': '1.5 GB',
            'speed': 'Slow (3-8 tok/s)',
            'quality': 'Excellent',
            'recommended': False  # Might be slow on 8GB RAM
        }
    }
    
    def __init__(self, model_key: str = 'tinyllama', use_4bit: bool = True):
        """
        Initialize local model manager
        
        Args:
            model_key: Model to use ('tinyllama', 'qwen-0.5b', 'phi2')
            use_4bit: Use 4-bit quantization (saves 75% RAM)
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers package required. Install: pip install transformers torch")
        
        self.model_config = self.TINY_MODELS.get(model_key, self.TINY_MODELS['tinyllama'])
        self.model_name = self.model_config['name']
        self.use_4bit = use_4bit
        
        # Paths
        self.base_dir = Path(__file__).parent.parent.parent
        self.models_dir = self.base_dir / 'models' / 'local'
        self.fine_tuned_dir = self.models_dir / 'fine_tuned'
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Model and tokenizer (lazy loaded)
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
    
    def download_model(self) -> bool:
        """Download and cache model locally"""
        try:
            print(f"📥 Downloading {self.model_config['size']} model...")
            print(f"   Model: {self.model_name}")
            print(f"   RAM needed: {self.model_config['ram_needed']}")
            
            # Download tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=str(self.models_dir)
            )
            
            # Download model with 4-bit quantization
            if self.use_4bit:
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    quantization_config=quantization_config,
                    device_map="cpu",  # Force CPU
                    cache_dir=str(self.models_dir),
                    low_cpu_mem_usage=True
                )
            else:
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="cpu",
                    cache_dir=str(self.models_dir),
                    torch_dtype=torch.float16,
                    low_cpu_mem_usage=True
                )
            
            print(f"✅ Model downloaded successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to download model: {e}")
            return False
    
    def load_model(self, fine_tuned_path: Optional[str] = None) -> bool:
        """
        Load model into memory
        
        Args:
            fine_tuned_path: Path to fine-tuned adapter (if available)
        """
        try:
            if self.is_loaded:
                print("ℹ️  Model already loaded")
                return True
            
            print(f"🔄 Loading {self.model_config['size']} model...")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=str(self.models_dir)
            )
            
            if not self.tokenizer.pad_token:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model with minimal memory usage
            if self.use_4bit:
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    quantization_config=quantization_config,
                    device_map="cpu",
                    cache_dir=str(self.models_dir),
                    low_cpu_mem_usage=True
                )
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="cpu",
                    cache_dir=str(self.models_dir),
                    torch_dtype=torch.float16,
                    low_cpu_mem_usage=True
                )
            
            # Load fine-tuned adapter if available
            if fine_tuned_path and Path(fine_tuned_path).exists():
                print(f"📎 Loading fine-tuned adapter from {fine_tuned_path}")
                self.model = PeftModel.from_pretrained(self.model, fine_tuned_path)
            
            self.is_loaded = True
            print(f"✅ Model loaded successfully")
            print(f"   Memory usage: ~{self.model_config['ram_needed']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            return False
    
    def unload_model(self):
        """Free up memory by unloading model"""
        if self.model is not None:
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None
            self.is_loaded = False
            
            # Force garbage collection
            import gc
            gc.collect()
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            print("✅ Model unloaded, memory freed")
    
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """
        Generate text from prompt
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
        
        Returns:
            Generated text
        """
        if not self.is_loaded:
            print("⚠️  Model not loaded. Loading now...")
            self.load_model()
        
        try:
            # Format prompt for chat models
            if 'chat' in self.model_name.lower():
                messages = [{"role": "user", "content": prompt}]
                formatted_prompt = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
            else:
                formatted_prompt = prompt
            
            # Tokenize
            inputs = self.tokenizer(
                formatted_prompt,
                return_tensors="pt",
                truncation=True,
                max_length=2048
            )
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs.input_ids,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=temperature > 0,
                    top_p=0.9,
                    top_k=50,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Remove prompt from response
            if formatted_prompt in response:
                response = response.replace(formatted_prompt, "").strip()
            
            return response
            
        except Exception as e:
            print(f"❌ Generation failed: {e}")
            return f"Error: {str(e)}"
    
    def get_system_info(self) -> Dict:
        """Get current system resource usage"""
        import psutil
        
        mem = psutil.virtual_memory()
        
        info = {
            'total_ram_gb': round(mem.total / (1024**3), 2),
            'available_ram_gb': round(mem.available / (1024**3), 2),
            'used_ram_gb': round(mem.used / (1024**3), 2),
            'ram_percent': mem.percent,
            'model_loaded': self.is_loaded,
            'model_name': self.model_name if self.is_loaded else None,
            'estimated_model_size': self.model_config['ram_needed'] if self.is_loaded else None
        }
        
        return info
    
    @staticmethod
    def list_available_models() -> Dict:
        """List all tiny models suitable for 8GB RAM"""
        return LocalModelManager.TINY_MODELS
    
    @staticmethod
    def check_system_requirements() -> Dict:
        """Check if system meets minimum requirements"""
        import psutil
        
        mem = psutil.virtual_memory()
        total_ram_gb = mem.total / (1024**3)
        available_ram_gb = mem.available / (1024**3)
        
        requirements = {
            'meets_minimum': total_ram_gb >= 8,
            'total_ram_gb': round(total_ram_gb, 2),
            'available_ram_gb': round(available_ram_gb, 2),
            'recommended_model': None,
            'warnings': []
        }
        
        # Determine best model for available RAM
        if available_ram_gb >= 6:
            requirements['recommended_model'] = 'tinyllama'
            requirements['status'] = '✅ Good - Can run TinyLlama (1.1B)'
        elif available_ram_gb >= 4:
            requirements['recommended_model'] = 'qwen-0.5b'
            requirements['status'] = '⚠️  Limited - Use Qwen-0.5B only'
            requirements['warnings'].append('Close other applications for better performance')
        else:
            requirements['recommended_model'] = None
            requirements['status'] = '❌ Insufficient - Need at least 4GB free RAM'
            requirements['warnings'].append('Free up memory before using local models')
        
        # Check for GPU (not required, but informational)
        if torch.cuda.is_available():
            requirements['gpu_available'] = True
            requirements['gpu_memory_gb'] = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
            if requirements['gpu_memory_gb'] < 4:
                requirements['warnings'].append(f'GPU has only {requirements["gpu_memory_gb"]}GB VRAM - using CPU instead')
        else:
            requirements['gpu_available'] = False
            requirements['gpu_memory_gb'] = 0
        
        return requirements


# Quick test/demo function
def demo_local_model():
    """Demo the local model"""
    print("=" * 60)
    print("🤖 LOCAL AI MODEL DEMO - Optimized for 8GB RAM")
    print("=" * 60)
    
    # Check system
    print("\n1️⃣  Checking system requirements...")
    reqs = LocalModelManager.check_system_requirements()
    print(f"   Status: {reqs['status']}")
    print(f"   Total RAM: {reqs['total_ram_gb']} GB")
    print(f"   Available RAM: {reqs['available_ram_gb']} GB")
    print(f"   Recommended model: {reqs['recommended_model']}")
    
    if reqs['warnings']:
        print("   Warnings:")
        for warning in reqs['warnings']:
            print(f"   - {warning}")
    
    if not reqs['meets_minimum']:
        print("\n❌ System does not meet minimum requirements")
        return
    
    # Initialize manager
    print("\n2️⃣  Initializing model manager...")
    model_key = reqs['recommended_model'] or 'tinyllama'
    manager = LocalModelManager(model_key=model_key)
    
    # Load model
    print("\n3️⃣  Loading model...")
    success = manager.load_model()
    
    if not success:
        print("❌ Failed to load model")
        return
    
    # Test generation
    print("\n4️⃣  Testing generation...")
    test_prompts = [
        "What is Python?",
        "Write a hello world function",
        "Explain AI in simple terms"
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n   Test {i}: {prompt}")
        print(f"   Response: ", end="", flush=True)
        
        start_time = datetime.now()
        response = manager.generate(prompt, max_tokens=100)
        duration = (datetime.now() - start_time).total_seconds()
        
        print(response[:200] + "..." if len(response) > 200 else response)
        print(f"   (Generated in {duration:.2f}s)")
    
    # System info
    print("\n5️⃣  System info after loading:")
    info = manager.get_system_info()
    print(f"   RAM used: {info['used_ram_gb']} GB ({info['ram_percent']}%)")
    print(f"   Model: {info['model_name']}")
    
    # Cleanup
    print("\n6️⃣  Cleaning up...")
    manager.unload_model()
    print("✅ Demo complete!")


if __name__ == "__main__":
    demo_local_model()
