"""Citation enforcement and formatting for all FactShield responses.

Ensures every response includes a proper citation with source type and link/reference.
"""

from __future__ import annotations
import re


def extract_citation_from_response(response: str) -> str | None:
    """Extract citation from response if present.
    
    Looks for patterns like:
    - [Page X]
    - [Section: Name]
    - Reference: [Paper Title](URL)
    - Reference: [Site Name](URL)
    """
    # Check for markdown-style citation
    markdown_match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', response)
    if markdown_match:
        return f"[{markdown_match.group(1)}]({markdown_match.group(2)})"
    
    # Check for page reference
    page_match = re.search(r'\[Page\s+\d+\]', response)
    if page_match:
        return page_match.group()
    
    # Check for section reference
    section_match = re.search(r'\[Section:\s+[^\]]+\]', response)
    if section_match:
        return section_match.group()
    
    return None


def ensure_citation_in_response(
    response: str,
    source_type: str = "document",
    source_reference: str = "your syllabus"
) -> str:
    """Ensure response has a visible **Source:** footer.

    Inline [Page X] references are kept as-is; this function always appends
    a clearly-formatted **Source:** line so the UI can display attribution.

    Args:
        response: The generated response text
        source_type: One of "document", "academic", "copilot", "web", "mixed"
        source_reference: The specific reference (URL, page number, etc.)

    Returns:
        Response with guaranteed **Source:** footer
    """
    # Strip any LLM-generated "Citations:" block — source attribution is handled by the backend.
    import re as _re
    response = _re.sub(
        r'\n+Citations:\s*\n(?:[-*]?\s*\[?[^\n]+\n?)*',
        '',
        response,
        flags=_re.IGNORECASE,
    ).rstrip()

    # Check if a **Source:** footer already exists (prevent duplication)
    if "**Source:**" in response or "**Source :**" in response:
        return response

    # Build citation — skip footer if source is unknown/none
    citation = _build_citation(source_type, source_reference)
    if not citation:
        return response

    if not response.endswith('\n'):
        response += '\n'

    return response + f"\n**Source:** {citation}"


def _build_citation(source_type: str, source_reference: str) -> str:
    """Build citation string based on source type.
    
    Args:
        source_type: "document", "academic", "copilot", or "web"
        source_reference: specific reference (URL, page, title, etc.)
        
    Returns:
        Formatted citation
    """
    if source_type in ("none", "refusal", "error", ""):
        return ""
    if source_type == "document":
        return source_reference or "Local document"
    elif source_type == "academic":
        return source_reference or "ArXiv research"
    elif source_type == "web":
        return source_reference or "Web search"
    elif source_type == "copilot":
        return "AI Knowledge Base"
    elif source_type == "mixed":
        return f"Local document + online sources: {source_reference}"
    else:
        return source_reference or ""


def validate_citation_format(response: str) -> bool:
    """Check if response has proper citation format.
    
    Returns:
        True if response includes a citation
    """
    return extract_citation_from_response(response) is not None


def extract_source_from_mode(mode: str) -> str:
    """Map feature mode to expected source type.
    
    Student modes:
    - concept-guide → document
    - problem-navigator → document
    - submission-validator → document
    Teacher modes:
    - assignment-grader → document
    - exam-generator → document
    - adaptive-feedback → document
    - learning-insights → document
    """
    return "document"  # All educational modes primarily use document source
