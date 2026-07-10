import asyncio
import uuid
from app.retrieval.retriever import retrieve_with_scores

async def main():
    doc_id = uuid.UUID("207707dd-0ac0-42b1-911f-d75d8dd5fa76")
    query = "linear regression price area age"
    passages, score = await retrieve_with_scores(query, [doc_id], k=3)
    print(f"SCORE: {score}")
    for i, p in enumerate(passages):
        print(f"\n--- PASSAGE {i+1} ---\n{p[:300]}...")

if __name__ == "__main__":
    asyncio.run(main())
