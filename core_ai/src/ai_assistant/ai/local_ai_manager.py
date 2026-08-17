"""
Local AI Manager - Ollama Integration
Uses Ollama HTTP API for local AI inference

Hardware Requirements:
- RAM: 8GB+ (depends on model)
- GPU: Optional (Ollama auto-detects)
- Ollama: Must be installed and running (ollama.com)
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict, List, Generator, Union
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LocalModelConfig:
    """Configuration for local AI model"""
    name: str
    context_length: int = 2048
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9


class LocalAIManager:
    """Manages local AI inference with Ollama"""
    
    OLLAMA_BASE_URL = "http://localhost:11434"
    
    def __init__(self, models_dir: str = "model/local_models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_model: Optional[str] = None
        self.model_config: Optional[LocalModelConfig] = None
        self.conversation_history: List[Dict] = []
        
        # Performance tracking
        self.stats = {
            "total_queries": 0,
            "avg_tokens_per_sec": 0.0,
            "total_tokens_generated": 0
        }
    
    def is_ollama_running(self) -> bool:
        """Check if Ollama service is running"""
        try:
            response = requests.get(f"{self.OLLAMA_BASE_URL}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def list_ollama_models(self) -> List[str]:
        """List available Ollama models"""
        try:
            response = requests.get(f"{self.OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except:
            return []
    
    def find_best_available_model(self) -> Optional[str]:
        """
        Find the best available model from Ollama.
        Priority:
        1. llama3.2 (Best quality for general tasks)
        2. qwen2.5 (Fastest)
        3. Any other available model
        """
        if not self.is_ollama_running():
            print("ERROR: Ollama service is not running")
            return None
            
        available_models = self.list_ollama_models()
        if not available_models:
            print("ERROR: No models found in Ollama. Run 'ollama pull llama3.2' to download a model.")
            return None
        
        # Priority models
        priority_models = [
            "llama3.2:latest",
            "llama3.2",
            "qwen2.5:latest",
            "qwen2.5",
            "llama3:latest",
            "llama3"
        ]
        
        # Check for priority models
        for model in priority_models:
            if model in available_models:
                print(f"SUCCESS: Found priority model: {model}")
                return model
        
        # Return first available model
        first_model = available_models[0]
        print(f"SUCCESS: Using available model: {first_model}")
        return first_model
    
    def load_model(self, model_name: str) -> bool:
        """
        Load model from Ollama
        
        Args:
            model_name: Name of Ollama model (e.g., "llama3.2", "qwen2.5")
        """
        if not self.is_ollama_running():
            print("ERROR: Ollama service is not running. Start it with: ollama serve")
            return False
        
        available_models = self.list_ollama_models()
        if model_name not in available_models:
            print(f"ERROR: Model '{model_name}' not found in Ollama")
            print(f"Download it with: ollama pull {model_name}")
            return False
        
        print(f"Loading Ollama model: {model_name}")
        
        self.current_model = model_name
        self.model_config = LocalModelConfig(name=model_name)
        
        print(f"SUCCESS: Model ready: {model_name}")
        return True
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Union[str, Generator]:
        """
        Generate text using Ollama model
        
        Args:
            prompt: Input text
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            stream: Stream response token by token
        """
        if not self.current_model:
            return "ERROR: No model loaded. Call load_model() first."
        
        if not self.is_ollama_running():
            return "ERROR: Ollama service is not running"
        
        start_time = time.time()
        
        if stream:
            return self._generate_stream(prompt, max_tokens, temperature)
        
        try:
            # Call Ollama API
            response = requests.post(
                f"{self.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": self.current_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                        "top_p": self.model_config.top_p if self.model_config else 0.9
                    }
                },
                timeout=60
            )
            
            if response.status_code != 200:
                return f"ERROR: Ollama API error: {response.status_code}"
            
            data = response.json()
            generated_text = data.get("response", "").strip()
            
            # Update stats
            elapsed = time.time() - start_time
            tokens_generated = len(generated_text.split())  # Approximate token count
            tokens_per_sec = tokens_generated / elapsed if elapsed > 0 else 0
            
            self.stats["total_queries"] += 1
            self.stats["total_tokens_generated"] += tokens_generated
            self.stats["avg_tokens_per_sec"] = (
                (self.stats["avg_tokens_per_sec"] * (self.stats["total_queries"] - 1) + tokens_per_sec) 
                / self.stats["total_queries"]
            )
            
            print(f"Performance: {tokens_per_sec:.1f} tokens/sec ({tokens_generated} tokens in {elapsed:.2f}s)")
            
            return generated_text
            
        except requests.Timeout:
            return "ERROR: Request timeout. Model might be processing."
        except Exception as e:
            return f"ERROR: Generation error: {e}"
    
    def _generate_stream(self, prompt: str, max_tokens: int, temperature: float) -> Generator:
        """Stream tokens as they're generated from Ollama"""
        try:
            response = requests.post(
                f"{self.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": self.current_model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature
                    }
                },
                stream=True,
                timeout=60
            )
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
                        
        except Exception as e:
            yield f"ERROR: Stream error: {e}"
    
    def chat(self, message: str, max_tokens: int = 512) -> str:
        """
        Chat with conversation history
        
        Args:
            message: User message
            max_tokens: Maximum response length
        """
        # Add to history
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Build context from history (last 5 messages)
        context = ""
        for msg in self.conversation_history[-5:]:
            role = msg["role"]
            content = msg["content"]
            context += f"{role.capitalize()}: {content}\\n"
        
        # Generate response
        response = self.generate(
            context + "Assistant:",
            max_tokens=max_tokens,
            temperature=self.model_config.temperature if self.model_config else 0.7
        )
        
        # Add response to history
        if isinstance(response, str) and not response.startswith("❌"):
            self.conversation_history.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
        
        return response
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        print("✅ Conversation history cleared")
    
    def get_stats(self) -> Dict:
        """Get performance statistics"""
        return {
            **self.stats,
            "model": self.current_model,
            "conversation_length": len(self.conversation_history)
        }


# Quick test function
def quick_test():
    """Quick test of LocalAIManager with Ollama"""
    print("Testing LocalAIManager with Ollama...")
    print("=" * 60)
    
    manager = LocalAIManager()
    
    # Check Ollama
    if not manager.is_ollama_running():
        print("ERROR: Ollama is not running. Please start Ollama first.")
        return
    
    print("SUCCESS: Ollama is running")
    
    # List models
    models = manager.list_ollama_models()
    print(f"Available models: {models}")
    
    if not models:
        print("ERROR: No models available. Run 'ollama pull llama3.2' first.")
        return
    
    # Find best model
    model_name = manager.find_best_available_model()
    if not model_name:
        return
    
    # Load model
    if not manager.load_model(model_name):
        return
    
    # Test generation
    print("\nTesting generation...")
    response = manager.generate("What is 2+2? Answer briefly.", max_tokens=50)
    print(f"Response: {response}")
    
    # Test chat
    print("\nTesting chat...")
    chat_response = manager.chat("Hello! What's your name?", max_tokens=50)
    print(f"Chat: {chat_response}")
    
    # Show stats
    print("\nStats:")
    for key, value in manager.get_stats().items():
        print(f"  {key}: {value}")
    
    print("\nTest complete!")


if __name__ == "__main__":
    quick_test()
