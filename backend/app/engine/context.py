"""Unified context builder: local document → ArXiv → Web.

Returns (passage, source_type, source_reference) for every request.
source_type: "document" | "academic" | "web" | "none"

Priority rule:
  - If the user has uploaded documents, ALWAYS answer from them.
    Only fall to external sources if the document has zero relevant content.
  - External sources (ArXiv, Web) are used only when no document is uploaded.
"""
from __future__ import annotations

import asyncio
import re
import uuid

from app.retrieval.retriever import retrieve_with_scores
from app.factshield.academic import search_arxiv
from app.factshield.search import search_web

# Use document if similarity >= this (permissive — prefer doc over web)
_DOC_THRESHOLD = 0.35
# Minimum bar to use document at all (below this = doc has nothing on this topic)
# 0.20 filters out noise matches (e.g. psych doc vs "quantum entanglement")
_DOC_MINIMUM = 0.20
_SUB_THRESHOLD = 0.30
_EXT_TIMEOUT = 6.0


async def build_context(
    query: str,
    doc_ids: list[uuid.UUID],
    doc_filenames: dict[uuid.UUID, str] | None = None,
    threshold: float = _DOC_THRESHOLD,
) -> tuple[str, str, str | None]:
    """Main context builder. Returns (passage, source_type, source_reference).

    If documents are uploaded, always prefer them.
    Only fall to ArXiv/Web when no documents are uploaded.
    """

    # 1. Local document — always try first, strongly preferred when uploaded
    if doc_ids:
        passages, score, used_ids = await retrieve_with_scores(query, doc_ids, k=8)

        if passages and score >= _DOC_MINIMUM:
            # Show only the document(s) that actually contributed chunks, not all uploads.
            ref = _doc_ref(used_ids or doc_ids, doc_filenames)
            return "\n".join(passages), "document", ref

        # Document uploaded but has truly nothing on this topic → fall through to external
        # This is the only case where we skip an uploaded document.

    # 2. ArXiv — only reached when no document is uploaded (or doc has zero content)
    try:
        text = await asyncio.wait_for(search_arxiv(query, max_results=2), _EXT_TIMEOUT)
        if text and len(text.strip()) > 60:
            return text, "academic", _first_url(text, "ArXiv")
    except Exception:
        pass

    # 3. Web — final fallback
    try:
        text = await asyncio.wait_for(search_web(query, max_results=2), _EXT_TIMEOUT)
        if text and len(text.strip()) > 60:
            return text, "web", _first_url(text, "Web")
    except Exception:
        pass

    return "", "none", None


async def build_submission_context(
    submission: str,
    doc_ids: list[uuid.UUID],
    doc_filenames: dict[uuid.UUID, str] | None = None,
    threshold: float = _SUB_THRESHOLD,
) -> tuple[str, str, str | None]:
    """Per-sentence retrieval for submission-validator — broader document coverage."""
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', submission) if len(s.strip()) > 10]
    seen: set[str] = set()
    passages: list[str] = []

    for sent in sentences[:8]:
        try:
            chunks, score, _used = await retrieve_with_scores(sent, doc_ids, k=2)
            if score >= threshold:
                for c in chunks:
                    if c not in seen:
                        seen.add(c)
                        passages.append(c)
        except Exception:
            pass

    if passages:
        ref = _doc_ref(doc_ids, doc_filenames)
        return "\n".join(passages), "document", ref

    return "", "none", None


def source_label(source_type: str) -> str:
    return {
        "document": "Your document",
        "academic": "ArXiv research",
        "web": "Web search",
        "none": "",
    }.get(source_type, source_type)


def _doc_ref(doc_ids: list[uuid.UUID], filenames: dict | None) -> str | None:
    if not filenames:
        return None
    names = list({filenames[d] for d in doc_ids if d in filenames})
    return ", ".join(sorted(names)) if names else None


def _first_url(text: str, label: str) -> str | None:
    m = re.search(r'https?://\S+', text)
    if m:
        url = m.group(0).rstrip(".,)]>")
        return f"[{label}]({url})"
    return None
