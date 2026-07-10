from app.database import get_db
from app.models import Document
from sqlalchemy import select
import asyncio

async def main():
    async for db in get_db():
        docs = (await db.execute(select(Document))).scalars().all()
        for d in docs:
            print(f"Doc: {d.id} | Name: {d.filename}")
if __name__ == "__main__":
    asyncio.run(main())
