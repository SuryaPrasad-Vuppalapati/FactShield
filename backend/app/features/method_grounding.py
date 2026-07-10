"""Method-Grounding Helper feature implementation.

Retrieves relevant technique passages from the student's material and generates
a conceptually grounded explanation using the FactShield pipeline.
"""

from __future__ import annotations

from typing import Any
import uuid

from app.factshield.best_scored import best_scored_candidate
from app.retrieval.retriever import retrieve_with_scores


async def get_method_grounding(
    question: str, doc_ids: list[uuid.UUID]
) -> dict[str, Any]:
    """Retrieve passages and generate a FactShield-audited explanation.

    Args:
        question: The student's stuck question.
        doc_ids: List of document UUIDs to search within.

    Returns:
        A dict containing generated text and audit scores.
    """
    # 1. Retrieve relevant context chunks
    passages, highest_score, _used_ids = await retrieve_with_scores(query=question, doc_ids=doc_ids, k=5)
    
    # Cosine similarity relevance check
    if highest_score < 0.3:
        return {
            "text": "I couldn't find a clear answer to that in your document. Try rephrasing or check if this topic is covered in your notes.",
            "entailment": False,
            "consistency": False,
            "confidence": 0.0,
        }

    source_passage = "\n".join(passages) if passages else "No grounding passage found."

    # 2. Construct the prompt
    prompt = (
        f"Question: {question}\n\n"
        "Answer the question above using only the document context below. "
        "Be direct — start with the answer, then give enough explanation for the student to genuinely understand it. "
        "Reference where in the document this comes from (section or page if available). "
        "If the context doesn't actually address the question, say so clearly rather than guessing.\n\n"
        f"Document Context:\n{source_passage}"
    )

    # 3. Generate response and score it using the FactShield pipeline
    res = best_scored_candidate(
        prompt=prompt,
        source_passage=source_passage,
        n_candidates=1,
    )
    winner = res["winner"]

    return {
        "text": winner["text"],
        "entailment": winner["grounding"] >= 0.6,
        "consistency": winner["consistency"] >= 0.6,
        "confidence": winner["confidence"],
    }
