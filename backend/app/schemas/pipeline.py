"""Shared pipeline score schemas used by all student and teacher endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PipelineScores(BaseModel):
    """FactShield 3-pipeline validation result.

    Individual pipeline signals
    ─────────────────────────
    entailment   MiniCheck NLI — is the response grounded in the source?
    consistency  SelfCheckGPT cosine similarity across 3 independent variants.
    confidence   Blended: 60% entailment + 40% logprob classifier.

    Composite trust signal (the primary FactShield output)
    ──────────────────────────────────────────────────────
    trust_score  0–1 weighted combination of all three signals.
    trust_tier   'verified' (≥0.65) | 'partial' (0.35–0.64) | 'unverified' (<0.35)
    """

    entailment: bool | None = Field(
        None,
        description="MiniCheck entailment result. None when skipped for non-document sources.",
    )
    consistency: bool = Field(
        ...,
        description="SelfCheckGPT self-consistency result across 3 variants.",
    )
    confidence: float = Field(
        ...,
        description="Blended confidence score (entailment + logprob classifier), 0–1.",
    )
    entailment_score: float = Field(
        0.0,
        description="Raw MiniCheck NLI score (0–1) before thresholding.",
    )
    consistency_score: float = Field(
        0.0,
        description="Raw cosine similarity score (0–1) before thresholding.",
    )
    trust_score: float = Field(
        0.0,
        description="Composite FactShield trust score (0–1).",
    )
    trust_tier: str = Field(
        "unverified",
        description="Trust tier: 'verified' | 'partial' | 'unverified'.",
    )
    fallback_type: str | None = Field(
        None,
        description="Source fallback type: 'none' | 'academic' | 'web'.",
    )
