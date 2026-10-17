"""Extract text from a PDF file-like object.

This module provides a single function, extract_text(), which accepts an
open binary stream (anything with .read() and .seek() — a file handle, a
BytesIO, FastAPI's UploadFile.file) and returns the concatenated text of
every page.

Failures raise specific exceptions so callers can map them to appropriate
responses:

    FileNotFoundError    - the source stream is not readable
    PdfExtractionError   - the PDF is invalid, encrypted, or has no text
"""

from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from exceptions import PdfExtractionError


def extract_text(pdf_source: BinaryIO) -> str:
    """Return all extractable text from a PDF file-like object.

    Args:
        pdf_source: An open binary stream positioned at the start of a PDF.

    Returns:
        A single string containing the concatenated text of every page,
        separated by newlines.

    Raises:
        PdfExtractionError: If the stream cannot be parsed as a PDF, the
            PDF is encrypted, or no page contains extractable text.
    """
    # --- Step 1: try to parse ---
    try:
        reader = PdfReader(pdf_source)
    except PdfReadError as e:
        raise PdfExtractionError(f"Not a valid PDF: {e}") from e

    # --- Step 2: check for encryption ---
    if reader.is_encrypted:
        raise PdfExtractionError("PDF is encrypted and cannot be read")

    # --- Step 3: iterate pages, coalescing None to empty string ---
    all_text = ""
    for page in reader.pages:
        text = page.extract_text() or ""
        all_text += text + "\n"

    # --- Step 4: ensure we actually got something ---
    if not all_text.strip():
        raise PdfExtractionError(
            "PDF contains no extractable text (image-only or empty)"
        )

    return all_text