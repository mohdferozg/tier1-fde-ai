"""Retrieve the most relevant chunks for a query from Supabase."""
import os
from dotenv import load_dotenv
import psycopg2

from embedder import embed_text

load_dotenv()


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """Find the top-k most similar chunks to the query.

    Returns a list of dicts with keys: id, content, metadata, similarity.
    Similarity is 0..1 (higher = more similar).
    """
    if not query or not query.strip():
        return []

    # Embed the query
    query_embedding = embed_text(query)
    vector_literal = "[" + ",".join(str(x) for x in query_embedding) + "]"

    db_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # Use pgvector's <=> operator (cosine distance). 
    # 1 - distance = similarity (higher is more similar).
    cur.execute(
        """
        SELECT id, content, metadata, 1 - (embedding <=> %s::vector) AS similarity
        FROM documents
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (vector_literal, vector_literal, top_k),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {"id": row[0], "content": row[1], "metadata": row[2], "similarity": row[3]}
        for row in rows
    ]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python retriever.py '<query>'")
        sys.exit(1)

    query = sys.argv[1]
    print(f"Query: {query}\n")
    results = retrieve(query, top_k=3)

    for i, r in enumerate(results, 1):
        print(f"Result {i} (id={r['id']}, similarity={r['similarity']:.4f}):")
        print(f"  {r['content'][:200]}...")
        print()