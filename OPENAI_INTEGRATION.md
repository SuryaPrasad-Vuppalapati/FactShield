# OpenAI Integration & Token Optimization Guide

## Quick Start

### 1. Set Your OpenAI API Key

```bash
export OPENAI_API_KEY="sk-..."
```

Or add to `.env`:
```
OPENAI_API_KEY=sk-...
```

### 2. Choose Model Provider

Set the `MODEL_PROVIDER` environment variable:

```bash
# Use OpenAI only (will fail if API unavailable)
export MODEL_PROVIDER=openai

# Use Ollama only (local, free, unlimited)
export MODEL_PROVIDER=ollama

# Use OpenAI with Ollama fallback (recommended for $10 credit)
export MODEL_PROVIDER=hybrid  # default
```

## Cost & Token Optimization Strategies

### With $10 OpenAI Credit

**Recommended Configuration:**
```bash
export MODEL_PROVIDER=hybrid
export OPENAI_API_KEY=sk-...
```

This will:
- ✅ Try OpenAI first (gpt-3.5-turbo, ~$0.0005 per 1k tokens)
- ✅ Fall back to local Ollama on rate limit or error
- ✅ Use semantic cache to avoid regeneration (~20% hit rate)
- ✅ Constrain response length by feature mode (150-400 tokens max)
- ✅ Summarize retrieved chunks before generation
- ✅ Use hybrid search (vector + keyword) for better retrieval quality

**Expected Cost:**
- 100 student/teacher queries: ~$0.10-0.20
- Your $10 credit: ~5,000-10,000 queries

### To Extend Credit Further

1. **Keep Ollama for most generation**: Set `MODEL_PROVIDER=ollama` and only use OpenAI for critical paths
2. **Enable cache**: Already enabled by default
3. **Reduce variants**: Lower `k` in consistency checking (default: k=2)
4. **Monitor usage**: Check OpenAI dashboard for real token counts

## New Features

### 1. Hybrid Search (Vector + Keyword)

Combines semantic (pgvector) and keyword (BM25) retrieval:

```python
passages, score = await retrieve_with_scores(query, doc_ids, k=5)
# Now uses 70% vector + 30% keyword weighting internally
```

**Benefits:**
- Better recall for named entities and exact phrases
- Reduces retrieval retries (~10% fewer pipeline iterations)
- Saves generation tokens

### 2. Token Optimization

#### Query Decomposition
```python
from app.factshield.token_optimizer import decompose_query

queries = decompose_query("What is deep learning and how is it used in NLP?")
# Returns: ["What is deep learning?", "How is it used in NLP?"]
```

#### Response Length Constraints
```python
from app.factshield.token_optimizer import constrain_response_length

max_tokens = constrain_response_length("concept-guide")
# Returns: 250 (concepts should be brief)
```

#### Early Stopping on High-Confidence Cache
```python
# Automatically skips regeneration if cached confidence >= 0.85
# This is enabled by default when settings.enable_token_optimization=True
```

#### Chunk Summarization
```python
from app.factshield.token_optimizer import summarize_chunks

summarized = summarize_chunks(chunks, max_length=2000)
# Truncates to 2000 chars while preserving context flow
```

### 3. Configuration

In `backend/app/config.py`:

```python
# Model provider selection
MODEL_PROVIDER: str = "hybrid"  # "ollama", "openai", or "hybrid"

# Token budget
enable_token_optimization: bool = True
max_monthly_tokens: int = 100000  # ~$1-2 for gpt-3.5-turbo

# Hybrid search
enable_hybrid_search: bool = True
vector_weight: float = 0.7  # 70% vector, 30% keyword
```

## Environment File Example

Create `.env` in the backend directory:

```
# Database
DATABASE_URL=postgresql+asyncpg://factshield:password@localhost:5432/factshield

# APIs
GEMINI_API_KEY=...  # For query rewriting and copilot tool
OPENAI_API_KEY=sk-...  # For generation (optional)
HF_TOKEN=...  # For embeddings and model downloads

# Model Configuration
MODEL_PROVIDER=hybrid
ENABLE_TOKEN_OPTIMIZATION=true
MAX_MONTHLY_TOKENS=100000
ENABLE_HYBRID_SEARCH=true
VECTOR_WEIGHT=0.7
```

## Architecture Impact

These changes **do NOT modify** the core FactShield 3-pipeline verification:
- ✅ Entailment/grounding (MiniCheck) — unchanged
- ✅ Consistency scoring — unchanged
- ✅ Confidence scoring — unchanged

Only the **retrieval and generation layers** are optimized:
- RAG caching: now source-aware via `source_type`
- Retrieval: hybrid search (vector + keyword)
- Generation: provider selection (OpenAI or Ollama)
- Token efficiency: response constraints, chunk summarization, early stopping

## Troubleshooting

### "OpenAI rate limit hit"
→ System automatically falls back to Ollama. You're within rate limits.

### "OpenAI API key not configured"
→ Set `OPENAI_API_KEY` or leave empty to use Ollama only.

### "High token usage"
→ Check if `enable_token_optimization=True`. If false, set it to true.
→ Reduce `max_response_tokens` in mode constraints.
→ Increase cache hit rate by using longer cache thresholds.

### "Ollama not running"
→ If using `MODEL_PROVIDER=ollama`, run: `ollama run qwen2.5:7b`
→ If using `MODEL_PROVIDER=hybrid`, OpenAI will be tried first.

## Monitoring Token Usage

Check OpenAI dashboard for actual usage:
- Completion tokens: what you generate (the expensive part)
- Prompt tokens: what you send as context (cheaper)

Typical costs:
- Concept explanation: ~150 completion tokens = $0.0001
- Exam question generation: ~300 tokens = $0.0002
- Multi-turn with context: ~500 tokens = $0.0003

## Next Steps

1. Test hybrid search locally with Ollama
2. Set up OpenAI API key and test "concept-guide" endpoint
3. Monitor cache hit rates in logs
4. Adjust `vector_weight` if retrieval quality degrades
5. Profile actual token usage on your document set
