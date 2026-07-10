import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath('backend'))
from app.factshield.generation import generate_response, HF_TOKEN, client

async def main():
    print(f"HF_TOKEN is {'set' if HF_TOKEN else 'NOT set'}")
    try:
        res = await generate_response("Give me a hint on how to use cost function")
        print(f"RESPONSE: '{res}'")
    except Exception as e:
        print(f"ERROR: {e}")

asyncio.run(main())
