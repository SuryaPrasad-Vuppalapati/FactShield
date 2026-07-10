"""Shared FactShield pipeline function.

All 9 modes (5 student + 4 teacher) call run_factshield_pipeline() to obtain
consistent entailment / consistency / confidence scores in one place.

Includes hybrid search, token optimization, and provider selection.
"""

from __future__ import annotations

from typing import Any

from app.retrieval.cache import check_semantic_cache, save_to_semantic_cache
from app.retrieval.retriever import retrieve_with_scores
from app.db.session import async_session_maker
from app.models.document import Document
from app.models.generation import Generation

from app.schemas.chat import ChatMessage

from app.factshield.confidence import score_confidence
from app.factshield.consistency import check_consistency
from app.factshield.generation import generate_k_variants, generate_with_logprobs, generate_response
from app.factshield.grounding import check_grounding
from app.factshield.token_optimizer import (
    decompose_query,
    constrain_response_length,
    summarize_chunks,
    should_skip_generation,
)
from app.factshield.citation_enforcer import ensure_citation_in_response
from app.config import Settings

settings = Settings()


def _source_label(source_type: str, mode: str | None = None) -> str:
    """Convert internal source codes into a UI-friendly label."""
    if source_type == "mixed":
        return "Local document + online sources"
    if source_type == "academic":
        return "ArXiv research"
    if source_type == "copilot":
        return "Copilot knowledge base"
    if source_type == "web":
        return "Live web search"
    if source_type == "document":
        return "Local document"
    if source_type == "refusal":
        return ""
    return mode or source_type


def _attach_source_metadata(payload: dict[str, Any], source_type: str, mode: str, source_reference: str | None = None) -> dict[str, Any]:
    label = _source_label(source_type, mode)
    payload["source_used"] = label  # empty string is fine; UI hides it
    payload["source_reference"] = source_reference or label or None
    return payload


def _markdown_link(title: str, url: str | None) -> str:
    if url and url.startswith("http"):
        return f"[{title}]({url})"
    return title


async def _resolve_document_references(doc_ids: list[Any] | None) -> tuple[list[str], str]:
    """Resolve selected document IDs into clickable markdown references.

    Returns a tuple of:
    - ordered list of markdown links (for citations)
    - plain display string (for source metadata / UI)
    """
    import uuid

    if not doc_ids:
        return [], "Local document"

    ordered_ids: list[uuid.UUID] = []
    for doc_id in doc_ids:
        try:
            ordered_ids.append(uuid.UUID(str(doc_id)))
        except Exception:
            continue

    if not ordered_ids:
        return [], "Local document"

    async with async_session_maker() as session:
        from sqlalchemy import select

        stmt = select(Document).where(Document.id.in_(ordered_ids))
        result = await session.execute(stmt)
        docs = {str(doc.id): doc for doc in result.scalars().all()}

    links: list[str] = []
    names: list[str] = []
    for doc_id in ordered_ids:
        doc = docs.get(str(doc_id))
        if not doc:
            continue
        names.append(doc.filename)
        # Local documents: reference by name only (no public URL to link to)
        links.append(doc.filename)

    if not links:
        return [], "Local document"

    return links, ", ".join(names)


async def _gather_parallel_evidence(
    query: str,
    source_passage: str,
    doc_ids: list[Any] | None,
    force_external: bool = False,
    prefer_external_sources: bool = False,
) -> tuple[str, str, str]:
    """Fetch local and online evidence in parallel and merge it into one bundle.

    Returns:
        A tuple of (evidence_bundle, source_type, source_reference).
    """
    import asyncio

    from app.factshield.academic import search_arxiv
    from app.factshield.copilot import search_copilot
    from app.factshield.search import search_web

    def _clip(text: str, limit: int = 1200) -> str:
        text = (text or "").strip()
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "\n[... truncated for token efficiency ...]"

    # In low latency mode, when local context exists, skip external calls entirely.
    document_links, document_names = await _resolve_document_references(doc_ids)
    document_reference = ", ".join(document_links) if document_links else "Local document"
    document_display = document_names or "Local document"

    if (not force_external) and settings.low_latency_mode and source_passage and source_passage != "No grounding passage found.":
        local_only = f"[Local document]\n{_clip(source_passage, 1800)}"
        return local_only, "document", document_reference

    async def _safe_fetch(coro):
        try:
            return await asyncio.wait_for(coro, timeout=settings.external_search_timeout_seconds)
        except Exception:
            return ""

    tasks = [
        asyncio.create_task(_safe_fetch(search_arxiv(query))),
        asyncio.create_task(_safe_fetch(search_copilot(query))),
        asyncio.create_task(_safe_fetch(search_web(query))),
    ]
    arxiv_snippet, copilot_snippet, web_snippet = await asyncio.gather(*tasks)

    import re

    def _extract_url(text: str) -> str | None:
        if not text:
            return None
        m = re.search(r"https?://[^\s\]]+", text)
        return m.group(0).rstrip("),.") if m else None

    sections: list[tuple[str, str, str | None]] = []
    local_sections: list[tuple[str, str, str | None]] = []
    external_sections: list[tuple[str, str, str | None]] = []
    if source_passage and source_passage != "No grounding passage found.":
        # Use document names/links when available; otherwise keep a generic label.
        ref = document_reference if document_links else None
        local_sections.append(("Local document", _clip(source_passage, 1800), ref))
    if arxiv_snippet:
        external_sections.append(("ArXiv", _clip(arxiv_snippet), _extract_url(arxiv_snippet)))
    if copilot_snippet:
        external_sections.append(("Copilot", _clip(copilot_snippet), "https://copilot.microsoft.com"))
    if web_snippet:
        external_sections.append(("Web", _clip(web_snippet), _extract_url(web_snippet)))

    sections.extend(external_sections if prefer_external_sources else local_sections)
    sections.extend(local_sections if prefer_external_sources else external_sections)

    if not sections:
        return "", "document", "your syllabus"

    bundle = "\n\n".join(f"[{label}]\n{content}" for label, content, _ in sections)
    has_local    = any(lbl == "Local document" for lbl, _, _ in sections)
    has_external = any(lbl != "Local document" for lbl, _, _ in sections)
    if has_local and has_external:
        source_type = "mixed"
    elif has_local:
        source_type = "document"
    else:
        # One or more external sources — use the most prominent one for the label
        dominant = next((lbl.lower() for lbl, _, _ in sections if lbl != "Copilot"), None)
        if dominant == "arxiv":
            source_type = "academic"
        elif dominant == "web":
            source_type = "web"
        else:
            source_type = "copilot"
    reference_parts = []
    for label, _, url in sections:
        if label == "Local document":
            reference_parts.append(document_display or "Local document")
        elif label == "Copilot":
            pass  # Copilot content is used for evidence but not surfaced as a named citation
        else:
            reference_parts.append(_markdown_link(label, url))
    source_reference = ", ".join(reference_parts) or "AI Knowledge Base"
    return bundle, source_type, source_reference


# ────────────────────────────────────────────────────────────────────────────
# Per-mode system prompt builder
# ────────────────────────────────────────────────────────────────────────────

from app.factshield.prompts import build_prompt


# ────────────────────────────────────────────────────────────────────────────
# Shared pipeline runner
# ────────────────────────────────────────────────────────────────────────────

async def run_factshield_pipeline(
    query: str,
    mode: str,
    role: str,
    source_passage: str,
    context: str | None = None,
    skip_entailment: bool = False,
    chat_history: list[ChatMessage] | None = None,
    doc_ids: list[Any] | None = None,
    fast_path: bool = False,
    source_type: str = "document",
) -> dict[str, Any]:
    """Run all three FactShield pipelines with CAG, token optimization, and hybrid retrieval."""
    import os
    import numpy as _np
    import pandas as _pd
    from pipelines.token_prob.scorer import extract_features_vectorized as _efv
    from pipelines.token_prob.classifier import FEATURE_COLS as _FC
    _debug = os.getenv("DEBUG_PIPELINE", "0") == "1"
    document_links, document_names = await _resolve_document_references(doc_ids)
    document_reference = ", ".join(document_links) if document_links else "Local document"
    document_display = document_names or "Local document"

    # Submission Validator requires a document — it audits the student's text against
    # course material. Without a doc the audit has nothing authoritative to check against.
    if mode == "submission-validator" and not doc_ids:
        return _attach_source_metadata({
            "text": (
                "**Document required for Submission Validator**\n\n"
                "This tool audits your submission sentence-by-sentence against your course document. "
                "Please upload your course material using the 📎 button, select it, and then paste your draft."
            ),
            "scores": {"entailment": False, "consistency": False, "confidence": 0.0, "fallback_type": "refusal"},
            "role": role,
            "mode": mode,
        }, "refusal", mode, None)

    # OPTIMIZATION: Constrain response length based on mode to reduce token usage
    max_response_tokens = constrain_response_length(mode)
    variant_k = 1 if settings.low_latency_mode else 2
    
    # Step 0: ARCH Component 3 — Intelligent Query Rewriting (runs in PARALLEL, non-blocking)
    effective_query = query
    history_len = len(chat_history) if chat_history else 0
    query_word_count = len(query.split())

    # Detect follow-up indicators: short pronouns, comparison words, continuation phrases
    _FOLLOWUP_TOKENS = {"that", "it", "this", "those", "them", "more", "again", "also", "same"}
    _FOLLOWUP_PHRASES = ("what about", "how about", "why is", "what if", "can you", "could you",
                         "explain more", "tell me more", "and how", "so how", "but why", "but what")
    _query_lower = query.lower()
    _is_followup = (
        any(tok in _query_lower.split() for tok in _FOLLOWUP_TOKENS)
        or any(ph in _query_lower for ph in _FOLLOWUP_PHRASES)
    )
    _should_rewrite = history_len > 0 and (query_word_count <= 20 or _is_followup)

    if (not settings.low_latency_mode) and _should_rewrite:
        import asyncio as _asyncio
        import os as _os

        async def _rewrite_query():
            try:
                from google import genai as _genai
                _client = _genai.Client(api_key=_os.environ.get("GEMINI_API_KEY"))
                history_str = " | ".join(
                    f"{m.role}: {m.content[:120]}" for m in (chat_history or [])[-8:]
                )
                rewrite_prompt = (
                    f"Conversation history: {history_str}\n"
                    f"Latest message: '{query}'\n\n"
                    "Task: Rewrite the latest message as a fully self-contained question or request, "
                    "resolving any pronouns ('it', 'that', 'this', 'those') or references to prior context. "
                    "If the message is already fully self-contained with no ambiguous references, return it unchanged. "
                    "Return ONLY the rewritten text — no explanation, no quotes."
                )
                resp = _client.models.generate_content(model="gemini-2.5-flash", contents=rewrite_prompt)
                rewritten = resp.text.strip().strip('"\'')
                if rewritten and len(rewritten) > 5:
                    return rewritten
            except Exception as _e:
                print(f"Query rewriter failed (using original): {_e}")
            return query

        # Fire rewrite task and let it run in parallel (non-blocking)
        rewrite_task = _asyncio.create_task(_rewrite_query())
        # Await rewrite result before submitting to orchestrator (it runs alongside cache check)
        effective_query = await rewrite_task
        if effective_query != query:
            print(f"=== QUERY REWRITTEN: '{query}' -> '{effective_query}' ===")

    # Step 1: Semantic Cache (CAG) with early stopping optimization
    # Skip cache for quiz-generator so fresh evidence is always used.
    cached_gen = None
    if mode not in ["quiz-generator"]:
        cached_gen = await check_semantic_cache(
            effective_query,
            doc_ids,
            mode,
            source_type=source_type,
        )

    if cached_gen:
        print(f"=== SEMANTIC CACHE HIT ===")
        cache_confidence = cached_gen.confidence_score
        
        # OPTIMIZATION: If cache confidence is very high, skip regeneration
        if settings.enable_token_optimization and should_skip_generation(cache_confidence, threshold=0.85):
            print(f"=== EARLY STOPPING (cache confidence={cache_confidence:.2f}) ===")
            cached_text = ensure_citation_in_response(
                cached_gen.response_text,
                source_type=source_type,
                source_reference=document_reference if source_type == "document" else "your syllabus",
            )
            return _attach_source_metadata({
                "text": cached_text,
                "scores": {
                    "entailment": cached_gen.grounding_score >= 0.6 if not skip_entailment else None,
                    "consistency": cached_gen.consistency_score >= 0.5,
                    "confidence": cache_confidence,
                },
                "role": role,
                "mode": mode,
            }, source_type, mode, document_reference if source_type == "document" else None)

    # OPTIMIZATION: Summarize chunks to reduce context size
    if settings.enable_token_optimization and source_passage:
        chunks = source_passage.split("\n")
        source_passage = summarize_chunks(chunks, max_length=2000)

    async def _run_verification_loop(v_prompt: str, v_source: str, v_skip_entailment: bool, v_fallback_type: str | None = None):
        MAX_RETRIES = 1 if fast_path else 3
        best_candidate = None
        best_combined_score = -1.0
        
        for attempt in range(MAX_RETRIES):
            if _debug: print(f"--- Attempt {attempt+1}/{MAX_RETRIES} (Fallback: {v_fallback_type}) ---")
            
            gen = await generate_with_logprobs(v_prompt, chat_history, max_tokens=max_response_tokens)
            if gen["text"] == "AI_SERVICE_UNAVAILABLE":
                return _attach_source_metadata({
                    "text": "AI_SERVICE_UNAVAILABLE",
                    "scores": {"entailment": False, "consistency": False, "confidence": 0.0, "fallback_type": v_fallback_type},
                    "role": role,
                    "mode": mode,
                }, v_fallback_type or source_type, mode)

            if fast_path:
                consistency_score = 1.0
                consistency_bool = True
                lr_signal = 1.0
                prob_bool = True
                entailment_bool = True
                grounding_score = 1.0
                confidence = 1.0
            else:
                import asyncio
                # OPTIMIZED: Run Pipeline 1 and 3 in parallel using asyncio.to_thread
                async def _run_p1():
                    if v_skip_entailment: return 1.0
                    # OPTIMIZED: Do not aggressively truncate; MiniCheck needs the full context to verify accurately.
                    claim = gen["text"]
                    if "Answer:" in claim:
                        claim = claim.split("Answer:", 1)[1]
                    elif "Guided Approach:" in claim:
                        claim = claim.split("Guided Approach:", 1)[1]
                    if "Citations:" in claim:
                        claim = claim.split("Citations:")[0]
                    claim = claim.strip()

                    return await asyncio.to_thread(check_grounding, v_source, claim)
                    
                async def _run_p3():
                    return await asyncio.to_thread(score_confidence, gen["token_logprobs"], gen["seq_len"])

                grounding_score, lr_p_hall = await asyncio.gather(_run_p1(), _run_p3())
                
                print(f"=== GROUNDING DEBUG ===")
                print(f"gen_text: {gen['text']}")
                print(f"v_source: {v_source[:1000]}...")
                print(f"grounding_score: {grounding_score}")
                print(f"=======================")
                
                lr_signal = float(_np.clip(1.0 - lr_p_hall, 0.1, 0.9))
                prob_bool = lr_p_hall < 0.5
                
                if v_skip_entailment:
                    entailment_bool = None
                else:
                    # Threshold 0.4: MiniCheck on real doc content typically scores 0.35–0.65
                    entailment_bool = grounding_score >= 0.4

                # OPTIMIZED: Fast-fail only when grounding clearly fails (< 0.4)
                # Don't short-circuit on prob_bool alone - it's based on simulated logprobs
                if entailment_bool is False:
                    consistency_score = 0.0
                    consistency_bool = False
                else:
                    # Note: k is already optimized to 2 in generation.py
                    variants = await generate_k_variants(
                        v_prompt,
                        k=variant_k,
                        chat_history=chat_history,
                        max_tokens=max(120, int(max_response_tokens * 0.75)),
                    )
                    other_samples = [v for v in variants if v != gen["text"]]
                    if not other_samples:
                        other_samples = variants[:1] if variants else [gen["text"]]

                    consistency_score = await asyncio.to_thread(check_consistency, gen["text"], other_samples)
                    consistency_bool = consistency_score >= 0.3

            if v_skip_entailment:
                confidence = float(0.60 * consistency_score + 0.40 * lr_signal)
            else:
                confidence = float(0.40 * grounding_score + 0.35 * consistency_score + 0.25 * lr_signal)

            candidate = {
                "text": gen["text"],
                "token_logprobs": gen["token_logprobs"],
                "seq_len": gen["seq_len"],
                "scores": {
                    "entailment": entailment_bool,
                    "consistency": consistency_bool,
                    "confidence": confidence,
                    "fallback_type": v_fallback_type,
                },
                "raw_scores": {
                    "grounding": grounding_score,
                    "consistency": consistency_score,
                    "lr_signal": lr_signal,
                }
            }

            passed_entailment = v_skip_entailment or entailment_bool
            passed_consistency = consistency_bool
            passed_prob = prob_bool

            # Accept response if grounding passes — consistency and prob are secondary signals
            if passed_entailment and (passed_consistency or passed_prob):
                best_candidate = candidate
                if _debug: print("-> STRICT PASS! Breaking loop.")
                break
            
            if confidence > best_combined_score:
                best_combined_score = confidence
                best_candidate = candidate

        return best_candidate

    prompt = build_prompt(effective_query, mode, role, source_passage, context)

    if mode == "quiz-generator":
        import json as _json
        import re as _re

        def _extract_exam_topic(q: str) -> str:
            text = (q or "").strip()
            patterns = [
                r"(?:give|generate|create|make)\s+me\s+\d+\s+(?:questions?|items?|problems?)\s+(?:on|about|for)\s+(.+)$",
                r"\d+\s+(?:questions?|items?|problems?)\s+(?:on|about|for)\s+(.+)$",
                r"(?:on|about|for)\s+(.+)$",
            ]
            for pattern in patterns:
                m = _re.search(pattern, text, flags=_re.I)
                if m:
                    candidate = m.group(1).strip()
                    candidate = _re.sub(r"^(the\s+topic\s+of\s+)", "", candidate, flags=_re.I)
                    candidate = candidate.rstrip(".?! ")
                    if candidate:
                        return candidate
            return text.rstrip(".?! ") or "the selected topic"

        def _extract_json_blob(text: str) -> str:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return text[start:end + 1]
            return text

        def _extract_json_array_blob(text: str) -> str:
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1 and end > start:
                return text[start:end + 1]
            return text

        def _requested_count_from_query(q: str) -> int:
            m = _re.search(r"\b(\d{1,2})\s+(?:questions?|items?|problems?)\b", q, flags=_re.I)
            if m:
                try:
                    return max(1, min(20, int(m.group(1))))
                except Exception:
                    return 5
            m = _re.search(r"\b(\d{1,2})\b", q)
            if m:
                try:
                    return max(1, min(20, int(m.group(1))))
                except Exception:
                    return 5
            return 5

        def _topic_understanding_layer(user_query: str) -> dict[str, Any]:
            topic = _extract_exam_topic(user_query)
            requested = _requested_count_from_query(user_query)
            return {
                "raw_query": (user_query or "").strip(),
                "topic": topic,
                "question_count": requested,
            }

        def _topic_profile_ok(profile: dict[str, Any]) -> bool:
            if not isinstance(profile, dict):
                return False
            domain = str(profile.get("domain", "")).strip()
            subdomains = profile.get("subdomains", [])
            core_concepts = profile.get("core_concepts", [])
            if not domain:
                return False
            if not isinstance(subdomains, list) or not subdomains:
                return False
            if not isinstance(core_concepts, list) or not core_concepts:
                return False
            return True

        async def _domain_understanding_layer(topic: str, evidence: str) -> dict[str, Any]:
            prompt = (
                "You are a domain expert.\n"
                f"Given the topic: {topic}\n\n"
                "First determine the correct meaning of the topic.\n"
                "Create JSON with EXACTLY these keys:\n"
                "1. domain\n"
                "2. subdomains\n"
                "3. core_concepts\n"
                "4. common_terminology\n"
                "5. real_world_applications\n"
                "6. avoid\n\n"
                "Rules:\n"
                "- Return ONLY valid JSON, no markdown or commentary.\n"
                "- Do not generate questions.\n"
                "- 'avoid' must contain concepts that are not related to the intended meaning.\n"
                "- Keep lists concise and topic-accurate.\n\n"
                f"Optional evidence context:\n{(evidence or '')[:3500]}"
            )
            try:
                raw = await generate_response(prompt, [], max_tokens=1400)
                if raw and raw != "AI_SERVICE_UNAVAILABLE":
                    parsed = _json.loads(_extract_json_blob(raw))
                    if _topic_profile_ok(parsed):
                        parsed.setdefault("common_terminology", [])
                        parsed.setdefault("real_world_applications", [])
                        parsed.setdefault("avoid", [])
                        return parsed
            except Exception:
                pass

            # deterministic fallback profile (non-hardcoded, topic-aware)
            return {
                "domain": f"{topic} domain",
                "subdomains": [
                    f"foundations of {topic}",
                    f"methods in {topic}",
                    f"applications of {topic}",
                ],
                "core_concepts": [
                    f"principles of {topic}",
                    f"decision-making using {topic}",
                    f"constraints and trade-offs in {topic}",
                ],
                "common_terminology": [
                    f"{topic} lifecycle",
                    f"{topic} metrics",
                    f"{topic} workflow",
                ],
                "real_world_applications": [
                    f"planning with {topic}",
                    f"execution with {topic}",
                    f"optimization with {topic}",
                ],
                "avoid": [
                    f"unrelated buzzwords not tied to {topic}",
                    "generic placeholders",
                ],
            }

        async def _concept_extraction_layer(topic: str, evidence: str) -> list[str]:
            extraction_prompt = (
                f"Extract 6 to 10 core concepts for exam design on this topic: {topic}.\n"
                "Use evidence if available. Return ONLY JSON with this format:\n"
                "{\"concepts\": [\"concept 1\", \"concept 2\"]}\n\n"
                f"Evidence (optional):\n{(evidence or '')[:3500]}"
            )
            try:
                raw = await generate_response(extraction_prompt, [], max_tokens=900)
                if raw and raw != "AI_SERVICE_UNAVAILABLE":
                    parsed = _json.loads(_extract_json_blob(raw))
                    concepts = parsed.get("concepts")
                    if isinstance(concepts, list):
                        cleaned = [str(c).strip() for c in concepts if str(c).strip()]
                        if cleaned:
                            unique: list[str] = []
                            seen = set()
                            for c in cleaned:
                                k = c.lower()
                                if k not in seen:
                                    seen.add(k)
                                    unique.append(c)
                            return unique[:10]
            except Exception:
                pass
            return [topic]

        async def _scenario_mapping_layer(topic: str, concepts: list[str], evidence: str, total_questions: int) -> list[dict[str, str]]:
            mapping_prompt = (
                f"Create exactly {total_questions} realistic scenario-task pairs for topic: {topic}.\n"
                f"Use these concepts as coverage targets: {_json.dumps(concepts[:10], ensure_ascii=False)}\n"
                "Return ONLY JSON with format:\n"
                "{\"scenarios\":[{\"number\":1,\"scenario\":\"...\",\"task\":\"...\"}]}\n"
                "Rules: scenario must be concrete and non-generic; task must be actionable.\n\n"
                f"Evidence (optional):\n{(evidence or '')[:3000]}"
            )
            try:
                raw = await generate_response(mapping_prompt, [], max_tokens=1300)
                if raw and raw != "AI_SERVICE_UNAVAILABLE":
                    parsed = _json.loads(_extract_json_blob(raw))
                    items = parsed.get("scenarios")
                    if isinstance(items, list) and items:
                        result: list[dict[str, str]] = []
                        for i, item in enumerate(items[:total_questions], start=1):
                            if not isinstance(item, dict):
                                continue
                            sc = str(item.get("scenario", "")).strip()
                            tk = str(item.get("task", "")).strip()
                            if sc and tk:
                                result.append({"number": i, "scenario": sc, "task": tk})
                        if len(result) == total_questions:
                            return result
            except Exception:
                pass

            # Deterministic backup (topic-aware, no hardcoded domain templates)
            backups: list[dict[str, str]] = []
            for i in range(1, total_questions + 1):
                concept = concepts[(i - 1) % max(1, len(concepts))]
                backups.append({
                    "number": i,
                    "scenario": f"A team is making a high-impact decision where {topic} and {concept} affect delivery quality, risk, and outcomes.",
                    "task": f"Choose the best option that applies {concept} correctly under the scenario constraints.",
                })
            return backups

        def _exam_layout_ok(text: str) -> bool:
            try:
                payload = _json.loads(_extract_json_blob(text))
                questions = payload.get("questions", [])
                if not isinstance(questions, list) or not questions:
                    return False

                difficulties: list[int] = []
                theoretical = 0
                practical = 0

                for q in questions:
                    if not isinstance(q, dict):
                        return False
                    d = q.get("difficulty")
                    if not isinstance(d, int):
                        return False
                    if d < 1 or d > 10:
                        return False
                    difficulties.append(d)

                    orientation = str(q.get("orientation", "")).strip().lower()
                    q_type = str(q.get("type", "")).strip().lower()
                    options = q.get("options", [])
                    prompt_text = str(q.get("prompt", "")).strip()
                    scenario = str(q.get("scenario", "")).strip()
                    task = str(q.get("task", "")).strip()
                    concept_tested = str(q.get("concept_tested", "")).strip()
                    skills_required = str(q.get("skills_required", "")).strip()
                    expected_solution_approach = str(q.get("expected_solution_approach", "")).strip()
                    correct_option = str(q.get("correct_option", "")).strip()
                    feedback_correct = str(q.get("feedback_correct", "")).strip()
                    feedback_incorrect = str(q.get("feedback_incorrect", "")).strip()
                    if q_type != "mcq":
                        return False
                    if not isinstance(options, list) or len(options) != 4:
                        return False
                    if not prompt_text:
                        return False
                    if not scenario or not task or not concept_tested or not skills_required or not expected_solution_approach:
                        return False
                    if not correct_option or correct_option not in options:
                        return False
                    if not feedback_correct or not feedback_incorrect:
                        return False
                    if orientation == "theoretical":
                        theoretical += 1
                    elif orientation == "practical":
                        practical += 1
                    else:
                        return False

                if difficulties != sorted(difficulties):
                    return False

                total = len(questions)
                if total % 2 == 0:
                    return theoretical == practical
                return abs(theoretical - practical) <= 1
            except Exception:
                return False

        def _exam_content_quality_ok(text: str, topic: str) -> bool:
            try:
                payload = _json.loads(_extract_json_blob(text))
                questions = payload.get("questions", [])
                if not isinstance(questions, list) or not questions:
                    return False

                generic_markers = [
                    "which statement best explains a core concept",
                    "complete the missing step in this",
                    "the key principle at this stage is",
                    "write or simplify the main equation used in",
                    "use definitions, formulas, and examples from your evidence context",
                    "a student is analyzing a scenario involving",
                    "in a real-world scenario involving",
                ]
                topic_lower = (topic or "").strip().lower()
                good_prompts = 0
                for q in questions:
                    prompt_text = str(q.get("prompt", "")).strip().lower()
                    hint_text = str(q.get("hint", "")).strip().lower()
                    if not prompt_text:
                        return False
                    if any(marker in prompt_text for marker in generic_markers):
                        return False
                    if any(marker in hint_text for marker in generic_markers):
                        return False
                    if "scenario" not in prompt_text and len(prompt_text.split()) < 8:
                        return False
                    if topic_lower and topic_lower in prompt_text:
                        good_prompts += 1
                    elif len(prompt_text.split()) >= 8:
                        good_prompts += 1
                return good_prompts >= max(2, len(questions) // 3)
            except Exception:
                return False

        def _exam_options_quality_ok(text: str) -> bool:
            try:
                payload = _json.loads(_extract_json_blob(text))
                questions = payload.get("questions", [])
                if not isinstance(questions, list) or not questions:
                    return False

                banned_markers = [
                    "distractor option",
                    "none of the above",
                    "all of the above",
                    "option a",
                    "option b",
                    "option c",
                    "option d",
                    "generic action",
                    "vague option",
                ]

                option_sets = set()
                for q in questions:
                    options = q.get("options", [])
                    if not isinstance(options, list) or len(options) != 4:
                        return False

                    normalized = []
                    for opt in options:
                        s = str(opt).strip()
                        if not s:
                            return False
                        low = s.lower()
                        if any(marker in low for marker in banned_markers):
                            return False
                        if len(s.split()) < 4:
                            return False
                        normalized.append(low)

                    if len(set(normalized)) != 4:
                        return False
                    option_signature = tuple(normalized)
                    if option_signature in option_sets:
                        return False
                    option_sets.add(option_signature)
                return True
            except Exception:
                return False

        def _normalize_quiz_json(text: str) -> str:
            """Fix common LLM mistakes before validation: letter-only MCQ answers, out-of-order levels."""
            try:
                import math as _math
                items = _json.loads(_extract_json_array_blob(text))
                if not isinstance(items, list):
                    return text
                n = len(items)
                # Re-assign levels 1..5 spaced across the list if they're invalid or non-ascending.
                level_vals = [item.get("level") for item in items if isinstance(item, dict)]
                needs_relevel = not (
                    all(isinstance(l, int) and 1 <= l <= 5 for l in level_vals)
                    and level_vals == sorted(level_vals)
                )
                if needs_relevel:
                    for i, item in enumerate(items):
                        if isinstance(item, dict):
                            item["level"] = min(5, max(1, _math.ceil((i + 1) * 5 / n)))
                # For code-type items: extract code from q field if code field is missing.
                import re as _re_norm
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    if str(item.get("type", "")).strip().lower() != "code":
                        continue
                    if str(item.get("code", "")).strip():
                        continue  # already has code field
                    q_text = str(item.get("q", ""))
                    # Look for fenced code blocks (```...```)
                    m = _re_norm.search(r'```[a-z]*\s*\n([\s\S]+?)\n```', q_text)
                    if m:
                        item["code"] = m.group(1).strip()
                        item["q"] = _re_norm.sub(r'```[a-z]*\s*\n[\s\S]+?\n```', '', q_text).strip()
                    else:
                        # Fallback: use a descriptive placeholder so the code field exists
                        item["code"] = f"// {q_text[:60].strip()}"

                # Normalize MCQ: trim to 4 options, fix letter-only answers.
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    if str(item.get("type", "")).strip().lower() != "mcq":
                        continue
                    options = item.get("options", [])
                    if isinstance(options, list) and len(options) > 4:
                        item["options"] = options[:4]
                        options = item["options"]
                    answer = item.get("answer", "")
                    if not isinstance(options, list) or len(options) < 2:
                        continue
                    if isinstance(answer, str) and answer not in options:
                        # Strip trailing punctuation and check if it's a bare letter
                        bare = answer.strip().rstrip(".").rstrip(")")
                        if bare.upper() in "ABCD" and len(bare) == 1:
                            idx = "ABCD".index(bare.upper())
                            if idx < len(options):
                                item["answer"] = options[idx]
                return _json.dumps(items, ensure_ascii=False)
            except Exception:
                return text

        def _quiz_layout_ok(text: str, expected_count: int) -> bool:
            """Lenient structure check — normalization has already fixed minor issues."""
            try:
                payload = _json.loads(_extract_json_array_blob(text))
                if not isinstance(payload, list) or not payload:
                    return False
                # Allow up to ±2 items from expected (LLM often generates ±1)
                if abs(len(payload) - expected_count) > 2:
                    return False
                valid_types = {"mcq", "fill", "code", "math"}
                seen_q: set[str] = set()
                for item in payload:
                    if not isinstance(item, dict):
                        return False
                    q_type = str(item.get("type", "")).strip().lower()
                    if q_type not in valid_types:
                        return False
                    q_text = str(item.get("q", "")).strip()
                    explain = str(item.get("explain", "")).strip()
                    if not q_text or not explain:
                        return False
                    if q_text.lower() in seen_q:
                        return False
                    seen_q.add(q_text.lower())
                    answer = item.get("answer")
                    if q_type == "mcq":
                        options = item.get("options", [])
                        # Allow 2–6 options; normalization trims or pads if needed
                        if not isinstance(options, list) or len(options) < 2:
                            return False
                        if not isinstance(answer, (str, list)):
                            return False
                    else:
                        # fill / code / math — answer may be None if LLM omitted it
                        if answer is not None and not isinstance(answer, (str, list)):
                            return False
                return True
            except Exception:
                return False

        def _quiz_content_quality_ok(text: str, topic: str) -> bool:
            try:
                payload = _json.loads(_extract_json_array_blob(text))
                if not isinstance(payload, list) or not payload:
                    return False
                generic_markers = [
                    "a student is analyzing",
                    "real-world scenario involving",
                    "core concept",
                    "key principle",
                    "template answer",
                ]
                topic_l = (topic or "").strip().lower()
                for item in payload:
                    q_text = str(item.get("q", "")).strip().lower()
                    explain = str(item.get("explain", "")).strip().lower()
                    if not q_text or len(q_text.split()) < 6:
                        return False
                    if any(m in q_text for m in generic_markers):
                        return False
                    if any(m in explain for m in generic_markers):
                        return False
                    if topic_l and topic_l not in q_text and topic_l not in explain:
                        # allow if specific concept is used, but avoid completely off-topic items
                        if len(q_text.split()) < 10:
                            return False
                return True
            except Exception:
                return False

        def _rebalance_correct_option_positions(text: str, topic: str) -> str:
            """Rotate correct-option index so answers are not always first."""
            try:
                payload = _json.loads(_extract_json_blob(text))
                questions = payload.get("questions", [])
                if not isinstance(questions, list) or not questions:
                    return text

                topic_bias = len((topic or "").strip()) % 4
                for idx, q in enumerate(questions):
                    if not isinstance(q, dict):
                        continue
                    options = q.get("options", [])
                    if not isinstance(options, list) or len(options) != 4:
                        continue

                    correct = str(q.get("correct_option", "")).strip()
                    if not correct or correct not in options:
                        correct = str(options[0]).strip()
                    if not correct:
                        continue

                    current_idx = options.index(correct)
                    target_idx = (idx + topic_bias) % 4
                    if current_idx != target_idx:
                        options[current_idx], options[target_idx] = options[target_idx], options[current_idx]
                    q["options"] = options
                    q["correct_option"] = options[target_idx]

                payload["questions"] = questions
                return _json.dumps(payload, ensure_ascii=False)
            except Exception:
                return text

        async def _build_exam_fallback_json(
            topic_query: str,
            total_questions: int,
            concepts: list[str] | None = None,
            domain_profile: dict[str, Any] | None = None,
            mapped_scenarios: list[dict[str, str]] | None = None,
        ) -> str:
            total_questions = max(1, min(20, int(total_questions or 5)))
            topic_clean = _extract_exam_topic(topic_query)
            concept_pool = [str(c).strip() for c in (concepts or []) if str(c).strip()] or [topic_clean]
            profile = domain_profile or {}
            terminology_pool = [str(t).strip() for t in profile.get("common_terminology", []) if str(t).strip()] or [f"{topic_clean} workflow"]
            applications_pool = [str(a).strip() for a in profile.get("real_world_applications", []) if str(a).strip()] or [f"{topic_clean} implementation"]
            subdomain_pool = [str(s).strip() for s in profile.get("subdomains", []) if str(s).strip()] or [f"{topic_clean} foundations"]
            mapped_pool = [m for m in (mapped_scenarios or []) if isinstance(m, dict)]

            difficulty_counts = {str(i): 0 for i in range(1, 11)}
            difficulties: list[int] = []
            for i in range(total_questions):
                d = 1 + ((i * 10) // total_questions)
                d = max(1, min(10, d))
                difficulties.append(d)
                difficulty_counts[str(d)] += 1

            diff_dist_json = _json.dumps(difficulty_counts)
            diff_str = _json.dumps(difficulties)
            fallback_prompt = (
                f"You are an expert assessment designer.\n"
                f"Generate exactly {total_questions} scenario-based MCQ questions on: {topic_clean}.\n\n"
                "Return ONLY a valid JSON object with this shape and no extra text:\n"
                "{\n"
                f"  \"exam_title\": \"{topic_clean.title()} Practice Exam\",\n"
                f"  \"question_count\": {total_questions},\n"
                f"  \"difficulty_distribution\": {diff_dist_json},\n"
                "  \"instructions\": \"Answer each scenario-based MCQ directly. Difficulty increases from 1 to 10. No answer key is shown.\",\n"
                "  \"questions\": [<question objects>]\n"
                "}\n\n"
                "Each question must include exactly these fields:\n"
                "number, difficulty, type, orientation, scenario, task, concept_tested, skills_required, "
                "expected_solution_approach, prompt, options, answer_format, hint, correct_option, "
                "feedback_correct, feedback_incorrect.\n\n"
                "Rules:\n"
                f"- Stay strictly on topic: {topic_clean}.\n"
                f"- Use exactly these difficulty values in ascending order: {diff_str}.\n"
                f"- Domain profile to respect: {_json.dumps(profile, ensure_ascii=False)}.\n"
                f"- Scenario mapping to reuse: {_json.dumps(mapped_pool[:total_questions], ensure_ascii=False)}.\n"
                "- type must be \"mcq\" and options must contain exactly 4 strings.\n"
                "- orientation: odd-numbered questions theoretical, even-numbered practical.\n"
                "- correct_option must match exactly one option string; do not keep the correct answer in the same option position for all questions.\n"
                "- No placeholders or generic templates.\n"
                "- Return only JSON.\n"
            )

            try:
                raw = await generate_response(fallback_prompt, [], max_tokens=max_response_tokens)
                if raw and raw != "AI_SERVICE_UNAVAILABLE":
                    parsed = _json.loads(_extract_json_blob(raw))
                    questions = parsed.get("questions")
                    if isinstance(questions, list) and questions:
                        for idx, q in enumerate(questions):
                            if not isinstance(q, dict):
                                continue
                            q.setdefault("number", idx + 1)
                            q.setdefault("difficulty", difficulties[idx] if idx < len(difficulties) else 5)
                            q.setdefault("type", "mcq")
                            q.setdefault("orientation", "theoretical" if idx % 2 == 0 else "practical")
                            q.setdefault("scenario", str(q.get("prompt", "")).strip() or f"Scenario about {topic_clean}")
                            q.setdefault("task", "Choose the best option that solves the scenario correctly.")
                            q.setdefault("concept_tested", topic_clean)
                            q.setdefault("skills_required", "Application and analysis")
                            q.setdefault("expected_solution_approach", f"Apply {topic_clean} concepts to the constraints and eliminate distractors.")
                            q.setdefault("answer_format", "string")
                            options = q.get("options")
                            if not isinstance(options, list):
                                options = []
                            q["options"] = options[:4]
                            while len(q["options"]) < 4:
                                concept_hint = concept_pool[idx % len(concept_pool)]
                                q["options"].append(
                                    f"Choose an approach that appears fast but ignores {concept_hint} constraints and validation needs"
                                )
                            correct_option = str(q.get("correct_option", "")).strip()
                            if not correct_option or correct_option not in q["options"]:
                                q["correct_option"] = q["options"][0]
                            q.setdefault("feedback_correct", "Correct. Your choice matches the scenario and concept.")
                            q.setdefault("feedback_incorrect", f"Revisit the scenario constraints and the {topic_clean} concept.")

                        parsed["exam_title"] = parsed.get("exam_title") or f"{topic_clean.title()} Practice Exam"
                        parsed["question_count"] = total_questions
                        parsed["difficulty_distribution"] = difficulty_counts
                        parsed["instructions"] = parsed.get("instructions") or "Answer each scenario-based MCQ directly. Difficulty increases from 1 to 10. No answer key is shown."
                        parsed["questions"] = questions[:total_questions]
                        return _rebalance_correct_option_positions(_json.dumps(parsed, ensure_ascii=False), topic_clean)
            except Exception:
                pass

            scenario_patterns = [
                "A cross-functional team must deliver a milestone where {topic} choices impact quality, cost, and timeline.",
                "A production issue requires a decision using {topic} while balancing speed, risk, and stakeholder expectations.",
                "A team is reviewing an implementation plan and must apply {topic} under real business constraints.",
                "A project lead must pick an approach grounded in {topic} to reduce rework and improve delivery outcomes.",
                "An organization is scaling delivery and needs to apply {topic} consistently across multiple teams.",
            ]
            task_patterns = [
                "Select the option that best aligns with the scenario constraints.",
                "Choose the most defensible decision given trade-offs and risks.",
                "Identify the action that most correctly applies the core concept.",
                "Pick the option that maximizes value while minimizing delivery risk.",
                "Choose the option that best fits both short-term and long-term outcomes.",
            ]
            prompt_patterns = [
                "Which option is the strongest application of {topic} in this case?",
                "Given this context, which decision best reflects correct {topic} reasoning?",
                "What is the most appropriate next step using {topic} principles?",
                "Which option best resolves the scenario using {topic} with minimal downside?",
                "Which choice most effectively satisfies the scenario constraints through {topic}?",
            ]
            hint_patterns = [
                "Check which option directly addresses constraints and measurable outcomes.",
                "Eliminate choices that ignore risk or stakeholder impact.",
                "Prioritize the option with the clearest alignment to the scenario goal.",
                "Compare options by feasibility, not by vague wording.",
                "Focus on trade-offs: speed, quality, and sustainability.",
            ]

            questions: list[dict[str, Any]] = []
            for idx in range(total_questions):
                difficulty = difficulties[idx]
                orientation = "theoretical" if idx % 2 == 0 else "practical"
                concept_focus = concept_pool[idx % len(concept_pool)]
                term_focus = terminology_pool[idx % len(terminology_pool)]
                application_focus = applications_pool[idx % len(applications_pool)]
                subdomain_focus = subdomain_pool[idx % len(subdomain_pool)]

                if idx < len(mapped_pool):
                    mapped = mapped_pool[idx]
                    scenario = str(mapped.get("scenario", "")).strip() or scenario_patterns[idx % len(scenario_patterns)].format(topic=topic_clean)
                    task = str(mapped.get("task", "")).strip() or task_patterns[(idx + 1) % len(task_patterns)]
                else:
                    scenario = scenario_patterns[idx % len(scenario_patterns)].format(topic=topic_clean)
                    task = task_patterns[(idx + 1) % len(task_patterns)]

                prompt = (
                    f"In this {subdomain_focus} scenario, which decision best applies {concept_focus} "
                    f"using {term_focus} for {application_focus}?"
                )
                correct_templates = [
                    "Define acceptance criteria and quality gates using {concept} and {term}, then schedule phased delivery aligned to {application}",
                    "Run a risk-first plan that applies {concept} through {term} checkpoints, owners, and rollback triggers for {application}",
                    "Sequence dependencies with {concept}, validate assumptions via {term}, and commit only the highest-value slice for {application}",
                    "Use {concept} to set measurable thresholds, execute controlled iterations with {term}, and review outcomes against {application} goals",
                    "Prioritize the bottleneck using {concept}, enforce {term} review cadence, and optimize trade-offs required by {application}",
                ]
                distractor_a_templates = [
                    "Choose a fast path that skips {concept} validation and removes {term} checkpoints to hit a short-term date",
                    "Prefer a shortcut that bypasses {concept} controls and omits ownership for {application}",
                    "Use an ad-hoc workaround without {concept} criteria, leaving {term} undefined for execution",
                    "Push implementation forward while ignoring {concept} risk signals from {term} reviews",
                    "Select an immediate fix that avoids {concept} governance despite known {application} dependencies",
                ]
                distractor_b_templates = [
                    "Recommend a broad best-practice summary that mentions {concept} but never maps it to this scenario's constraints",
                    "Choose a high-level framework statement that references {term} without concrete actions for {application}",
                    "Adopt a generic strategy using {concept} wording but no measurable checkpoints or accountability",
                    "Select an abstract policy that sounds correct yet does not address the current bottleneck in {application}",
                    "Use a template recommendation that cites {term} and {concept} but omits execution detail",
                ]
                distractor_c_templates = [
                    "Optimize a single metric now even if it increases downstream delivery risk, rework, and coordination cost",
                    "Maximize short-term throughput while accepting hidden quality debt and stakeholder misalignment",
                    "Reduce immediate cycle time by shifting risk to later phases where rollback is expensive",
                    "Improve one KPI locally while degrading reliability and predictability across the full workflow",
                    "Prioritize visible progress over resilience, creating cascading dependencies and recovery overhead",
                ]

                correct = correct_templates[idx % len(correct_templates)].format(
                    concept=concept_focus,
                    term=term_focus,
                    application=application_focus,
                )
                distractor_a = distractor_a_templates[(idx + 1) % len(distractor_a_templates)].format(
                    concept=concept_focus,
                    term=term_focus,
                    application=application_focus,
                )
                distractor_b = distractor_b_templates[(idx + 2) % len(distractor_b_templates)].format(
                    concept=concept_focus,
                    term=term_focus,
                    application=application_focus,
                )
                distractor_c = distractor_c_templates[(idx + 3) % len(distractor_c_templates)]
                questions.append({
                    "number": idx + 1,
                    "difficulty": difficulty,
                    "type": "mcq",
                    "orientation": orientation,
                    "scenario": scenario,
                    "task": task,
                    "concept_tested": concept_focus,
                    "skills_required": "Analysis" if difficulty >= 6 else "Application",
                    "expected_solution_approach": f"Identify constraints, apply {concept_focus} principles, compare trade-offs, and choose the most robust option.",
                    "prompt": prompt,
                    "options": [
                        correct,
                        distractor_a,
                        distractor_b,
                        distractor_c,
                    ],
                    "answer_format": "string",
                    "hint": hint_patterns[(idx + 3) % len(hint_patterns)],
                    "correct_option": correct,
                    "feedback_correct": "Correct. This option is the most complete and constraint-aware choice.",
                    "feedback_incorrect": f"Not quite. Re-evaluate constraints and which option applies {concept_focus} with explicit trade-offs.",
                })

            payload = {
                "exam_title": f"{topic_clean.title()} Practice Exam",
                "question_count": total_questions,
                "difficulty_distribution": difficulty_counts,
                "instructions": "Answer each scenario-based MCQ directly. Difficulty increases from 1 to 10. No answer key is shown.",
                "questions": questions,
            }
            return _rebalance_correct_option_positions(_json.dumps(payload, ensure_ascii=False), topic_clean)

        def _level_sequence(n: int) -> list[int]:
            seq: list[int] = []
            for i in range(n):
                seq.append(max(1, min(5, 1 + ((i * 5) // n))))
            return seq

        async def _build_quiz_fallback_json(
            topic_query: str,
            total_questions: int,
            concepts: list[str] | None = None,
            domain_profile: dict[str, Any] | None = None,
            mapped_scenarios: list[dict[str, str]] | None = None,
        ) -> str:
            total_questions = max(1, min(20, int(total_questions or 5)))
            topic_clean = _extract_exam_topic(topic_query)
            concept_pool = [str(c).strip() for c in (concepts or []) if str(c).strip()] or [topic_clean]
            profile = domain_profile or {}
            terminology_pool = [str(t).strip() for t in profile.get("common_terminology", []) if str(t).strip()] or [f"{topic_clean} workflow"]
            mapped_pool = [m for m in (mapped_scenarios or []) if isinstance(m, dict)]
            levels = _level_sequence(total_questions)
            type_cycle = ["mcq", "fill", "code", "math"]

            quiz: list[dict[str, Any]] = []
            for idx in range(total_questions):
                level = levels[idx]
                q_type = type_cycle[idx % len(type_cycle)]
                concept = concept_pool[idx % len(concept_pool)]
                term = terminology_pool[idx % len(terminology_pool)]
                mapped = mapped_pool[idx] if idx < len(mapped_pool) else {}
                scenario = str(mapped.get("scenario", "")).strip() or f"A team applies {topic_clean} in a practical setting."

                if q_type == "mcq":
                    correct = f"The option that correctly applies {concept} using {term} within the stated constraints"
                    item = {
                        "level": level,
                        "type": "mcq",
                        "q": f"In {topic_clean}, which choice best reflects correct use of {concept} in this context: {scenario}",
                        "options": [
                            correct,
                            f"A shortcut that skips {concept} validation",
                            f"A generic recommendation unrelated to {term}",
                            "A choice that optimizes one metric while increasing systemic risk",
                        ],
                        "answer": correct,
                        "explain": f"This matches the source-backed constraints for {concept} and aligns with the retrieved context on {topic_clean}.",
                    }
                elif q_type == "fill":
                    answer = [concept.lower(), concept]
                    item = {
                        "level": level,
                        "type": "fill",
                        "q": f"Fill in the blank: In this {topic_clean} context, the primary concept being applied is ___.",
                        "answer": answer,
                        "explain": f"The scenario and retrieved facts specifically point to {concept} as the governing concept.",
                    }
                elif q_type == "code":
                    code = (
                        "function apply_process(constraints):\n"
                        "  step1 = analyze(constraints)\n"
                        f"  step2 = map_to_concept(step1, \"{concept}\")\n"
                        "  if not validate(step2):\n"
                        "    _________\n"
                        "  return execute(step2)"
                    )
                    item = {
                        "level": level,
                        "type": "code",
                        "q": f"Complete the missing pseudocode step for a {topic_clean} process.",
                        "code": code,
                        "answer": ["return revise(step2)", "revise(step2)"],
                        "explain": f"Retrieved process guidance requires a correction/revision step when validation fails for {concept}.",
                    }
                else:
                    item = {
                        "level": level,
                        "type": "math",
                        "q": f"A {topic_clean} plan has 12 tasks and 3 critical constraints from {concept}. If each constraint affects 2 tasks, how many constrained task-impact pairs are there?",
                        "answer": ["6"],
                        "explain": f"This is a direct context-grounded counting step tied to the {concept} constraint model (3 × 2 = 6).",
                    }

                quiz.append(item)

            return _json.dumps(quiz, ensure_ascii=False)

        if mode == "quiz-generator":
            topic_understanding = _topic_understanding_layer(effective_query)
            requested_count = int(topic_understanding["question_count"])
            requested_topic = str(topic_understanding["topic"])
            quiz_context, quiz_source_type, quiz_source_reference = await _gather_parallel_evidence(
                effective_query,
                source_passage if doc_ids else "",  # only cite a doc when one is actually selected
                doc_ids,
                force_external=True,
                prefer_external_sources=True,
            )
            domain_profile = await _domain_understanding_layer(requested_topic, quiz_context)
            profile_concepts = [str(c).strip() for c in domain_profile.get("core_concepts", []) if str(c).strip()]
            extracted_concepts = profile_concepts or await _concept_extraction_layer(requested_topic, quiz_context)
            mapped_scenarios = await _scenario_mapping_layer(requested_topic, extracted_concepts, quiz_context, requested_count)

            # Scale token budget: ~220 tokens per question, floored at 900, capped at 2000
            quiz_max_tokens = min(2000, max(900, requested_count * 220))

            base_quiz_prompt = build_prompt(effective_query, mode, role, quiz_context, context)
            quiz_prompt = (
                f"{base_quiz_prompt}\n\n"
                f"Generate exactly {requested_count} quiz questions.\n"
                "- Each question must test a DIFFERENT fact, definition, formula, or process from the context above.\n"
                "- Difficulty levels must ascend from 1 to 5.\n"
                "- Mix types: mcq, fill, code, math — choose the type that best fits each fact.\n"
                f"- Key concepts to cover: {_json.dumps(extracted_concepts[:8], ensure_ascii=False)}\n"
                "Return ONLY a strict JSON array. No markdown fences, no commentary.\n"
            )

            # Quiz generation is stateless — pass empty history so prior chat context
            # does not confuse the LLM and cause malformed JSON / fallback triggering.
            # Use generate_with_logprobs so Pipeline 3 (confidence) gets token logprob data.
            quiz_gen = await generate_with_logprobs(quiz_prompt, [], max_tokens=quiz_max_tokens)
            quiz_text = quiz_gen["text"]
            quiz_logprobs = quiz_gen["token_logprobs"]
            quiz_seqlen = quiz_gen["seq_len"]

            if quiz_text == "AI_SERVICE_UNAVAILABLE":
                return _attach_source_metadata({
                    "text": quiz_text,
                    "scores": {"entailment": False, "consistency": False, "confidence": 0.0, "fallback_type": "refusal"},
                    "role": role,
                    "mode": mode,
                }, quiz_source_type, mode, quiz_source_reference)

            # Normalize before validation: fix letter-only MCQ answers and out-of-order levels.
            quiz_text = _normalize_quiz_json(quiz_text)

            if not _quiz_layout_ok(quiz_text, requested_count) or not _quiz_content_quality_ok(quiz_text, requested_topic):
                repair_prompt = (
                    f"{quiz_prompt}\n\n"
                    "STRICT CORRECTION REQUIRED:\n"
                    f"- Output exactly {requested_count} items in a JSON array.\n"
                    "- Types must only be mcq|fill|code|math.\n"
                    "- Levels must be ascending and between 1 and 5.\n"
                    "- Each item must reference a different source-backed concept/fact.\n"
                    "- No generic placeholders or template phrases.\n"
                    "- Return ONLY JSON array.\n"
                )
                repair_gen = await generate_with_logprobs(repair_prompt, [], max_tokens=quiz_max_tokens)
                repaired_quiz_text = repair_gen["text"]
                if repaired_quiz_text != "AI_SERVICE_UNAVAILABLE":
                    repaired_quiz_text = _normalize_quiz_json(repaired_quiz_text)
                    if _quiz_layout_ok(repaired_quiz_text, requested_count) and _quiz_content_quality_ok(repaired_quiz_text, requested_topic):
                        quiz_text = repaired_quiz_text
                        quiz_logprobs = repair_gen["token_logprobs"]
                        quiz_seqlen = repair_gen["seq_len"]

            if not _quiz_layout_ok(quiz_text, requested_count) or not _quiz_content_quality_ok(quiz_text, requested_topic):
                quiz_text = await _build_quiz_fallback_json(
                    requested_topic,
                    requested_count,
                    extracted_concepts,
                    domain_profile,
                    mapped_scenarios,
                )

            # ── 3-PIPELINE VERIFICATION ───────────────────────────────────────────
            # Extract explain fields as natural-language claims for P1 + P2.
            try:
                _qitems = _json.loads(_extract_json_array_blob(quiz_text))
                quiz_claims = " ".join(
                    str(qi.get("explain", "")).strip()
                    for qi in _qitems
                    if isinstance(qi, dict) and qi.get("explain")
                )
            except Exception:
                quiz_claims = quiz_text[:800]

            import asyncio as _qasyncio
            import re as _re_p1

            # Clip claims for consistency check budget.
            _quiz_claims_clipped = quiz_claims[:400]

            # Pipeline 3 (Confidence) always runs.
            async def _quiz_p3():
                return await _qasyncio.to_thread(score_confidence, quiz_logprobs, quiz_seqlen)

            # Pipeline 1 (Entailment): MiniCheck is only meaningful when the quiz was
            # generated from an uploaded document. For online sources (web/academic),
            # MiniCheck scores paraphrased quiz explanations against short web snippets
            # at near-zero, making the check useless. Trust P2+P3 for online quizzes.
            if quiz_source_type == "document":
                import re as _re_p1
                _quiz_ctx_clean = _re_p1.sub(r'^\[[^\]]+\]\n', '', quiz_context, flags=_re_p1.MULTILINE).strip()
                _quiz_ctx_clipped = _quiz_ctx_clean[:1200]

                async def _quiz_p1():
                    return await _qasyncio.to_thread(check_grounding, _quiz_ctx_clipped, _quiz_claims_clipped)

                grounding_score, lr_p_hall = await _qasyncio.gather(_quiz_p1(), _quiz_p3())
                quiz_entailment = grounding_score >= 0.25
            else:
                # Online source: skip MiniCheck, grant entailment.
                lr_p_hall = await _quiz_p3()
                grounding_score = 1.0
                quiz_entailment = True

            print(f"[QUIZ-PIPELINE] source={quiz_source_type} grounding={grounding_score:.3f} lr_p_hall={lr_p_hall:.3f}")
            lr_signal = float(_np.clip(1.0 - lr_p_hall, 0.1, 0.9))

            # Pipeline 2 (Consistency): generate one quiz variant, compare explain fields.
            quiz_variants = await generate_k_variants(
                quiz_prompt, k=1, chat_history=[],
                max_tokens=min(900, quiz_max_tokens),
            )
            variant_claims = ""
            for _vt in quiz_variants:
                try:
                    _vitems = _json.loads(_extract_json_array_blob(_vt))
                    variant_claims = " ".join(
                        str(_vi.get("explain", "")).strip()
                        for _vi in _vitems
                        if isinstance(_vi, dict) and _vi.get("explain")
                    )
                    if variant_claims:
                        break
                except Exception:
                    variant_claims = _vt[:400]

            consistency_score = await _qasyncio.to_thread(
                check_consistency,
                _quiz_claims_clipped,
                [variant_claims[:400]] if variant_claims else [_quiz_claims_clipped],
            )
            print(f"[QUIZ-PIPELINE] consistency={consistency_score:.3f}")
            quiz_consistency = consistency_score >= 0.3

            # Weighted confidence (same formula as other entailment-enabled modes).
            quiz_confidence = float(
                0.40 * grounding_score + 0.35 * consistency_score + 0.25 * lr_signal
            )
            # ─────────────────────────────────────────────────────────────────────

            return _attach_source_metadata({
                "text": quiz_text,
                "scores": {
                    "entailment": quiz_entailment,
                    "consistency": quiz_consistency,
                    "confidence": quiz_confidence,
                    "fallback_type": "exam",
                },
                "role": role,
                "mode": mode,
            }, quiz_source_type, mode, quiz_source_reference)

        topic_understanding = _topic_understanding_layer(effective_query)
        requested_count = int(topic_understanding["question_count"])
        requested_topic = str(topic_understanding["topic"])
        exam_context, exam_source_type, exam_source_reference = await _gather_parallel_evidence(
            effective_query,
            source_passage,
            doc_ids,
            force_external=True,
            prefer_external_sources=True,
        )
        domain_profile = await _domain_understanding_layer(requested_topic, exam_context)
        profile_concepts = [str(c).strip() for c in domain_profile.get("core_concepts", []) if str(c).strip()]
        extracted_concepts = profile_concepts or await _concept_extraction_layer(requested_topic, exam_context)
        mapped_scenarios = await _scenario_mapping_layer(requested_topic, extracted_concepts, exam_context, requested_count)

        base_exam_prompt = build_prompt(effective_query, mode, role, exam_context, context)
        exam_prompt = (
            f"{base_exam_prompt}\n\n"
            "ASSESSMENT DESIGN FLOW (must follow):\n"
            "User Topic -> Topic Understanding Layer -> Concept Extraction -> Knowledge Retrieval (optional) -> "
            "Scenario Mapping -> Question Generation -> Quality Evaluation -> Final Output\n\n"
            f"Topic Understanding Layer output:\n{_json.dumps(topic_understanding, ensure_ascii=False)}\n\n"
            f"Domain Understanding output:\n{_json.dumps(domain_profile, ensure_ascii=False)}\n\n"
            f"Concept Extraction output:\n{_json.dumps(extracted_concepts, ensure_ascii=False)}\n\n"
            f"Scenario Mapping output:\n{_json.dumps(mapped_scenarios, ensure_ascii=False)}\n\n"
            "Question Generation requirements:\n"
            "- Use scenario/task pairs directly; do not replace with generic placeholders.\n"
            "- Keep the requested topic explicit in each question.\n"
            "- Respect the 'avoid' list from domain understanding and do not drift to unrelated meanings.\n"
            "- Return only JSON with exam schema.\n"
        )
        exam_text = await generate_response(exam_prompt, chat_history, max_tokens=max_response_tokens)
        exam_text = _rebalance_correct_option_positions(exam_text, requested_topic)
        if exam_text == "AI_SERVICE_UNAVAILABLE":
            return _attach_source_metadata({
                "text": exam_text,
                "scores": {"entailment": False, "consistency": False, "confidence": 0.0, "fallback_type": "refusal"},
                "role": role,
                "mode": mode,
            }, exam_source_type, mode, exam_source_reference)

        if not _exam_layout_ok(exam_text) or not _exam_content_quality_ok(exam_text, requested_topic) or not _exam_options_quality_ok(exam_text):
            half_count = requested_count // 2
            repair_prompt = (
                f"{exam_prompt}\n\n"
                "STRICT CORRECTION REQUIRED:\n"
                f"- Output exactly {requested_count} questions.\n"
                "- Questions must be in ascending difficulty order (1->10).\n"
                f"- If count is even, output exactly {half_count} theoretical and {half_count} practical questions.\n"
                "- If count is odd, keep theoretical/practical split as balanced as possible (difference <= 1).\n"
                f"- The actual topic is: {requested_topic}. Use that exact topic, not the full user sentence.\n"
                "- Include \"orientation\" for every question: \"theoretical\" or \"practical\".\n"
                "- Stay strictly on the requested topic.\n"
                "- Every question must be an MCQ with exactly 4 options.\n"
                "- Every question must be scenario-based.\n"
                "- Each question must include: correct_option, feedback_correct, feedback_incorrect.\n"
                "- correct_option must match exactly one option string.\n"
                "- Do not keep the correct answer in option 1 across all questions; vary the correct-option position.\n"
                "- Options quality: each question must have 4 distinct, plausible options that are specific to that scenario.\n"
                "- Avoid placeholders like 'option A/B/C/D', 'distractor option', 'all of the above', and 'none of the above'.\n"
                "- Reuse the provided Scenario Mapping output; do not invent generic templates.\n"
                "- Do not use generic placeholders like 'core concept', 'key principle', or 'main equation used in the topic'.\n"
                "- Return ONLY valid JSON, no commentary.\n"
            )
            repaired_exam_text = await generate_response(repair_prompt, chat_history, max_tokens=max_response_tokens)
            repaired_exam_text = _rebalance_correct_option_positions(repaired_exam_text, requested_topic)
            if repaired_exam_text != "AI_SERVICE_UNAVAILABLE" and _exam_layout_ok(repaired_exam_text) and _exam_content_quality_ok(repaired_exam_text, requested_topic) and _exam_options_quality_ok(repaired_exam_text):
                exam_text = repaired_exam_text

        if not _exam_layout_ok(exam_text) or not _exam_content_quality_ok(exam_text, requested_topic) or not _exam_options_quality_ok(exam_text):
            exam_text = await _build_exam_fallback_json(
                requested_topic,
                requested_count,
                extracted_concepts,
                domain_profile,
                mapped_scenarios,
            )

        exam_text = _rebalance_correct_option_positions(exam_text, requested_topic)

        return _attach_source_metadata({
            "text": exam_text,
            "scores": {"entailment": True, "consistency": True, "confidence": 0.9, "fallback_type": "exam"},
            "role": role,
            "mode": mode,
        }, exam_source_type, mode, exam_source_reference)

    best_failed_candidate = None
    best_failed_score = -1.0
    
    # Helper to track the best failed candidate
    def _track_failed(cand):
        nonlocal best_failed_candidate, best_failed_score
        if cand and cand["text"] != "AI_SERVICE_UNAVAILABLE":
            conf = cand["scores"]["confidence"]
            if conf > best_failed_score:
                best_failed_score = conf
                best_failed_candidate = cand

    # Low-latency fast path: verify local evidence first if available.
    if source_passage and source_passage != "No grounding passage found.":
        local_candidate = await _run_verification_loop(
            prompt,
            source_passage,
            skip_entailment,
            v_fallback_type="document",
        )
        if local_candidate and local_candidate["text"] != "AI_SERVICE_UNAVAILABLE":
            s = local_candidate["scores"]
            passed_all = (s["entailment"] is not False) and (s["consistency"] is not False)
            if passed_all:
                response_with_citation = ensure_citation_in_response(
                    local_candidate["text"],
                    source_type="document",
                    source_reference=document_reference,
                )
                return _attach_source_metadata({
                    "text": response_with_citation,
                    "scores": local_candidate["scores"],
                    "role": role,
                    "mode": mode,
                }, "document", mode, document_reference)
            _track_failed(local_candidate)
            # Document failed entailment — topic is outside the document's scope.
            # Clear the passage so it is not bundled with online sources and falsely cited.
            source_passage = "No grounding passage found."

    # Parallel evidence: local + online summary merge.
    # Only pass source_passage if still valid (not cleared by a failed local check above).
    parallel_bundle, parallel_source_type, parallel_source_reference = await _gather_parallel_evidence(
        effective_query,
        source_passage,
        doc_ids,
    )

    if parallel_bundle:
        parallel_prompt = build_prompt(effective_query, mode, role, parallel_bundle, context)
        parallel_candidate = await _run_verification_loop(
            parallel_prompt,
            parallel_bundle,
            skip_entailment,
            v_fallback_type="parallel",
        )

        if parallel_candidate and parallel_candidate["text"] != "AI_SERVICE_UNAVAILABLE":
            s = parallel_candidate["scores"]
            passed_all = (s["entailment"] is not False) and (s["consistency"] is not False)
            if passed_all:
                response_with_citation = ensure_citation_in_response(
                    parallel_candidate["text"],
                    source_type=parallel_source_type,
                    source_reference=parallel_source_reference,
                )
                return _attach_source_metadata({
                    "text": response_with_citation,
                    "scores": parallel_candidate["scores"],
                    "role": role,
                    "mode": mode,
                }, parallel_source_type, mode, parallel_source_reference)

        # Use the merged evidence bundle for any fallback verification/orchestration.
        source_passage = parallel_bundle
        if parallel_source_type:
            source_type = parallel_source_type

    prompt = build_prompt(effective_query, mode, role, source_passage, context)

    # In low-latency mode, skip the slower orchestrator step after local+parallel verification.
    if settings.low_latency_mode:
        refusal_prompt = (
            f"The student asked: '{effective_query}'. \n"
            "You checked local materials and online evidence, but found no fully verifiable answer. "
            "Politely ask for clarification or a narrower question in under 2 sentences."
        )
        refusal_variants = await generate_k_variants(
            refusal_prompt,
            k=1,
            max_tokens=120,
        )
        refusal_text = refusal_variants[0] if refusal_variants else "No fully verifiable source found. Please rephrase or add context."
        refusal_text = ensure_citation_in_response(
            refusal_text,
            source_type=source_type,
            source_reference=document_reference if source_type == "document" else "Local + online verification",
        )
        return _attach_source_metadata({
            "text": refusal_text,
            "scores": {"entailment": False, "consistency": False, "confidence": 0.0, "fallback_type": "refusal"},
            "role": role,
            "mode": mode,
        }, source_type, mode, document_reference if source_type == "document" else "Local + online verification")

    # --- MCP Orchestrator Loop ---
    import os
    import json
    from google import genai
    from app.factshield.tools import search_document, search_arxiv, search_copilot, search_web

    failed_tools = []
    # Submission validator audits against course material only — online tools are excluded
    # so the source citation always reflects the uploaded document, never web/academic fallbacks.
    if mode == "submission-validator":
        available_tools = {"search_document": search_document}
    else:
        available_tools = {
            "search_document": search_document,
            "search_arxiv": search_arxiv,
            "search_copilot": search_copilot,
            "search_web": search_web,
        }

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    while len(failed_tools) < len(available_tools):
        # 1. Ask Orchestrator for the next tool
        orchestrator_prompt = (
            f"The student asked: '{query}'.\n"
            f"You are the Multi-Agent Orchestrator. You have these tools available to search for context: {list(available_tools.keys())}.\n"
            f"These tools have already failed: {failed_tools}.\n"
            "Which tool should we call next? Always try 'search_document' first, then 'search_arxiv', then 'search_copilot', then 'search_web'.\n"
            "Return ONLY a valid JSON object like: {\"tool\": \"tool_name\"} or {\"tool\": \"none\"} if all logical tools are exhausted."
        )
        
        try:
            resp = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=orchestrator_prompt
            )
            # Parse the JSON response
            raw_text = resp.text.strip().removeprefix("```json").removesuffix("```").strip()
            decision = json.loads(raw_text)
            tool_name = decision.get("tool", "none")
        except Exception as e:
            print(f"Orchestrator JSON Error: {e}")
            # Fallback sequence if Orchestrator LLM is unavailable (e.g., rate limit)
            for fallback_tool in ["search_document", "search_arxiv", "search_copilot", "search_web"]:
                if fallback_tool not in failed_tools:
                    tool_name = fallback_tool
                    break
            else:
                tool_name = "none"

        if tool_name == "none" or tool_name not in available_tools:
            break

        if tool_name in failed_tools:
            # Prevent infinite loops if LLM is stubborn
            break

        # 2. Execute the Tool
        if tool_name == "search_document":
            snippet = source_passage
        else:
            tool_func = available_tools[tool_name]
            snippet = await tool_func(query)
        
        if snippet:
            # Setup specific prompt based on tool
            if tool_name == "search_document":
                current_prompt = prompt # Use the standard document prompt
                current_mode = mode
                is_general = skip_entailment
            elif tool_name == "search_arxiv":
                current_prompt = (
                    f"The user asked: '{query}'. \n"
                    f"Here are abstracts from academic research papers on ArXiv:\n{snippet}\n"
                    "Provide a highly accurate answer based on these academic papers. "
                    "FORMATTING: Provide a rich, step-by-step educational answer. If there are math formulas, you MUST format them using LaTeX.\n"
                    "CITATION: The very last line of your response MUST STRICTLY be a clickable markdown link: `Reference: [Paper Title](URL)`."
                )
                current_mode = "academic"
                is_general = False
            elif tool_name == "search_copilot":
                current_prompt = (
                    f"The user asked: '{query}'. \n"
                    f"Here is a technical snippet from the Copilot AI Knowledge Base:\n{snippet}\n"
                    "Provide a helpful technical answer based on this snippet. "
                    "FORMATTING: Provide a rich, step-by-step educational answer. If there are math formulas, you MUST format them using LaTeX.\n"
                    "CITATION: The very last line of your response MUST STRICTLY be: `Reference: AI Knowledge Base`."
                )
                current_mode = "copilot"
                is_general = False
            elif tool_name == "search_web":
                current_prompt = (
                    f"The user asked: '{query}'. \n"
                    f"Here are search results from the web:\n{snippet}\n"
                    "Provide a helpful answer based on these web search results. "
                    "FORMATTING: Provide a rich, step-by-step educational answer. If there are math formulas, you MUST format them using LaTeX.\n"
                    "CITATION: The very last line of your response MUST STRICTLY be a clickable markdown link: `Reference: [Site Name](URL)`."
                )
                current_mode = "web"
                is_general = False

            # 3. CRITICAL: Pass the snippet to the Core FactShield 3-Layer Pipeline
            cand = await _run_verification_loop(current_prompt, snippet, is_general, current_mode)
            
            if cand:
                s = cand["scores"]
                # Document RAG allows entailment fallback to None, but external tools require strict entailment
                passed_all = (s["entailment"] is not False) and (s["consistency"] is not False)
                if passed_all:
                    # Success! FactShield has verified the Orchestrator's tool output.
                    if tool_name == "search_document":
                        from app.db.session import async_session_maker
                        from app.models.generation import Generation
                        from app.retrieval.cache import save_to_semantic_cache
                        async with async_session_maker() as session:
                            db_gen = Generation(
                                prompt=current_prompt,
                                response_text=cand["text"],
                                token_logprobs=cand.get("token_logprobs", b""),
                                seq_len=cand.get("seq_len", 10),
                                grounding_score=cand.get("raw_scores", {}).get("grounding", 0.0),
                                consistency_score=cand.get("raw_scores", {}).get("consistency", 0.0),
                                confidence_score=cand["scores"]["confidence"],
                                combined_score=cand["scores"]["confidence"],
                            )
                            session.add(db_gen)
                            await session.commit()
                            await save_to_semantic_cache(
                                query,
                                doc_ids,
                                mode,
                                db_gen.id,
                                source_type=source_type,
                            )
                    # CITATION: Ensure response includes source attribution
                    response_with_citation = ensure_citation_in_response(cand["text"], source_type=source_type)
                    return _attach_source_metadata(
                        {"text": response_with_citation, "scores": cand["scores"], "role": role, "mode": current_mode},
                        current_mode if current_mode in ["academic", "copilot", "web"] else source_type,
                        current_mode,
                        parallel_source_reference if "parallel_source_reference" in locals() else document_reference,
                    )
                else:
                    _track_failed(cand)
        
        # 4. Validation Failed or Snippet Empty -> Inform Orchestrator to try another tool
        failed_tools.append(tool_name)

    # --- Fallback: Dynamic Synthesizer Refusal ---
    # All orchestrator tools exhausted — generate a graceful refusal.
    refusal_prompt = (
        f"The student asked: '{effective_query}'. \n"
        "You searched their syllabus, ArXiv academic papers, and the live internet, but found no verifiable information. "
        "Politely explain to the student that there are no available verifiable sources in these areas to answer their question, "
        "and ask if they can provide more context or rephrase. Keep it under 3 sentences. "
        "Do NOT attempt to answer the question."
    )
    refusal_variants = await generate_k_variants(
        refusal_prompt,
        k=1,
        max_tokens=120,
    )
    refusal_text = refusal_variants[0] if refusal_variants else "No verifiable source found for this query. Please rephrase or provide more context."

    return _attach_source_metadata({
        "text": refusal_text,
        "scores": {"entailment": False, "consistency": False, "confidence": 0.0, "fallback_type": "refusal"},
        "role": role,
        "mode": mode,
    }, source_type, mode, document_reference if source_type == "document" else None)
