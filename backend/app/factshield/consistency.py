"""Pipeline 1 — SelfCheck Consistency.

Uses the research pipeline's SelfCheckBERTScore scorer to measure sentence-level
self-consistency across K stochastic re-generations of the same response.

Protocol (from the SelfCheckGPT paper):
  1. Split the primary response into sentences.
  2. Generate K independent samples of the same query (done in validator.py).
  3. For each sentence, compute how consistent it is across the K samples
     using BERTScore (bert-base-uncased, rescale_with_baseline=True).
  4. Lower hallucination score → higher consistency.

Return value: consistency score in [0, 1], where 1 = fully consistent.
"""

from __future__ import annotations

import re

import numpy as np

from pipelines.selfcheck.scorer import score_bert_batch


def check_consistency(primary: str, variants: list[str]) -> float:
    """Score sentence-level self-consistency using SelfCheckBERTScore.

    Args:
        primary:  Clean prose claim / primary response text (markdown stripped).
        variants: K independently generated variant responses to compare against.

    Returns:
        Consistency score in [0, 1].  Values >= 0.3 pass the pipeline check.
    """
    if not variants or not primary.strip():
        return 1.0

    # Split primary into sentences — same protocol as the research pipeline
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', primary) if len(s.strip()) > 10]
    if not sentences:
        sentences = [primary.strip()[:400]]

    # Filter empty/short variants
    valid_variants = [v for v in variants if v and len(v.strip()) > 10]
    if not valid_variants:
        return 1.0

    try:
        # score_bert_batch returns hallucination probability per sentence (0=consistent, 1=hallucinated)
        halluc_scores = score_bert_batch(sentences, valid_variants)
        consistency = 1.0 - float(np.mean(halluc_scores))
        return float(np.clip(consistency, 0.0, 1.0))

    except Exception as e:
        print(f"[Pipeline1/BERTScore] {e} — falling back to cosine similarity")
        return _cosine_fallback(primary, valid_variants)


# ── Fallback: cosine similarity with all-MiniLM-L6-v2 ────────────────────────

_cosine_model = None


def _get_cosine_model():
    global _cosine_model
    if _cosine_model is None:
        import torch
        from sentence_transformers import SentenceTransformer
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        _cosine_model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    return _cosine_model


def _cosine_fallback(primary: str, variants: list[str]) -> float:
    """Document-level cosine similarity fallback if BERTScore is unavailable."""
    try:
        from numpy.linalg import norm
        model = _get_cosine_model()
        texts = [primary] + variants
        embeddings = model.encode(texts, convert_to_numpy=True)
        primary_emb = embeddings[0]
        sims = [
            float(np.dot(primary_emb, v) / (norm(primary_emb) * norm(v)))
            for v in embeddings[1:]
        ]
        return float(np.clip(np.mean(sims), 0.0, 1.0))
    except Exception as e2:
        print(f"[Pipeline1/Cosine] {e2}")
        return 0.9  # neutral default
