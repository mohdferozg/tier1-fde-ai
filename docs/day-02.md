# Day 2 — Endpoint accepts PDF upload, returns extracted text

**Date:** 2026-10-19

**Focus:** Wire the tested `extract_text()` module into `POST /cv-analysis`. Replace the placeholder echo endpoint with real file upload handling. No LLM yet — this is plumbing.

## What was built

- `POST /cv-analysis` now accepts `multipart/form-data` with a `file` field (was JSON body)
- Handler validates the filename ends in `.pdf` → returns `400` on wrong extension
- Handler calls `extract_text(file.file)` → returns `422` on `PdfExtractionError`
- Handler returns `CVAnalysisResponse { filename, text_length, text }` on success
- Added `python-multipart` — required by FastAPI for file upload parsing

## The architecture

The endpoint now has three distinct failure modes, each mapped to a specific HTTP status:

| Input | HTTP Status | Response |
|-------|-------------|----------|
| Valid PDF | 200 OK | `{filename, text_length, text}` |
| Wrong extension (e.g. `.txt`) | 400 Bad Request | `"Expected a .pdf file, got: '...'"` |
| Valid extension, invalid content | 422 Unprocessable | `"Not a valid PDF: ..."` |
| Unexpected internal error | 500 Internal Server Error | `"Unexpected error while processing PDF: ..."` |

The endpoint is now a **contract** — not just "does something." Clients can distinguish bad input from bad file from server error.

## What was proven

| Test | Input | Status | Result |
|------|-------|--------|--------|
| Happy path | CV PDF (274 KB) | 200 | 11,920 chars extracted |
| Wrong extension | `wrong_file.txt` | 400 | Clear message |
| Double extension | `corrupted.pdf.txt` | 400 | Clear message |
| Corrupted content | `corrupted.pdf` | 422 | `"Not a valid PDF: ..."` |

The full endpoint behavior is verified end-to-end via Swagger UI.

## What broke, and what we learned

**1. `RuntimeError: Form data requires "python-multipart" to be installed`**

After changing the endpoint to accept `UploadFile`, Uvicorn crashed on startup. FastAPI's file upload support requires a companion package — `python-multipart` — that isn't bundled with FastAPI by default.

Fix: `pip install python-multipart`, then update `requirements.txt` and commit as a separate `chore:` commit.

Lesson: FastAPI keeps its base install small. Different features require different optional dependencies. When adding a new endpoint capability, expect an optional dependency install. Document it in `requirements.txt` and commit it separately from the code change.

**2. Windows file extension hiding**

When creating `corrupted.pdf` in Notepad, Windows actually saved it as `corrupted.pdf.txt` because the "show known file extensions" setting is off by default. The endpoint correctly rejected it as `wrong_file.txt` (400), which confused the test — the wrong file was created, but the endpoint's response was actually correct.

Fix: create test files via PowerShell (`"content" | Out-File -FilePath corrupted.pdf -Encoding ascii`), where filenames are exactly what you specify.

Lesson: always verify actual filenames with `Get-ChildItem`, not by reading Explorer's display. Windows hides extensions by default.

**3. The orphaned `# class Skill` block in main.py**

The original `main.py` had a commented-out class definition followed by two orphaned indented lines:

# class Skill(BaseModel):
    title: str
    description: str

Those lines would have been a SyntaxError if reached at runtime. They happened to not break because CVItem was defined immediately after. The Day 2 rewrite replaced the whole file, resolving this latent bug.

Lesson: commented-out code followed by indented lines is a persistent hazard. When touching a file with that shape, fix it, not just ignore it.

## Commit history

```text
0b9efa4  chore: add python-multipart dependency
af6595f  feat: change cv-analysis endpoint to accept PDF upload
bf332cb  docs: add day 1 engineering log
f18f348  test: add four-way failure mode coverage for pdf extractor
35003f2  feat: add PDF extraction module with structured error handling
```
## Tomorrow
Day 3: Bring Gemini back into the endpoint. The extractor is proven. The endpoint is proven. The only remaining piece is turning the extracted text into a structured CVAnalysis object via the LLM:

1. Write a prompt that instructs Gemini to produce { technicalSkills, experience, projects }

2. Use Gemini's structured output mode (JSON schema)

3. Validate the LLM's response against the CVAnalysis Pydantic model

4. Return the validated object (or a clear error if the LLM's output fails validation)

5. Handle the LLM-unavailable case — return a clear message, not a crash

6. Read model name from .env (no hardcoding)

The architectural point: today the endpoint accepts files and returns text. Tomorrow the endpoint accepts files and returns structured, validated data — the shape that the frontend actually needs.