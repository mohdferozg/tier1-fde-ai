# Day 6 — RAG Pipeline: Ingestion, Retrieval, Generation

**Date:** 2026-11-11
**Focus:** Build a full Retrieval-Augmented Generation pipeline from scratch using Supabase (pgvector), Gemini embeddings, and Gemini generation.

## What was built
- `chunker.py` — Splits text into 800-char chunks with 100-char overlap.
- `embedder.py` — Generates 768-dim embeddings via `gemini-embedding-001`.
- `ingest.py` — Full pipeline: PDF → text → chunks → embeddings → Supabase.
- `retriever.py` — Semantic search: query → embed → similarity search → top-k chunks.
- `generator.py` — Grounded generation: chunks → prompt → Gemini → cited answer.
- `main.py` — FastAPI wrapper exposing `POST /query`.

## The architecture
The pipeline follows the standard RAG pattern:

1. **Ingestion:** `pypdf` extracts text from a PDF → `chunker.py` splits into overlapping chunks → `embedder.py` generates 768-dim vectors → `psycopg2` inserts into Supabase `documents` table.
2. **Retrieval:** user query → `embedder.py` → pgvector `<=>` cosine distance search → top-k chunks returned with similarity scores.
3. **Generation:** retrieved chunks formatted into a strict prompt → Gemini → grounded answer with `[Sources: chunk N]` citations.

## What was proven
| Test | Result |
|------|--------|
| Ingestion | 17 chunks from 11,920-char CV inserted into `documents` table |
| Retrieval (Angular query) | Top 3 chunks with similarity 0.62–0.70, all about Angular/frontend |
| Retrieval (banking query) | Top 3 chunks with similarity 0.61–0.65, all about banking experience |
| Generation (Angular query) | Grounded answer with correct version numbers and citations |
| Generation (banking query) | Clean list of PNC, ENBD, Maybank, SBI with per-line citations |
| Hallucination defense | "Favorite color" query correctly returned "I don't have enough information in the provided documents to answer that." |
| Model fallback chain | `gemini-3.5-flash` handled a 503 from `gemini-3.8-flash` transparently |

## What broke, and what we learned
**1. Embedding dimension mismatch (3072 vs 768)**
`gemini-embedding-001` returns 3072-dim vectors by default. Our database column is `vector(768)`. Fix: `EmbedContentConfig(output_dimensionality=768)` in the embedder.

Lesson: the database column dimension and the model output dimension must match exactly. Every RAG tutorial hits this once.

**2. Rolling model alias not supported on v1beta API**
`gemini-flash-latest` returned 404 on the new `google-genai` SDK (3.1.0). The `v1beta` API doesn't support rolling aliases. Fix: use specific model names (`gemini-3.8-flash`, `gemini-3.5-flash`, etc.) and add a fallback chain in `generator.py`.

Lesson: the SDK version determines the API endpoint, which determines which model names work. Always use explicit version numbers and a fallback chain in production.

**3. Gemini model deprecation for new users**
`gemini-2.5-flash` returned 404 with a specific message: "no longer available to new users. Please update your code to use models/gemini-3.8-flash." Fix: fallback chain includes both deprecated and current models.

Lesson: hardcoding one model name guarantees breakage. The `.env` + fallback chain pattern is the durable answer.

**4. CORS middleware**
`main.py` includes `allow_origins=["*"]` for the RAG API because we haven't built a frontend yet. The cv-analyzer uses a stricter origin list because it has a deployed Angular frontend. Different contexts, different policies.

## What was measured (journal entry)
- 17 chunks ingested from 11,920-char CV (800-char chunks, 100-char overlap)
- Retrieval similarity: 0.62–0.70 on top-3
- Embedding dimension: 768
- Fallback chain: 1/3 model calls required fallback (gemini-3.8 → gemini-3.5)
- Hallucination test: 1/1 refused correctly

## Tomorrow (Day 7)
Build a simple HTML/JS chat interface (like the cv-analyzer UI) that talks to the RAG API. Then deploy the RAG app to Render + Vercel so it's a live portfolio artifact.