"""Entailment/NLI scorer implementations for Pipeline 2.

Provides lazy-loaded singleton accessors and batched scoring helpers for
SummaC-ZS, SummaC-Conv, MiniCheck, and AlignScore models."""

from minicheck.minicheck import MiniCheck
_minicheck = None
_zs = None
_conv = None
_minicheck = None
_alignscore = None


def _get_zs():
    """Lazily load and cache the SummaCZS model singleton."""
    global _zs
    if _zs is None:
        from summac.model_summac import SummaCZS
        print("[SummaC] loading SummaCZS...")
        _zs = SummaCZS(granularity='sentence', model_name='vitc', device='cpu')
    return _zs


def _get_conv():
    """Lazily load and cache the SummaCConv model singleton."""
    global _conv
    if _conv is None:
        from summac.model_summac import SummaCConv
        print("[SummaC] loading SummaCConv...")
        _conv = SummaCConv(
            models=['vitc'], bins='percentile', granularity='sentence', device='cpu'
        )
    return _conv


def _get_minicheck():
    """Lazily load and cache the MiniCheck model singleton."""
    global _minicheck
    if _minicheck is None:
        _minicheck = MiniCheck(model_name='roberta-large')
    return _minicheck


def _get_alignscore():
    """Lazily load and cache the AlignScore model singleton."""
    global _alignscore
    if _alignscore is None:
        from alignscore import AlignScore
        print("[AlignScore] loading roberta-large...")
        _alignscore = AlignScore(
            model='roberta-large',
            batch_size=32,
            device='cpu',
            ckpt_path=(
                'https://huggingface.co/yzha/AlignScore/resolve/main/'
                'AlignScore-large.ckpt'
            )
        )
    return _alignscore


# ── single-pair helpers (used internally by batch functions) ──────────────────

def score_summac_zs(source: str, sentence: str) -> float:
    """Score a single (source, sentence) pair using SummaC-ZS."""
    return float(_get_zs().score([source], [sentence])['scores'][0])


def score_summac_conv(source: str, sentence: str) -> float:
    """Score a single (source, sentence) pair using SummaC-Conv."""
    return float(_get_conv().score([source], [sentence])['scores'][0])


def score_minicheck(source, sentence):
    """Score a single (source, sentence) pair using MiniCheck."""
    _, score, _, _ = _get_minicheck().score(docs=[source], claims=[sentence])
    return float(score[0])


def score_alignscore(source: str, sentence: str) -> float:
    """Score a single (source, sentence) pair using AlignScore."""
    return float(
        _get_alignscore().score(contexts=[source], claims=[sentence])[0]
    )


# ── batched helpers — score many (source, sentence) pairs at once ─────────────

def score_summac_zs_batch(sources: list[str], sentences: list[str]) -> list[float]:
    """Single forward pass for all pairs."""
    result = _get_zs().score(sources, sentences)
    return [float(s) for s in result['scores']]


def score_summac_conv_batch(sources: list[str], sentences: list[str]) -> list[float]:
    """Score all (source, sentence) pairs in a single forward pass (SummaC-Conv)."""
    result = _get_conv().score(sources, sentences)
    return [float(s) for s in result['scores']]


def score_minicheck_batch(sources: list[str], sentences: list[str]) -> list[float]:
    """Score all (source, sentence) pairs in a single forward pass (MiniCheck)."""
    _, scores, _, _ = _get_minicheck().score(docs=sources, claims=sentences)
    return [float(s) for s in scores]


def score_alignscore_batch(sources: list[str], sentences: list[str]) -> list[float]:
    """Score all (source, sentence) pairs in a single forward pass (AlignScore)."""
    return [
        float(s)
        for s in _get_alignscore().score(contexts=sources, claims=sentences)
    ]
