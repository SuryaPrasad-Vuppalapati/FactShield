"""Pipeline 3 — Token Probability Confidence.

Uses the research pipeline's feature extractor (5 uncertainty features from
token log-probabilities) to estimate hallucination probability.

Features extracted (from pipelines.token_prob.scorer):
  perplexity    exp(-mean(logprobs))               — primary uncertainty signal
  mean_entropy  mean(-exp(lp) * lp)  per token     — chosen-token entropy contribution
  max_entropy   max(-exp(lp) * lp)                 — worst-token uncertainty
  tail_mean_nll -mean(logprobs[-5:])               — uncertainty at end of response
  sent_length   number of tokens                   — length proxy

Why not the trained classifier?
────────────────────────────────
The logistic regression classifier (task3_classifier.pkl) was trained on logprobs
from BART/T5/Pegasus (seq2seq encoder-decoder models, greedy decoding on CNN/DM,
XSum, FaithBench).  GPT-4o-mini is a decoder-only chat model — the logprob
distributions differ fundamentally in scale and shape.  The classifier predicts
p_hallucination ≈ 0.72 for every input regardless of content quality, making it
useless for discrimination.

Instead, we use the feature extractor directly (authentic research pipeline code)
with calibrated thresholds derived from observed GPT-4o-mini logprob distributions:
  — Well-grounded responses: perplexity 1.3-2.5, tail_nll 0.3-1.0
  — Uncertain/hallucinated:  perplexity 5-20+,   tail_nll 1.5-3+

Perplexity and tail_nll are monotonically related to uncertainty and are the two
most predictive features.  Mean_entropy is bell-shaped (max at lp=-1.0) and
therefore not monotonic — omitted from the primary signal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pipelines.token_prob.scorer import extract_features_vectorized


def score_confidence(token_logprobs: bytes, seq_len: int) -> float:
    """Returns P(hallucinated) ∈ [0, 1] from token probability features.

    Uses the research pipeline's extract_features_vectorized to compute all
    5 uncertainty features, then maps perplexity and tail_nll to a calibrated
    hallucination probability.

    Args:
        token_logprobs: Binary-serialised numpy float32 array of token log-probs.
        seq_len:        Number of tokens in the response.

    Returns:
        Hallucination probability in [0, 1].  Lower = more confident.
    """
    if not token_logprobs or seq_len == 0:
        return 0.5  # neutral when no logprobs available (Gemini/Ollama fallback)

    try:
        df = pd.DataFrame([{
            "doc_id": "live",
            "token_logprobs": token_logprobs,
            "seq_len": seq_len,
        }])
        feat = extract_features_vectorized(df).iloc[0]

        ppl      = float(feat["perplexity"])
        tail_nll = float(feat["tail_mean_nll"])

        # Map to confidence in [0, 1] (1 = certain, 0 = uncertain)
        # Perplexity range: 1.5 → confident (1.0), 21.5 → uncertain (0.0)
        ppl_conf  = float(np.clip(1.0 - (ppl - 1.5) / 20.0, 0.0, 1.0))
        # Tail NLL range:  0.0 → confident (1.0),  3.0 → uncertain (0.0)
        tail_conf = float(np.clip(1.0 - tail_nll / 3.0,       0.0, 1.0))

        # Perplexity carries more predictive weight than tail NLL
        confidence   = 0.65 * ppl_conf + 0.35 * tail_conf
        p_hallucinated = 1.0 - confidence

        return float(np.clip(p_hallucinated, 0.0, 1.0))

    except Exception as e:
        print(f"[Pipeline3/TokenProb] {e}")
        return 0.5
