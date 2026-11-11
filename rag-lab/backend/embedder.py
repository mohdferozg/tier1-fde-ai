"""Generate embeddings using Gemini's text-embedding model."""
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


def _get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    return genai.Client(api_key=api_key)


def embed_text(text: str) -> list[float]:
    """Generate a 768-dim embedding for the given text."""
    client = _get_client()
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=768),
    )
    return response.embeddings[0].values


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in one API call."""
    if not texts:
        return []
    client = _get_client()
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=texts,
        config=types.EmbedContentConfig(output_dimensionality=768),
    )
    return [emb.values for emb in response.embeddings]