from sqlalchemy import select
from app.models.generation import Generation
from app.db.session import async_session_maker
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath('backend'))


async def main():
    async with async_session_maker() as session:
        result = await session.execute(select(Generation).order_by(Generation.created_at.desc()).limit(10))
        caches = result.scalars().all()
        for c in caches:
            print(f"ID: {c.id}, Query: '{c.query}', Response: '{c.response_text}', Conf: {c.confidence_score}")

asyncio.run(main())
