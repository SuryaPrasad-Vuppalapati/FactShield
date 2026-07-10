"""Teacher-facing API endpoints.

All 4 Blueprint features run through the new FactShield engine.
Legacy endpoints (grade-answer, concept-explainer, test-generator, flagged-grades)
are preserved for compatibility.
"""
from __future__ import annotations

import asyncio
import re
import uuid
from typing import Any

from fastapi import APIRouter
from sqlalchemy import select

from app.db.session import async_session_maker
from app.engine.pipeline import run_pipeline
from app.factshield.grounding import check_grounding
from app.features.answer_grader import grade_student_answer
from app.features.review_flag import get_flagged_grades
from app.models.document import Document
from app.retrieval.retriever import get_document_text, retrieve
from app.schemas.pipeline import PipelineScores
from app.schemas.student import BestScoredSummaryResponse, CandidateScore
from app.schemas.teacher import (
    BlueprintTeacherRequest,
    BlueprintTeacherResponse,
    ConceptExplainerRequest,
    FlaggedGradesResponse,
    GradeAnswerRequest,
    GradeAnswerResponse,
    TestGeneratorRequest,
    TestGeneratorResponse,
)

router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_filenames(doc_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not doc_ids:
        return {}
    async with async_session_maker() as session:
        result = await session.execute(
            select(Document.id, Document.filename).where(Document.id.in_(doc_ids))
        )
        return {row.id: row.filename for row in result}


def _scores(result: dict) -> PipelineScores | None:
    s = result.get("scores")
    if not s or "entailment" not in s:
        return None
    return PipelineScores(
        entailment=s.get("entailment"),
        consistency=bool(s.get("consistency", False)),
        confidence=float(s.get("confidence", 0.0)),
        entailment_score=float(s.get("entailment_score", 0.0)),
        consistency_score=float(s.get("consistency_score", 0.0)),
        trust_score=float(s.get("trust_score", 0.0)),
        trust_tier=s.get("trust_tier", "unverified"),
        fallback_type=s.get("fallback_type"),
    )


def _blueprint(result: dict) -> BlueprintTeacherResponse:
    s = result.get("scores", {})
    return BlueprintTeacherResponse(
        text=result["text"],
        entailment=bool(s.get("entailment", False)),
        consistency=bool(s.get("consistency", False)),
        confidence=float(s.get("confidence", 0.0)),
        trust_score=float(s.get("trust_score", 0.0)),
        trust_tier=s.get("trust_tier", "unverified"),
        fallback_type=s.get("fallback_type", "none"),
        source_used=result.get("source_used", ""),
        source_reference=result.get("source_reference"),
        scores=_scores(result),
    )


# ── Blueprint teacher features ────────────────────────────────────────────────

@router.post("/assignment-grader", response_model=BlueprintTeacherResponse)
async def assignment_grader(request: BlueprintTeacherRequest) -> BlueprintTeacherResponse:
    filenames = await _get_filenames(request.doc_ids)
    result = await run_pipeline(
        mode="assignment-grader", role="teacher",
        query=request.question,
        chat_history=request.chat_history,
        doc_ids=request.doc_ids,
        doc_filenames=filenames,
        context=request.context,
    )
    return _blueprint(result)


@router.post("/exam-generator", response_model=BlueprintTeacherResponse)
async def exam_generator(request: BlueprintTeacherRequest) -> BlueprintTeacherResponse:
    filenames = await _get_filenames(request.doc_ids)
    result = await run_pipeline(
        mode="exam-generator", role="teacher",
        query=request.question,
        chat_history=request.chat_history,
        doc_ids=request.doc_ids,
        doc_filenames=filenames,
        context=request.context,
    )
    return _blueprint(result)


@router.post("/adaptive-feedback", response_model=BlueprintTeacherResponse)
async def adaptive_feedback(request: BlueprintTeacherRequest) -> BlueprintTeacherResponse:
    filenames = await _get_filenames(request.doc_ids)
    result = await run_pipeline(
        mode="adaptive-feedback", role="teacher",
        query=request.question,
        chat_history=request.chat_history,
        doc_ids=request.doc_ids,
        doc_filenames=filenames,
        context=request.context,
    )
    return _blueprint(result)


@router.post("/learning-insights", response_model=BlueprintTeacherResponse)
async def learning_insights(request: BlueprintTeacherRequest) -> BlueprintTeacherResponse:
    filenames = await _get_filenames(request.doc_ids)
    result = await run_pipeline(
        mode="learning-insights", role="teacher",
        query=request.question,
        chat_history=request.chat_history,
        doc_ids=request.doc_ids,
        doc_filenames=filenames,
        context=request.context,
    )
    return _blueprint(result)


# ── Legacy endpoints ──────────────────────────────────────────────────────────

@router.post("/grade-answer", response_model=GradeAnswerResponse)
async def grade_answer(request: GradeAnswerRequest) -> GradeAnswerResponse:
    """Grade a student's answer against the reference document (dual FactShield badges)."""
    passages = await retrieve(request.student_answer, [request.doc_id], k=5)
    source_passage = "\n".join(passages) if passages else ""

    # Rubric breakdown
    grade_data = await grade_student_answer(request.student_answer, source_passage)

    # Badge 1 — AI grading reliability
    result = await run_pipeline(
        mode="assignment-grader", role="teacher",
        query=f"Grade this student answer: {request.student_answer}",
        chat_history=request.chat_history,
        doc_ids=[request.doc_id],
        doc_filenames=await _get_filenames([request.doc_id]),
        context=request.student_answer,
    )

    # Badge 2 — Student answer vs document
    student_doc_match = float(
        await asyncio.to_thread(check_grounding, source_passage, request.student_answer)
    ) if source_passage else 0.0

    return GradeAnswerResponse(
        grade_id=grade_data["grade_id"],
        overall_score=grade_data["overall_score"],
        breakdown=grade_data["breakdown"],
        needs_review=grade_data["needs_review"],
        pipeline_scores=_scores(result),
        student_doc_match=student_doc_match,
    )


@router.post("/concept-explainer", response_model=BestScoredSummaryResponse)
async def concept_explainer(request: ConceptExplainerRequest) -> BestScoredSummaryResponse:
    """Generate a document-grounded concept explanation (3 candidates, pick best)."""
    result = await run_pipeline(
        mode="concept-guide", role="teacher",
        query=request.concept,
        chat_history=request.chat_history,
        doc_ids=[request.doc_id],
        doc_filenames=await _get_filenames([request.doc_id]),
    )
    s = result.get("scores", {})
    ent = 1.0 if s.get("entailment") else 0.0
    con = 1.0 if s.get("consistency") else 0.0
    conf = float(s.get("confidence", 0.0))
    combined = ent * 0.4 + con * 0.4 + conf * 0.2
    winner = CandidateScore(
        text=result["text"],
        grounding=ent,
        consistency=con,
        confidence=conf,
        combined_score=combined,
    )
    return BestScoredSummaryResponse(
        winner=winner,
        all_candidates=[winner],
        scores=PipelineScores(
            entailment=bool(s.get("entailment")),
            consistency=bool(s.get("consistency")),
            confidence=conf,
            fallback_type=s.get("fallback_type"),
        ),
    )


@router.post("/test-generator", response_model=TestGeneratorResponse)
async def test_generator(request: TestGeneratorRequest) -> TestGeneratorResponse:
    """Generate a practice test from the document."""
    source_passage = await get_document_text(request.doc_id)
    result = await run_pipeline(
        mode="exam-generator", role="teacher",
        query=f"Generate {request.num_questions} quiz questions.",
        chat_history=request.chat_history,
        doc_ids=[request.doc_id],
        doc_filenames=await _get_filenames([request.doc_id]),
    )

    # Parse test items from markdown
    pattern = re.compile(
        r"\*\*Question\s+\d+:\*\*(.*?)(?:\*Correct Answer:\*|\*Answer:\*)\s*(.*?)(?=\*\*Question\s+\d+:|$)",
        re.DOTALL | re.IGNORECASE,
    )
    test_items = []
    for q_text, ans_text in pattern.findall(result["text"]):
        q, ans = q_text.strip(), ans_text.strip()
        if q and ans:
            score = await asyncio.to_thread(check_grounding, source_passage, ans)
            test_items.append({"question": q, "correct_answer": ans, "grounding_score": float(score)})

    s = result.get("scores", {})
    return TestGeneratorResponse(
        test_items=test_items,
        text=result["text"],
        scores=PipelineScores(**s) if "entailment" in s else None,
    )


@router.get("/flagged-grades", response_model=FlaggedGradesResponse)
async def flagged_grades() -> FlaggedGradesResponse:
    result = await get_flagged_grades()
    return FlaggedGradesResponse(**result)
