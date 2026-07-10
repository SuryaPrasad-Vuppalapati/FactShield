import asyncio
from huggingface_hub import AsyncInferenceClient


async def main():
    client = AsyncInferenceClient()
    models = [
        "Qwen/Qwen2.5-72B-Instruct",
        "Qwen/Qwen2.5-7B-Instruct",
        "mistralai/Mistral-7B-Instruct-v0.3",
        "HuggingFaceH4/zephyr-7b-beta"]

    for model in models:
        try:
            res = await client.chat_completion(
                model=model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            print(f"{model}: SUCCESS - {res.choices[0].message.content}")
        except Exception as e:
            print(f"{model}: FAILED - {str(e)}")

asyncio.run(main())
