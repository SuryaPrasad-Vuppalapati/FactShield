"""Pydantic schemas for Student feature requests and responses."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.schemas.chat import ChatMessage
from app.schemas.pipeline import PipelineScores


class MethodGroundingRequest(BaseModel):
    """Request schema for the Method-Grounding Helper."""

    question: str = Field(..., description="The student's question/problem.")
    doc_ids: list[uuid.UUID] = Field(
        ..., description="List of document UUIDs to search within."
    )
    chat_history: list[ChatMessage] = Field(default_factory=list)


class MethodGroundingResponse(BaseModel):
    """Response schema for the Method-Grounding Helper."""

    text: str = Field(..., description="The LLM-generated explanation text.")
    entailment: bool = Field(..., description="Whether the entailment check passed.")
    consistency: bool = Field(..., description="Whether the consistency check passed.")
    confidence: float = Field(..., description="Confidence score from 0.0 to 1.0.")
    scores: PipelineScores | None = Field(None, description="Unified pipeline scores block.")


class ChallengeBackRequest(BaseModel):
    """Request schema for Challenge-Back Mode."""

    student_restatement: str = Field(
        ..., description="The student's restatement of the method."
    )
    doc_id: uuid.UUID = Field(..., description="The grounding document UUID.")
    chat_history: list[ChatMessage] = Field(default_factory=list)


class ChallengeBackResponse(BaseModel):
    """Response schema for Challenge-Back Mode."""

    score: float = Field(
        ..., description="Entailment score between restatement and source."
    )
    accurate: bool = Field(
        ..., description="True if the restatement is verified accurate."
    )
    feedback: str = Field(..., description="System feedback regarding correctness.")
    scores: PipelineScores | None = Field(None, description="Unified pipeline scores block.")


class SentenceSelfCheck(BaseModel):
    """Self-check result for a single sentence."""

    sentence: str = Field(..., description="The evaluated sentence.")
    score: float = Field(..., description="Grounding/consistency score.")
    supported: bool = Field(..., description="True if supported by the source.")


class SelfCheckRequest(BaseModel):
    """Request schema for Self-Check Reviewer."""

    student_text: str = Field(..., description="The student's written response.")
    doc_id: uuid.UUID = Field(..., description="The grounding document UUID.")
    chat_history: list[ChatMessage] = Field(default_factory=list)


class SelfCheckResponse(BaseModel):
    """Response schema for Self-Check Reviewer."""

    sentence_checks: list[SentenceSelfCheck] = Field(
        ..., description="Per-sentence self-check breakdown."
    )
    feedback: str = Field("", description="Factual comparison feedback.")
    scores: PipelineScores | None = Field(None, description="Unified pipeline scores block.")


class SourceHunterRequest(BaseModel):
    """Request schema for Source Hunter."""

    claim: str = Field(..., description="The claim to look up in materials.")
    doc_ids: list[uuid.UUID] = Field(
        ..., description="List of document UUIDs to search."
    )
    chat_history: list[ChatMessage] = Field(default_factory=list)


class SourceHunterResponse(BaseModel):
    """Response schema for Source Hunter."""

    found: bool = Field(..., description="Whether the source passage was found.")
    cited_passage: str | None = Field(
        None, description="The best matching cited passage."
    )
    score: float = Field(..., description="Cosine similarity score.")
    answer: str = Field("", description="Factual locator explanation.")
    scores: PipelineScores | None = Field(None, description="Unified pipeline scores block.")


class CandidateScore(BaseModel):
    """Score breakdowns for a generation candidate."""

    text: str = Field(..., description="The generated candidate text.")
    grounding: float = Field(..., description="Grounding score.")
    consistency: float = Field(..., description="Consistency score.")
    confidence: float = Field(..., description="Confidence score.")
    combined_score: float = Field(..., description="Overall combined score.")


class BestScoredSummaryRequest(BaseModel):
    """Request schema for Best-Scored Summary."""

    prompt: str = Field(..., description="The prompt to generate from.")
    doc_id: uuid.UUID = Field(..., description="The grounding document UUID.")
    n_candidates: int = Field(3, description="Number of summaries to generate.")
    chat_history: list[ChatMessage] = Field(default_factory=list)


class BestScoredSummaryResponse(BaseModel):
    """Response schema for Best-Scored Summary."""

    winner: CandidateScore = Field(..., description="The highest-scoring candidate.")
    all_candidates: list[CandidateScore] = Field(
        ..., description="All generated candidates with their scores."
    )
    scores: PipelineScores | None = Field(None, description="Unified pipeline scores block.")

class BlueprintStudentRequest(BaseModel):
    """Generic request schema for Blueprint Student Features."""
    question: str = Field(..., description="The user's prompt or question.")
    doc_ids: list[uuid.UUID] = Field(..., description="Document UUIDs to search within.")
    chat_history: list[ChatMessage] = Field(default_factory=list)

class BlueprintStudentResponse(BaseModel):
    """Generic response schema for Blueprint Student Features."""
    text: str = Field(..., description="The structured response text.")
    entailment: bool = Field(..., description="Whether the entailment check passed.")
    consistency: bool = Field(..., description="Whether the consistency check passed.")
    confidence: float = Field(..., description="Confidence score from 0.0 to 1.0.")
    trust_score: float = Field(0.0, description="Composite FactShield trust score (0–1).")
    trust_tier: str = Field("unverified", description="Trust tier: verified | partial | unverified.")
    fallback_type: str = Field("none", description="Source of fallback if used.")
    source_used: str = Field("document", description="Primary source or combined source used.")
    source_reference: str | None = Field(None, description="Human-readable source reference(s).")
    scores: PipelineScores | None = Field(None, description="Unified pipeline scores block.")
