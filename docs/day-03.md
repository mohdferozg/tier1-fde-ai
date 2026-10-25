# Day 3 — Gemini integration: text → validated CVAnalysis

**Date:** 2026-10-25

**Focus:** Wire Gemini into `POST /cv-analysis`. The endpoint goes from returning raw extracted text to returning a validated, structured `CVAnalysis` object.

## What was built

- `models.py` — Pydantic models extracted from `main.py` to break a circular import: `AnalyzeRequest`, `CVItem`, `CVAnalysis`, `CVAnalysisResponse`
- `llm_extractor.py` — new module with `extract_cv_data(cv_text) -> CVAnalysis`. Handles prompt construction, Gemini API call with fallback chain, markdown fence stripping, JSON parsing, and Pydantic validation.
- `LlmExtractionError` added to `exceptions.py`
- `main.py` — endpoint updated: extract PDF text → call Gemini → return validated `CVAnalysis`
- `scripts/test_llm_extractor.py` — isolation test for the LLM module

## The architecture

The endpoint now has four distinct failure modes:

| Failure | HTTP Status | Response |
|---------|-------------|----------|
| Wrong file extension | 400 Bad Request | `"Expected a .pdf file, got: '...'"` |
| Invalid PDF content | 422 Unprocessable | `"Not a valid PDF: ..."` |
| Extracted text too short (<100 chars) | 422 Unprocessable | `"Extracted text is too short to be a CV (...)"` |
| LLM unavailable or invalid output | 503 Service Unavailable | `"LLM extraction failed: ..."` |
| Valid CV | 200 OK | `CVAnalysisResponse { filename, text_length, analysis }` |

**Model fallback chain:** the LLM extractor tries a primary model first (`gemini-flash-latest` from `.env`), then falls back through `gemini-flash-lite-latest`, `gemini-3.7-flash`, `gemini-3.5-flash` if the primary fails with 503 or 404. Only raises `LlmExtractionError` if all four fail.

## What was proven

| Test | Input | Status | Result |
|------|-------|--------|--------|
| Happy path | CV PDF (274 KB) | 200 | 14 skills, 7 experiences, 7 projects — all validated |
| Wrong extension | `wrong.txt.txt` | 400 | Clear error message |
| Corrupted content | `corrupted.pdf` (text named .pdf) | 422 | `"Extracted text is too short to be a CV (11 chars)"` |
| LLM unavailable | CV PDF, `GEMINI_API_KEY` commented out | 503 | `"LLM extraction failed: GEMINI_API_KEY not set"` |

Extraction time: ~5–15 seconds (dominated by Gemini API latency). Text length: 11,920 chars, identical to the extraction verified on Day 1.

## What broke, and what we learned

**1. Circular import between `main.py` and `llm_extractor.py`**

`main.py` imported `extract_cv_data` from `llm_extractor`, and `llm_extractor` imported `CVAnalysis` from `main`. When `main` was imported first, it began loading, hit line 13 (`from llm_extractor import ...`), which triggered `llm_extractor` to load, which then tried to import `CVAnalysis` from `main` — but `main` was still on line 13, so `CVAnalysis` didn't exist yet. `ImportError`.

Fix: extracted `AnalyzeRequest`, `CVItem`, `CVAnalysis`, `CVAnalysisResponse` into `models.py`. Both `main.py` and `llm_extractor.py` now import from `models.py`. No cycle.

Lesson: circular imports in Python are structural — two modules that need each other's definitions can't both import at the top. The correct fix is to move shared definitions into a third module, not to lazy-import or use `if TYPE_CHECKING` (those are hacks). `models.py` is now the single source of truth for data shapes.

**2. Corrupted PDF returned 200 OK with empty analysis**

Uploading a 19-byte text file named `.pdf` produced `{technicalSkills: [], experience: [], projects: []}` with HTTP 200. `extract_text()` didn't raise because the string content was 11 chars (non-empty). Then Gemini received 11 chars of garbage and correctly returned empty lists — no schema violation, but no useful data either.

Fix: added a minimum-length check in `main.py` after extraction: `if len(text.strip()) < 100: raise HTTPException(422, ...)`. A real CV has thousands of characters. Any file producing less than 100 is not a CV.

Lesson: schema validation isn't enough. A "valid" `CVAnalysis` with empty lists passes Pydantic but is semantically useless. Content validation must happen before (or in addition to) schema validation.

**3. Model fallback chain obviated the naive "force a 503" test**

When we changed `GEMINI_MODEL` to a nonexistent name, the endpoint still returned 200 — because the fallback chain tried the failing primary, then succeeded on `gemini-flash-lite-latest`. This is correct behavior, but the break test needed adjustment: to truly force a 503, we had to comment out `GEMINI_API_KEY` entirely, so `_get_client()` raises `LlmExtractionError` before any API call.

Lesson: testing fallback chains requires breaking the fallback source (auth), not just the primary. A well-designed fallback chain makes single-failure scenarios transparent — which is the goal, but means break tests need to target deeper failure modes.

## Commit history

```text
<hash-3>  feat: integrate Gemini into cv-analysis endpoint
18a66be   docs: add day 2 engineering log
0b9efa4   chore: add python-multipart dependency
af6595f   feat: change cv-analysis endpoint to accept PDF upload
```
Tomorrow
Day 4: Add the frontend. Angular UI that:

Offers a file-upload control for CV PDFs

Sends the file to POST /cv-analysis

Renders the returned CVAnalysis as structured cards/tables (skills, experience, projects)

Handles error states (400, 422, 503) with user-friendly messages

Displays a loading state during the 5–15s Gemini call