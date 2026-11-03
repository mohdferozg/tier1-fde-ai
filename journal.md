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