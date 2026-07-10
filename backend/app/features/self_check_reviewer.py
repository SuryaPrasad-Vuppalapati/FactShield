"""Self-Check Reviewer feature implementation.

Splits student's writing into sentences and performs factual consistency checks
on each sentence against the source textbook material.
"""

from __future__ import annotations

from typing import Any

from app.factshield.grounding import check_grounding


def split_sentences(text: str) -> list[str]:
    """Split text into sentences by looking for period markers."""
    return [s.strip() for s in text.split(".") if s.strip()]


async def run_self_check(student_text: str, source_passage: str) -> dict[str, Any]:
    """Check each sentence of student's text against the source passage.

    Args:
        student_text: The student's written response.
        source_passage: The source passage containing factual ground truth.

    Returns:
        A dictionary containing a list of sentence-level checks.
    """
    sentences = split_sentences(student_text)
    sentence_checks = []

    for sentence in sentences:
        score = check_grounding(source_passage, sentence)
        supported = score >= 0.6
        sentence_checks.append(
            {
                "sentence": sentence,
                "score": score,
                "supported": supported,
            }
        )

    return {"sentence_checks": sentence_checks}
