"""Open-Ended Answer Grader feature implementation.

Decomposes a source passage into key factual points using Gemini, checks if each
point is entailed by the student's answer, and flags borderline cases.
"""

from __future__ import annotations

from typing import Any

from app.config import settings
from app.db.session import async_session_maker
from app.factshield.grounding import check_grounding
from app.models.grade import Grade


from app.factshield.generation import generate_response
from app.schemas.chat import ChatMessage

async def decompose_source(source_passage: str) -> list[str]:
    """Decomposes a source passage into a list of key factual points.

    Uses Hugging Face Serverless Inference API.
    """
    try:
        prompt = (
            "Decompose the following reference passage into key factual points "
            "that a student must cover. Return them as a clean list of single "
            "sentences, each on a new line. Do not include any introductory "
            "or concluding text.\n\n"
            f"Passage: {source_passage}"
        )
        # Using the Hugging Face wrapper
        text = await generate_response(prompt, chat_history=None)
        
        if text == "AI_SERVICE_UNAVAILABLE":
            return fallback_decompose(source_passage)
            
        lines = [line.strip().lstrip("-*•").strip() for line in text.split("\n")]
        points = [line for line in lines if line]
        return points if points else fallback_decompose(source_passage)
    except Exception:
        return fallback_decompose(source_passage)


def fallback_decompose(source_passage: str) -> list[str]:
    """Fallback method to split text into sentences when Gemini is unavailable."""
    return [s.strip() for s in source_passage.split(".") if s.strip()]


async def grade_student_answer(
    student_answer: str, source_passage: str
) -> dict[str, Any]:
    """Decomposes source passage, evaluates student answer, saves, and returns grades.

    Args:
        student_answer: The student's written response.
        source_passage: The source passage containing ground truth facts.

    Returns:
        A dict matching the GradeAnswerResponse schema.
    """
    # 1. Decompose source passage into key rubric points
    points = await decompose_source(source_passage)

    breakdown = []
    total_score = 0.0
    overall_needs_review = False

    # 🛑 STOP — CONFIRM WITH HUMAN: Borderline review thresholds.
    # We use 0.4 and 0.6 as the default thresholds as outlined in Task 4.2.
    for point in points:
        # Check if student answer entails the key point
        score = check_grounding(student_answer, point)
        passed = score >= 0.6
        point_needs_review = 0.4 < score < 0.6

        if point_needs_review:
            overall_needs_review = True

        breakdown.append(
            {
                "point": point,
                "score": score,
                "passed": passed,
                "needs_review": point_needs_review,
            }
        )
        total_score += score

    overall_score = total_score / len(points) if points else 0.0

    # Also trigger overall review if overall score is borderline
    if 0.4 < overall_score < 0.6:
        overall_needs_review = True

    # 2. Persist the grade record in PostgreSQL
    db_grade = Grade(
        student_answer=student_answer,
        rubric_breakdown=breakdown,
        overall_score=overall_score,
        needs_review=overall_needs_review,
    )

    async with async_session_maker() as session:
        session.add(db_grade)
        await session.commit()
        await session.refresh(db_grade)
        grade_id = db_grade.id

    return {
        "grade_id": grade_id,
        "overall_score": overall_score,
        "breakdown": breakdown,
        "needs_review": overall_needs_review,
    }
