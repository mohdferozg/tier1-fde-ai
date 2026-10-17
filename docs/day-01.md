# Day 1 — PDF extraction module: built, tested, broken, fixed

**Date:** 2026-10-17

**Focus:** Turn the written-but-untested `pdf_extractor.py` module into a verified, committed component.

## What was built

- `pdf_extractor.py` — a function `extract_text(pdf_source: BinaryIO) -> str` that reads a PDF file-like object and returns the concatenated text of every page
- `exceptions.py` — a custom `PdfExtractionError` class, separate from `FileNotFoundError`
- `scripts/test_pdf.py` — happy-path diagnostic: runs the extractor against the sample CV PDF
- `scripts/test_pdf_breaks.py` — four-way break test: non-PDF bytes, empty PDF, blank-page PDF, encrypted PDF

## The architecture

- **Input:** `BinaryIO` only (file-like object). The caller adapts paths or bytes.
- **Failure modes handled:**
  1. Non-PDF input → `PdfExtractionError("Not a valid PDF: ...")`
  2. Encrypted PDF → `PdfExtractionError("PDF is encrypted and cannot be read")`
  3. No extractable text (empty or image-only) → `PdfExtractionError("PDF contains no extractable text (image-only or empty)")`
  4. Missing file → `FileNotFoundError` (Python's built-in, raised naturally)
- **Exception chaining:** `raise ... from e` preserves the underlying pypdf error in the traceback while keeping the user-facing message clean.

## What was proven

| Layer | Proof |
|-------|-------|
| Happy path | `extract_text()` returns 11,920 characters from the CV PDF |
| Content integrity | 153 lines; contains EDUCATION, PNC, Emirates |
| Failure 1 | Non-PDF bytes raise `PdfExtractionError` with "Not a valid PDF" |
| Failure 2 | Empty PDF raises `PdfExtractionError` with "no extractable text" |
| Failure 3 | Blank-page PDF raises `PdfExtractionError` with "no extractable text" |
| Failure 4 | Encrypted PDF raises `PdfExtractionError` with "encrypted" |

## What broke, and what we learned

**1. ModuleNotFoundError: No module named 'pdf_extractor'**

When running `python scripts/test_pdf.py`, Python added only `scripts/` to `sys.path[0]` — not the parent `backend/` directory where `pdf_extractor.py` lives. So `from pdf_extractor import extract_text` failed.

Fix: added two lines to the top of both test scripts:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

Lesson: Python resolves imports relative to the script's location, not the current working directory. When a script lives in a subfolder but imports from the parent, sys.path must be adjusted explicitly.

2. PowerShell >> continuation prompt

Multiple pasted commands in one block caused PowerShell to enter multi-line continuation mode (>> prompts). Harmless but confusing. Lesson: paste one command at a time, or use ; as a separator on a single line.

3. pypdf prints warnings to stderr before raising

In break test 1, pypdf printed invalid pdf header and EOF marker not found before the exception propagated. Those are pypdf's own diagnostics, not errors in our code. The exception was caught correctly.

Lesson: not all stderr output is a failure — some is the library being informative about why it rejected input.

Commit history
text
f18f348  test: add four-way failure mode coverage for pdf extractor
35003f2  feat: add PDF extraction module with structured error handling
6d7c2a5  docs: rename day 1 log to day 0 foundation
067ee35  chore: add pypdf dependency
4febd2c  docs: add day 1 engineering log
Tomorrow
Wire extract_text() into POST /cv-analysis:

Change the endpoint to accept an UploadFile

Pass file.file (a BinaryIO) to extract_text()

Return the extracted text as JSON (no LLM yet)

Prove the endpoint works end-to-end with a real upload

Commit

The LLM integration and Pydantic validation of LLM output move to Day 3.

The architectural point: the extractor is now a tested component. The endpoint is just plumbing on top of it.