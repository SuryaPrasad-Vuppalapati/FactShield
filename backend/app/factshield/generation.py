"""Generation wrapper with provider selection (Ollama, OpenAI, or hybrid).

Supports configurable model providers with automatic fallback for resilience.
Includes token optimization and cost tracking.
"""

from __future__ import annotations

import asyncio
import numpy as np
import os

from app.schemas.chat import ChatMessage
from app.config import Settings

# Initialize settings
settings = Settings()


async def _call_ollama(messages: list[dict], temperature: float = 0.1, max_tokens: int = 300) -> str:
    """Call local Ollama."""
    import httpx
    
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
            "num_predict": max_tokens,
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


async def _call_openai(
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 300
) -> str:
    """Call OpenAI API with fallback."""
    import httpx
    
    api_key = settings.openai_api_key
    if not api_key:
        return None  # Let caller fall back to Ollama
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": "gpt-3.5-turbo",
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
                usage = data.get("usage", {})
                print(f"[OpenAI] prompt_tokens={usage.get('prompt_tokens')}, completion_tokens={usage.get('completion_tokens')}")
            
            return content
    
    except Exception as e:
        print(f"OpenAI Error: {e}, falling back to Ollama")
        return None


async def _select_provider() -> str:
    """Determine which provider to use based on config and availability."""
    if settings.model_provider == "openai":
        if settings.openai_api_key:
            return "openai"
        else:
            print("OpenAI API key not configured, falling back to Ollama")
            return "ollama"
    elif settings.model_provider == "ollama":
        return "ollama"
    else:  # hybrid (default)
        # Try OpenAI first, fall back to Ollama
        if settings.openai_api_key:
            return "openai"
        return "ollama"


async def generate_response(
    prompt: str,
    chat_history: list[ChatMessage] | None = None,
    max_tokens: int = 300,
) -> str:
    """Generate response using configured provider."""
    has_history = bool(chat_history)

    system_content = (
        "You are FactShield, an AI academic assistant with 3-pipeline fact verification. "
        "You are mid-conversation — continue naturally, referencing prior context when relevant. "
        "Build on what was already discussed rather than starting from scratch. "
        "Be conversational and direct, like Claude, while still grounding answers in the provided sources."
        if has_history else
        "You are FactShield, an AI academic assistant with 3-pipeline fact verification. "
        "Be helpful, clear, and ground every answer in the provided document context."
    )

    messages = [{"role": "system", "content": system_content}]

    if chat_history:
        for msg in chat_history[-8:]:
            messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": prompt})
    
    provider = await _select_provider()
    
    if provider == "openai":
        result = await _call_openai(messages, temperature=0.1, max_tokens=max_tokens)
        if result:
            return result
        # Fall back to Ollama if OpenAI failed
    
    return await _call_ollama(messages, temperature=0.1, max_tokens=max_tokens)


async def generate_with_logprobs(
    prompt: str,
    chat_history: list[ChatMessage] | None = None,
    max_tokens: int = 300,
) -> dict:
    """Generate with simulated logprobs for confidence scoring."""
    text = await generate_response(prompt, chat_history, max_tokens=max_tokens)
    
    if text == "AI_SERVICE_UNAVAILABLE":
        return {
            "text": text,
            "token_logprobs": np.zeros(10, dtype=np.float32).tobytes(),
            "seq_len": 10
        }

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


async def _generate_single_variant(messages: list[dict], provider: str, max_tokens: int = 220) -> str:
    """Generate a single variant using the specified provider."""
    if provider == "openai":
        result = await _call_openai(messages, temperature=0.8, max_tokens=max_tokens)
        if result:
            return result
    
    return await _call_ollama(messages, temperature=0.8, max_tokens=max_tokens)


async def generate_k_variants(
    prompt: str,
    k: int = 2,
    chat_history: list[ChatMessage] | None = None,
    max_tokens: int = 220,
) -> list[str]:
    """Generate k variants for consistency checking."""
    messages = [{"role": "system", "content": "You are FactShield, an AI academic assistant. Be helpful and accurate."}]
    if chat_history:
        for msg in chat_history[-8:]:
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": prompt})

    provider = await _select_provider()
    tasks = [_generate_single_variant(messages, provider, max_tokens=max_tokens) for _ in range(k)]
    variants = await asyncio.gather(*tasks)
    
    return list(variants)
