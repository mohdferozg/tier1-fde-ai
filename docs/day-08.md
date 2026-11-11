# Day 8 — RAG Deployment to Production

**Date:** 2026-11-11
**Focus:** Deploy the RAG backend (FastAPI + Supabase) to Render and the RAG frontend (Angular) to Vercel.

## What was built
- Prepared the RAG backend with `Procfile`, `.python-version`, and updated CORS regex for Vercel.
- Deployed the backend to Render, configuring `DATABASE_URL` and `GEMINI_API_KEY` as environment variables.
- Updated the Angular frontend to point to the live Render API URL.
- Deployed the frontend to Vercel.

## What was proven
- **Live Backend:** `https://rag-lab-api-2dix.onrender.com` successfully connects to Supabase and returns grounded answers via `POST /query`.
- **Live Frontend:** `https://rag-chat-ui.vercel.app` successfully renders the chat UI, communicates with the Render API, and displays source citations.

## What broke, and what we learned
**1. Missing `requirements.txt` on first deploy**
Render failed the first build because `requirements.txt` was missing in the `rag-lab/backend` folder. Fix: Ran `pip freeze` to generate it, committed, and re-deployed.

Lesson: Every deployable Python app needs a pinned `requirements.txt`. The cv-analyzer had one; the rag-lab didn't until we hit the error.

**2. Render free-tier cold start**
The backend spins down after 15 minutes of inactivity. The first request after sleep takes ~50 seconds. This is expected on the free tier and will be noted in the README so recruiters aren't confused.

## Tomorrow
Day 9: RAG evaluation. Build a golden dataset of questions, measure retrieval precision and answer quality, and add an eval harness. This is the skill that makes RAG systems defensible in production.