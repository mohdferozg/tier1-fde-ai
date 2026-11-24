# Day 10 — First Agent with Tool Calling

**Date:** 2026-11-24
**Focus:** Move from a reactive RAG pipeline to a proactive agent: give Gemini tools, let it choose which to call, execute them locally, feed results back, and repeat until it can answer.

## What was built

`agent-lab/backend/` — a delivery-operations agent over a seeded SQLite database.

| File | Role |
|------|------|
| `db.py` | SQLite schema + seed data (6 clients, 11 incidents). Idempotent `init_db()`. |
| `tools.py` | 5 typed tools, their model-facing JSON-schema declarations, and `execute_tool()` — the only bridge between the model and Python. |
| `llm.py` | Gemini call with a repaired fallback chain (retired 2.5 rungs dropped, lite tier added), one SDK attempt per model, 30s timeout, `extract_text()`. |
| `agent.py` | The loop itself: model → tool call → observation → model → answer. CLI with `--json` trace. |
| `main.py` | FastAPI wrapper: `GET /`, `GET /tools`, `POST /ask`. |
| `smoke_test.py` | 19 offline checks of the data layer and tools. No API key, no tokens. |
| `test_agent_loop.py` | 28 offline checks of the loop, using a scripted fake LLM, plus the fallback chain's contents and the SDK retry pinning. No network. |
| `test_api.py` | 21 offline checks of the HTTP layer via `TestClient`, with `main.run` patched. No server, no network. |
| `test_wire.py` | 17 offline checks of the transport: the real SDK against a local mock endpoint, inspecting the JSON it actually sent. No key, no network. |

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
| `python test_agent_loop.py` | 28/28 checks passed — tool call → observation → answer on a scripted fake LLM; chain carries no retired model, SDK retries pinned to one attempt |
| `python test_api.py` | 21/21 checks passed — routing, validation, full-trace serialization, 502 mapping, CORS |
| `python test_wire.py` | 17/17 checks passed — real SDK, real HTTP, mock endpoint: declarations out, `functionCall` parsed, observation back |
| Tool error handling | Unknown client returns `{"error": "Unknown client 'HSBC'. Known clients: ..."}` to the model instead of raising |
| Parallel tool calls | Two `function_response` parts in one turn are serialized and replayed correctly |
| Turn budget | A model that never stops is cut off at `max_turns` with `truncated: true` |
| Live HTTP server (`uvicorn` on :8011) | `GET /` 200 · `GET /tools` 200 (5 tools) · `POST /ask` blank 400 · `max_turns=99` 422 · missing field 422 · dead credential 502 · CORS preflight from `*.vercel.app` 200 with the origin echoed · unknown origin rejected |
| Live end-to-end model run | 2/2 answered — 3 turns each, 4 and 2 tool calls, `error: null`; the unknown-client run recovered from a tool error on its own |

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

## The HTTP layer, verified two ways

`test_api.py` patches `main.run` and asserts the contract replayably. That alone is not enough, because a `TestClient` never opens a socket and never installs the CORS middleware in the same order a real ASGI server does. So the server was also run for real:

```powershell
python -m uvicorn main:app --port 8011
```

| Request | Observed | Means |
|---|---|---|
| `GET /` | 200 `{"message": "Agent Lab API is running"}` | ASGI stack is live |
| `GET /tools` | 200, 5 declarations | the model's tool contract is inspectable over HTTP |
| `POST /ask` `{"question":"  "}` | 400 | manual blank check fires before the agent runs |
| `POST /ask` `{"max_turns":99}` | 422 | `Field(ge=1, le=12)` is enforced, cost guard can't be bypassed by a client |
| `POST /ask` `{"max_turns":2}` (no question) | 422 | Pydantic required-field validation |
| `POST /ask` valid question, dead key | 502 + real error text | an upstream failure is reported as upstream, not as a 500 crash |
| `OPTIONS /ask` `Origin: https://agent-ui.vercel.app` | 200, origin echoed | `allow_origin_regex` admits any `*.vercel.app` preview |
| `OPTIONS /ask` `Origin: https://evil.example.com` | rejected, no allow-origin | the regex is not a wildcard |

The 502 detail is the useful one: `POST /ask` with a dead credential returned the fallback chain's own error string, so a caller can tell "the model provider is down" apart from "the agent code threw."

## The wire, verified against a mock endpoint

`test_agent_loop.py` fakes the model by *constructing* SDK objects. That proves the loop but says nothing about transport. So `test_wire.py` does the opposite: it points the **real** `genai` client at a local server speaking the REST dialect (`types.HttpOptions(base_url=...)`), then asserts on the JSON the SDK actually produced.

Two details worth knowing:

- The mock returns a `functionCall` part as raw JSON, so the parse path `response.function_calls` is exercised for real, not faked.
- It also returns a `thought` part alongside the answer, which proves `extract_text()` filters reasoning out of a live-shaped payload.

What came back from the second request body, exactly as serialized:

```json
[
  { "role": "model", "parts": [ { "functionCall": { "name": "get_open_incidents", "args": { "severity": "SEV1" } } } ] },
  { "role": "user",  "parts": [ { "functionResponse": {
      "name": "get_open_incidents",
      "response": { "result": { "count": 2, "incidents": [ { "client": "Emirates NBD" }, { "client": "Nordbank" } ] } }
  } } ] }
]
```

That `"response": { "result": ... }` nesting is not cosmetic — it is the shape a bare list was rejected for earlier. Here it is confirmed on the wire rather than in a constructed object.

Three layers now run in CI-shaped form: 85 assertions, no key, no network, no server process.

The one thing those three layers cannot reach is whether Gemini *chooses* the right tool for a natural-language question. That needs a live key — and it is the next section.

## The live run: two questions, both answered

The key was replaced and the agent ran end to end. What it did without being told:

**1. `"Which clients have an open SEV1 right now, and who do I page for each?"`**

| Turn | Tool | Arguments | Outcome |
|------|------|-----------|---------|
| 1 | `get_open_incidents` | `{"severity": "SEV1"}` | ok, 2ms — 2 incidents |
| 1 | `list_clients` | `{}` | ok, 1ms — not needed for this question |
| 2 | `get_escalation_contact` | `{"client": "Emirates NBD"}` | ok, 3ms → Omar Haddad |
| 2 | `get_escalation_contact` | `{"client": "Nordbank"}` | ok, 6ms → Lena Fischer |
| 3 | — | — | answer |

`turns: 3 · tools_used: 4 · latency_s: 148.58 · truncated: false · error: null`

The second turn is the part worth reading. Nothing in the prompt said "look up the contacts" — the model read the two SEV1 rows, worked out that "who do I page for each" needs one lookup per client, and issued both calls in a single turn.

**2. `"What is the SLA for HSBC?"`** — a client that does not exist.

| Turn | Tool | Outcome |
|------|------|---------|
| 1 | `get_client_snapshot({"client": "HSBC"})` | **error** — `Unknown client 'HSBC'. Known clients: Axiata, Emirates NBD, ...` |
| 2 | `list_clients({})` | ok, 3ms — self-correction |
| 3 | — | "HSBC is not an active client deployment. Known clients are Axiata, Emirates NBD, Maybank, Nordbank, PNC Bank, and SBI. Confirm if HSBC was recently onboarded…" |

`turns: 3 · latency_s: 124.17 · error: null`

The tool returned an error instead of raising, the loop kept going, and the model used the error text to correct itself. That is the entire argument for `execute_tool()` never raising.

## The bug the live run found: a chain with dead rungs

The first live attempt failed outright:

```
All Gemini models failed. gemini-3.8-flash: 503 UNAVAILABLE | gemini-3.5-flash: 503 UNAVAILABLE
| gemini-2.5-flash: 404 NOT_FOUND | gemini-2.5-flash-lite: 404 NOT_FOUND
```

Two of the four rungs could never fire. Probing every candidate with a real tool-enabled request, one attempt each:

| Model | Result |
|---|---|
| `gemini-3.8-flash` | 503 UNAVAILABLE, 8.6s |
| `gemini-3.7-flash` | 503 UNAVAILABLE, 9.8s |
| `gemini-3.6-flash` | 504 DEADLINE_EXCEEDED, 19.2s |
| `gemini-3.5-flash` | 503 UNAVAILABLE, 17.3s |
| `gemini-3.5-flash-lite` | **OK, 0.9s** |
| `gemini-3.1-flash-lite` | **OK, 7.1s** |
| `gemini-2.5-flash` | 404 — "no longer available to new users… use models/gemini-3.8-flash" |
| `gemini-2.5-flash-lite` | 404 — "no longer available… use models/gemini-3.5-flash-lite" |

Three findings, in order of cost:

**1. The 2.5 series is retired for new keys, and the error says so.** Those rungs were unreachable, so every request paid two guaranteed failures. Removed. The `gemini-flash-latest` default was wrong for a second reason — `v1beta` rejects rolling aliases (Day 6) — so the default is now an explicit `gemini-3.8-flash`.

**2. The lite tier was the only thing up.** Every flash model was saturated; both lite models answered in under a second. The chain now ends on the lite tier instead of on dead model names.

**3. The SDK was retrying underneath the chain.** `HttpRetryOptions` defaults to several backoff attempts per model, so one 503 could stall a turn for minutes before the next rung was even tried. Pinned to a single attempt per model (`GEMINI_ATTEMPTS`, default `1`) — the fallback chain *is* the retry strategy. The same 503: **8.6s instead of minutes**.

Finding 3 also explains Day 9's latency: 13s on a good question, 539s on a bad one. That was never the RAG code — it was SDK retries stacked under an unhelpful chain. `rag-lab/backend/generator.py` still carries both defects (see Day 11).

The chain that runs now, primary first:

```python
[os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
 "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash",
 "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
```

Both successful runs above were answered entirely by `gemini-3.5-flash-lite` — every flash rung returned 503 on every turn that day. That is the chain doing its job, and it is also why the latency reads 124–149s: roughly 35s of failed rungs before each of the three turns. The loop is not slow; the provider was saturated. Under a healthy flash model the same question is a single turn.

## How to run it

```powershell
cd agent-lab/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # then paste a fresh GEMINI_API_KEY

python smoke_test.py        # 19 offline checks
python test_agent_loop.py   # 28 offline checks
python test_api.py          # 21 offline checks (no server needed)
python test_wire.py         # 17 offline checks (real SDK, mock endpoint)
python agent.py "Which clients have an open SEV1 right now, and who do I page for each?"
python agent.py "Is Emirates NBD meeting its SLA?" --json
python -m uvicorn main:app --reload
```

## What was measured (journal entry)

- 5 tools declared, 5 implemented, 1:1 contract check enforced by test
- 19/19 tool checks + 28/28 loop checks + 21/21 API checks + 17/17 wire checks = **85 offline assertions, 0 network calls**
- Seed data: 6 clients, 11 incidents, 2 open SEV1
- Turn budget: 6 (env `AGENT_MAX_TURNS`), per-call timeout 30s (`GEMINI_TIMEOUT_MS`), one SDK attempt per model (`GEMINI_ATTEMPTS`)
- 1 real bug found by the tests (timezone offset label), 1 API-contract constraint discovered (dict-only `FunctionResponse`)
- HTTP status codes verified against a live server: 200 / 400 / 422 ×3 / 502 / CORS 200 + rejection
- Wire format verified without a key: 5 declarations out, raw `functionCall` parsed, `functionResponse.response` a JSON object
- **Live model runs: 2/2 answered.** 3 turns each. SEV1 escalation question: 4 tool calls, 148.58s. Unknown-client question: 2 tool calls, 124.17s, self-corrected from a tool error. Both answered by `gemini-3.5-flash-lite` after three flash rungs returned 503 per turn
- **1 real bug found by going live:** the fallback chain carried two rungs the API had retired (404), and the SDK was retrying beneath it — fixed and now covered by 7 assertions

## Tomorrow (Day 11)

Two candidates, both one step up from here:

1. **Agentic RAG:** wrap `rag-lab`'s `retrieve()` as a sixth tool, so one agent can answer "is this candidate's Angular experience relevant to the Emirates NBD incident?" by mixing document search with operational data.
2. **Agent UI + deploy:** an Angular chat that renders each tool step as a timeline, and the Render/Vercel deployment to make artifact #3 live.

Carried over, and worth doing first because it is small: **`rag-lab/backend/generator.py` still has both chain defects** — the retired 2.5 rungs and un-pinned SDK retries. That is the real explanation for Day 9's 24.69s average and its 539s outlier, so fixing it should be paired with re-running the 10-question eval and publishing the improved latency against the recorded baseline.

Recommended: fix the rag-lab chain and re-measure, then agentic RAG. The tool contract and the loop are already proven, and retrieval-as-a-tool is where this stops being a demo and starts being an architecture.
