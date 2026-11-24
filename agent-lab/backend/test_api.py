"""Offline test of the HTTP layer. No network, no API key, no server process.

`main.run` is patched with a canned agent result, so this proves the API
contract rather than the agent: routing, request validation, response_model
serialization (every trace field survives the trip), error mapping to status
codes, and CORS for the Vercel frontend.

The live server was also exercised by hand against a real dead credential and
returned the codes asserted here; this file is what keeps that true.
"""
import sys

from fastapi.testclient import TestClient

import main
from tools import TOOL_REGISTRY

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"[PASS] {label}")
    else:
        print(f"[FAIL] {label} {detail}".rstrip())
        failures.append(label)


SAMPLE_RESULT = {
    "question": "Which clients have an open SEV1?",
    "answer": "Emirates NBD and Nordbank.",
    "steps": [
        {
            "turn": 1,
            "model": "gemini-3.8-flash",
            "tool": "get_open_incidents",
            "arguments": {"severity": "SEV1"},
            "ok": True,
            "duration_ms": 4,
            "result": '{"count": 2}',
        }
    ],
    "tools_used": ["get_open_incidents"],
    "models": ["gemini-3.8-flash"],
    "turns": 2,
    "latency_s": 3.1,
    "truncated": False,
    "error": None,
}

FAILED_RESULT = {
    "question": "Which clients have an open SEV1?",
    "answer": "Agent call failed: All Gemini models failed.",
    "steps": [],
    "tools_used": [],
    "models": [],
    "turns": 1,
    "latency_s": 0.8,
    "truncated": False,
    "error": "All Gemini models failed. Errors: gemini-3.8-flash: ClientError: 401",
}


def run_checks() -> int:
    original_run = main.run
    client = TestClient(main.app)
    try:
        # --- 1. Health and the tool contract --------------------------------
        r = client.get("/")
        check("GET / is 200", r.status_code == 200, str(r.status_code))
        check("GET / says the API is running", "running" in r.json().get("message", ""),
              str(r.json()))

        r = client.get("/tools")
        declared = r.json()
        check("GET /tools is 200", r.status_code == 200, str(r.status_code))
        check("GET /tools returns every tool", len(declared) == len(TOOL_REGISTRY),
              f"{len(declared)} declared vs {len(TOOL_REGISTRY)} registered")
        check("declared names match the registry",
              sorted(d["name"] for d in declared) == sorted(TOOL_REGISTRY),
              str(sorted(d["name"] for d in declared)))
        check("every declaration carries a description and a schema",
              all(d.get("description") and d.get("parameters") for d in declared),
              str([d["name"] for d in declared
                   if not (d.get("description") and d.get("parameters"))]))

        # --- 2. A successful agent run serializes in full -------------------
        main.run = lambda question, max_turns, verbose: dict(SAMPLE_RESULT)
        r = client.post("/ask", json={"question": "Which clients have an open SEV1?"})
        body = r.json()

        check("POST /ask is 200", r.status_code == 200, str(r.status_code))
        check("answer is returned", body.get("answer") == SAMPLE_RESULT["answer"], str(body))
        check("trace survives the response_model",
              body["steps"][0]["tool"] == "get_open_incidents", str(body.get("steps")))
        check("per-step model survives serialization",
              body["steps"][0]["model"] == "gemini-3.8-flash", str(body.get("steps")))
        check("step flags survive",
              body["steps"][0]["ok"] is True and body["steps"][0]["duration_ms"] == 4,
              str(body.get("steps")))
        check("top-level trace fields survive",
              body["tools_used"] == ["get_open_incidents"]
              and body["models"] == ["gemini-3.8-flash"]
              and body["turns"] == 2 and body["truncated"] is False,
              str({k: body.get(k) for k in ("tools_used", "models", "turns", "truncated")}))
        check("response validates against AskResponse",
              isinstance(main.AskResponse(**body), main.AskResponse))

        # --- 3. Agent failure maps to 502, not a crash -----------------------
        main.run = lambda question, max_turns, verbose: dict(FAILED_RESULT)
        r = client.post("/ask", json={"question": "Which clients have an open SEV1?"})
        check("agent failure returns 502", r.status_code == 502, str(r.status_code))
        check("502 body carries the real error", "All Gemini models failed" in str(r.json()),
              str(r.json())[:160])

        # --- 4. Request validation ------------------------------------------
        r = client.post("/ask", json={"question": "   "})
        check("blank question returns 400", r.status_code == 400, str(r.status_code))

        r = client.post("/ask", json={"question": "hi", "max_turns": 99})
        check("max_turns above the cap returns 422", r.status_code == 422, str(r.status_code))

        r = client.post("/ask", json={"question": "hi", "max_turns": 0})
        check("max_turns below the floor returns 422", r.status_code == 422, str(r.status_code))

        r = client.post("/ask", json={"max_turns": 2})
        check("missing question returns 422", r.status_code == 422, str(r.status_code))

        # --- 5. CORS for the future frontend ---------------------------------
        r = client.options("/ask", headers={
            "Origin": "https://agent-ui.vercel.app",
            "Access-Control-Request-Method": "POST",
        })
        check("Vercel origin is allowed by the regex",
              r.headers.get("access-control-allow-origin") == "https://agent-ui.vercel.app",
              str(dict(r.headers)))

        r = client.options("/ask", headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        })
        check("unknown origin is not allowed",
              r.headers.get("access-control-allow-origin") is None,
              str(r.headers.get("access-control-allow-origin")))
    finally:
        main.run = original_run

    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1

    print("All checks passed. The API validates requests, serializes the full trace,"
          " maps failures to 502, and only allows the right origins.")
    return 0


if __name__ == "__main__":
    sys.exit(run_checks())
