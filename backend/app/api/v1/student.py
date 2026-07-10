"""Student-facing API endpoints.

All 4 Blueprint features (concept-guide, problem-navigator,
submission-validator, quiz-generator) run through the new FactShield engine.
Legacy endpoints preserved for compatibility.
"""
from __future__ import annotations

import asyncio
import re
import uuid
from typing import Any

from fastapi import APIRouter
from sqlalchemy import select

from app.db.session import async_session_maker
from app.engine.pipeline import run_pipeline, run_quiz_pipeline
from app.factshield.grounding import check_grounding
from app.models.document import Document
from app.retrieval.retriever import retrieve, retrieve_with_scores
from app.schemas.chat import ChatMessage
from app.schemas.pipeline import PipelineScores
from app.schemas.student import (
    BlueprintStudentRequest,
    BlueprintStudentResponse,
    ChallengeBackRequest,
    ChallengeBackResponse,
    MethodGroundingRequest,
    MethodGroundingResponse,
    SelfCheckRequest,
    SelfCheckResponse,
    SentenceSelfCheck,
    SourceHunterRequest,
    SourceHunterResponse,
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


def _blueprint(result: dict) -> BlueprintStudentResponse:
    s = result.get("scores", {})
    return BlueprintStudentResponse(
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


# ── Blueprint student features ────────────────────────────────────────────────

@router.post("/concept-guide", response_model=BlueprintStudentResponse)
async def concept_guide(request: BlueprintStudentRequest) -> BlueprintStudentResponse:
    filenames = await _get_filenames(request.doc_ids)
    result = await run_pipeline(
        mode="concept-guide", role="student",
        query=request.question,
        chat_history=request.chat_history,
        doc_ids=request.doc_ids,
        doc_filenames=filenames,
    )
    return _blueprint(result)


@router.post("/problem-navigator", response_model=BlueprintStudentResponse)
async def problem_navigator(request: BlueprintStudentRequest) -> BlueprintStudentResponse:
    filenames = await _get_filenames(request.doc_ids)
    result = await run_pipeline(
        mode="problem-navigator", role="student",
        query=request.question,
        chat_history=request.chat_history,
        doc_ids=request.doc_ids,
        doc_filenames=filenames,
    )
    return _blueprint(result)


@router.post("/submission-validator", response_model=BlueprintStudentResponse)
async def submission_validator(request: BlueprintStudentRequest) -> BlueprintStudentResponse:
    if not request.doc_ids:
        return BlueprintStudentResponse(
            text=(
                "Please upload your course material using the 📎 button and select it "
                "before submitting your draft for validation."
            ),
            entailment=False, consistency=False, confidence=0.0,
            fallback_type="refusal", source_used="", source_reference=None, scores=None,
        )
    filenames = await _get_filenames(request.doc_ids)
    result = await run_pipeline(
        mode="submission-validator", role="student",
        query=request.question,
        chat_history=request.chat_history,
        doc_ids=request.doc_ids,
        doc_filenames=filenames,
    )
    return _blueprint(result)


@router.post("/quiz-generator", response_model=BlueprintStudentResponse)
async def quiz_generator(request: BlueprintStudentRequest) -> BlueprintStudentResponse:
    filenames = await _get_filenames(request.doc_ids)
    result = await run_quiz_pipeline(
        query=request.question,
        chat_history=request.chat_history,
        doc_ids=request.doc_ids,
        doc_filenames=filenames,
    )
    return _blueprint(result)


# ── Legacy endpoints (preserved for compatibility) ────────────────────────────

@router.post("/method-grounding", response_model=MethodGroundingResponse)
async def method_grounding(request: MethodGroundingRequest) -> MethodGroundingResponse:
    filenames = await _get_filenames(request.doc_ids)
    result = await run_pipeline(
        mode="concept-guide", role="student",
        query=request.question,
        chat_history=request.chat_history,
        doc_ids=request.doc_ids,
        doc_filenames=filenames,
    )
    s = result.get("scores", {})
    return MethodGroundingResponse(
        text=result["text"],
        entailment=bool(s.get("entailment", False)),
        consistency=bool(s.get("consistency", False)),
        confidence=float(s.get("confidence", 0.0)),
        scores=_scores(result),
    )


@router.post("/challenge-back", response_model=ChallengeBackResponse)
async def challenge_back(request: ChallengeBackRequest) -> ChallengeBackResponse:
    passages = await retrieve(request.student_restatement, [request.doc_id], k=3)
    source = "\n".join(passages) if passages else ""
    score = float(
        await asyncio.to_thread(check_grounding, source, request.student_restatement)
    ) if source else 0.0
    accurate = score >= 0.5
    feedback = (
        "Well done — your restatement aligns with the source material."
        if accurate else
        "Your restatement differs from the source. Review the section and try again."
    )
    return ChallengeBackResponse(
        score=score, accurate=accurate, feedback=feedback,
        scores=PipelineScores(
            entailment=accurate, consistency=accurate,
            confidence=score, fallback_type=None,
        ),
    )


@router.post("/self-check", response_model=SelfCheckResponse)
async def self_check(request: SelfCheckRequest) -> SelfCheckResponse:
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', request.student_text) if s.strip()]
    passages = await retrieve(request.student_text, [request.doc_id], k=5)
    source = "\n".join(passages) if passages else ""

    async def _check(sent: str) -> SentenceSelfCheck:
        s = float(await asyncio.to_thread(check_grounding, source, sent)) if source else 0.0
        return SentenceSelfCheck(sentence=sent, score=s, supported=s >= 0.4)

    checks = list(await asyncio.gather(*[_check(s) for s in sentences]))
    avg = sum(c.score for c in checks) / max(len(checks), 1)
    return SelfCheckResponse(
        sentence_checks=checks,
        feedback="",
        scores=PipelineScores(
            entailment=all(c.supported for c in checks),
            consistency=True,
            confidence=avg,
            fallback_type=None,
        ),
    )


@router.post("/source-hunter", response_model=SourceHunterResponse)
async def source_hunter(request: SourceHunterRequest) -> SourceHunterResponse:
    passages = await retrieve(request.claim, request.doc_ids, k=1)
    if not passages:
        return SourceHunterResponse(
            found=False, cited_passage=None, score=0.0,
            answer="No relevant passage found in your document.", scores=None,
        )
    best = passages[0]
    score = float(await asyncio.to_thread(check_grounding, best, request.claim))
    found = score >= 0.5

    filenames = await _get_filenames(request.doc_ids)
    result = await run_pipeline(
        mode="concept-guide", role="student",
        query=f"Where in the document does it discuss: {request.claim}",
        chat_history=request.chat_history,
        doc_ids=request.doc_ids,
        doc_filenames=filenames,
    )
    return SourceHunterResponse(
        found=found, cited_passage=best, score=score,
        answer=result["text"],
        scores=_scores(result),
    )
