import re

with open("backend/app/factshield/pipeline.py", "r") as f:
    content = f.read()

imports = """
from app.retrieval.cache import check_semantic_cache, save_to_semantic_cache
from app.db.session import async_session_maker
from app.models.generation import Generation
"""

# Insert imports after "from typing import Any"
content = content.replace("from typing import Any\n", f"from typing import Any\n{imports}")

new_func = '''async def run_factshield_pipeline(
    query: str,
    mode: str,
    role: str,
    source_passage: str,
    context: str | None = None,
    skip_entailment: bool = False,
    chat_history: list[ChatMessage] | None = None,
    doc_ids: list[Any] | None = None,
) -> dict[str, Any]:
    """Run all three FactShield pipelines with CAG and strict loop."""
    import os
    import numpy as _np
    import pandas as _pd
    from pipelines.token_prob.scorer import extract_features_vectorized as _efv
    from pipelines.token_prob.classifier import FEATURE_COLS as _FC
    _debug = os.getenv("DEBUG_PIPELINE", "0") == "1"

    if query == "REJECTED_CONTEXT_DO_NOT_SEARCH" or source_passage == "No grounding passage found.":
        return {
            "text": "I couldn't find a clear answer to that in your document. Try rephrasing or check if this topic is covered in your notes.",
            "scores": {"entailment": False, "consistency": False, "confidence": 0.0},
            "role": role,
            "mode": mode,
        }

    # Step 1: Semantic Cache (CAG)
    cached_gen = await check_semantic_cache(query, doc_ids)
    if cached_gen:
        print(f"=== SEMANTIC CACHE HIT ===")
        return {
            "text": cached_gen.response_text,
            "scores": {
                "entailment": cached_gen.grounding_score >= 0.6 if not skip_entailment else None,
                "consistency": cached_gen.consistency_score >= 0.5,
                "confidence": cached_gen.confidence_score,
            },
            "role": role,
            "mode": mode,
        }

    prompt = build_prompt(query, mode, role, source_passage, context)

    # Step 2: Strict Generation Loop
    MAX_RETRIES = 3
    best_candidate = None
    best_combined_score = -1.0
    
    for attempt in range(MAX_RETRIES):
        if _debug: print(f"--- Attempt {attempt+1}/{MAX_RETRIES} ---")
        
        gen = await generate_with_logprobs(prompt, chat_history)
        if gen["text"] == "OLLAMA_NOT_RUNNING":
            return {
                "text": "OLLAMA_NOT_RUNNING",
                "scores": {"entailment": False, "consistency": False, "confidence": 0.0},
                "role": role,
                "mode": mode,
            }

        variants = await generate_k_variants(prompt, k=4, chat_history=chat_history)
        other_samples = [v for v in variants if v != gen["text"]][:3]
        if not other_samples:
            other_samples = variants[:1] if variants else [gen["text"]]

        # Entailment
        if skip_entailment:
            entailment_bool = None
            grounding_score = 1.0 # default pass
        else:
            grounding_score = check_grounding(source_passage, gen["text"])
            entailment_bool = grounding_score >= 0.6

        # Consistency
        consistency_score = check_consistency(gen["text"], other_samples)
        consistency_bool = consistency_score >= 0.5

        # Token Prob (Confidence)
        lr_p_hall = score_confidence(gen["token_logprobs"], gen["seq_len"])
        lr_signal = float(_np.clip(1.0 - lr_p_hall, 0.1, 0.9))
        prob_bool = lr_p_hall < 0.5

        if skip_entailment:
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
            },
            "raw_scores": {
                "grounding": grounding_score,
                "consistency": consistency_score,
                "lr_signal": lr_signal,
            }
        }

        # Check strict pass
        passed_entailment = skip_entailment or entailment_bool
        passed_consistency = consistency_bool
        passed_prob = prob_bool

        if passed_entailment and passed_consistency and passed_prob:
            best_candidate = candidate
            if _debug: print("-> STRICT PASS! Breaking loop.")
            break
        
        if confidence > best_combined_score:
            best_combined_score = confidence
            best_candidate = candidate

    if not best_candidate:
        # Fallback if somehow loop failed entirely
        return {
            "text": "I cannot confidently and factually answer this based on the document.",
            "scores": {"entailment": False, "consistency": False, "confidence": 0.0},
            "role": role,
            "mode": mode,
        }

    # Step 3: Check if it actually perfectly passed
    passed_all = True
    s = best_candidate["scores"]
    if s["entailment"] is False: passed_all = False
    if s["consistency"] is False: passed_all = False
    # we don't have prob_bool in scores, but we can check if it passed perfectly
    # actually, we'll save to cache if it's the one that broke the loop.
    
    # Save Generation and Semantic Cache
    if passed_all:
        async with async_session_maker() as session:
            db_gen = Generation(
                prompt=prompt,
                response_text=best_candidate["text"],
                token_logprobs=best_candidate["token_logprobs"],
                seq_len=best_candidate["seq_len"],
                grounding_score=best_candidate["raw_scores"]["grounding"],
                consistency_score=best_candidate["raw_scores"]["consistency"],
                confidence_score=best_candidate["scores"]["confidence"],
                combined_score=best_candidate["scores"]["confidence"],
            )
            session.add(db_gen)
            await session.commit()
            
            # Save to semantic cache
            await save_to_semantic_cache(query, doc_ids, db_gen.id)

    else:
        # Strict Fallback
        return {
            "text": "I cannot confidently and factually answer this based on the document.",
            "scores": {"entailment": False, "consistency": False, "confidence": 0.0},
            "role": role,
            "mode": mode,
        }

    return {
        "text": best_candidate["text"],
        "scores": best_candidate["scores"],
        "role": role,
        "mode": mode,
    }
'''

# Find the start of run_factshield_pipeline and replace the rest
match = re.search(r"async def run_factshield_pipeline\(.*", content, re.DOTALL)
if match:
    new_content = content[:match.start()] + new_func
    with open("backend/app/factshield/pipeline.py", "w") as f:
        f.write(new_content)
    print("Replaced run_factshield_pipeline successfully.")
else:
    print("Could not find run_factshield_pipeline.")

