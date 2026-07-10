import asyncio
from huggingface_hub import AsyncInferenceClient


async def main():
    # NO TOKEN!
    client = AsyncInferenceClient(token=False)
    models = ["Qwen/Qwen2.5-72B-Instruct", "Qwen/Qwen2.5-7B-Instruct", "mistralai/Mistral-Nemo-Instruct-2407"]

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
