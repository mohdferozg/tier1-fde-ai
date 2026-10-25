# FDE Tier-1 Project — Daily Metrics Journal

One number, per day, from the system I built. Not what I learned — what I measured.

---

## Day 3 — 2026-10-25 (Gemini integration)

**Number:** Gemini structured extraction on 11,920-char CV text returned 14 technical skills + 7 experiences + 7 projects = 28 validated items. 100% pass rate on Pydantic validation across all runs. Endpoint tested end-to-end via Swagger with 4 scenarios (happy path 200, wrong extension 400, corrupted PDF 422, LLM unavailable 503) — all 4 returned correct status codes. Fallback chain (primary + 3 fallbacks) verified when primary model 503'd during development.

**What I changed because of it:** Two real bugs found and fixed:
1. Circular import between `main.py` and `llm_extractor.py` — fixed by extracting Pydantic models into `models.py`.
2. Corrupted PDF content (12 chars of garbage) returned 200 OK with empty analysis — fixed by adding a 100-char minimum-length check on extracted text before LLM call.

Both fixes make the endpoint handle failure modes that a naive implementation would silently accept.