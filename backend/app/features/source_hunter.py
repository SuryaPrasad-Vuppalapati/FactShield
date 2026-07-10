"""Source Hunter feature implementation.

Finds the exact passage a student's claim comes from in their uploaded material,
or verifies that it doesn't exist.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.factshield.best_scored import best_scored_candidate
from app.factshield.grounding import check_grounding
from app.retrieval.retriever import retrieve


async def hunt_source(claim: str, doc_ids: list[uuid.UUID]) -> dict[str, Any]:
    """Retrieve the most relevant chunk and verify if it supports the claim.

    Args:
        claim: The student's claim or fact to check.
        doc_ids: List of document UUIDs to search within.

    Returns:
        A dictionary containing found status, cited passage, grounding score, and generated answer.
    """
    # 1. Retrieve the single most relevant chunk
    passages = await retrieve(query=claim, doc_ids=doc_ids, k=1)

    if not passages:
        return {"found": False, "cited_passage": None, "score": 0.0, "answer": "No source passages located."}

    best_passage = passages[0]

    # 2. Check if the retrieved passage entails the claim
    score = check_grounding(best_passage, claim)
    found = score >= 0.6

    # 3. Generate the prompt using the FIND system prompt
    system_prompt = (
        "You are a learning assistant. The student wants to find where something is in their document. "
        "Search the document context and tell them: (1) the section or heading where this topic appears, "
        "(2) a one-sentence description of what that section covers. Quote at most one short phrase from the document."
    )
    prompt = (
        f"{system_prompt}\n\n"
        f"Document Context:\n{best_passage}\n\n"
        f"Search query: {claim}"
    )

    res = best_scored_candidate(
        prompt=prompt,
        source_passage=best_passage,
        n_candidates=1,
    )
    answer = res["winner"]["text"]

    return {
        "found": found,
        "cited_passage": best_passage,
        "score": score,
        "answer": answer,
    }
