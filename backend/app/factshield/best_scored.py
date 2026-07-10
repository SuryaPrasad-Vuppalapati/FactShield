"""Best-Scored Summary engine.

Generates multiple candidates from the Gemini model, evaluates each using the
three analysis scorers (grounding, consistency, confidence), and returns the
highest scoring summary.
"""

from __future__ import annotations

from typing import Any

from app.factshield.confidence import score_confidence
from app.factshield.consistency import check_consistency
from app.factshield.generation import generate_k_variants, generate_with_logprobs
from app.factshield.grounding import check_grounding


async def best_scored_candidate(
    prompt: str,
    source_passage: str,
    n_candidates: int = 3,
    k_variants_per_candidate: int = 3,
    skip_entailment: bool = False,
) -> dict[str, Any]:
    """Generates n candidates, scores each on all three pipelines, returns the best.

    Note: The combined_score weighting is currently an equal-weight average
    of grounding, consistency, and confidence.

    Args:
        prompt: The generation prompt.
        source_passage: Reference source passage to verify against.
        n_candidates: Number of candidate generations to compare.
        k_variants_per_candidate: Number of resamples for consistency checking.
        skip_entailment: If True, skips entailment (grounding) in the selection score.

    Returns:
        A dict containing 'winner' (the best candidate dict) and 'all_candidates' list.
    """
    candidates = []
    for _ in range(n_candidates):
        gen = await generate_with_logprobs(prompt)
        variants = await generate_k_variants(prompt, k=k_variants_per_candidate)
        grounding = check_grounding(source_passage, gen["text"])
        consistency = check_consistency(gen["text"], variants)
        confidence = 1.0 - score_confidence(gen["token_logprobs"], gen["seq_len"])
        
        if skip_entailment:
            combined = (consistency + confidence) / 2.0
        else:
            combined = (grounding + consistency + confidence) / 3.0
            
        candidates.append(
            {
                **gen,
                "grounding": grounding,
                "consistency": consistency,
                "confidence": confidence,
                "combined_score": combined,
            }
        )
    candidates.sort(key=lambda c: c["combined_score"], reverse=True)
    return {"winner": candidates[0], "all_candidates": candidates}
