# FactShield — Investor Pitch

## The AI Tutor That Knows When It's Wrong

---

## The Problem Nobody Is Talking About

Every school, university, and corporate training program is rushing to adopt AI assistants. Students are using ChatGPT to understand their coursework. Teachers are using AI to generate exams. Companies are using AI to train employees.

**But there is a fundamental flaw nobody is solving.**

AI systems like ChatGPT make things up. The technical term is "hallucination" — the AI generates text that sounds completely authoritative and confident, but is factually wrong. It does this silently. There is no warning. No indicator. No way for the user to know.

In entertainment or casual use, this is annoying. **In education, this is dangerous.**

A student who learns an incorrect explanation of a concept from an AI tutor will carry that misconception into their exam, their career, and their professional decisions. A teacher who uses AI-generated exam questions with wrong answers sets back an entire classroom. A company that trains employees using unverified AI content exposes itself to serious risk.

**The AI education market is projected to reach $30 billion by 2030. Yet every product in that market has the same critical flaw: they trust the AI blindly and pass that trust directly to the user.**

---

## What We Built

**FactShield is an AI education assistant that knows when it might be wrong — and tells you.**

We built a two-layer product:

**Layer 1 — The AI Education Assistant**
A full-featured tutoring and teaching platform powered by the same technology behind ChatGPT, serving students and teachers through 8 specialised tools. Students get concept explanations, problem guidance, submission checking, and quizzes. Teachers get automated grading, exam generation, personalised feedback, and learning analytics.

**Layer 2 — The FactShield Validation Engine**
Before any response reaches the user, it passes through our proprietary three-pipeline hallucination detection system. We score every answer for factual accuracy, self-consistency, and confidence — in real time. The user sees a trust rating. If the answer cannot be verified, we tell them before they act on it.

**This is not a feature. This is the product.**

---

## The Market Opportunity

| Segment | Size (2024) | Projected (2030) |
|---|---|---|
| AI in Education | $4.8B | $30.1B |
| EdTech overall | $142B | $348B |
| Corporate e-learning | $38B | $78B |

Every student, every teacher, every corporate trainer who uses AI tools today is exposed to unverified information. FactShield is the first product that systematically addresses this.

---

## Our Research — Three Ways to Catch a Lie

This is where FactShield is fundamentally different from every other AI education tool on the market.

We spent two years conducting original academic research on a specific problem: **how do you know if an AI is making something up?** We developed three independent detection methods, each catching a different type of hallucination. We then embedded all three into a live AI assistant that runs them simultaneously on every single response.

Here is how each one works — in plain terms.

---

### Pipeline 1 — The Consistency Test

**The core idea:** A person who is telling the truth tells the same story every time you ask. A person who is making something up changes the details.

AI systems work the same way. When an AI is confident about a fact — because it has learned it from thousands of reliable sources — it will state that fact consistently no matter how many times you ask. When it is guessing or hallucinating, the answer changes slightly each time.

**What we do:** For every response the AI generates, we secretly ask it the same question three more times using slightly different approaches. We then use a sophisticated language comparison system — originally developed at Google — to measure how similar all four answers are at the sentence level.

If the AI says "backpropagation uses the chain rule to compute gradients" in all four versions, that sentence is likely factual. If it says something different each time, that sentence is flagged as potentially hallucinated.

**The result:** A consistency score between 0% and 100% for the response.

---

### Pipeline 2 — The Document Grounding Test

**The core idea:** If a student uploads their textbook and asks a question about it, the AI's answer should come from that textbook — not from what the AI learned during its training, which may be outdated, incorrect, or from a different curriculum.

**What we do:** When a student uploads a course document, we retrieve the most relevant sections from that document for every question. We then use a Natural Language Inference model — an AI specifically trained to determine whether one piece of text logically supports another — to check whether the AI's response is genuinely supported by the student's own document.

Think of it like a plagiarism checker in reverse. Instead of checking if someone copied, we check if the AI's answer is actually derived from the source material it is supposed to be using.

If a student asks about gradient descent and their textbook discusses it on page 43, our system checks whether the AI's explanation is actually grounded in what page 43 says — or whether it is generating a generic answer from its training data.

**The result:** A grounding score between 0% and 100%, and we only run this check when the source material is relevant (we are smart enough not to penalise the AI for information that simply is not in the document).

---

### Pipeline 3 — The Confidence Test

**The core idea:** When a person is uncertain, they hesitate. They use filler words. Their voice changes. AI systems have an equivalent — when generating text they are uncertain about, they assign lower internal probability to each word they choose.

Every modern AI system like GPT-4 produces a hidden number alongside every word it generates — a confidence score for that specific word choice. These numbers are invisible to the user but accessible to developers. A high score means the AI was confident in that word. A low score means it was guessing.

**What we do:** We capture these hidden confidence numbers for every word in every response. We then run them through a feature extraction algorithm from our research pipeline, computing five different measures of the AI's internal uncertainty — including how uncertain it was at the beginning of its response versus the end, and how much variation there was across different parts of the text.

We translate these five signals into a single confidence score. A response about a topic the AI knows well will have uniformly high confidence throughout. A response where the AI is venturing into uncertain territory will show spikes of low confidence — often right where the hallucination is occurring.

**The result:** A confidence score between 0% and 100%, calibrated specifically for the AI model we use.

---

## The Trust Score — One Number That Matters

Running three separate scores for every response would be overwhelming for a user. So we combine all three into a single **Trust Score**, weighted intelligently based on the situation:

- When the student has uploaded their own document, the document grounding test carries the most weight — because that is the most direct signal of accuracy.
- When the AI is drawing from general research sources, consistency and confidence carry more weight.
- When there is no source material available, we cap the trust score automatically and warn the user.

The Trust Score maps to three tiers that every user can understand immediately:

| Tier | Score | What it means |
|---|---|---|
| **Verified** | 65%+ | The response is grounded in your document, the AI gave the same answer multiple times, and it was highly confident. You can rely on this. |
| **Partially Verified** | 35–64% | Some signals are strong, but the response may draw on general knowledge beyond your specific document. Cross-check key facts before relying on them. |
| **Unverified** | Below 35% | We could not verify this response. The AI may be drawing on uncertain ground. Confirm with your instructor or another source. |

**Critically — this is not just a badge. If a response is Unverified, we inject a warning directly into the text of the response itself.** The student does not need to remember to check the score. The warning is part of what they read.

---

## The Product — 8 Features for Students and Teachers

### For Students

**Concept Guide** — Ask any question about your uploaded course material and get a clear, structured explanation grounded in your document. Every explanation includes citations to the specific page or section it came from, and a FactShield trust score.

**Problem Navigator** — A Socratic coach that guides students through problems step by step without giving away the answer. Teaches thinking, not just solutions. Designed to build genuine understanding.

**Submission Validator** — Students paste their homework or essay and our system audits it sentence by sentence against their course document, flagging claims that contradict the material or cannot be verified. Catches errors before submission.

**Quiz Generator** — Generates adaptive practice quizzes at three difficulty levels — recall, comprehension, and application — from the student's own course material.

### For Teachers

**Assignment Grader** — AI-assisted grading with rubric-based feedback. Identifies specific strengths and weaknesses with citations to the course material. Not a replacement for the teacher — an accelerator.

**Exam Generator** — Creates complete multiple-choice exams from uploaded course material, with varied difficulty, a full answer key, and source citations for every question.

**Adaptive Feedback** — Generates personalised coaching for struggling students based on the teacher's description of the student's difficulties. Backed by pedagogical research.

**Learning Insights** — Surfaces which topics students are most likely to struggle with based on the course material, so teachers can prioritise their time.

---

## How We Built It — The Technology, Simply Explained

**The AI Brain**
We use GPT-4o-mini — the same underlying technology as ChatGPT, but accessed directly through the API which gives us capabilities that the standard ChatGPT product does not expose, including the hidden confidence scores our Pipeline 3 depends on. We built a fallback chain: if GPT-4o-mini is unavailable, the system automatically switches to Google's Gemini AI, and then to a locally-running AI model. The app never goes down.

**The Knowledge System**
When a student uploads a document, we break it into intelligent chunks and store it in a mathematical representation called a vector database. When a question arrives, we find the most relevant parts of the document in milliseconds using geometric similarity — the same technology that powers Google Search.

If no document is uploaded, the system automatically searches academic paper databases (ArXiv) and the web to find relevant source material. The user always gets a response grounded in something.

**The FactShield Engine**
Our three pipelines run simultaneously the moment the AI produces a response — while the user is waiting for their answer. By the time the response appears on screen, the trust score is already calculated. There is no additional wait time for validation.

**The Interface**
Built with modern web technology (React), works in any browser, no installation required. Every response includes the trust tier badge, the source that was used, and a clickable panel that reveals the full three-pipeline breakdown for users who want to understand why a score was given.

---

## Why FactShield Is Different From Everything Else

| | ChatGPT / Claude | Generic AI Tutors | FactShield |
|---|---|---|---|
| AI-powered responses | ✓ | ✓ | ✓ |
| Uses your course documents | Partial | Some | ✓ |
| Education-specific features | ✗ | ✓ | ✓ |
| Tells you when it might be wrong | ✗ | ✗ | ✓ |
| Grounded in research | ✗ | ✗ | ✓ |
| Source citations on every response | ✗ | Rarely | ✓ |
| Trust score per response | ✗ | ✗ | ✓ |
| Warns user in the response text | ✗ | ✗ | ✓ |

The key distinction: **every other AI education product asks you to trust the AI. FactShield earns that trust by proving it.**

---

## The Business Model

**SaaS Subscription**

| Tier | Target | Price | What's included |
|---|---|---|---|
| Student | Individual learners | $12/month | All 4 student features, 5 document uploads |
| Teacher | Educators | $29/month | All 8 features, unlimited documents, class analytics |
| Institution | Schools & universities | Custom | Multi-user, admin dashboard, API access, white-labelling |
| Enterprise | Corporate training | Custom | Custom integration, compliance reporting, volume pricing |

**Why institutions will pay:** Every university that deploys AI tools without hallucination detection is one student complaint — or one lawsuit — away from a major reputational incident. FactShield is the only product that gives institutions a defensible answer to "how do you know your AI is accurate?"

---

## The Traction

- Complete working product with all 8 features live
- Three original research pipelines embedded in production code
- 88% validation accuracy across all features in internal testing
- Response time under 20 seconds including full three-pipeline validation
- Zero-dependency deployment — any institution can run it in one command

---

## What We're Looking For

We are raising a seed round to:

1. **Scale the infrastructure** — move from a single-server deployment to a cloud architecture that can handle thousands of simultaneous users
2. **Expand the research** — fine-tune our validation pipelines on education-specific content so trust scores become even more precise
3. **Build the sales motion** — hire a dedicated education sales team focused on university and K-12 district contracts
4. **Develop the institution dashboard** — teacher analytics, class-wide trust reporting, and compliance documentation for administrators

---

## The Team

We built this because we saw the problem firsthand as students and researchers. Our team combines original NLP research — published work on hallucination detection in summarisation systems — with full-stack product engineering. We did not buy technology or assemble existing tools. We built the validation system from scratch, tested it against academic benchmarks, and then embedded it in a product people can actually use.

---

## The One-Line Summary

**FactShield is the only AI education assistant in the world that scores the accuracy of every answer it gives — in real time — using three independent research-grade detection methods, and warns users before they rely on information that cannot be verified.**

Every other AI tool teaches with confidence. We teach with honesty.

---

*For a live product demonstration, technical deep-dive, or partnership discussion, reach out to the FactShield team.*
