# FactShield Local-First + Citation Architecture

## Overview

All 8 student and teacher features now:
1. **Search LOCAL first** (syllabus/course documents)
2. **Fall back to ONLINE** if local source is weak
3. **Verify ALL sources** with 3 pipelines (entailment + consistency + confidence)
4. **Cite every response** with source type

## Search Order (Local-First)

Every feature searches in this order:

```
Query received
    ↓
1. search_document (local syllabus/course materials)
    ├─ Passes 3-pipeline? → Return with [Document] citation
    └─ Fails? Continue to step 2
    ↓
2. search_arxiv (academic research)
    ├─ Passes 3-pipeline? → Return with [Academic Paper](URL) citation
    └─ Fails? Continue to step 3
    ↓
3. search_copilot (technical snippets)
    ├─ Passes 3-pipeline? → Return with [Copilot](URL) citation
    └─ Fails? Continue to step 4
    ↓
4. search_web (web search)
    ├─ Passes 3-pipeline? → Return with [Web Source](URL) citation
    └─ Fails? Generate refusal
    ↓
Refusal: "No verifiable sources found. Please rephrase."
```

## 3-Pipeline Verification

**Every response** (from any source) is verified before returning:

1. **Entailment/Grounding** (MiniCheck) — Is claim supported by source?
2. **Consistency** (SelfCheckGPT) — Do variants agree? (no hallucination)
3. **Confidence** (Token Probability + LR) — How confident is the model?

**Threshold to pass:**
- Entailment ≥ 0.6
- Consistency ≥ 0.5
- Confidence combined score > best failed candidate

## Citation Enforcement

### Automatic Citation

If response lacks citation, one is appended:

```python
from app.factshield.citation_enforcer import ensure_citation_in_response

response = "Deep learning is a subset of machine learning..."
# Append citation if missing
response_cited = ensure_citation_in_response(response, source_type="document")
# Result: "Deep learning is a subset of machine learning...\n\n**Source:** Your syllabus / course materials"
```

### Citation Formats by Source

| Source | Format | Example |
|--------|--------|---------|
| Local Document | Plain text | "Your syllabus / course materials" |
| Academic | Paper title + URL | "Academic research: [Deep Learning (LeCun et al., 2015)](arxiv.org/...)" |
| Copilot | Technical KB | "Technical Knowledge Base: Copilot" |
| Web | URL | "Web search result: https://example.com" |

## Code Changes

### 1. Student/Teacher Handlers
**File:** `backend/app/api/v1/student.py` and `backend/app/api/v1/teacher.py`

Changed from:
```python
# OLD: Pre-load document and skip orchestrator
passages, _ = await retrieve_with_scores(query, doc_ids)
source_passage = "\n".join(passages)
```

To:
```python
# NEW: Empty source_passage lets orchestrator run from start
source_passage = ""  # Orchestrator searches all sources
result = await run_factshield_pipeline(
    query=search_query,
    mode=mode,
    source_passage=source_passage,  # Empty!
    doc_ids=request.doc_ids,  # Doc IDs still passed for local search
)
```

### 2. Citation Enforcer
**File:** `backend/app/factshield/citation_enforcer.py` (NEW)

```python
def ensure_citation_in_response(response, source_type, source_reference):
    """Append citation if missing."""
    if already_has_citation(response):
        return response
    return response + f"\n**Source:** {citation_text}"
```

### 3. Pipeline Integration
**File:** `backend/app/factshield/pipeline.py`

All return statements now enforce citations:

```python
# Cache hit
response_with_citation = ensure_citation_in_response(cached_gen.response_text, source_type)

# Orchestrator success
response_with_citation = ensure_citation_in_response(cand["text"], source_type)

# Both ensure citation is present
return {"text": response_with_citation, ...}
```

## Feature Behavior

### Example: Concept Guide

**Query:** "Can you explain what is deep learning"

**Flow:**
1. Search local documents
   - Query embedding searched in syllabus chunks
   - If passages found and pass 3-pipeline
   - Return: "Deep learning is... [concepts explained]\n**Source:** Your syllabus"
   
2. If local fails, search arXiv
   - Query sent to arXiv API
   - Top papers retrieved and summarized
   - If passes 3-pipeline verification
   - Return: "Deep learning is... [from research]\n**Source:** Academic research: [Paper Title](arxiv.org/...)"

3. If arXiv fails, search Copilot KB
   - Technical snippets retrieved
   - If passes 3-pipeline
   - Return: "Deep learning is... [technical]\n**Source:** Technical Knowledge Base: Copilot"

4. If Copilot fails, search web
   - DuckDuckGo results retrieved
   - If passes 3-pipeline
   - Return: "Deep learning is... [web]\n**Source:** Web search result: https://..."

5. If all fail
   - Generate refusal: "No verifiable sources found. Please rephrase or provide more context."

## Core Pipelines Unchanged

✅ Entailment/grounding (MiniCheck) — unchanged
✅ Consistency (SelfCheckGPT) — unchanged
✅ Confidence (token probability + LR) — unchanged

**Only changed:** Retrieval ordering and citation enforcement

## Configuration

In `backend/app/config.py`:

```python
MODEL_PROVIDER: str = "hybrid"  # OpenAI + Ollama fallback
enable_token_optimization: bool = True
enable_hybrid_search: bool = True  # Vector + keyword
```

In `.env`:

```
MODEL_PROVIDER=hybrid
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...  # For query rewriting
```

## Testing

### Manual Test

```bash
# Start backend
cd backend
python -m uvicorn app.main:app --reload

# In browser/Postman
POST /api/v1/student/concept-guide
{
  "question": "Can you explain what is deep learning",
  "doc_ids": ["doc-uuid"],
  "chat_history": []
}

# Expected response:
{
  "text": "Deep learning is a subset of machine learning that...[explanation with inline [Page X] citations]\n**Source:** Your syllabus / course materials",
  "entailment": true,
  "consistency": true,
  "confidence": 0.87,
  "fallback_type": "none"
}
```

### Testing Each Source

1. **Local first** — Ask a question covered in the document
2. **Academic fallback** — Ask about a topic not in document but in research (e.g., recent papers)
3. **Copilot fallback** — Ask technical implementation details
4. **Web fallback** — Ask about current events / news
5. **Refusal** — Ask something completely off-topic

All should return with appropriate citations and 3-pipeline scores.

## Troubleshooting

### Response doesn't have citation
→ Citation enforcer should append one. Check logs for errors.

### "All orchestrator tools exhausted"
→ All sources failed 3-pipeline. System correctly returns refusal.

### Local always fails
→ Check if `doc_ids` are passed correctly to pipeline
→ Verify document chunks are embedded and searchable

### High latency
→ Multiple sources being tried. Consider using OpenAI with `MODEL_PROVIDER=hybrid` for speed.
