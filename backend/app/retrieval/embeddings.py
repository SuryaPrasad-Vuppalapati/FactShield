"""Embeddings generation utility using SentenceTransformers.

Wraps the sentence-transformers library to compute vector representations of
text chunks for semantic similarity search.
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Lazily load the SentenceTransformer model.

    Returns:
        The instantiated SentenceTransformer model.
    """
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    return _model


def embed_text(text: str) -> list[float]:
    """Generates an embedding vector for a single text string.

    Args:
        text: The string to embed.

    Returns:
        A list of floats representing the embedding vector.
    """
    vector = get_model().encode(text)
    # Convert numpy array to list of floats
    if isinstance(vector, np.ndarray):
        return [float(x) for x in vector.tolist()]
    return [float(x) for x in vector]


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Generates embedding vectors for a batch of texts.

    Args:
        texts: A list of text strings.

    Returns:
        A list of lists of floats.
    """
    vectors = get_model().encode(texts, batch_size=32)
    result = []
    for vec in vectors:
        if isinstance(vec, np.ndarray):
            result.append([float(x) for x in vec.tolist()])
        else:
            result.append([float(x) for x in vec])
    return result
