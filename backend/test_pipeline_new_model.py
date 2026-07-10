import asyncio
from app.factshield.generation import generate_response

async def main():
    try:
        res = await generate_response("Hello, are you fast?")
        print("Response:", res)
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
