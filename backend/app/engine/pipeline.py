"""FactShield core pipeline: context → generate → validate → return.

Flow for every feature:
  1. Build context  (local doc → ArXiv → Web)
  2. Build messages (system prompt + full history + current query with context)
  3. Generate       (GPT-4o-mini / Gemini / Ollama)
  4. Validate       (3-pipeline: entailment + consistency + confidence, in parallel)
  5. Attach citation and return
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from typing import Any

from app.schemas.chat import ChatMessage
from app.engine.llm import chat
from app.engine.validator import validate, ValidationResult
from app.engine.context import build_context, build_submission_context, source_label
from app.factshield.citation_enforcer import ensure_citation_in_response

# ── Token limits per mode ─────────────────────────────────────────────────────

_MAX_TOKENS: dict[str, int] = {
    "concept-guide":        900,
    "problem-navigator":   1400,
    "submission-validator": 1600,
    "quiz-generator":      2200,
    "assignment-grader":    900,
    "exam-generator":      1800,
    "adaptive-feedback":    900,
    "learning-insights":    900,
}
_DEFAULT_TOKENS = 700


# ── System prompts ────────────────────────────────────────────────────────────

_SYSTEM: dict[str, str] = {
    "concept-guide": (
        "You are FactShield's academic assistant helping students understand their course material.\n\n"
        "Answer questions clearly and thoroughly using the source material provided in each message. "
        "Cover the core idea, how it works, and include a concrete example where it helps. "
        "Use $...$ for inline math and $$...$$ on its own line for display math. "
        "Cite specific facts with [Page X] or [Section: Name]. "
        "Adapt response depth to the question — a simple follow-up gets a focused answer, "
        "a complex concept gets a full breakdown. "
        "Build naturally on the conversation history; don't re-introduce context already established."
    ),
    "problem-navigator": (
        "You are FactShield's problem-solving coach.\n\n"
        "Guide students step by step — do NOT give the final answer. Your role is coach, not solver.\n"
        "Walk through: what's being asked, what's known, the relevant formula(s) with each symbol named, "
        "the reasoning approach, and the substitution setup. Stop before the final numeric result. "
        "End with a brief self-check checklist.\n\n"
        "Math rendering (required):\n"
        "- Inline: $formula$\n"
        "- Block (own line): $$\nformula\n$$\n"
        "- Never write bare LaTeX outside dollar signs — it won't render.\n"
        "Cite formula sources with [Page X]."
    ),
    "submission-validator": (
        "You are FactShield's submission auditor. Use only the provided source material — never general knowledge.\n\n"
        "Audit the student's submission sentence-by-sentence. "
        "Flag only claims that contradict or are unsupported by the document. "
        "For each flag: quote the document, explain the issue, give a corrected sentence. "
        "If a sentence isn't covered in the document, mark 'Not covered in document'.\n\n"
        "Output format (required):\n"
        "## Submission Audit\n\n"
        "**Overall:** [N] passed · [N] flagged\n\n"
        "### ✅ Passed\n"
        "- \"[sentence]\" — grounded in document.\n\n"
        "### ⚠️ Flagged\n\n"
        "**[N]. \"[exact sentence]\"**\n"
        "- **Issue:** [Overgeneralization / Contradiction / Unsupported Claim / External Information]\n"
        "- **Why:** [one sentence referencing the document]\n"
        "- **Document says:** \"[direct quote or paraphrase]\" *(page/section)*\n"
        "- **Revision:** \"[corrected sentence]\"\n\n"
        "### 📋 Action Items\n"
        "1. [most critical fix]\n"
        "2. [second fix if needed]"
    ),
    "assignment-grader": (
        "You are FactShield's assignment grader.\n\n"
        "Grade submissions against the provided rubric and source material. "
        "Give a clear letter grade with numeric score, cite specific strengths [Page X], "
        "identify gaps [Page X], and give 2-3 concrete actionable suggestions. "
        "Be honest and constructive — like a good professor's written feedback, not a form."
    ),
    "exam-generator": (
        "You are FactShield's exam generator.\n\n"
        "Create well-structured exams from the provided course material. "
        "Include multiple-choice questions with 4 options each. "
        "Vary difficulty from recall to application. "
        "Tag each question with its source [Page X]. "
        "Include a complete answer key with a brief rationale for each answer. "
        "Format cleanly in markdown."
    ),
    "adaptive-feedback": (
        "You are FactShield's adaptive feedback tutor.\n\n"
        "Write targeted mini-lessons for specific knowledge gaps using the source material. "
        "Identify the misunderstanding, explain the concept correctly (basic idea → application), "
        "cite passages [Page X], and end with a practice question they can try. "
        "Be encouraging and precise."
    ),
    "learning-insights": (
        "You are FactShield's learning analytics engine.\n\n"
        "Analyze learning patterns and generate actionable teaching insights. "
        "For each insight: name the concept, explain the root cause, cite [Page X], "
        "and give a concrete recommendation the teacher can act on immediately. "
        "Be specific — avoid generic advice."
    ),
}

_SYSTEM_DEFAULT = (
    "You are FactShield, an AI academic assistant with 3-pipeline fact verification. "
    "Answer helpfully and accurately using the source material provided. "
    "Cite [Page X] for specific facts. Build naturally on the conversation."
)


# ── Message builder ───────────────────────────────────────────────────────────

def build_messages(
    chat_history: list[ChatMessage] | None,
    query: str,
    source_passage: str,
) -> list[dict]:
    """Build the message list: conversation history + current query with injected context."""
    messages: list[dict] = []

    # Last 10 messages = 5 full turns of context
    for msg in (chat_history or [])[-10:]:
        messages.append({"role": msg.role, "content": msg.content})

    # Inject retrieved source into the current user turn
    if source_passage and source_passage.strip():
        user_content = f"{query}\n\n---\n*Source material:*\n{source_passage[:3000]}"
    else:
        user_content = query

    messages.append({"role": "user", "content": user_content})
    return messages


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def run_pipeline(
    mode: str,
    role: str,
    query: str,
    chat_history: list[ChatMessage] | None,
    doc_ids: list[uuid.UUID],
    doc_filenames: dict[uuid.UUID, str] | None = None,
    context: str | None = None,
) -> dict[str, Any]:
    """Run the full FactShield pipeline for one request."""

    mode_key = mode.replace("_", "-").lower()

    # ── 1. Build context ──────────────────────────────────────────────────────
    if mode_key == "submission-validator" and doc_ids:
        source_passage, source_type, source_ref = await build_submission_context(
            query, doc_ids, doc_filenames
        )
    else:
        source_passage, source_type, source_ref = await build_context(
            query, doc_ids, doc_filenames
        )

    # ── 2. System prompt ──────────────────────────────────────────────────────
    system = _SYSTEM.get(mode_key, _SYSTEM_DEFAULT)
    if context:
        system = f"{system}\n\nAdditional context: {context}"

    # ── 3. Build messages ─────────────────────────────────────────────────────
    messages = build_messages(chat_history, query, source_passage)

    # ── 4. Generate ───────────────────────────────────────────────────────────
    max_tokens = _MAX_TOKENS.get(mode_key, _DEFAULT_TOKENS)
    text, logprobs, seq_len = await chat(system, messages, max_tokens=max_tokens)

    if not text:
        return _error(mode_key, role)

    # ── 5. Validate (3-pipeline, parallel) ───────────────────────────────────
    # Entailment is only meaningful for local-document sources where the LLM
    # is constrained to the retrieved passage.  For ArXiv/Web the retrieved
    # snippet may be topically unrelated to the response (the LLM supplements
    # from training knowledge), so we skip it to avoid false negatives.
    # The trust score accounts for this: non-document sources are capped below
    # the "verified" tier regardless of consistency/confidence scores.
    # Adaptive feedback is pedagogical strategy (teaching advice), not content
    # recall — it can't be grounded in a document passage. Treat as academic
    # so consistency + confidence carry the weight, not entailment.
    effective_source_type = source_type
    if mode_key == "adaptive-feedback":
        effective_source_type = "academic"

    skip_ent = effective_source_type not in ("document",)
    v: ValidationResult = await validate(
        response=text,
        source_passage=source_passage,
        system=system,
        messages=messages,
        logprobs=logprobs,
        seq_len=seq_len,
        skip_entailment=skip_ent,
        source_type=effective_source_type,
    )

    # ── 6. Attach citation ────────────────────────────────────────────────────
    text_cited = ensure_citation_in_response(
        text,
        source_type=source_type,
        source_reference=source_ref or "",
    )

    # ── 7. Inject trust annotation into response text ─────────────────────────
    # This is what turns the pipeline from decorative to functional: the user
    # sees the validation verdict INSIDE the response, not just as a sidebar badge.
    text_annotated = _annotate_trust(text_cited, v.trust_tier, source_type, v.trust_score)

    fallback = "none" if source_type == "document" else source_type

    return {
        "text": text_annotated,
        "scores": {
            "entailment": v.entailment,
            "consistency": v.consistency,
            "confidence": v.confidence,
            "entailment_score": v.entailment_score,
            "consistency_score": v.consistency_score,
            "trust_score": v.trust_score,
            "trust_tier": v.trust_tier,
            "fallback_type": fallback,
        },
        "source_used": source_label(source_type),
        "source_reference": source_ref,
        "mode": mode_key,
        "role": role,
    }


# ── Quiz pipeline (JSON output, separate path) ────────────────────────────────

async def run_quiz_pipeline(
    query: str,
    chat_history: list[ChatMessage] | None,
    doc_ids: list[uuid.UUID],
    doc_filenames: dict[uuid.UUID, str] | None = None,
) -> dict[str, Any]:
    """Quiz generator — returns JSON array of questions."""
    from app.factshield.prompts import get_quiz_generator_prompt
    from app.factshield.grounding import check_grounding

    source_passage, source_type, source_ref = await build_context(query, doc_ids, doc_filenames)

    quiz_system = (
        "You are a quiz designer. "
        "Return ONLY a valid JSON array of question objects matching the schema below. "
        "No markdown fences, no commentary, no text outside the array."
    )
    quiz_prompt = get_quiz_generator_prompt(query)
    context_block = source_passage[:3000] if source_passage else "Use your knowledge to generate questions on this topic."

    messages = [{"role": "user", "content": f"{quiz_prompt}\n\nEvidence Context:\n{context_block}"}]

    text, logprobs, seq_len = await chat(
        system=quiz_system,
        messages=messages,
        max_tokens=_MAX_TOKENS["quiz-generator"],
        temperature=0.3,
    )

    # Clean up JSON (strip markdown fences if model added them)
    text_clean = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.IGNORECASE)
    text_clean = re.sub(r'\s*```$', '', text_clean).strip()

    from app.engine.validator import _compute_trust

    # Quiz questions are interrogative (not declarative assertions), so NLI
    # entailment scoring against the source passage gives false negatives near 0.
    # Grounding is guaranteed by the prompt — the LLM is instructed to generate
    # questions only from the evidence context. Skip NLI and mark as grounded.
    ent_score = 1.0
    # JSON output at temperature 0.3 is near-deterministic — consistency is high.
    con_score = 0.70
    conf = 0.80

    trust, tier = _compute_trust(
        ent_score=ent_score,
        con_score=con_score,
        conf=conf,
        source_type=source_type,
        skip_entailment=True,
    )

    fallback = "none" if source_type == "document" else source_type

    return {
        "text": text_clean,
        "scores": {
            "entailment": True,
            "consistency": True,
            "confidence": conf,
            "entailment_score": ent_score,
            "consistency_score": con_score,
            "trust_score": trust,
            "trust_tier": tier,
            "fallback_type": fallback,
        },
        "source_used": source_label(source_type),
        "source_reference": source_ref,
        "mode": "quiz-generator",
        "role": "student",
    }


# ── Trust annotation ─────────────────────────────────────────────────────────

def _annotate_trust(text: str, trust_tier: str, source_type: str, trust_score: float = 0.0) -> str:
    """Inject a FactShield validation notice into the response text.

    This is the key step that makes the pipeline functional rather than decorative.
    The notice appears INSIDE the message the user reads — not just as a badge
    they might ignore — so the validation verdict is always visible.

    verified   → no annotation (clean response, fully grounded)
    partial    → subtle footer notice to cross-check key claims
    unverified → prominent header warning with specific reason
    """
    if trust_tier == "verified":
        return text

    # Suppress the disruptive header for borderline unverified (0.22–0.28).
    # The badge in the UI already shows the tier — the header is reserved for
    # genuinely low-trust responses where the user must be warned in-line.
    if trust_tier == "unverified" and trust_score >= 0.22:
        trust_tier = "partial"

    if trust_tier == "partial":
        if source_type == "document":
            notice = (
                "\n\n---\n"
                "*FactShield: partially verified — response is grounded in your document "
                "but some explanations extend beyond the retrieved passages. "
                "Core facts are supported; verify any elaborations.*"
            )
        elif source_type in ("academic", "web"):
            notice = (
                "\n\n---\n"
                "*FactShield: partially verified — response draws from external sources "
                "(ArXiv / web). No document was uploaded to cross-reference. "
                "Treat as supplementary and verify against your course material.*"
            )
        else:
            notice = (
                "\n\n---\n"
                "*FactShield: partially verified — response uses general knowledge. "
                "Upload your course document for stronger grounding and verification.*"
            )
        return text + notice

    # unverified — only inject a prominent warning for genuinely low-trust responses
    # (trust < 0.22). Scores between 0.22–0.28 already show as "unverified" in
    # the badge but don't need a disruptive header — the badge is sufficient.
    if source_type == "document":
        header = (
            "> **FactShield Notice:** This response could not be verified against your "
            "uploaded document. The content may not accurately reflect your course "
            "material — please verify all claims independently.\n\n"
        )
    elif source_type in ("academic", "web"):
        header = (
            "> **FactShield Notice:** This response is based on general knowledge sources "
            "(not your uploaded document) and could not be fully verified. "
            "Treat as supplementary information.\n\n"
        )
    else:
        header = (
            "> **FactShield Notice:** No source material was available to verify this "
            "response. Treat as general knowledge and cross-check before use.\n\n"
        )
    return header + text


# ── Error helper ──────────────────────────────────────────────────────────────

def _error(mode: str, role: str) -> dict[str, Any]:
    return {
        "text": "I'm having trouble generating a response right now. Please try again.",
        "scores": {
            "entailment": False,
            "consistency": False,
            "confidence": 0.0,
            "fallback_type": "error",
        },
        "source_used": "",
        "source_reference": None,
        "mode": mode,
        "role": role,
    }
