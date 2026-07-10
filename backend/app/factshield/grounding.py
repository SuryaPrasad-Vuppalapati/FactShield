"""Grounding scorer wrapper using MiniCheck.

Wraps pipelines.entailment.scorer.score_minicheck_batch to evaluate the grounding
of a claim against a source passage.
"""

from __future__ import annotations

import re

from pipelines.entailment.scorer import score_minicheck_batch

# Conversational preambles that the LLM adds (e.g. "According to your notes,")
# confuse MiniCheck's NLI model and drive scores from ~0.90 to ~0.19.
# Strip them before scoring so MiniCheck sees only the factual content.
_PREAMBLE_RE = re.compile(
    r"^(?:"
    r"according to (?:your (?:notes?|document)|the (?:document|text|passage)|(?:section|chapter) \S+)[,\s]+"
    r"|based on (?:your (?:notes?|document)|the (?:document|text|passage|provided (?:notes?|context)))[,\s]+"
    r"|(?:from|in) (?:your (?:notes?|document|material)|the (?:document|text|passage))[,\s]+"
    r"|the (?:document|text|passage|notes?) (?:states?|says?|indicates?|mentions?|covers?)[,\s]+"
    r"|as (?:stated|mentioned|described|covered) in (?:your (?:notes?|document)|the (?:document|text))[,\s]+"
    r"|your (?:notes?|document) (?:states?|says?|indicates?|mentions?|covers?)[,\s]+"
    r"|⚠️[^\n]*\n+"
    r")",
    re.IGNORECASE,
)


def _strip_preamble(text: str) -> str:
    """Remove conversational preambles that confuse NLI entailment models."""
    return _PREAMBLE_RE.sub("", text).strip()


def check_grounding(source_passage: str, claim: str) -> float:
    """Wraps score_minicheck_batch for a single (source, claim) pair.

    Preambles like "According to your notes," are stripped from the claim
    before scoring because they reduce MiniCheck scores by ~70% even when
    the factual content is correct.

    Args:
        source_passage: The reference text grounding the claim.
        claim: The generated sentence or assertion to check.

    Returns:
        A grounding score (entailment probability) between 0.0 and 1.0.
    """
    clean_claim = _strip_preamble(claim)
    return float(score_minicheck_batch([source_passage], [clean_claim])[0])
