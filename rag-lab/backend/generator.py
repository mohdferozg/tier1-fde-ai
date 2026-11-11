"""Generate a grounded answer from retrieved chunks using Gemini."""
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

from retriever import retrieve

load_dotenv()


SYSTEM_PROMPT = """You are a helpful assistant answering questions about a candidate's CV.

STRICT RULES:
1. Answer ONLY using the provided context chunks. Do NOT use outside knowledge.
2. If the answer is not in the context, say: "I don't have enough information in the provided documents to answer that."
3. Cite the chunk ID(s) you used at the end of your answer in the format: [Sources: chunk 4, chunk 8]
4. Be concise. Cite directly from the chunks.

Context chunks:
{context}
"""


def _get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    return genai.Client(api_key=api_key)


def _get_model():
    return os.getenv("GEMINI_MODEL", "gemini-flash-latest")


def answer(query: str, top_k: int = 3) -> dict:
    """Full RAG pipeline: query → retrieve → generate grounded answer.

    Returns:
        dict with keys: answer (str), sources (list of chunk ids), chunks (list of dicts)
    """
    # Step 1: Retrieve relevant chunks
    chunks = retrieve(query, top_k=top_k)

    if not chunks:
        return {
            "answer": "No relevant chunks found in the database.",
            "sources": [],
            "chunks": [],
        }

    # Step 2: Build context from chunks
    context = "\n\n".join(
        f"[Chunk {c['id']}]\n{c['content']}" for c in chunks
    )

    # Step 3: Build the prompt
    prompt = SYSTEM_PROMPT.format(context=context)
    full_prompt = f"{prompt}\n\nQuestion: {query}"

    # Step 4: Call Gemini
    client = _get_client()
    primary_model = _get_model()

    # Try multiple models in order. First success wins.
    fallback_models = [
        primary_model,
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ]
    # Deduplicate while preserving order
    seen = set()
    fallback_models = [m for m in fallback_models if not (m in seen or seen.add(m))]

    errors = []
    response = None
    working_model = None
    for candidate in fallback_models:
        try:
            response = client.models.generate_content(
                model=candidate,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                    temperature=0.2,
                ),
            )
            working_model = candidate
            print(f"[INFO] Responded using: {candidate}")
            break
        except Exception as e:
            errors.append(f"{candidate}: {type(e).__name__}: {str(e)[:80]}")

    if response is None:
        raise RuntimeError(f"All Gemini models failed. Errors: {' | '.join(errors)}")

    answer_text = response.text.strip() if response.text else ""
    sources = [c["id"] for c in chunks]

    return {
        "answer": answer_text,
        "sources": sources,
        "chunks": chunks,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python generator.py '<question>'")
        sys.exit(1)

    query = sys.argv[1]
    print(f"Question: {query}\n")

    result = answer(query)

    print("Answer:")
    print(result["answer"])
    print()
    print(f"Sources: {result['sources']}")