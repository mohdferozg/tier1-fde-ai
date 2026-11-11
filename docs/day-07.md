# Day 7 — RAG Frontend Chat Interface

**Date:** 2026-11-12
**Focus:** Build a usable chat interface for the RAG pipeline.

## What was built
- A new Angular frontend in `rag-lab/frontend`.
- A chat-style UI with user messages on the right and AI messages on the left.
- A typing indicator (bouncing dots) while waiting for the RAG pipeline to retrieve and generate.
- Visual source badges that show exactly which chunks the AI used to answer the question.
- Error handling for network issues.
- Fixed CORS policy in `main.py` to allow `localhost:4200` to talk to `127.0.0.1:8000`.

## What was proven
- The UI successfully connects to the local RAG API.
- Queries like "What banking clients..." return grounded answers.
- The source citations from the JSON response are rendered as visual badges.
- The Angular UI compiles and runs without errors.

## What broke, and what we learned
**1. CORS blocked fetch requests**
The Angular app threw "Failed to fetch" because it couldn't talk to the FastAPI backend. Fix: Changed `allow_origins=["*"]` in `main.py` to explicitly include `http://localhost:4200` and `http://127.0.0.1:4200`.

Lesson: Wildcard `*` CORS origins sometimes fail silently in browsers when credentials are involved. Being explicit is safer and more reliable.

## Tomorrow
Deploy the RAG backend to Render and the RAG frontend to Vercel so it becomes a live, shareable URL (Portfolio Artifact #2).