# FDE Tier-1 Project — Daily Metrics Journal

One number, per day, from the system I built. Not what I learned — what I measured.

---

## Day 3 — 2026-10-25 (Gemini integration)

**Number:** 28 items validated (14 skills, 7 experiences, 7 projects) from a 11,920-char CV. 4/4 endpoint scenarios returned correct status codes (200/400/422/503). 0/10 Pydantic validation failures.

**What I changed because of it:** Fixed circular import (models.py extraction) and added 100-char min-length check on extracted text.

---

## Day 4 — 2026-11-03 (Angular UI)

**Number:** 28 items rendered as UI cards (16 skills, 7 experiences, 7 projects). E2E upload-to-render time: ~8s. CORS blocked 1/1 requests before fix; 0/1 after.

**What I changed because of it:** Added CORS middleware to FastAPI. Built Angular UI with file upload, loading spinner, error handling, and structured card rendering.

## Day 5 — 2026-11-03 (Deployment)

**Number:** Live URLs deployed. Backend response time: ~400ms (warm) / ~50s (cold start on Render free tier). Frontend build time on Vercel: 1m 12s. 2/2 deployment targets successful.

**What I changed because of it:** Configured `Procfile` and `.python-version` for Render. Set `allow_origin_regex` in FastAPI to permit Vercel domains. Hardcoded the Render API URL into the Angular `fetch` call.

## Day 6 — 2026-11-11 (RAG pipeline)

**Number:** 17 chunks ingested from 11,920-char CV (768-dim embeddings). Retrieval similarity: 0.62–0.70 top-3. Generation: 2/2 grounded answers with correct citations. Hallucination defense: 1/1 correct refusal. Model fallback: 1/3 calls needed fallback (gemini-3.8-flash → gemini-3.5-flash).

**What I changed because of it:** Set embedding output_dimensionality=768 to match the database column. Added a 5-model fallback chain to `generator.py` to survive Gemini model deprecations and 503 spikes.

## Day 7 — 2026-11-12 (RAG Chat UI)

**Number:** 2/2 successful RAG queries rendered in UI with correct source citations. End-to-end time: ~4.5s (retrieval + generation + render). CORS blocked 1/1 requests before fix; 0/1 after.

**What I changed because of it:** Built an Angular chat interface. Changed CORS policy in `main.py` to explicitly allow `localhost:4200`. Rendered source chunk IDs as visual badges under the AI responses.

## Day 8 — 2026-11-11 (RAG Deployment)

**Number:** 2/2 deployment targets successful (Render backend + Vercel frontend). Live RAG query: 200 OK, grounded answer with correct sources. Cold start time: ~50s.

**What I changed because of it:** Generated `requirements.txt` to fix the Render build. Configured `allow_origin_regex` for Vercel. Hardcoded the live Render URL into the Angular fetch call.

## Day 9 — 2026-11-11 (RAG Evaluation)

**Number:** 10-question eval. Retrieval accuracy: 70% (7/10). Answer accuracy: 60% (6/10). Avg latency: 24.69s. Fallback chain saved 7/10 queries from 504 errors.

**What I changed because of it:** Built a golden dataset and evaluation script. Added a 30s HTTP timeout to `generator.py`. Improved eval matching with text normalization.