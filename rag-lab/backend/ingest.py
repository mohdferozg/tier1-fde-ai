"""Ingest a PDF: extract text, chunk it, embed chunks, store in Supabase."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import psycopg2
from pypdf import PdfReader

from chunker import chunk_text
from embedder import embed_batch

load_dotenv()


def extract_pdf_text(pdf_path: str) -> str:
    """Read all text from a PDF."""
    reader = PdfReader(pdf_path)
    all_text = ""
    for page in reader.pages:
        text = page.extract_text() or ""
        all_text += text + "\n"
    return all_text


def store_chunks(chunks: list[str], embeddings: list[list[float]], source: str):
    """Insert chunks and their embeddings into the documents table."""
    db_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    for chunk, embedding in zip(chunks, embeddings):
        # Convert Python list to pgvector literal format: [0.1, 0.2, ...]
        vector_literal = "[" + ",".join(str(x) for x in embedding) + "]"
        cur.execute(
            """
            INSERT INTO documents (content, metadata, embedding)
            VALUES (%s, %s, %s)
            """,
            (chunk, f'{{"source": "{source}"}}', vector_literal),
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"Inserted {len(chunks)} chunks into documents table")


def ingest_pdf(pdf_path: str):
    """Full pipeline: PDF → text → chunks → embeddings → database."""
    print(f"Reading PDF: {pdf_path}")
    text = extract_pdf_text(pdf_path)
    print(f"Extracted {len(text)} characters")

    print(f"Chunking (size=800, overlap=100)...")
    chunks = chunk_text(text)
    print(f"Generated {len(chunks)} chunks")

    if not chunks:
        print("No chunks generated. Aborting.")
        return

    print(f"Generating embeddings (batch of {len(chunks)})...")
    embeddings = embed_batch(chunks)
    print(f"Generated {len(embeddings)} embeddings, dimension: {len(embeddings[0])}")

    print(f"Storing in Supabase...")
    store_chunks(chunks, embeddings, source=Path(pdf_path).name)

    print("Ingestion complete")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <path-to-pdf>")
        sys.exit(1)
    ingest_pdf(sys.argv[1])