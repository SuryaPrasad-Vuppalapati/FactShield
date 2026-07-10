"""Challenge-Back Mode feature implementation.

Evaluates a student's restatement of a technique/method against the source
passage to verify their understanding.
"""

from __future__ import annotations

from typing import Any

from app.factshield.grounding import check_grounding


async def evaluate_restatement(
    student_restatement: str, source_passage: str
) -> dict[str, Any]:
    """Check the student's restatement against the source technique definition.

    Args:
        student_restatement: The student's explanation of the method.
        source_passage: The reference text defining the method.

    Returns:
        A dictionary containing score, accuracy boolean, and written feedback.
    """
    score = check_grounding(source_passage, student_restatement)
    accurate = score >= 0.6

    if accurate:
        feedback = (
            "Your restatement is accurate and successfully grounded in the "
            "reference material."
        )
    elif score > 0.4:
        feedback = (
            "Your restatement is partially accurate but seems borderline. "
            "It might be missing key elements or nuances from the reference."
        )
    else:
        feedback = (
            "Your restatement is not supported by the reference material. "
            "Please review the cited passages and try explaining it again."
        )

    return {
        "score": score,
        "accurate": accurate,
        "feedback": feedback,
    }
