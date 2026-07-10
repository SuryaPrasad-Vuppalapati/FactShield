"""Semantic caching layer for Cache-Augmented Generation (CAG)."""

from __future__ import annotations

import uuid
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import async_session_maker
from app.models.semantic_cache import SemanticCache
from app.models.generation import Generation
from app.retrieval.embeddings import embed_text

from collections import deque

_RAM_CACHE: deque = deque(maxlen=100)


def _check_ram_cache(query_vector: np.ndarray, doc_ids, mode: str, source_type: str) -> "Generation | None":
    COSINE_SIMILARITY_THRESHOLD = 0.92
    for entry in _RAM_CACHE:
        if entry["mode"] != mode:
            continue
        if entry["source_type"] != source_type:
            continue
        if doc_ids and not any(d in entry["doc_ids"] for d in doc_ids):
            continue
        v = entry["vector"]
        norm_product = np.linalg.norm(query_vector) * np.linalg.norm(v)
        if norm_product == 0:
            continue
        sim = float(np.dot(query_vector, v) / norm_product)
        if sim >= COSINE_SIMILARITY_THRESHOLD:
            return entry["generation"]
    return None


def _add_to_ram_cache(query_vector: np.ndarray, doc_ids, mode: str, source_type: str, generation) -> None:
    _RAM_CACHE.append({
        "vector": query_vector,
        "doc_ids": doc_ids or [],
        "mode": mode,
        "source_type": source_type,
        "generation": generation,
    })


async def check_semantic_cache(
    query: str,
    doc_ids: list[uuid.UUID] | None,
    mode: str,
    threshold: float = 0.05,
    source_type: str = "document",
) -> Generation | None:
    """Check if a semantically equivalent query exists in the cache."""
    if query == "REJECTED_CONTEXT_DO_NOT_SEARCH":
        return None

    query_vector = embed_text(query)

    ram_hit = _check_ram_cache(query_vector, doc_ids, mode, source_type)
    if ram_hit:
        return ram_hit

    async with async_session_maker() as session:
        distance_expr = SemanticCache.query_embedding.cosine_distance(query_vector)
        stmt = select(SemanticCache).options(selectinload(SemanticCache.generation))
        stmt = stmt.filter(SemanticCache.mode == mode)
        stmt = stmt.filter(SemanticCache.source_type == source_type)
        if doc_ids:
            stmt = stmt.filter(SemanticCache.document_id.in_(doc_ids))
        stmt = stmt.filter(distance_expr < threshold).order_by(distance_expr).limit(1)

        result = await session.execute(stmt)
        cache_hit = result.scalar_one_or_none()

        if cache_hit:
            _add_to_ram_cache(query_vector, doc_ids, mode, source_type, cache_hit.generation)
            return cache_hit.generation
        return None


async def save_to_semantic_cache(
    query: str,
    doc_ids: list[uuid.UUID] | None,
    mode: str,
    generation_id: uuid.UUID,
    source_type: str = "document",
) -> None:
    """Save a verified query and its generation to the semantic cache."""
    if query == "REJECTED_CONTEXT_DO_NOT_SEARCH":
        return

    query_vector = embed_text(query)

    async with async_session_maker() as session:
        stmt = select(Generation).where(Generation.id == generation_id)
        result = await session.execute(stmt)
        gen_obj = result.scalar_one_or_none()

        if gen_obj:
            _add_to_ram_cache(query_vector, doc_ids, mode, source_type, gen_obj)

        new_cache_entry = SemanticCache(
            query_text=query,
            query_embedding=query_vector,
            mode=mode,
            source_type=source_type,
            document_id=doc_ids[0] if doc_ids else None,
            generation_id=generation_id,
        )
        session.add(new_cache_entry)
        await session.commit()
