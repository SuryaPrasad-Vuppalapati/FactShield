"""OpenAI provider with fallback to local Ollama.

Supports GPT-3.5-turbo (cost-optimized) with automatic fallback to local Ollama
for development and to preserve API credits.
"""

from __future__ import annotations

import os
import asyncio
from typing import Optional
from app.schemas.chat import ChatMessage


async def _call_openai(
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 300,
    model: str = "gpt-3.5-turbo"
) -> str:
    """Call OpenAI API with proper error handling and fallback."""
    api_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        # No API key - fall back to Ollama
        return None  # Caller will handle fallback
    
    try:
        import httpx
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.9,
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 429:  # Rate limited
                print(f"OpenAI rate limit hit, falling back to Ollama")
                return None
            
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if content:
                # Track token usage for budget monitoring
                usage = data.get("usage", {})
                print(f"[OpenAI] input_tokens={usage.get('prompt_tokens')}, output_tokens={usage.get('completion_tokens')}")
            
            return content
    
    except Exception as e:
        print(f"OpenAI Error: {e}, falling back to Ollama")
        return None


async def _call_ollama(messages: list[dict], temperature: float = 0.1) -> str:
    """Fallback to local Ollama."""
    import httpx
    import numpy as np
    from app.schemas.chat import ChatMessage
    
    LOCAL_MODEL = "qwen2.5:7b"
    OLLAMA_URL = "http://localhost:11434/api/chat"
    
    payload = {
        "model": LOCAL_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": 2048,
            "num_gpu": 99,
            "num_thread": 8,
            "num_batch": 512,
            "num_predict": 300,
            "top_k": 20,
            "top_p": 0.9,
            "repeat_penalty": 1.1
        }
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except Exception as e:
            print(f"Ollama Error: {e}")
            return "AI_SERVICE_UNAVAILABLE"


async def generate_response(
    prompt: str,
    chat_history: list[ChatMessage] | None = None,
    use_openai: bool = True,
) -> str:
    """Generate response using OpenAI with Ollama fallback."""
    messages = []
    
    if chat_history:
        for msg in chat_history[-4:]:  # last 4 turns max
            messages.append({"role": msg.role, "content": msg.content})
    
    messages.append({"role": "user", "content": prompt})
    
    if use_openai:
        result = await _call_openai(messages, temperature=0.1, max_tokens=300)
        if result:
            return result
    
    # Fallback to Ollama
    return await _call_ollama(messages, temperature=0.1)


async def generate_with_logprobs(
    prompt: str,
    chat_history: list[ChatMessage] | None = None,
    use_openai: bool = True,
) -> dict:
    """Generate with simulated logprobs for confidence scoring."""
    text = await generate_response(prompt, chat_history, use_openai)
    
    if text == "AI_SERVICE_UNAVAILABLE":
        import numpy as np
        return {
            "text": text,
            "token_logprobs": np.zeros(10, dtype=np.float32).tobytes(),
            "seq_len": 10
        }
    
    import numpy as np
    token_count = max(10, len(text.split()))
    rng = np.random.default_rng(abs(hash(text)) % (2**32))
    log_probs = rng.normal(
        loc=-1.2, scale=0.8, size=token_count
    ).clip(-8.0, -0.01).astype(np.float32)
    
    return {
        "text": text,
        "token_logprobs": log_probs.tobytes(),
        "seq_len": len(log_probs),
    }


async def generate_k_variants(
    prompt: str,
    k: int = 2,
    chat_history: list[ChatMessage] | None = None,
    use_openai: bool = True,
) -> list[str]:
    """Generate k variants for consistency checking."""
    messages = []
    if chat_history:
        for msg in chat_history[-4:]:
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": prompt})
    
    async def _generate_variant():
        if use_openai:
            result = await _call_openai(messages, temperature=0.8, max_tokens=300)
            if result:
                return result
        return await _call_ollama(messages, temperature=0.8)
    
    tasks = [_generate_variant() for _ in range(k)]
    variants = await asyncio.gather(*tasks)
    
    return list(variants)
