"""Text chunking utility for retrieval preprocessing.

Utilizes RecursiveCharacterTextSplitter to segment documents into digestible,
overlapping text chunks.
"""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_document(
    text: str, chunk_size: int = 500, chunk_overlap: int = 50
) -> list[str]:
    """Splits a document's text into small overlapping chunks.

    Args:
        text: The source document text to split.
        chunk_size: Maximum character count per chunk.
        chunk_overlap: Overlapping character count between adjacent chunks.

    Returns:
        A list of non-empty text chunks.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    chunks = splitter.split_text(text)
    return [c.strip() for c in chunks if c.strip()]
