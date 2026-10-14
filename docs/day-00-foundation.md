# Day 1 — Environment, Git foundation, first LLM call

**Date:** 2026-10-04
**Focus:** Establish a durable engineering environment and prove the full stack works end to end.

## What was built

- FastAPI backend scaffold with two functional endpoints
- Pydantic models defining the API contracts
- A pinned, reproducible Python environment
- Verified Gemini connectivity from Python
- A Git repository with clean, atomic history

## The API contract

Defined in `cv-analyzer/backend/main.py`:

```
POST /analyze
  body: { "name": str }
  returns: { "message": "Hello <name>" }

POST /cv-analysis
  body: CVAnalysis
  returns: CVAnalysis (echo for now)
```

Where `CVAnalysis` composes three lists of the same shape:

```python
class CVItem(BaseModel):
    title: str
    description: str

class CVAnalysis(BaseModel):
    technicalSkills: list[CVItem]
    experience: list[CVItem]
    projects: list[CVItem]
```

The key mental model established: **a Pydantic model is a data contract + validation rules + a Python object representation.** The request object is an *instance* of that model, created after FastAPI validates the incoming body.

## What was proven

| Layer | Proof |
|---|---|
| Python environment | `sys.executable` resolves inside `.venv` |
| FastAPI | `/` returns the health message; `/docs` renders |
| Pydantic validation | Nested validation errors report the exact path |
| Secrets handling | `.env` exists on disk, `git status` shows nothing |
| Gemini connectivity | `Response text: pong` from a live API call |
| Git hygiene | `git check-ignore` confirms `.env`, `.venv`, PDF are excluded |

## What broke, and what we learned

Several real failures shaped the setup.

**1. Git repository was initialized one level too high.**
The original repo root was `FDE_TRACK_CHATGPT/` instead of `tier1-fde-ai/`. Solution: relocate the project out of OneDrive entirely (to `C:\dev\`) and reinitialize Git at the correct root. Nothing was lost because no commits had been made yet.

**2. `.gitignore` did not cover `.env`.**
Before creating the API key file, `git check-ignore -v .env` was run. It printed nothing — meaning Git would have tracked the file. A `.gitignore` was written and verified with `git check-ignore` **before** the secret was placed on disk.

Lesson: verify the ignore rule with `git check-ignore`, not by eyeballing the file.

**3. `requirements.txt` was written as UTF-16 by PowerShell.**
`pip freeze > requirements.txt` on Windows PowerShell 5.x produces a UTF-16 file with BOM. Git classified it as binary and showed `Bin 1220 -> 577 bytes` in diffs. Solution: regenerate with Python writing UTF-8 directly, and add a `.gitattributes` file to enforce consistent line endings repo-wide.

Lesson: never use PowerShell's `>` redirect for files Git will track.

**4. The Gemini key format was different than expected.**
Google AI Studio now issues keys in the form `AQ.Ab8RN6...` (53 characters) rather than the legacy `AIzaSy...` (39 characters). The `google-genai` SDK accepts both. We initially suspected the key was wrong because the format didn't match documentation; verified by making an actual API call, which succeeded.

Lesson: the shape of a credential is not the same as whether it works. Make the call.

**5. Model name changed.**
`gemini-2.5-flash` returned a `404 NOT_FOUND` with a specific recommendation to use `gemini-3.8-flash`. Reading the error literally resolved it in seconds.

Lesson: when an API error names a replacement, use it.

**6. PowerShell console misreports UTF-8 em-dashes.**
When displaying `README.md`, PowerShell printed `â€"` instead of `—`. `Format-Hex` confirmed the file itself was correct UTF-8 (`E2 80 94` bytes). The terminal's rendering was the problem, not the file.

Lesson: when you suspect encoding issues, check the bytes with `Format-Hex`, not the console display.

## Commit history

```
1542639 docs: add project readme with setup and run instructions
c6242f1 chore: add gitattributes for consistent line endings
5600116 chore: add backend setup diagnostic scripts
0e944ec chore: pin backend dependencies
67840ef feat: scaffold FastAPI backend with Pydantic analysis contracts
fb152ff chore: add gitignore for venv, caches, secrets, personal PDFs
```

Six commits so far, each atomic, each with a single "why."

## Tomorrow

Wire the PDF extraction pipeline into `POST /cv-analysis`:

1. Install `pypdf`
2. Build a `pdf_extractor` module — function, not script, with error handling
3. Test against the sample CV PDF
4. Accept an uploaded file in the endpoint
5. Send the extracted text to Gemini with a prompt producing the `CVAnalysis` structure
6. Validate the LLM's output with Pydantic before returning it

The critical architectural point: **the schema is the source of truth, not the LLM.** The model produces a candidate; the schema decides whether it's acceptable.