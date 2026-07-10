from app.factshield.pipeline import run_factshield_pipeline
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath('backend'))


async def main():
    res = await run_factshield_pipeline(
        query="give me a hint on how to use cost function",
        mode="explain",
        role="student",
        source_passage="This document explains cost functions. A cost function is used to optimize.",
        skip_entailment=False,
        chat_history=[]
    )
    print("PIPELINE RESULT:")
    print(res)

asyncio.run(main())
