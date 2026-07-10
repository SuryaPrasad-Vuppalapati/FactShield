"""Token optimization strategies for RAG.

Implements query decomposition, response length constraints, and early stopping
to reduce token consumption while maintaining answer quality.
"""

from __future__ import annotations

import re


def decompose_query(query: str) -> list[str]:
    """Break down multi-part questions into individual sub-queries.
    
    Examples:
        "What is deep learning and how is it used in NLP?" -> 
        ["What is deep learning?", "How is deep learning used in NLP?"]
    
    Args:
        query: The user's question
        
    Returns:
        List of decomposed queries (or single query if not decomposable)
    """
    # Pattern: "... and ..."
    and_parts = re.split(r'\s+and\s+', query, maxsplit=3)
    if len(and_parts) > 1 and len(and_parts) <= 3:
        # Looks decomposable
        return [q.strip() for q in and_parts if q.strip()]
    
    # Pattern: "... How/What/When/Why ...", comma-separated
    if ',' in query:
        parts = [q.strip() for q in query.split(',') if q.strip()]
        if 2 <= len(parts) <= 3:
            return parts
    
    # Single query
    return [query]


def constrain_response_length(mode: str) -> int:
    """Get max tokens for response based on feature mode.
    
    Args:
        mode: The feature mode (document, academic, copilot, web, etc.)
        
    Returns:
        Maximum token count for response
    """
    # Educational modes should be concise
    mode_constraints = {
        "concept-guide": 600,
        "problem-navigator": 1100,
        "submission-validator": 1200,
        "quiz-generator": 1600,
        "assignment-grader": 280,
        "exam-generator": 420,
        "adaptive-feedback": 300,
        "learning-insights": 320,
        "document": 220,
        "academic": 240,
        "copilot": 200,
        "web": 200,
    }
    
    return mode_constraints.get(mode, 220)


def summarize_chunks(chunks: list[str], max_length: int = 1000) -> str:
    """Combine and optionally summarize chunks to control context size.
    
    Args:
        chunks: List of retrieved chunks
        max_length: Maximum total character length
        
    Returns:
        Combined and truncated chunks
    """
    combined = "\n".join(chunks)
    
    if len(combined) <= max_length:
        return combined
    
    # If too long, return first max_length chars to preserve context
    # In production, you'd use an extractive summarizer here
    return combined[:max_length] + "\n[... truncated for token efficiency ...]"


def should_skip_generation(cache_confidence: float, threshold: float = 0.85) -> bool:
    """Determine if cached result is confident enough to skip generation.
    
    Args:
        cache_confidence: The confidence score of the cached result (0-1)
        threshold: Minimum confidence to skip generation
        
    Returns:
        True if confident cached result should be used without regeneration
    """
    return cache_confidence >= threshold


def estimate_token_usage(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Rough estimate of token count for cost tracking.
    
    Uses ~1 token per 4 characters for English text (varies by model).
    
    Args:
        text: The text to estimate tokens for
        model: The model to estimate for (affects token ratio)
        
    Returns:
        Estimated token count
    """
    # GPT-3.5-turbo: ~1 token per 4 chars on average
    # GPT-4: similar, but more efficient on code
    char_ratio = 4.0
    
    # Adjust for code/special content
    if any(marker in text for marker in ['```', 'def ', 'function', 'import']):
        char_ratio = 3.5
    
    return max(1, len(text.encode('utf-8')) // int(char_ratio))
