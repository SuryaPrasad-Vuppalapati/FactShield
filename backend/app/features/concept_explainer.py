"""Concept Explainer feature implementation.

Explains technical concepts to students using the shared Best-Scored Summary engine
to ensure high factual consistency.
"""

from __future__ import annotations

from typing import Any

from app.factshield.best_scored import best_scored_candidate


async def explain_concept(concept: str, source_passage: str) -> dict[str, Any]:
    """Explain a concept using the verified best summary generation.

    Args:
        concept: The technical concept to explain.
        source_passage: Reference course text containing facts about the concept.

    Returns:
        A dict containing the highest-scoring candidate and all candidate scores.
    """
    prompt = (
        f"Concept: {concept}\n\n"
        "Explain this concept using only the reference material below. "
        "Cover the core idea, how it works, and a concrete example where it helps understanding. "
        "Use $...$ for inline math and $$...$$ on its own line for display math. "
        "Cite [Page X] or [Section: Name] for specific facts. "
        "Write clearly and naturally — like a sharp tutor who actually understands this, not a textbook summary.\n\n"
        f"Reference material:\n{source_passage}"
    )

    # Use the shared Best-Scored Summary engine
    res = best_scored_candidate(prompt=prompt, source_passage=source_passage)
    return res
