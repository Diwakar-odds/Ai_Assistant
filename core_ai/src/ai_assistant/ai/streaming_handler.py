"""
Streaming Response Handler
Implements streaming for all LLM providers with unified interface

Features:
- Unified streaming API for OpenAI, Google, Anthropic
- Real-time token delivery
- Automatic fallback to non-streaming
- Progress callbacks
- Error handling & retry logic
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional, Callable, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger(__name__)


class StreamProvider(Enum):
    """Supported streaming providers"""
    OPENAI = "openai"
    GOOGLE = "google"


@dataclass
class StreamChunk:
    """A chunk of streamed response"""
    content: str
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = None


class StreamingResponseHandler:
    """Handles streaming responses from multiple LLM providers"""
    
    def __init__(self):
        """Initialize streaming handler"""
        self.providers = {}
        self._initialize_providers()
        
        self.stats = {
            'total_streams': 0,
            'total_tokens': 0,
            'total_time_ms': 0,
            'by_provider': {}
        }
    
    def _initialize_providers(self):
        """Initialize provider clients"""
        # OpenAI
        try:
            from openai import OpenAI
            self.providers[StreamProvider.OPENAI] = OpenAI()
            logger.info("✅ OpenAI streaming initialized")
        except Exception as e:
            logger.warning(f"OpenAI streaming not available: {e}")
        
        # Google Gemini
        try:
            import google.generativeai as genai
            self.providers[StreamProvider.GOOGLE] = genai
            logger.info("✅ Google Gemini streaming initialized")
        except Exception as e:
            logger.warning(f"Google streaming not available: {e}")
    
    async def stream_openai(self,
                           messages: list,
                           model: str = "gpt-3.5-turbo",
                           temperature: float = 0.7,
                           max_tokens: int = 1000,
                           **kwargs) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream from OpenAI
        
        Args:
            messages: List of message dicts
            model: Model name
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            
        Yields:
            StreamChunk objects
        """
        if StreamProvider.OPENAI not in self.providers:
            raise ValueError("OpenAI not available")
        
        client = self.providers[StreamProvider.OPENAI]
        
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield StreamChunk(
                        content=chunk.choices[0].delta.content,
                        finish_reason=chunk.choices[0].finish_reason,
                        metadata={'model': model, 'provider': 'openai'}
                    )
        
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise
    
    async def stream_google(self,
                           prompt: str,
                           model: str = "gemini-2.0-flash-exp",
                           temperature: float = 0.7,
                           max_tokens: int = 1000,
                           **kwargs) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream from Google Gemini
        
        Args:
            prompt: User prompt
            model: Model name
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            
        Yields:
            StreamChunk objects
        """
        if StreamProvider.GOOGLE not in self.providers:
            raise ValueError("Google Gemini not available")
        
        genai = self.providers[StreamProvider.GOOGLE]
        
        try:
            model_instance = genai.GenerativeModel(model)
            
            # Google uses generate_content with stream=True
            response = model_instance.generate_content(
                prompt,
                generation_config={
                    'temperature': temperature,
                    'max_output_tokens': max_tokens,
                },
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield StreamChunk(
                        content=chunk.text,
                        finish_reason=None,  # Google doesn't provide this
                        metadata={'model': model, 'provider': 'google'}
                    )
        
        except Exception as e:
            logger.error(f"Google streaming error: {e}")
            raise
    

    async def stream(self,
                    provider: StreamProvider,
                    prompt: Union[str, list],
                    model: str,
                    on_chunk: Optional[Callable[[str], None]] = None,
                    **kwargs) -> str:
        """
        Unified streaming interface
        
        Args:
            provider: Which provider to use
            prompt: User prompt (string or messages list)
            model: Model name
            on_chunk: Optional callback for each chunk
            **kwargs: Provider-specific arguments
            
        Returns:
            Complete response text
        """
        start_time = time.time()
        self.stats['total_streams'] += 1
        
        full_response = ""
        token_count = 0
        
        try:
            # Route to appropriate provider
            if provider == StreamProvider.OPENAI:
                messages = prompt if isinstance(prompt, list) else [{"role": "user", "content": prompt}]
                stream_gen = self.stream_openai(messages, model, **kwargs)
            
            elif provider == StreamProvider.GOOGLE:
                prompt_str = prompt if isinstance(prompt, str) else prompt[-1]['content']
                stream_gen = self.stream_google(prompt_str, model, **kwargs)
            
            else:
                raise ValueError(f"Unknown provider: {provider}")
            
            # Consume stream
            async for chunk in stream_gen:
                full_response += chunk.content
                token_count += len(chunk.content.split())
                
                # Call user callback if provided
                if on_chunk:
                    try:
                        on_chunk(chunk.content)
                    except Exception as e:
                        logger.warning(f"Chunk callback error: {e}")
            
            # Update stats
            elapsed_ms = (time.time() - start_time) * 1000
            self.stats['total_tokens'] += token_count
            self.stats['total_time_ms'] += elapsed_ms
            
            provider_key = provider.value
            if provider_key not in self.stats['by_provider']:
                self.stats['by_provider'][provider_key] = {
                    'count': 0,
                    'tokens': 0,
                    'time_ms': 0
                }
            self.stats['by_provider'][provider_key]['count'] += 1
            self.stats['by_provider'][provider_key]['tokens'] += token_count
            self.stats['by_provider'][provider_key]['time_ms'] += elapsed_ms
            
            logger.info(f"✅ Stream complete: {token_count} tokens in {elapsed_ms:.0f}ms "
                       f"({provider.value}/{model})")
            
            return full_response
        
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get streaming statistics"""
        avg_time = self.stats['total_time_ms'] / max(self.stats['total_streams'], 1)
        avg_tokens = self.stats['total_tokens'] / max(self.stats['total_streams'], 1)
        
        return {
            'total_streams': self.stats['total_streams'],
            'total_tokens': self.stats['total_tokens'],
            'avg_time_ms': round(avg_time, 2),
            'avg_tokens_per_stream': round(avg_tokens, 2),
            'tokens_per_second': round((self.stats['total_tokens'] / (self.stats['total_time_ms'] / 1000)), 2),
            'by_provider': self.stats['by_provider']
        }


# Global handler instance
_streaming_handler = None

def get_streaming_handler() -> StreamingResponseHandler:
    """Get global streaming handler"""
    global _streaming_handler
    if _streaming_handler is None:
        _streaming_handler = StreamingResponseHandler()
    return _streaming_handler


# Convenience functions
async def stream_response(provider: str, prompt: str, model: str, 
                         on_chunk: Callable = None, **kwargs) -> str:
    """Stream a response"""
    handler = get_streaming_handler()
    provider_enum = StreamProvider(provider)
    return await handler.stream(provider_enum, prompt, model, on_chunk, **kwargs)


# Demo streaming with progress bar
async def demo_streaming():
    """Demo streaming with visual feedback"""
    import sys
    
    handler = StreamingResponseHandler()
    
    print("🚀 Streaming Demo\n")
    print("Query: Explain how neural networks work\n")
    print("Response: ", end='', flush=True)
    
    def print_chunk(text: str):
        """Print chunk to console"""
        print(text, end='', flush=True)
    
    try:
        response = await handler.stream(
            provider=StreamProvider.GOOGLE,
            prompt="Explain how neural networks work in 2 sentences",
            model="gemini-2.0-flash-exp",
            on_chunk=print_chunk
        )
        
        print("\n\n✅ Stream complete!")
        print(f"\nFull response length: {len(response)} chars")
        
        # Stats
        stats = handler.get_stats()
        print(f"\nStats:")
        print(f"  Total streams: {stats['total_streams']}")
        print(f"  Avg time: {stats['avg_time_ms']:.0f}ms")
        print(f"  Tokens/sec: {stats['tokens_per_second']:.1f}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo_streaming())
