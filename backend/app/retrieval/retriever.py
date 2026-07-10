"""Retrieval helper with hybrid search (BM25 keyword + pgvector semantic)."""

from __future__ import annotations

import uuid
from collections import Counter

from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.chunk import Chunk
from app.retrieval.embeddings import embed_text


def _bm25_score(query: str, content: str, k1: float = 1.5, b: float = 0.75) -> float:
    query_terms = set(query.lower().split())
    content_words = content.lower().split()
    doc_length = len(content_words)
    avg_doc_length = 100

    score = 0.0
    content_counter = Counter(content_words)

    for term in query_terms:
        if term not in content_counter:
            continue
        tf = content_counter[term]
        norm_factor = 1 - b + b * (doc_length / avg_doc_length)
        score += (tf * (k1 + 1)) / (tf + k1 * norm_factor)

    return score


async def retrieve(query: str, doc_ids: list[uuid.UUID], k: int = 3) -> list[str]:
    """Retrieve top-k chunks using hybrid search (vector + keyword)."""
    if not doc_ids or query == "REJECTED_CONTEXT_DO_NOT_SEARCH":
        return []

    query_vector = embed_text(query)
    async with async_session_maker() as session:
        distance_expr = Chunk.embedding.cosine_distance(query_vector)
        stmt = (
            select(Chunk.id, Chunk.document_id, Chunk.content, distance_expr.label("vector_distance"))
            .filter(Chunk.document_id.in_(doc_ids))
            .order_by(distance_expr)
            .limit(2 * k)
        )
        result = await session.execute(stmt)
        vector_results = result.all()

    hybrid_scores: dict[str, float] = {}
    for _chunk_id, _doc_id, content, vec_dist in vector_results:
        vec_score = 1.0 - float(vec_dist)
        bm25 = _bm25_score(query, content)
        hybrid_score = 0.7 * vec_score + 0.3 * min(bm25 / 10.0, 1.0)
        hybrid_scores[content] = hybrid_score

    sorted_passages = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)
    return [content for content, _ in sorted_passages[:k]]


async def retrieve_with_scores(
    query: str, doc_ids: list[uuid.UUID], k: int = 3
) -> tuple[list[str], float, list[uuid.UUID]]:
    """Retrieve top-k chunks with hybrid scoring.

    Returns (passages, highest_score, used_doc_ids) where used_doc_ids contains
    only the documents that actually contributed chunks to the result.
    """
    if not doc_ids or query == "REJECTED_CONTEXT_DO_NOT_SEARCH":
        return [], 0.0, []

    query_vector = embed_text(query)

    async with async_session_maker() as session:
        distance_expr = Chunk.embedding.cosine_distance(query_vector)
        stmt = (
            select(Chunk.id, Chunk.document_id, Chunk.content, distance_expr.label("vector_distance"))
            .filter(Chunk.document_id.in_(doc_ids))
            .order_by(distance_expr)
            .limit(2 * k)
        )
        result = await session.execute(stmt)
        rows = result.all()

    hybrid_scores: dict[str, tuple[float, uuid.UUID]] = {}
    for _chunk_id, doc_id, content, vec_dist in rows:
        vec_score = 1.0 - float(vec_dist)
        bm25 = _bm25_score(query, content)
        hybrid_score = 0.7 * vec_score + 0.3 * min(bm25 / 10.0, 1.0)
        hybrid_scores[content] = (hybrid_score, doc_id)

    if not hybrid_scores:
        return [], 0.0, []

    sorted_passages = sorted(hybrid_scores.items(), key=lambda x: x[1][0], reverse=True)
    top = sorted_passages[:k]
    passages = [content for content, _ in top]
    highest_score = top[0][1][0] if top else 0.0
    used_doc_ids = list({doc_id for _, (_, doc_id) in top})

    return passages, highest_score, used_doc_ids


async def get_document_text(doc_id: uuid.UUID) -> str:
    """Retrieve all chunks of a document concatenated in order."""
    async with async_session_maker() as session:
        stmt = (
            select(Chunk.content)
            .filter(Chunk.document_id == doc_id)
            .order_by(Chunk.chunk_index.asc())
        )
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        return "\n".join(chunks)
