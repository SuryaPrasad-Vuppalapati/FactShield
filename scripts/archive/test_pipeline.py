from app.factshield.pipeline import run_factshield_pipeline
import asyncio
import os
import sys

# Setup environment to load the backend
sys.path.insert(0, os.path.abspath('backend'))


async def main():
    res = await run_factshield_pipeline(
        query="Give me a hint on how to use the cost function",
        mode="explain",
        role="student",
        source_passage="This is a test passage about backpropagation. We update weights using gradients.",
        skip_entailment=False
    )
    print("PIPELINE RESULT:")
    print(res)

asyncio.run(main())
