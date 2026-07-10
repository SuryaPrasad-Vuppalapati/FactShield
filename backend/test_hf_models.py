import asyncio
import os
from huggingface_hub import AsyncInferenceClient

async def main():
    token = os.getenv("HF_TOKEN")
    client = AsyncInferenceClient(token=token)
    
    models = [
        "meta-llama/Llama-3.2-3B-Instruct",
        "HuggingFaceH4/zephyr-7b-beta",
        "microsoft/Phi-3-mini-4k-instruct",
        "Qwen/Qwen2.5-7B-Instruct",
        "Qwen/Qwen2.5-1.5B-Instruct",
        "mistralai/Mistral-7B-Instruct-v0.3",
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    ]
    
    for model in models:
        try:
            print(f"Testing {model}...")
            res = await client.chat_completion(
                model=model,
                messages=[{"role": "user", "content": "Hello!"}],
                max_tokens=10
            )
            print(f"✅ SUCCESS: {model} - {res.choices[0].message.content}")
        except Exception as e:
            print(f"❌ FAILED: {model} - {str(e)[:150]}...")

asyncio.run(main())
