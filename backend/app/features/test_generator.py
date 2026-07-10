"""Test Generator feature implementation.

Generates practice questions and answers from course material, verifying the
factuality of each generated answer key against the source text.
"""

from __future__ import annotations

import json
from typing import Any

from google import genai

from app.config import settings
from app.factshield.grounding import check_grounding


async def generate_practice_test(
    source_passage: str, num_questions: int = 3
) -> dict[str, Any]:
    """Generate question/answer pairs and score answer factuality.

    Args:
        source_passage: Reference text material to base questions on.
        num_questions: Count of questions to generate.

    Returns:
        A dictionary with a list of generated test items, their scores, and raw text.
    """
    items = []
    response_text = ""

    if settings.gemini_api_key:
        try:
            client = genai.Client(api_key=settings.gemini_api_key)
            prompt = (
                f"Generate exactly {num_questions} questions from the reference text below. "
                "Each question should test a specific, concrete concept — not ask students to summarise the document. "
                "Vary the difficulty and question type (multiple choice or short answer).\n\n"
                "Use this exact format for each question (required for parsing):\n"
                "**Question 1:** [question text]\n"
                "*Correct Answer:* [answer]\n\n"
                "**Question 2:** [question text]\n"
                "*Correct Answer:* [answer]\n\n"
                f"Reference text:\n{source_passage}"
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            response_text = response.text or ""
            
            import re
            pattern = re.compile(
                r"\*\*Question\s+\d+:\*\*(.*?)(?:\*Correct Answer:\*|\*Answer:\*)\s*(.*?)(?=\*\*Question\s+\d+:|$)",
                re.DOTALL | re.IGNORECASE
            )
            matches = pattern.findall(response_text)
            for q_text, ans_text in matches:
                q = q_text.strip()
                ans = ans_text.strip()
                if q and ans:
                    score = check_grounding(source_passage, ans)
                    items.append({
                        "question": q,
                        "correct_answer": ans,
                        "grounding_score": score
                    })
        except Exception:
            pass

    # Fallback if Gemini failed or key missing
    if not items:
        # Create dummy sentence completion questions
        sentences = [
            s.strip() for s in source_passage.split(".") if len(s.strip()) > 15
        ]
        fallback_text = []
        for idx, sentence in enumerate(sentences[:num_questions]):
            # Split sentence into two parts for a question
            words = sentence.split(" ")
            mid = len(words) // 2
            q = "Complete the statement: " + " ".join(words[:mid]) + "..."
            ans = sentence
            score = check_grounding(source_passage, ans)
            items.append(
                {
                    "question": q,
                    "correct_answer": ans,
                    "grounding_score": score,
                }
            )
            fallback_text.append(f"**Question {idx + 1}:** {q}\n*Correct Answer:* {ans}")
        response_text = "\n\n".join(fallback_text)

    return {"test_items": items, "text": response_text}
