# FactShield — AI Education Assistant with Hallucination Detection

FactShield is a RAG+CAG powered AI education assistant that wraps every LLM response in a live three-pipeline hallucination detection system. It serves students and teachers through 8 specialised features, and every single response is independently scored for factual grounding before it reaches the user.

---

## Table of Contents

1. [What Problem We Are Solving](#1-what-problem-we-are-solving)
2. [Product Overview](#2-product-overview)
3. [System Architecture](#3-system-architecture)
4. [Context Engine — RAG + CAG](#4-context-engine--rag--cag)
5. [LLM Layer](#5-llm-layer)
6. [FactShield Validation — The 3 Pipelines](#6-factshield-validation--the-3-pipelines)
7. [Trust Score & Tier System](#7-trust-score--tier-system)
8. [Annotation Injection](#8-annotation-injection)
9. [The 8 Features — A to Z](#9-the-8-features--a-to-z)
10. [Conversation Continuity](#10-conversation-continuity)
11. [Frontend UI](#11-frontend-ui)
12. [Tech Stack](#12-tech-stack)
13. [Project Structure](#13-project-structure)
14. [Running the App](#14-running-the-app)

---

## 1. What Problem We Are Solving

Large language models hallucinate. They generate confident, fluent text that is factually wrong — and in an education setting, that is dangerous. A student who gets a wrong explanation of backpropagation from an AI tutor may go into an exam with a misconception. A teacher who uses AI-generated exam questions with incorrect answers undermines their own course.

Existing AI assistants have no mechanism to tell the user when they are likely to be wrong. They display every response with the same confidence regardless of whether the claim is solidly grounded in source material or entirely fabricated.

FactShield fixes this by running every LLM response through three independent research-grade hallucination detection pipelines and reporting a composite trust score to the user before they act on the information.

---

## 2. Product Overview

FactShield is two things simultaneously:

**An AI Education Assistant** — students upload their course material and get a tutor that explains concepts, navigates problems, validates submissions, and generates quizzes. Teachers get grading assistance, exam generation, adaptive feedback, and learning insight analytics.

**A Hallucination Detection Layer** — every response from the assistant is intercepted by three parallel pipelines derived from our NLP research. The pipelines produce a single composite trust score and a tier (Verified / Partial / Unverified) that is shown to the user and, when needed, injected as a warning directly into the response text.

```
User Query
    │
    ▼
Context Engine ──── Local Document (vector search, cosine threshold 0.60)
    │           ──── ArXiv Semantic Search (fallback 1)
    │           ──── Web Search (fallback 2)
    ▼
LLM (GPT-4o-mini → Gemini 2.5 Flash → Ollama qwen2.5:7b)
    │
    ▼
FactShield 3-Pipeline Validator ─── Pipeline 1: SelfCheckGPT (BERTScore)
    │                            ─── Pipeline 2: MiniCheck NLI (Entailment)
    │                            ─── Pipeline 3: Token Probability Features
    ▼
Composite Trust Score → Trust Tier → Annotated Response → User
```

---

## 3. System Architecture

### Request Lifecycle (every feature, every turn)

```
1.  Request arrives at FastAPI router (student or teacher endpoint)
2.  build_context() retrieves the best available source passage
        → tries local document first (vector cosine similarity ≥ 0.60)
        → falls back to ArXiv semantic search
        → falls back to web scrape / search
        returns: (passage_text, source_type, source_reference)
3.  System prompt selected for the active feature mode
4.  Full conversation history injected into the user message (last 10 messages)
5.  LLM called with logprobs=True (GPT-4o-mini primary)
        returns: (response_text, token_logprobs_bytes, seq_len)
6.  validate() called — all 3 pipelines run in parallel via asyncio.gather
        returns: ValidationResult(trust_score, trust_tier, ...)
7.  _annotate_trust() injects notice into response_text if tier is not verified
8.  ensure_citation_in_response() appends source reference footer
9.  Serialised response returned to frontend
```

### Backend Directory Layout

```
backend/
├── app/
│   ├── api/v1/
│   │   ├── student.py          # 4 student endpoints
│   │   └── teacher.py          # 4 teacher endpoints + legacy
│   ├── engine/
│   │   ├── pipeline.py         # orchestrator — context → generate → validate
│   │   ├── validator.py        # 3-pipeline runner + trust computation
│   │   ├── llm.py              # GPT-4o-mini / Gemini / Ollama client
│   │   └── context.py          # RAG+CAG context builder
│   ├── factshield/
│   │   ├── grounding.py        # Pipeline 2 bridge → MiniCheck NLI
│   │   ├── consistency.py      # Pipeline 1 bridge → SelfCheckBERTScore
│   │   ├── confidence.py       # Pipeline 3 bridge → token prob features
│   │   ├── academic.py         # ArXiv semantic search
│   │   ├── search.py           # Web scrape/search
│   │   ├── citation_enforcer.py
│   │   └── prompts.py          # Feature-specific prompt templates
│   ├── retrieval/
│   │   └── retriever.py        # ChromaDB vector retrieval
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic schemas
│   └── db/                     # Async SQLite session
└── pipelines/                  # Research pipeline code (unchanged)
    ├── selfcheck/              # Pipeline 1 — SelfCheckGPT
    ├── entailment/             # Pipeline 2 — MiniCheck / SummaC / AlignScore
    ├── token_prob/             # Pipeline 3 — logprob feature extraction
    └── shared/                 # Data loaders, evaluators
```

---

## 4. Context Engine — RAG + CAG

Every request goes through a three-tier context cascade before the LLM is called. The cascade tries each tier in order and stops at the first that returns usable content.

### Tier 1 — Local Document (RAG)

The student or teacher uploads a course document (PDF, DOCX). The document is chunked, embedded using a sentence-transformer model, and stored in ChromaDB.

When a query arrives, the top-5 most relevant chunks are retrieved using cosine similarity. If the best chunk scores above **0.60**, the passage is used as context and `source_type` is set to `"document"`. This enables the full three-pipeline validation including the entailment check against the specific retrieved passage.

For the `submission-validator` mode, retrieval is run **per sentence** of the student's submission (not per query) to maximise document coverage when auditing multi-claim text.

### Tier 2 — ArXiv (CAG)

If no local document is uploaded or the similarity score falls below the threshold, the system queries the ArXiv API using the original question as a semantic search. Up to 2 paper abstracts are returned. `source_type` is set to `"academic"`.

Because the retrieved ArXiv snippet may not directly address the specific question (the search is keyword-based, not topic-guaranteed), **entailment validation is skipped for academic sources**. Trust is capped at 0.64 to reflect this lower reliability.

### Tier 3 — Web Search

If ArXiv returns nothing useful, a live web search is executed. The top result is scraped and returned as context. `source_type` is set to `"web"`. Same cap as academic: 0.64 maximum trust, entailment skipped.

### Active Knowledge Base

The system ships with a pre-built knowledge base (indexed at startup). No document upload is required to use the system — the knowledge base provides domain coverage for general education queries.

---

## 5. LLM Layer

### Model Chain

```
GPT-4o-mini (primary — real token logprobs available)
    ↓ fails or rate-limits
Gemini 2.5 Flash (fallback 1 — logprobs unavailable, synthetic used)
    ↓ fails
Ollama qwen2.5:7b (local fallback 2 — logprobs unavailable, synthetic used)
```

GPT-4o-mini is called with `logprobs=True`, which returns the log-probability of each generated token. These logprobs are the raw material for Pipeline 3 (token probability confidence scoring).

When Gemini or Ollama is used, real logprobs are unavailable. In this case, synthetic logprobs drawn from a normal distribution (mean=-1.2, std=0.8) are used as a placeholder, and Pipeline 3's output is treated as a neutral fallback score of 0.5.

### Variant Generation (for Pipeline 1)

For the SelfCheckGPT consistency check, the system needs K=3 independently sampled re-generations of the same query. These are generated in parallel using `chat_variant()`, which calls the LLM at temperature=0.85 (higher temperature = more stochastic = better test of self-consistency). All 3 calls run concurrently via `asyncio.gather`, so the total added latency equals approximately one LLM call, not three.

---

## 6. FactShield Validation — The 3 Pipelines

This is the core research contribution. Every response passes through all three pipelines simultaneously. The pipelines are wired directly to the research code in the `pipelines/` directory — not re-implementations, not proxies.

```python
ent_score, con_score = await asyncio.gather(_entailment(), _consistency())
conf = await _confidence(ent_score)
```

---

### Pipeline 1 — SelfCheckGPT (Self-Consistency via BERTScore)

**Research code:** `pipelines/selfcheck/scorer.py → score_bert_batch()`

**What it detects:** A hallucinating model is inconsistent with itself. When you ask the same question multiple times with slight temperature variation, a hallucinated claim will appear differently phrased or contradicted across samples. A factual claim will be stated consistently.

**How it works:**

1. The primary LLM response is split into individual sentences.
2. Three independent re-generations of the same query are produced in parallel (K=3 samples).
3. `score_bert_batch(sentences, samples)` from the research pipeline computes a BERTScore-based hallucination probability for each sentence. BERTScore uses contextual embeddings (bert-base-uncased) to measure semantic similarity — it is more robust than n-gram matching.
4. The hallucination probabilities are averaged across all sentences.
5. `consistency_score = 1.0 − mean(hallucination_probabilities)`, clipped to [0, 1].

**Interpretation:**

- A consistent, factual response: hallucination score ≈ 0.43 per sentence → consistency ≈ 0.57 (PASS, threshold ≥ 0.30)
- A hallucinated response (model contradicts itself): hallucination score ≈ 1.0+ → consistency ≈ 0.0 (FAIL)

**Fallback:** If BERTScore model loading fails, the system falls back to cosine similarity using `all-MiniLM-L6-v2` embeddings at document level.

---

### Pipeline 2 — Entailment (MiniCheck NLI Grounding)

**Research code:** `pipelines/entailment/scorer.py → score_minicheck_batch()`

**What it detects:** Whether the LLM response is actually supported by (entailed by) the retrieved source document. If the student asks a question and the AI answers from general training knowledge rather than the uploaded course material, entailment will fail even if the answer is technically correct.

**How it works:**

1. The raw LLM response is preprocessed:
   - All markdown syntax is stripped (`**bold**`, `## headings`, `` `code` ``, `$math$`, etc.) because MiniCheck (roberta-large) was trained on plain text — markdown tokens drop NLI scores from ~0.94 to ~0.01 on identical factual content.
   - Conversational preambles ("According to your notes,", "Based on the document,") are stripped because they mislead the NLI model.
   - The first ~500 characters of substantive prose are extracted as the claim.
2. `score_minicheck_batch([source_passage], [clean_claim])` runs the NLI model to compute entailment probability — the probability that the source document logically supports the claim.
3. Returns `entailment_score ∈ [0, 1]`.

**Source-aware gating:**

Entailment is only meaningful when the source passage directly corresponds to the query topic. For ArXiv and web sources, the retrieved snippet may be tangentially related but not specifically about the query — scoring entailment in this case produces false negatives. Therefore:

- `source_type == "document"` → entailment runs, score is load-bearing
- `source_type in ("academic", "web", "none")` → entailment is skipped, returns neutral 1.0

**Interpretation:**

- Score ≥ 0.25: PASS — response is supported by the document
- Score < 0.25: FAIL — response cannot be verified against source material
- Score < 0.10: Hard cap applied — trust score cannot exceed 0.34 regardless of other signals

---

### Pipeline 3 — Token Probability Confidence

**Research code:** `pipelines/token_prob/scorer.py → extract_features_vectorized()`

**What it detects:** The LLM's internal uncertainty signal. When a model generates a token it is uncertain about, its log-probability for that token is low. High uncertainty across the response indicates the model is "guessing" rather than recalling well-learned facts.

**How it works:**

1. GPT-4o-mini is called with `logprobs=True`. The log-probability of every generated token is collected as a byte-serialised float32 array.
2. `extract_features_vectorized()` from the research pipeline computes 5 features:

   | Feature | Formula | What it measures |
   |---|---|---|
   | `perplexity` | `exp(-mean(logprobs))` | Overall generation difficulty |
   | `mean_entropy` | `mean(-exp(lp) × lp)` per token | Average chosen-token uncertainty |
   | `max_entropy` | `max(-exp(lp) × lp)` | Worst single token uncertainty |
   | `tail_mean_nll` | `-mean(logprobs[-5:])` | Uncertainty at end of sequence |
   | `sent_length` | token count | Length proxy |

3. Only `perplexity` and `tail_mean_nll` are used for confidence scoring. `mean_entropy` is deliberately excluded: it is **bell-shaped** (peaks at log-probability = -1.0) and therefore **not monotonically related to uncertainty** — it cannot be used as a threshold signal.

4. Both perplexity and tail_nll are monotonically related to uncertainty. Calibrated thresholds derived from observed GPT-4o-mini distributions:
   - Perplexity 1.5 → confidence 1.0 (certain). Perplexity 21.5 → confidence 0.0 (uncertain).
   - Tail NLL 0.0 → confidence 1.0. Tail NLL 3.0 → confidence 0.0.

5. `confidence = 0.65 × ppl_conf + 0.35 × tail_conf`

6. The final confidence value is blended 60/40 with the entailment score to combine the document-grounding signal (pipeline 2) with the model-internal uncertainty signal (pipeline 3):
   `conf_final = 0.60 × ent_score + 0.40 × logprob_conf`

**Why not the trained classifier?**

The `pipelines/token_prob/` directory includes a trained logistic regression classifier (`task3_classifier.pkl`). This classifier was trained on logprobs from BART, T5, and Pegasus — seq2seq encoder-decoder models evaluated on CNN/DM, XSum, and FaithBench summarisation datasets. GPT-4o-mini is a decoder-only chat model. The logprob distributions differ fundamentally in scale and shape, causing the classifier to return p_hallucination ≈ 0.72 for every single input regardless of content quality. The classifier is out-of-distribution and cannot discriminate. We use the feature extractor (authentic research code) with calibrated thresholds instead.

---

## 7. Trust Score & Tier System

The three pipeline outputs are combined into a single composite trust score using source-aware weights.

### Trust Formula

**Document source (full validation):**
```
raw = 0.50 × entailment_score + 0.30 × consistency_score + 0.20 × confidence
if entailment_score < 0.10:
    raw = min(raw, 0.34)   # hard cap — clearly ungrounded, cannot be partial or above
```

Entailment carries the most weight (50%) because document grounding is the strongest signal for an education assistant. A self-consistent, confident response that isn't supported by the course material is still untrustworthy.

**Academic / Web source (entailment skipped):**
```
raw = 0.55 × consistency_score + 0.45 × confidence
raw = min(raw, 0.64)   # hard cap — cannot reach "verified" without local document
```

**No source:**
```
raw = 0.45 × consistency_score + 0.55 × confidence
raw = min(raw, 0.50)   # hard cap — always at most partial
```

### Trust Tiers

| Tier | Score Range | Meaning |
|---|---|---|
| **Verified** | ≥ 0.65 | Response is grounded in the document, self-consistent, and generated with high confidence. Presented clean. |
| **Partial** | 0.35 – 0.64 | Some signals are missing. The response may draw from general knowledge beyond the retrieved passage, or the source was ArXiv/web. A footnote is added. |
| **Unverified** | < 0.35 | The response could not be verified. Either the entailment check failed, the model contradicted itself across samples, or no source was available. A warning is prepended to the response. |

---

## 8. Annotation Injection

FactShield validation is not decorative. The trust tier has a direct consequence on what the user reads.

**Verified** — response is returned as-is, no annotation.

**Partial** — italic footnote appended:
```
---
*FactShield: partially verified — some claims draw from general knowledge
rather than your document. Cross-check key facts before use.*
```

**Unverified (document source)** — blockquote warning prepended:
```
> **FactShield Notice:** This response could not be verified against your
> uploaded document. The claims below may go beyond what your course
> material covers. Verify with your instructor before use.
```

**Unverified (academic/web source)** — informational header:
```
> **FactShield Notice:** This response is based on general knowledge
> sources (ArXiv / web). Treat it as supplementary, not authoritative.
```

This makes hallucination detection functional rather than decorative. The user does not need to read a sidebar score — the warning is part of the response itself.

---

## 9. The 8 Features — A to Z

### Student Features

#### Concept Guide
**Endpoint:** `POST /api/v1/student/concept-guide`

The core tutoring feature. Students ask questions about their course material and get clear, structured explanations grounded in the uploaded document.

**Mechanism:**
- Retrieves up to 5 relevant passages from the document using vector similarity.
- System prompt instructs the LLM to cover the core idea, mechanism, and a concrete example.
- Inline and block math rendered with LaTeX (`$...$` and `$$...$$`).
- Citations tagged with `[Page X]` or `[Section: Name]`.
- All 3 FactShield pipelines run. Trust tier reflects how well the response is grounded in the specific retrieved passage.

**Good questions:** "What is gradient descent?", "How does the chain rule work in backpropagation?", "What is the vanishing gradient problem?"

---

#### Problem Navigator
**Endpoint:** `POST /api/v1/student/problem-navigator`

A Socratic coach. Guides students step-by-step through problems without giving away the final answer.

**Mechanism:**
- Context retrieval same as concept-guide but with higher token budget (1400 tokens).
- System prompt enforces a coaching structure: restate the question, identify knowns, name formula variables, set up substitution, stop before the answer.
- Ends every response with a self-check checklist.
- Falls back to ArXiv/web if no document is provided, so it works for general problem types.

**Good questions:** "I don't understand how to compute the gradient of the cross-entropy loss", "Can you walk me through this matrix multiplication problem?"

---

#### Submission Validator
**Endpoint:** `POST /api/v1/student/submission-validator`

Audits a student's written submission sentence by sentence against the course document.

**Mechanism:**
- Uses `build_submission_context()` — retrieval is run per sentence of the submission (not per query) to maximise document coverage when the submission spans multiple topics.
- LLM audits each sentence: Passed / Flagged with issue type (Overgeneralisation, Contradiction, Unsupported Claim, External Information).
- For each flagged sentence: quotes the document, explains the issue, provides a corrected sentence.
- Entailment check in Pipeline 2 validates the audit response itself against the retrieved passages.

**Good inputs:** Paste a homework paragraph or answer and ask "Validate my submission."

---

#### Quiz Generator
**Endpoint:** `POST /api/v1/student/quiz-generator`

Generates structured practice quizzes in JSON format. Three difficulty levels: recall, comprehension, application.

**Mechanism:**
- Retrieves document context; falls back to knowledge base / web.
- LLM instructed to return a valid JSON array of question objects (no markdown, no commentary).
- JSON is cleaned of any stray markdown fences after generation.
- Trust score computed from entailment of quiz content against source (for document sources) and fixed consistency estimate of 0.70 (quiz output at temperature=0.3 is near-deterministic, implying high implicit consistency).

---

### Teacher Features

#### Assignment Grader
**Endpoint:** `POST /api/v1/teacher/assignment-grader`

Grades student submissions with rubric-based feedback, identifying strengths and gaps, with page-level citations.

**Mechanism:**
- Retrieves document context (rubric + course material).
- Produces: letter grade, numeric score, specific strengths with citations, identified gaps with citations, 2-3 actionable suggestions.
- All 3 pipelines validate the grading response. Entailment checks that grade rationale is supported by the document.
- A dual-badge mode exists in the legacy `/grade-answer` endpoint: one badge for AI grading reliability, a second badge for student answer vs document match.

---

#### Exam Generator
**Endpoint:** `POST /api/v1/teacher/exam-generator`

Generates full exams from course material. Multiple-choice format, varied difficulty, complete answer key with rationale.

**Mechanism:**
- Retrieves document context; falls back to ArXiv for topic coverage.
- System prompt enforces: 4 options per MCQ, difficulty range from recall to application, `[Page X]` citation on every question, full answer key.
- Higher token budget (1800 tokens) to fit full exam structure.
- Trust tier reflects whether the questions are grounded in the uploaded course material.

---

#### Adaptive Feedback
**Endpoint:** `POST /api/v1/teacher/adaptive-feedback`

Generates personalised feedback for a struggling student based on the teacher's description of the student's difficulties.

**Mechanism:**
- Falls back aggressively to ArXiv and web (teachers often describe pedagogy challenges, not document-specific questions).
- System prompt focuses on actionable, constructive coaching language.
- FactShield trust score tells the teacher how much the feedback draws from general pedagogical knowledge vs the specific course material.

---

#### Learning Insights
**Endpoint:** `POST /api/v1/teacher/learning-insights`

Analyses the course material and student interaction patterns to surface what topics students are struggling with, where the material has gaps, and what to prioritise in upcoming lectures.

**Mechanism:**
- Uses the Active Knowledge Base (no upload required) plus ArXiv for research-backed insights.
- Designed for high-level pedagogical questions rather than specific document lookups.
- Trust score reflects confidence in the insights relative to available evidence.

**Good questions:** "What concepts are students most likely to struggle with in this chapter?", "What prerequisite gaps should I address before teaching transformers?", "Which topics in this document need more examples?"

---

## 10. Conversation Continuity

Every feature supports multi-turn conversation. The system maintains a **10-message rolling window** (5 complete turns: user + assistant × 5).

History is injected directly into the user message for each turn rather than the system prompt, so the LLM sees the full conversation context as part of the query without polluting the feature-specific system prompt.

This means:
- Follow-up questions ("Can you expand on that?", "What about the learning rate specifically?") work correctly.
- The assistant does not re-introduce concepts already established in the conversation.
- FactShield validation runs independently on each turn — the trust score for a follow-up answer is scored on its own merits, not inherited from the previous turn.

---

## 11. Frontend UI

Built in React + TypeScript + Vite.

### FactShield Score Badge

Every response displays a trust tier banner showing:

- **Tier label** with colour coding: green (Verified), amber (Partial), red (Unverified)
- **Pulsing status dot**
- **Trust percentage pill** (e.g. "87%")
- **Clickable to expand** — reveals the 3-pipeline breakdown:
  - Pipeline 1 SelfCheck score
  - Pipeline 2 NLI Entailment score
  - Pipeline 3 Token Probability confidence
  - Trust formula at the bottom

### Source Banner

Every response shows which source was used: `Local document`, `ArXiv research`, `Web search`, or `Active Knowledge Base`. Source links open in a new tab.

### Markdown Rendering

Response text is rendered with `react-markdown` + `remark-gfm` + `remark-math` + `rehype-katex`. Inline math (`$...$`) and display math (`$$...$$`) render correctly. All links open in new tabs (`target="_blank"`).

---

## 12. Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI (Python 3.11) |
| Primary LLM | GPT-4o-mini (OpenAI) with logprobs |
| LLM fallback 1 | Gemini 2.5 Flash |
| LLM fallback 2 | Ollama qwen2.5:7b (local) |
| Vector store | ChromaDB |
| Embeddings | sentence-transformers |
| Pipeline 1 | SelfCheckGPT — BERTScore (bert-base-uncased) |
| Pipeline 2 | MiniCheck (roberta-large NLI) |
| Pipeline 3 | Token probability features + perplexity/tail-NLL calibration |
| Database | SQLite (async via SQLAlchemy + aiosqlite) |
| Frontend | React 18 + TypeScript + Vite |
| Math rendering | KaTeX via rehype-katex |
| Markdown | react-markdown + remark-gfm |
| Package manager | npm (frontend), conda/pip (backend) |

---

## 13. Project Structure

```
FactShield/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── student.py          # concept-guide, problem-navigator,
│   │   │   │                       # submission-validator, quiz-generator
│   │   │   └── teacher.py          # assignment-grader, exam-generator,
│   │   │                           # adaptive-feedback, learning-insights
│   │   ├── engine/
│   │   │   ├── pipeline.py         # main orchestrator
│   │   │   ├── validator.py        # 3-pipeline runner + trust formula
│   │   │   ├── llm.py              # LLM client + variant generation
│   │   │   └── context.py          # RAG+CAG cascade
│   │   ├── factshield/
│   │   │   ├── grounding.py        # Pipeline 2 — MiniCheck NLI bridge
│   │   │   ├── consistency.py      # Pipeline 1 — BERTScore bridge
│   │   │   ├── confidence.py       # Pipeline 3 — token prob bridge
│   │   │   ├── academic.py         # ArXiv search
│   │   │   ├── search.py           # Web search
│   │   │   ├── citation_enforcer.py
│   │   │   └── prompts.py
│   │   ├── retrieval/
│   │   │   └── retriever.py        # ChromaDB vector retrieval
│   │   ├── models/                 # Document, Grade ORM models
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   │   ├── student.py
│   │   │   ├── teacher.py
│   │   │   └── pipeline.py         # PipelineScores schema
│   │   └── db/session.py
│   └── pipelines/                  # Research pipeline code (read-only)
│       ├── selfcheck/
│       │   └── scorer.py           # score_bert_batch()
│       ├── entailment/
│       │   └── scorer.py           # score_minicheck_batch()
│       ├── token_prob/
│       │   └── scorer.py           # extract_features_vectorized()
│       └── shared/
├── frontend/
│   └── src/
│       ├── App.tsx                 # Main UI, FactShield badge, chat
│       ├── lib/
│       │   ├── api.ts              # API client
│       │   └── types.ts            # Type definitions
│       └── App.css
├── configs/                        # Research pipeline experiment configs
├── docker-compose.yml
└── README.md
```

---

## 14. Running the App

### Prerequisites

- Python 3.11 with conda environment `fs_env`
- Node.js 18+
- OpenAI API key (required for GPT-4o-mini and real logprobs)
- Gemini API key (optional fallback)
- Ollama running locally (optional fallback)

### Backend

```bash
cd backend
PYTHONPATH=/path/to/FactShield \
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### Environment Variables

```
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...         # optional
DATABASE_URL=sqlite+aiosqlite:///./factshield.db
CHROMA_PERSIST_DIR=./chroma_db
```

### First Run

1. Open `http://localhost:5173`
2. Switch to the Student or Teacher panel
3. Upload a course document (PDF recommended) — or skip to use the Active Knowledge Base
4. Select a feature and start asking questions
5. Observe the FactShield trust badge on every response — click it to expand the 3-pipeline breakdown

---

## Research Context

FactShield originated as an NLP research project investigating hallucination detection in abstractive summarisation. The three pipelines were developed and evaluated on the FaithBench dataset using BART, T5, and Pegasus models:

- **SelfCheckGPT** (Pipeline 1): Sentence-level consistency using BERTScore across stochastic samples. Adapted from the SelfCheckGPT paper for use in live inference.
- **MiniCheck NLI** (Pipeline 2): Document-grounding via a fine-tuned roberta-large NLI model. Extended with markdown stripping and preamble normalisation for robust use with chat LLMs.
- **Token Probability Features** (Pipeline 3): Five features derived from token log-probabilities. The trained logistic regression classifier is research-purpose (seq2seq models on FaithBench). Production deployment uses calibrated feature thresholds derived from GPT-4o-mini's actual logprob distribution, since the classifier is out-of-distribution for decoder-only chat models.

The FactShield product demonstrates that research-grade hallucination detection can be integrated into a production AI assistant with meaningful, discriminative trust signals — not just academic benchmark scores.
