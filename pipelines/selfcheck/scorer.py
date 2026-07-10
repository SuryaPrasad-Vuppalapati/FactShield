"""SelfCheckGPT sentence-level scoring helpers.

Provides lazy-loaded singleton accessors and batched scoring functions for
BERTScore, NLI (DeBERTa), and Ngram-based consistency checking."""

import torch

_scorer_bert = None
_scorer_nli = None
_scorer_ngram = None


def _get_device():
    """Select the best available compute device (MPS, CUDA, or CPU)."""
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _get_bert():
    """Lazily load and cache the SelfCheckBERTScore model singleton."""
    global _scorer_bert
    if _scorer_bert is None:
        from selfcheckgpt.modeling_selfcheck import SelfCheckBERTScore
        _scorer_bert = SelfCheckBERTScore(rescale_with_baseline=True)
    return _scorer_bert


def _get_nli():
    """Lazily load and cache the SelfCheckNLI model singleton."""
    global _scorer_nli
    if _scorer_nli is None:
        from selfcheckgpt.modeling_selfcheck import SelfCheckNLI
        device = _get_device()
        print(f"[SelfCheckNLI] loading on device: {device}")
        _scorer_nli = SelfCheckNLI(
            nli_model='cross-encoder/nli-deberta-v3-large',
            device=device
        )
    return _scorer_nli


def _get_ngram():
    """Lazily load and cache the SelfCheckNgram model singleton."""
    global _scorer_ngram
    if _scorer_ngram is None:
        from selfcheckgpt.modeling_selfcheck import SelfCheckNgram
        _scorer_ngram = SelfCheckNgram(n=1)
    return _scorer_ngram


def score_bert_batch(sentences: list[str], others: list[str]) -> list[float]:
    """Score all sentences in one forward pass (BERTScore)."""
    others = [s for s in others if s and isinstance(s, str) and s.strip()]
    if not others:
        return [0.0] * len(sentences)
    try:
        scores = _get_bert().predict(sentences=sentences, sampled_passages=others)
        return [float(s) for s in scores]
    except Exception as e:
        print(f"  [warn] bert_score failed: {e} — returning zeros")
        return [0.0] * len(sentences)


def score_nli_batch(sentences: list[str], others: list[str]) -> list[float]:
    """Score all sentences in one forward pass (NLI/DeBERTa on MPS)."""
    others = [s for s in others if s and isinstance(s, str) and s.strip()]
    if not others:
        return [0.0] * len(sentences)
    try:
        scores = _get_nli().predict(sentences=sentences, sampled_passages=others)
        return [float(s) for s in scores]
    except Exception as e:
        print(f"  [warn] nli_score failed: {e} — returning zeros")
        return [0.0] * len(sentences)


def score_ngram_batch(sentences: list[str], others: list[str]) -> list[float]:
    """Score all sentences in one forward pass using Ngram unigram overlap."""
    others = [s for s in others if s and isinstance(s, str) and s.strip()]
    if not others:
        return [0.0] * len(sentences)
    try:
        passage = ' '.join(others)
        result = _get_ngram().predict(
            sentences=sentences,
            passage=passage,
            sampled_passages=others
        )
        return [float(s) for s in result['sent_level']['avg_neg_logprob']]
    except Exception as e:
        print(f"  [warn] ngram_score failed: {e} — returning zeros")
        return [0.0] * len(sentences)

# --- legacy single-sentence API kept for backward compatibility ---


def score_bert(sentence, sentences, others):
    """Score a single sentence using BERTScore (legacy single-sentence API)."""
    scores = _get_bert().predict(sentences=sentences, sampled_passages=others)
    idx = sentences.index(sentence)
    return float(scores[idx])


def score_nli(sentence, sentences, others):
    """Score a single sentence using NLI/DeBERTa (legacy single-sentence API)."""
    scores = _get_nli().predict(sentences=sentences, sampled_passages=others)
    idx = sentences.index(sentence)
    return float(scores[idx])


def score_ngram(sentence, sentences, others):
    """Score a single sentence using Ngram (legacy single-sentence API)."""
    passage = ' '.join(others)
    result = _get_ngram().predict(
        sentences=sentences,
        passage=passage,
        sampled_passages=others
    )
    scores = result['sent_level']['avg_neg_logprob']
    idx = sentences.index(sentence)
    return float(scores[idx])
