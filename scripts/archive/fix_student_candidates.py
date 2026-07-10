
with open('backend/app/api/v1/student.py', 'r') as f:
    content = f.read()

# Replace best_scored_summary logic
new_logic = """
    import asyncio

    async def generate_candidate(i: int):
        varied_query = f"{search_query} (Variant {i+1}: Please subtly vary your sentence structure and word choice.)"
        return await run_factshield_pipeline(
            query=varied_query,
            mode="summarise",
            role="student",
            source_passage=source_passage,
            skip_entailment=False,
            chat_history=request.chat_history,
            doc_ids=getattr(request, 'doc_ids', [getattr(request, 'doc_id', None)]),
        )

    tasks = [generate_candidate(i) for i in range(request.n_candidates)]
    results = await asyncio.gather(*tasks)

    all_candidates = []
    for result in results:
        if result["text"] == "AI_SERVICE_UNAVAILABLE":
            return JSONResponse(status_code=503, content={"error": True, "response": "The Hugging Face Inference API is currently unavailable."})  # noqa: E501

        s = result["scores"]
        ent_score = 1.0 if s["entailment"] else 0.0
        con_score = 1.0 if s["consistency"] else 0.0
        conf_score = s["confidence"]

        # Penalize if it failed entailment or consistency
        combined = (ent_score * 0.4) + (con_score * 0.4) + (conf_score * 0.2)

        candidate = CandidateScore(
            text=result["text"],
            grounding=ent_score,
            consistency=con_score,
            confidence=conf_score,
            combined_score=combined,
        )
        all_candidates.append(candidate)

    all_candidates.sort(key=lambda x: x.combined_score, reverse=True)
    winner_candidate = all_candidates[0]

    # BestScoredSummaryResponse preserves winner/all_candidates for compatibility
    return BestScoredSummaryResponse(
        winner=winner_candidate,
        all_candidates=all_candidates,
        scores=PipelineScores(
            entailment=bool(winner_candidate.grounding >= 0.5),
            consistency=bool(winner_candidate.consistency >= 0.5),
            confidence=winner_candidate.confidence
        ),
    )
"""

# Find the start of `result = await run_factshield_pipeline` in best_scored_summary
start_idx = content.find(
    '    result = await run_factshield_pipeline(\n        query=search_query,\n        mode="summarise"')
end_idx = content.find('    return BestScoredSummaryResponse(', start_idx)
end_idx = content.find(')', end_idx) + 1

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_logic.strip() + '\n' + content[end_idx:]

with open('backend/app/api/v1/student.py', 'w') as f:
    f.write(content)
print("Updated student.py")
