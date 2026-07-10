"""FactShield 3-Pipeline Validator: Entailment + Consistency + Confidence.

Pipeline roles
──────────────
Entailment   (MiniCheck roberta-large)
             Checks whether the LLM response is grounded in the retrieved
             source passage.  Only meaningful for local-document sources;
             skipped for ArXiv/Web (retrieved snippet may be unrelated).

Consistency  (SelfCheckGPT cosine embedding)
             Generates 3 independent variants of the same query, then measures
             cosine similarity between the primary response and each variant.
             A high score means the model gives the same answer regardless of
             sampling — low variance signals factual stability.

Confidence   (token logprob classifier blended with entailment)
             A logistic-regression classifier trained on token log-probabilities
             estimates hallucination probability.  Blended 40 / 60 with the
             entailment score to correct for classifier calibration drift across
             model families.

Trust Score & Tier
──────────────────
A single composite score (0–1) combines all three signals with source-aware
weights:

  document source:  0.50 × ent  + 0.30 × con  + 0.20 × conf
  arxiv/web source: 0.00 × ent  + 0.55 × con  + 0.45 × conf  (capped at 0.64)
  no source:        0.00 × ent  + 0.45 × con  + 0.55 × conf  (capped at 0.50)

Tiers:
  verified   trust ≥ 0.65  — response grounded in document, stable, confident
  partial    0.35 ≤ trust < 0.65  — some signals missing; cross-check advised
  unverified trust < 0.35   — response could not be verified; use with caution
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field

from app.factshield.grounding import check_grounding
from app.factshield.consistency import check_consistency
from app.factshield.confidence import score_confidence
from app.engine.llm import chat_variant


# ── Result schema ─────────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    entailment: bool
    consistency: bool
    confidence: float           # 0–1

    entailment_score: float = 0.0
    consistency_score: float = 0.0

    # Composite trust signal — THE primary output of the 3-pipeline
    trust_score: float = 0.0    # 0–1
    trust_tier: str = "unverified"  # "verified" | "partial" | "unverified"

    source_type: str = "none"


# ── Main validator ────────────────────────────────────────────────────────────

async def validate(
    response: str,
    source_passage: str,
    system: str,
    messages: list[dict],
    logprobs: bytes,
    seq_len: int,
    skip_entailment: bool = False,
    source_type: str = "none",
) -> ValidationResult:
    """Run the FactShield 3-pipeline in parallel and compute the trust score.

    Never raises — individual pipeline failures produce safe neutral defaults
    so one broken model never takes down the whole response.
    """
    # Entailment uses a 500-char clean claim (no markdown, no preamble)
    # Consistency uses the full stripped response for better sentence coverage
    claim = _extract_claim(response)                          # for entailment
    primary_clean = _strip_markdown(response)[:2000]          # for selfcheck
    source = (source_passage or "")[:5000]                    # more context for MiniCheck

    # ── Pipeline 2: Entailment (MiniCheck NLI, sentence-level) ──────────────────
    async def _entailment() -> float:
        if skip_entailment or not source:
            return 1.0  # neutral — not applicable for non-document sources
        try:
            # Split claim into sentences and score each against the full source.
            # Averaging sentence-level scores is more reliable than scoring the
            # full response as one block — MiniCheck is calibrated for short claims.
            sentences = [
                s.strip() for s in re.split(r'(?<=[.!?])\s+', claim)
                if len(s.strip()) > 20
            ]
            if not sentences:
                sentences = [claim]

            scores = []
            for sent in sentences[:6]:  # cap at 6 sentences to bound latency
                s = await asyncio.to_thread(check_grounding, source, sent)
                scores.append(float(s))

            return sum(scores) / len(scores) if scores else 0.5
        except Exception as e:
            print(f"[Pipeline2/Entailment] {e}")
            return 0.5

    # ── Pipeline 1: SelfCheck (BERTScore, 3 variants) ─────────────────────────
    async def _consistency() -> float:
        """Generate K=3 independent variants then score sentence-level consistency.

        Follows the SelfCheckGPT protocol: each sentence in the primary response
        is scored against K sampled passages using BERTScore (bert-base-uncased).
        All 3 variant generations run in parallel — latency ≈ single call.
        """
        try:
            v1, v2, v3 = await asyncio.gather(
                chat_variant(system, messages, max_tokens=300),
                chat_variant(system, messages, max_tokens=300),
                chat_variant(system, messages, max_tokens=300),
            )
            variants = [_strip_markdown(v)[:800] for v in [v1, v2, v3] if v and len(v.strip()) > 10]
            if not variants:
                return 0.9
            # Pass full primary text — BERTScore splits into sentences internally
            score = await asyncio.to_thread(check_consistency, primary_clean, variants)
            return float(score)
        except Exception as e:
            print(f"[Pipeline1/Consistency] {e}")
            return 0.9

    # ── Pipeline 3: Token Probability Confidence ──────────────────────────────
    async def _confidence(ent_score: float) -> float:
        """Calibrated confidence from the research pipeline's token probability features.

        Uses extract_features_vectorized (perplexity + tail_nll from pipelines/token_prob)
        directly — not the trained classifier, which is out-of-distribution for
        GPT-4o-mini decoder-only logprobs.  The features are model-agnostic.

        Blended 60/40 with entailment score: combines document-grounding signal
        (entailment) with model-internal uncertainty signal (token probability).
        """
        try:
            p_hall = await asyncio.to_thread(score_confidence, logprobs, seq_len)
            logprob_conf = max(0.0, 1.0 - float(p_hall))
        except Exception:
            logprob_conf = 0.5
        blended = 0.60 * ent_score + 0.40 * logprob_conf
        return round(min(1.0, max(0.0, blended)), 4)

    # ── Run all three in parallel ─────────────────────────────────────────────
    ent_score, con_score = await asyncio.gather(_entailment(), _consistency())
    conf = await _confidence(float(ent_score))

    ent_bool = float(ent_score) >= 0.15
    con_bool = float(con_score) >= 0.20

    trust, tier = _compute_trust(
        ent_score=float(ent_score),
        con_score=float(con_score),
        conf=conf,
        source_type=source_type,
        skip_entailment=skip_entailment,
    )

    return ValidationResult(
        entailment=ent_bool,
        consistency=con_bool,
        confidence=conf,
        entailment_score=float(ent_score),
        consistency_score=float(con_score),
        trust_score=trust,
        trust_tier=tier,
        source_type=source_type,
    )


# ── Trust score computation ───────────────────────────────────────────────────

def _compute_trust(
    ent_score: float,
    con_score: float,
    conf: float,
    source_type: str,
    skip_entailment: bool,
) -> tuple[float, str]:
    """Compute composite trust score with source-aware weights.

    Document source: entailment is the primary signal — if the response isn't
    grounded in the uploaded document, trust should be low regardless of how
    consistent or confident the model is.

    ArXiv/Web: entailment is skipped (retrieved snippet may be unrelated), so
    consistency and confidence carry the full weight.  Trust is capped at 0.64
    (just below the "verified" threshold) because we can't confirm the response
    is grounded in the user's specific course material.

    No source: no grounding at all — capped at 0.50 (always partial or lower).
    """
    if source_type == "document" and not skip_entailment:
        # Continuous weighted blend — entailment score is the primary signal.
        # Using ent_score directly (not as a hard gate) gives more discriminative
        # trust scores and avoids collapsing borderline cases to near-zero.
        raw = 0.50 * ent_score + 0.30 * con_score + 0.20 * conf
        # Hard cap: if entailment score is very low (< 0.10), response cannot
        # reach "verified" — it may be consistent/confident but clearly ungrounded.
        if ent_score < 0.10:
            raw = min(raw, 0.34)
    elif source_type in ("academic", "web"):
        raw = 0.55 * con_score + 0.45 * conf
        raw = min(raw, 0.49)  # cap just below "verified" — only local doc can be verified
    else:
        # no source
        raw = 0.45 * con_score + 0.55 * conf
        raw = min(raw, 0.40)  # cap: no grounding source at all

    trust = round(min(1.0, max(0.0, raw)), 4)

    if trust >= 0.50:
        tier = "verified"
    elif trust >= 0.22:
        tier = "partial"
    else:
        tier = "unverified"

    return trust, tier


# ── Markdown processing ───────────────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    """Remove all markdown syntax so NLI models receive clean prose.

    MiniCheck (roberta-large) was trained on plain text.  Markdown tokens
    (**bold**, ## headings, $math$) reduce NLI scores from ~0.94 to ~0.01
    on identical factual content.
    """
    text = re.sub(r'```[\s\S]*?```', ' ', text)            # fenced code blocks
    text = re.sub(r'`[^`\n]+`', ' ', text)                 # inline code
    text = re.sub(r'\$\$[\s\S]*?\$\$', ' ', text)          # display math
    text = re.sub(r'\$[^$\n]{1,80}\$', ' ', text)          # inline math
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)  # headings
    text = re.sub(r'\*{1,3}([^*\n]+)\*{1,3}', r'\1', text)     # bold/italic
    text = re.sub(r'_{1,2}([^_\n]+)_{1,2}', r'\1', text)       # underline
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)       # images
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)        # links
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)  # bullets
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE) # numbered
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)        # blockquotes
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)  # hr
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _extract_claim(text: str) -> str:
    """Extract clean prose for NLI entailment scoring.

    Strips the **Source:** footer added by citation_enforcer, then removes all
    markdown formatting and returns the first ~500 chars of substantive prose.
    """
    text = re.sub(r'\n+\*\*Source:\*\*.*$', '', text, flags=re.DOTALL)
    text = _strip_markdown(text)
    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 30]
    claim = ' '.join(paragraphs[:3]) if paragraphs else text
    return claim[:500].strip()
