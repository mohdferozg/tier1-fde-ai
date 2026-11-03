# Day 5 — Deployment to Production

**Date:** 2026-11-03
**Focus:** Deploy the full-stack CV Analyzer to the cloud (Render + Vercel).

## What was built
- Prepared the backend for production with a `Procfile`, `.python-version`, and expanded CORS regex.
- Deployed the FastAPI backend to Render (free tier).
- Updated the Angular frontend to point to the live Render API URL.
- Deployed the Angular frontend to Vercel.

## What was proven
- **Live Backend:** `https://cv-analyzer-api-rbgc.onrender.com` successfully processes PDF uploads and calls Gemini.
- **Live Frontend:** `https://cv-analyzer-ui-roan.vercel.app` successfully accepts user uploads and renders the structured UI cards.
- The CORS regex `r"https://.*\.vercel\.app"` correctly authorizes the Vercel domain to talk to the Render domain.

## What broke, and what we learned
*(If you encountered the 50-second cold start, note it here. If the deployment was seamless, note that the preparation steps prevented errors.)*

## Tomorrow
Start Day 6: RAG fundamentals. Now that the "Hello World" of AI apps is deployed, we move to the core FDE skill: building a Retrieval-Augmented Generation pipeline.