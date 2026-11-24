# Day 10 — First Agent with Tool Calling

**Date:** 2026-11-24
**Focus:** Move from a reactive RAG pipeline to a proactive agent: give Gemini tools, let it choose which to call, execute them locally, feed results back, and repeat until it can answer.

## What was built

`agent-lab/backend/` — a delivery-operations agent over a seeded SQLite database.

| File | Role |
|------|------|
| `db.py` | SQLite schema + seed data (6 clients, 11 incidents). Idempotent `init_db()`. |
| `tools.py` | 5 typed tools, their model-facing JSON-schema declarations, and `execute_tool()` — the only bridge between the model and Python. |
| `llm.py` | Gemini call with the model fallback chain from Day 6, plus a 30s timeout and `extract_text()`. |
| `agent.py` | The loop itself: model → tool call → observation → model → answer. CLI with `--json` trace. |
| `main.py` | FastAPI wrapper: `GET /`, `GET /tools`, `POST /ask`. |
| `smoke_test.py` | 19 offline checks of the data layer and tools. No API key, no tokens. |
| `test_agent_loop.py` | 21 offline checks of the loop, using a scripted fake LLM. No network. |

## The architecture

An agent is a loop, not a framework. Every step is visible in the trace:

1. Send the question + the tool declarations to Gemini, with automatic function calling **disabled**.
2. Gemini either returns text (done) or a list of `function_call` parts — name + JSON args.
3. For each call, run the real Python function locally and capture the result.
4. Append the model turn verbatim, then a `role="user"` turn containing one `function_response` per call.
5. Call Gemini again. Repeat until it answers or the turn budget (default 6) is exhausted.

Disabling automatic function calling is deliberate. The SDK can run this loop for you, but then you cannot log which tool ran, how long it took, or what the model actually saw. Every failure in agent work is a failure to see the trace.

## The tools

| Tool | Arguments | Returns |
|------|-----------|---------|
| `list_clients` | — | `[{name, tier, service, region}]` |
| `get_client_snapshot` | `client` | uptime_30d, SLA target, `sla_met`, gap, open incident counts |
| `get_open_incidents` | `client?`, `severity?` | open incidents with `age_hours` |
| `get_escalation_contact` | `client` | owner + email + tier |
| `get_current_time` | `timezone_name?` | ISO time + UTC offset |

The descriptions are the prompt. `get_open_incidents` says "omit the filters to get every open incident across all clients" because a model that does not know it can omit a filter will burn a turn listing clients first.

## What was proven

| Test | Result |
|------|--------|
| `python smoke_test.py` | 19/19 checks passed — seeded data, every tool, every failure mode |
| `python test_agent_loop.py` | 21/21 checks passed — tool call → observation → answer, using a scripted fake LLM |
| Tool error handling | Unknown client returns `{"error": "Unknown client 'HSBC'. Known clients: ..."}` to the model instead of raising |
| Parallel tool calls | Two `function_response` parts in one turn are serialized and replayed correctly |
| Turn budget | A model that never stops is cut off at `max_turns` with `truncated: true` |
| Live end-to-end run | **Blocked** — the local `GEMINI_API_KEY` returns `401 UNAUTHENTICATED` (see below) |

## What broke, and what we learned

**1. `datetime + timedelta` moves the clock but not the label**

The Windows Python here has no IANA database (`TZPATH` is empty, `tzdata` not installed), so `ZoneInfo("Asia/Dubai")` raises and the fallback path runs. The first version did:

```python
now = datetime.now(timezone.utc) + timedelta(hours=4)
```

That returns `11:03+00:00` for Dubai — the correct wall-clock time with the wrong offset, so `utcoffset()` reported `0` and the tool returned "offset 0 hours". The fix is to build a real tzinfo: `timezone(timedelta(hours=4))`.

Lesson: a test that checks the *offset* (not just that the call returned) is what caught this. Printing the time would have looked correct.

**2. `FunctionResponse.response` must be a JSON object**

`list_clients` returns a list. Passing it straight to `types.Part.from_function_response(...)` fails Pydantic validation:

```
Input should be a valid dictionary [type=dict_type, input_value=[{'a': 1}], input_type=list]
```

The loop wraps successful results as `{"result": ...}` and passes error dicts through unchanged, so the model sees `{"result": [...]}` or `{"error": "..."}`. Both shapes are valid and both are unambiguous.

**3. The model turn must be echoed back verbatim**

The `function_response` is not enough on its own — the preceding model turn has to be appended as-is. Gemini 3 attaches **thought signatures** to parts, and reconstructing the parts by hand drops them. Append `response.candidates[0].content` instead of rebuilding a `types.Content` from the `function_call` objects.

**4. `response.function_calls` empty is the exit condition, not an error**

The loop terminates when the model returns no function calls. Treating "no tool call" as a failure would turn a correct answer into a stack trace. Truncation (`truncated: true`) is a different, explicit outcome that carries the trace so a human can see where it got stuck.

## The blocker: expired API key

Every live call returned:

```
401 UNAUTHENTICATED: API key not valid. reason: ACCESS_TOKEN_TYPE_UNSUPPORTED
```

The key in `rag-lab/backend/.env` is a 53-character `AQ.A...` value — an OAuth-style access token, not an AI Studio API key (those start with `AIza`). It worked on Day 9 and is now rejected, which means it expired. Regenerate at <https://aistudio.google.com/apikey>, paste into `agent-lab/backend/.env`, and the same command will run.

This is also why the offline suite exists: the loop, the tools, and the serialization are all verified without a single token, so a dead key is a credential problem, not a code problem.

## How to run it

```powershell
cd agent-lab/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # then paste a fresh GEMINI_API_KEY

python smoke_test.py        # 19 offline checks
python test_agent_loop.py   # 21 offline checks
python agent.py "Which clients have an open SEV1 right now, and who do I page for each?"
python agent.py "Is Emirates NBD meeting its SLA?" --json
python -m uvicorn main:app --reload
```

## What was measured (journal entry)

- 5 tools declared, 5 implemented, 1:1 contract check enforced by test
- 19/19 tool checks + 21/21 loop checks = **40 offline assertions, 0 network calls**
- Seed data: 6 clients, 11 incidents, 2 open SEV1
- Turn budget: 6 (env `AGENT_MAX_TURNS`), per-call timeout 30s (`GEMINI_TIMEOUT_MS`)
- 1 real bug found by the tests (timezone offset label), 1 API-contract constraint discovered (dict-only `FunctionResponse`)
- Live runs: 0 successful — blocked on a 401 from an expired key

## Tomorrow (Day 11)

Two candidates, both one step up from here:

1. **Agentic RAG:** wrap `rag-lab`'s `retrieve()` as a sixth tool, so one agent can answer "is this candidate's Angular experience relevant to the Emirates NBD incident?" by mixing document search with operational data.
2. **Agent UI + deploy:** an Angular chat that renders each tool step as a timeline, and the Render/Vercel deployment to make artifact #3 live.

Recommended: agentic RAG first. The tool contract and the loop are already proven, and adding retrieval as a tool is where this stops being a demo and starts being an architecture.
