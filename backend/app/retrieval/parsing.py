"""Utility functions for parsing different document formats (PDF, DOCX, PPTX, TXT)."""

from __future__ import annotations

from io import BytesIO

from markitdown import MarkItDown


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Extract markdown text from uploaded file bytes using MarkItDown.

    Args:
        file_bytes: The raw file bytes.
        filename: The filename with extension.

    Returns:
        The extracted markdown content.
    """
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    
    try:
        md = MarkItDown()
        stream = BytesIO(file_bytes)
        # MarkItDown uses the extension to determine the file type parser
        result = md.convert_stream(stream, file_extension=f".{ext}")
        return result.text_content.strip()
    except Exception as e:
        # Fallback to raw text decoding if markitdown fails or format is exotic
        try:
            return file_bytes.decode('utf-8').strip()
        except UnicodeDecodeError:
            try:
                return file_bytes.decode('latin-1').strip()
            except Exception:
                raise ValueError(f"File could not be parsed by MarkItDown and is not readable text. Original error: {e}")
