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

Future phases will add `mcp-lab/` and `evaluations/` at the same level as `cv-analyzer/`, `rag-lab/`, and `agent-lab/`.

## Current status

**Day 10 complete** — three working artifacts, two of them deployed.

- **Artifact 1 — CV analyzer:** FastAPI + Pydantic structured extraction from PDFs, validated nested models. Live.
- **Artifact 2 — RAG chat:** chunking, embeddings, pgvector retrieval, grounded answers with citations. Live. Measured against a 10-question golden set: 70% retrieval hit rate, 60% exact-match answer accuracy, 24.69s average latency.
- **Artifact 3 — Delivery-ops agent:** 5 typed tools over SQLite, a manual agent loop with a per-step trace, and 78 offline assertions that run without an API key or a server. Local.

**Day 11 next** — agentic RAG: expose `retrieve()` as a sixth tool so one agent can combine document search with operational data.

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

Currently in Phase 5 (agents). Phases 1–4 are delivered: FastAPI/Pydantic services, structured LLM output, RAG, and tool declarations.

## 🚀 Live Demo

- **Frontend UI:** [https://cv-analyzer-ui-roan.vercel.app](https://cv-analyzer-ui-roan.vercel.app)
- **Backend API:** [https://cv-analyzer-api-rbgc.onrender.com/docs](https://cv-analyzer-api-rbgc.onrender.com/docs)

*(Note: The backend is hosted on Render's free tier. If it has been inactive for 15 minutes, the first request may take up to 50 seconds to wake up the server.)*

### Portfolio Artifact #2: RAG Chat Application

- **Frontend UI:** [https://rag-chat-ui.vercel.app](https://rag-chat-ui.vercel.app)
- **Backend API:** [https://rag-lab-api-2dix.onrender.com/docs](https://rag-lab-api-2dix.onrender.com/docs)

*A Retrieval-Augmented Generation system that answers questions about a document knowledge base using Supabase (pgvector), Gemini embeddings, and grounded generation with source citations.*

### Portfolio Artifact #3: Delivery-Ops Agent (tool calling)

- **Location:** [`agent-lab/backend`](agent-lab/backend) — local, not yet deployed

*A Gemini agent that decides which tool to call, executes it against SQLite, reads the result, and keeps going until it can answer. The loop is written by hand — automatic function calling is disabled — so every step is traceable: which model ran the call, the arguments it chose, the latency, and the outcome.*

```powershell
cd agent-lab/backend
.\.venv\Scripts\Activate.ps1
python smoke_test.py        # 19 offline checks — data layer and tools
python test_agent_loop.py   # 21 offline checks — loop, with a scripted fake LLM
python test_api.py          # 21 offline checks — HTTP contract, no server or key needed
python test_wire.py         # 17 offline checks — real SDK vs a local mock endpoint
python agent.py "Which clients have an open SEV1 right now, and who do I page for each?"
python -m uvicorn main:app --reload
```

| Tool | What the model can ask for |
|------|---------------------------|
| `list_clients` | every client, tier, service, region |
| `get_client_snapshot` | uptime, SLA target, whether the SLA is met, open incident counts |
| `get_open_incidents` | open incidents, optionally filtered by client or severity |
| `get_escalation_contact` | who owns the account and how to reach them |
| `get_current_time` | current time and UTC offset for a named timezone |

Evidence it behaves: unknown clients come back as `{"error": ...}` for the model to self-correct, parallel tool calls are serialized into a single turn, and a runaway model is stopped by a turn budget (`truncated: true`) instead of looping forever.
