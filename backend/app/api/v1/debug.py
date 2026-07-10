"""Debug endpoints — development only.

GET /api/v1/debug/mode-prompt?mode=quiz&role=student
  Returns the exact system prompt that would be sent to the LLM for a given mode.
  Use this to verify prompt selection is working before testing in the UI.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.factshield.pipeline import build_prompt

router = APIRouter()

# Dummy values used to render the prompt template for inspection
_DUMMY_QUERY = "[student's question goes here]"
_DUMMY_DOC = "[document chunks would appear here]"
_DUMMY_CONTEXT = "[extra context e.g. student answer for grader]"

# All 9 known mode keys
KNOWN_MODES = [
    "explain",
    "quiz",
    "check",
    "find",
    "summarise",
    "grade",
    "explain_concept",
    "generate_test",
    "insights",
]


@router.get("/mode-prompt")
async def mode_prompt_debug(
    mode: str = Query(..., description="Mode key e.g. quiz, explain, summarise"),
    role: str = Query("student", description="Role: student or teacher"),
) -> JSONResponse:
    """Return the exact system prompt that would be sent to the LLM for the given mode.

    Example:
        GET /api/v1/debug/mode-prompt?mode=quiz
        GET /api/v1/debug/mode-prompt?mode=grade&role=teacher
    """
    prompt = build_prompt(
        query=_DUMMY_QUERY,
        mode=mode,
        role=role,
        source_passage=_DUMMY_DOC,
        context=_DUMMY_CONTEXT,
    )

    unknown = mode not in KNOWN_MODES
    return JSONResponse(
        content={
            "mode": mode,
            "role": role,
            "known_mode": not unknown,
            "warning": f"Unknown mode '{mode}' — will use generic fallback prompt." if unknown else None,
            "known_modes": KNOWN_MODES,
            "prompt": prompt,
            "prompt_line_count": prompt.count("\n") + 1,
        }
    )
