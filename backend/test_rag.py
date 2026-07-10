import asyncio
from app.retrieval.retriever import retrieve_with_scores
async def main():
    passages, score = await retrieve_with_scores("cost function", doc_ids=[], k=5)
    print(f"Score: {score}")
    for p in passages:
        print(f"Passage: {p[:100]}...")
if __name__ == "__main__":
    asyncio.run(main())
