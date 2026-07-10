"""Low-Confidence Review Flag dashboard feature implementation.

Fetches and lists grading records from the database that have been flagged
as borderline (needs_review = True) for human review.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.grade import Grade


async def get_flagged_grades() -> dict[str, Any]:
    """Retrieve all evaluation records that are flagged for manual teacher review.

    Returns:
        A dictionary containing a list of flagged grade records.
    """
    async with async_session_maker() as session:
        # Select grades where needs_review is True, ordered by created_at desc
        stmt = (
            select(Grade)
            .where(Grade.needs_review == True)  # noqa: E712
            .order_by(Grade.created_at.desc())
        )
        result = await session.execute(stmt)
        grades = result.scalars().all()

        flagged_list = []
        for g in grades:
            flagged_list.append(
                {
                    "grade_id": g.id,
                    "student_answer": g.student_answer,
                    "overall_score": g.overall_score,
                    "rubric_breakdown": g.rubric_breakdown,
                    "created_at": g.created_at,
                }
            )

        return {"flagged_grades": flagged_list}
