"""Split a long text into overlapping chunks for embedding.

Chunk size: 800 chars. Overlap: 100 chars. Both can be tuned later.
"""


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks.

    Args:
        text: The full document text.
        chunk_size: Target characters per chunk.
        overlap: Characters shared between consecutive chunks.

    Returns:
        List of chunk strings.
    """
    if not text or not text.strip():
        return []

    # Clean up excessive whitespace
    text = " ".join(text.split())

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks