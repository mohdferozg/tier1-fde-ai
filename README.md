# tier1-fde-ai

A working lab for becoming a **Tier-1 Forward Deployed Engineer** — technically deep, architecture-capable, and able to take AI systems from problem discovery to production.

This is not a tutorial follow-along. Each component here is built, broken, fixed, understood, and explained before it moves forward.

## Why this repo exists

Most "AI engineer" portfolios show demos. This one tracks the engineering discipline behind them: typed contracts, validated LLM output, failure handling, structured commits, and honest documentation of what broke and why.

The north star is the ability to sit in front of a customer, map their problem to an architecture, and then open an editor and implement the critical parts.

## Repository layout

```
tier1-fde-ai/
├── cv-analyzer/                  # Project 1: structured CV extraction
│   └── backend/                  # FastAPI service
│       ├── main.py               # API endpoints and Pydantic models
│       ├── requirements.txt      # Pinned dependencies (UTF-8)
│       ├── scripts/              # Setup verification tools
│       │   ├── test_env.py       # Confirms .env loads and key is present
│       │   └── test_gemini.py    # Confirms Gemini connectivity end-to-end
│       └── .env                  # Secrets (gitignored)
├── .gitignore                    # Excludes venv, caches, secrets, personal data
├── .gitattributes                # Line-ending consistency across platforms
└── docs/                         # Engineering logs
    └── day-01.md                 # Day 1: environment, Git, FastAPI, first LLM call
```

Future phases will add `rag-lab/`, `agent-lab/`, `mcp-lab/`, and `evaluations/` at the same level as `cv-analyzer/`.

## Current status

**Day 1 complete** — backend skeleton with typed contracts and verified LLM connectivity.

- FastAPI app with `GET /`, `POST /analyze`, `POST /cv-analysis`
- Pydantic models: `AnalyzeRequest`, `CVItem`, `CVAnalysis`
- Nested validation across `technicalSkills`, `experience`, `projects`
- Gemini API verified end-to-end (`google-genai` SDK)
- Secrets loaded via `python-dotenv`, provably gitignored

**Day 2 next** — PDF extraction wired into `/cv-analysis`, with Gemini producing structured `CVAnalysis` output validated by Pydantic.

## Setup

Requirements: Python 3.10+ (tested on 3.14), Git.

```powershell
cd cv-analyzer/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file at `cv-analyzer/backend/.env` with a single line:

```
GEMINI_API_KEY=<your-key-from-https://aistudio.google.com/apikey>
```

Run the API:

```powershell
python -m uvicorn main:app --reload
```

Then open:
- `http://127.0.0.1:8000/` — health check
- `http://127.0.0.1:8000/docs` — interactive API docs

## Verifying your environment

Two diagnostic scripts confirm setup before you trust a build:

```powershell
python scripts/test_env.py      # .env loads, key present, format correct
python scripts/test_gemini.py   # Real Gemini call returns a response
```

Both must succeed before new code is expected to run.

## Commit discipline

This repository uses [Conventional Commits](https://www.conventionalcommits.org/) with atomic boundaries. Each commit represents one logical change. Prefixes used: `feat:`, `fix:`, `refactor:`, `test:`, `chore:`, `docs:`.

The `git log` should read as a chronological engineering narrative, not a diary.

## Phase roadmap

| Phase | Focus |
|-------|-------|
| 1 | Python, FastAPI, Pydantic |
| 2 | LLM applications, structured output |
| 3 | RAG — parsing, chunking, embeddings, retrieval |
| 4 | Tools and function calling |
| 5 | Agents — planning, state, memory, failure modes |
| 6 | MCP — standardized AI-to-system interaction |
| 7 | Guardrails, evaluation, human-in-the-loop |
| 8 | Production AI engineering — cloud, observability, cost |
| 9 | LLMOps and AI platform engineering |
| 10 | FDE / customer architecture |

Currently in Phase 1, moving into Phase 2.