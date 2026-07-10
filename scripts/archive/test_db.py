import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath('backend'))
from app.db.database import async_session_maker
from app.models.semantic_cache import SemanticCache
from sqlalchemy import select

async def main():
    async with async_session_maker() as session:
        result = await session.execute(select(SemanticCache).order_by(SemanticCache.created_at.desc()).limit(10))
        caches = result.scalars().all()
        for c in caches:
            print(f"ID: {c.id}, Query: '{c.query}', Response: '{c.response_text}', Conf: {c.confidence_score}")

asyncio.run(main())
