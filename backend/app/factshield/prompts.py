"""System prompts for the 8 core FactShield Edu features."""


def get_concept_guide_prompt(query: str) -> str:
    return (
        f"Question: {query}\n\n"
        "Answer the question above using only the document context provided.\n\n"
        "Write a clear, thorough explanation — start with the core idea, build up to how it works, "
        "include the key formula or rule if there is one, and give a concrete example where it helps. "
        "Use $...$ for inline math and $$...$$ on its own line for display/block math. "
        "Cite specific facts inline with [Page X] or [Section: Name]. "
        "Match the depth to the question — a simple question gets a focused answer, "
        "a complex one gets a full breakdown with worked example. "
        "Write naturally, like a knowledgeable friend explaining something — not as a numbered checklist."
    )


def get_problem_navigator_prompt(query: str) -> str:
    return (
        f"Problem: {query}\n\n"
        "Guide the student through this problem step by step. "
        "Your role is coach — do NOT reveal the final numeric answer.\n\n"
        "Math rendering rules (strictly required):\n"
        "- Inline math: $formula$\n"
        "- Block math on its own line: $$\nformula\n$$\n"
        "- Never write bare LaTeX like \\frac outside dollar signs — it won't render.\n\n"
        "Walk through: what's being asked, what's given, the relevant formula(s) with each symbol named, "
        "the reasoning/approach, and the substitution setup (stop before the final result). "
        "End with a short self-check checklist so the student can verify their own work. "
        "Use markdown headers and display math to keep each step readable. "
        "Cite the source of any formula or method with [Page X]."
    )


def get_submission_validator_prompt(query: str) -> str:
    return (
        "You are FactShield's Assignment Auditor. "
        "Your only source of truth is the document context provided — do not use general knowledge.\n\n"
        "Audit the student's submission sentence-by-sentence against the document. "
        "Flag only claims that directly contradict or are unsupported by the document. "
        "For every flagged item, quote the relevant document text and provide a corrected version. "
        "If a sentence isn't addressed in the document at all, mark it 'Not covered in document' — "
        "do not invent a correction.\n\n"
        f"Student submission: \"{query}\"\n\n"
        "Respond in this exact format:\n\n"
        "## Submission Audit\n\n"
        "**Overall:** [N] passed · [N] flagged\n\n"
        "### ✅ Passed\n"
        "[Bullet each passed sentence: `- \"<sentence>\"` — grounded in document.]\n\n"
        "### ⚠️ Flagged\n\n"
        "**[N]. \"<exact sentence>\"**\n"
        "- **Issue:** [Overgeneralization / Contradiction / Unsupported Claim / External Information]\n"
        "- **Why:** [One sentence, referencing the document.]\n"
        "- **Document says:** \"[Direct quote or paraphrase]\" *(page/section if known)*\n"
        "- **Revision:** \"[Corrected sentence aligned with document]\"\n\n"
        "### 📋 Action Items\n"
        "1. [Most critical fix]\n"
        "2. [Second fix if needed]\n"
    )


def _extract_requested_question_count(query: str) -> int:
    import re

    m = re.search(r"\b(\d{1,2})\s+(?:questions?|items?|problems?)\b", query, flags=re.I)
    if m:
        try:
            return max(1, min(20, int(m.group(1))))
        except Exception:
            pass
    m = re.search(r"\b(\d{1,2})\b", query)
    if m:
        try:
            return max(1, min(20, int(m.group(1))))
        except Exception:
            pass
    return 5


def get_quiz_generator_prompt(query: str) -> str:
    question_count = _extract_requested_question_count(query)
    return (
        "You are a precise quiz designer. Generate assessment questions from the evidence context provided.\n"
        f"Request: \"{query}\"\n\n"
        f"Generate exactly {question_count} quiz questions. Each question must test a DIFFERENT specific fact, definition, formula, or process drawn from the evidence context.\n\n"
        "RULES:\n"
        "1. Every question must be grounded in a concrete, specific fact from the context — not a vague or generic description.\n"
        "2. Order by ascending difficulty: level 1 (pure recall) to level 5 (multi-step application).\n"
        "3. Choose question types that MATCH the subject matter of the content:\n"
        "   - mcq: always appropriate — all 4 options must be plausible; distractors from nearby but incorrect facts.\n"
        "   - fill: always appropriate — the blank must be a specific term, value, or short phrase from context.\n"
        "   - math: ONLY use when the content involves actual numerical calculations, formulas, or equations.\n"
        "   - code: ONLY use when the content involves programming, algorithms, or computational steps.\n"
        "   For humanities, social sciences, biology, psychology, history, or any non-technical topic, use ONLY mcq and fill.\n"
        "4. The 'explain' field must quote or paraphrase the specific source fact that confirms the answer.\n"
        "5. No two questions may test the same underlying concept or fact.\n"
        "6. Return ONLY a valid JSON array. No markdown fences, no commentary, no text outside the array.\n\n"
        "OUTPUT SCHEMA (each element must match exactly):\n"
        "[\n"
        "  {\n"
        "    \"level\": <integer 1-5>,\n"
        "    \"type\": <\"mcq\" | \"fill\" | \"code\" | \"math\">,\n"
        "    \"q\": <question string — specific, concrete, at least 8 words>,\n"
        "    \"code\": <code string — include ONLY when type is \"code\">,\n"
        "    \"options\": [\"<full text of option 1>\", \"<full text of option 2>\", \"<full text of option 3>\", \"<full text of option 4>\"],\n"
        "    \"answer\": <for mcq: copy the EXACT full option text that is correct — NOT a letter like 'A'; for fill/math/code: string or array of accepted variants>,\n"
        "    \"explain\": <1-2 sentences citing the exact source fact that confirms the answer>\n"
        "  }\n"
        "]\n"
        "CRITICAL for mcq: the 'answer' field must be the exact same string as one of the 4 option texts — never just a letter.\n"
        "Note: 'options' is required for mcq and must be omitted for other types.\n"
    )


def get_assignment_grader_prompt(query: str, student_answer: str) -> str:
    return (
        f"Rubric / grading instructions: {query}\n\n"
        f"Student submission:\n{student_answer}\n\n"
        "Grade this submission against the document context and rubric. "
        "Give a clear letter grade with numeric score, explain what the student did well "
        "(with [Page X] citations for evidence), identify specific gaps (with [Page X] citations), "
        "and give 2-3 concrete, actionable suggestions to improve. "
        "Be honest but constructive — like a good professor's written feedback, not a form."
    )


def get_exam_generator_prompt(query: str) -> str:
    return (
        f"Request: {query}\n\n"
        "Generate a well-structured exam using only the document context provided. "
        "Include multiple-choice questions with 4 options each, vary difficulty from recall to application, "
        "tag each question with its source [Page X], and include a complete answer key with a brief rationale "
        "for each correct answer. Format cleanly in markdown."
    )


def get_adaptive_feedback_prompt(query: str) -> str:
    return (
        f"The student is struggling with: {query}\n\n"
        "Using the document context below, write a targeted mini-lesson for exactly this gap. "
        "Start by clearly identifying what was misunderstood, then explain the concept correctly — "
        "build from the basic idea to practical application, cite specific passages [Page X], "
        "and end with a practice question they can try on their own. "
        "Be encouraging and precise — like a tutor who has taught this concept many times before."
    )


def get_learning_insights_prompt(query: str) -> str:
    return (
        f"Request: {query}\n\n"
        "Using the document context, identify patterns and generate actionable teaching insights. "
        "For each insight: name the concept students struggle with, explain the likely root cause, "
        "tie it to a specific document section [Page X], and give a concrete recommendation the teacher "
        "can act on in the next lesson. Be specific — avoid generic advice."
    )


def build_prompt(query: str, mode: str, role: str, source_passage: str, context: str | None = None) -> str:
    """Build the full prompt for a given mode."""
    mode_normalized = mode.replace("_", "-").lower()

    if mode_normalized == "concept-guide":
        system = get_concept_guide_prompt(query)
    elif mode_normalized == "problem-navigator":
        system = get_problem_navigator_prompt(query)
    elif mode_normalized == "submission-validator":
        system = get_submission_validator_prompt(query)
    elif mode_normalized == "quiz-generator":
        system = get_quiz_generator_prompt(query)
    elif mode_normalized == "assignment-grader":
        system = get_assignment_grader_prompt(query, context or "")
    elif mode_normalized == "exam-generator":
        system = get_exam_generator_prompt(query)
    elif mode_normalized == "adaptive-feedback":
        system = get_adaptive_feedback_prompt(query)
    elif mode_normalized == "learning-insights":
        system = get_learning_insights_prompt(query)
    else:
        system = (
            f"Question: {query}\n\n"
            "Answer using the document context provided. "
            "Be clear and direct. Cite [Page X] for specific facts."
        )

    context_label = "Document Context"
    if mode_normalized == "quiz-generator":
        context_label = "Evidence Context"

    return f"{system}\n\n{context_label}:\n{source_passage}\n"
