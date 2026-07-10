"""Pydantic schemas for Teacher feature requests and responses."""

from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, Field

from app.schemas.chat import ChatMessage
from app.schemas.pipeline import PipelineScores


class GradeAnswerRequest(BaseModel):
    """Request schema for the Open-Ended Answer Grader."""

    student_answer: str = Field(
        ..., description="The student's submitted open-ended answer."
    )
    doc_id: uuid.UUID = Field(
        ..., description="The reference document UUID to grade against."
    )
    chat_history: list[ChatMessage] = Field(default_factory=list)


class PointGrade(BaseModel):
    """Grading breakdown for a single rubric key point."""

    point: str = Field(..., description="The decomposed key point statement.")
    score: float = Field(
        ..., description="The entailment score (0.0 to 1.0) of the point."
    )
    passed: bool = Field(
        ..., description="Whether the student successfully covered the point."
    )
    needs_review: bool = Field(
        ..., description="Whether this score is in the borderline review range."
    )


class GradeAnswerResponse(BaseModel):
    """Response schema for the Open-Ended Answer Grader."""

    grade_id: uuid.UUID = Field(
        ..., description="The unique database identifier for this grade."
    )
    overall_score: float = Field(
        ..., description="The overall normalized score (0.0 to 1.0) for the answer."
    )
    breakdown: list[PointGrade] = Field(
        ..., description="The per-point rubric breakdown."
    )
    needs_review: bool = Field(
        ..., description="Whether the overall grade needs manual human review."
    )
    # Pipeline scores for AI grading reliability (Badge 1)
    pipeline_scores: PipelineScores | None = Field(
        None, description="FactShield scores for the AI grading response reliability."
    )
    # Student answer document match score (Badge 2)
    student_doc_match: float | None = Field(
        None,
        description="MiniCheck score (0.0–1.0) of the student's answer against the document.",
    )


class ConceptExplainerRequest(BaseModel):
    """Request schema for Concept Explainer."""

    concept: str = Field(..., description="The concept to explain.")
    doc_id: uuid.UUID = Field(
        ..., description="The reference document UUID containing the concept."
    )
    chat_history: list[ChatMessage] = Field(default_factory=list)


class GeneratedTestItem(BaseModel):
    """A single generated test question and answer pair."""

    question: str = Field(..., description="The generated test question.")
    correct_answer: str = Field(..., description="The generated correct answer.")
    grounding_score: float = Field(
        ..., description="Grounding score of the answer against source."
    )


class TestGeneratorRequest(BaseModel):
    """Request schema for Test Generator."""

    doc_id: uuid.UUID = Field(
        ..., description="The reference document UUID to base the test on."
    )
    num_questions: int = Field(3, description="Number of questions to generate.")
    chat_history: list[ChatMessage] = Field(default_factory=list)


class TestGeneratorResponse(BaseModel):
    """Response schema for Test Generator."""

    test_items: list[GeneratedTestItem] = Field(
        ..., description="The list of generated test items."
    )
    text: str = Field("", description="The raw generated test markdown text.")
    scores: PipelineScores | None = Field(
        None, description="FactShield scores checking questions are document-grounded."
    )


class FlaggedGradeItem(BaseModel):
    """Grade record details for borderline scores flagged for review."""

    grade_id: uuid.UUID = Field(..., description="Grade record identifier.")
    student_answer: str = Field(..., description="The student's answer text.")
    overall_score: float = Field(..., description="The calculated overall score.")
    rubric_breakdown: list[PointGrade] = Field(
        ..., description="Breakdown of key facts evaluated."
    )
    created_at: datetime.datetime = Field(
        ..., description="Timestamp of the evaluation."
    )


class FlaggedGradesResponse(BaseModel):
    """Response schema containing list of flagged grades."""

    flagged_grades: list[FlaggedGradeItem] = Field(
        ..., description="List of review-flagged grades."
    )

class BlueprintTeacherRequest(BaseModel):
    """Generic request schema for Blueprint Teacher Features."""
    question: str = Field(..., description="The user's prompt or question.")
    doc_ids: list[uuid.UUID] = Field(..., description="Document UUIDs to search within.")
    chat_history: list[ChatMessage] = Field(default_factory=list)
    context: str | None = Field(None, description="Additional context like student submissions.")

class BlueprintTeacherResponse(BaseModel):
    """Generic response schema for Blueprint Teacher Features."""
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
