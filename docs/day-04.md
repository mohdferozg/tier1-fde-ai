# Day 4 — Angular UI for CV Analyzer

**Date:** 2026-11-03
**Focus:** Build a user-facing UI for the CV Analyzer API.

## What was built
- Angular 19 standalone component UI.
- File upload interface with loading state during Gemini call.
- Structured rendering of `CVAnalysis` JSON into CSS grid cards (Skills) and lists (Experience, Projects).
- Error handling for 400 (wrong extension) and network failures.
- CORS middleware added to FastAPI backend to allow `localhost:4200`.

## What broke, and what we learned
**1. CORS blocking fetch requests**
The Angular app hung indefinitely when uploading. The browser's network tab showed a blocked request. Fixed by adding `CORSMiddleware` to `main.py` allowing `http://localhost:4200`.

Lesson: Browsers block cross-origin requests by default. Even if the backend is running, the frontend cannot talk to it unless the backend explicitly sends the `Access-Control-Allow-Origin` header.

## Tomorrow
Deploy the frontend and backend so the CV Analyzer is a live URL, not just localhost.