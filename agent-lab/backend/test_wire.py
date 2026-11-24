"""Wire-level test: the real SDK, real HTTP, a mock Gemini endpoint.

`test_agent_loop.py` fakes the model by *constructing* SDK objects, which proves
the loop but not the transport. This file does the opposite: it points the real
`genai` client at a local server that speaks the REST dialect, then inspects the
request bodies the SDK actually produced and the responses it actually parsed.

What it proves: tool declarations leave as valid JSON, the parsed `functionCall`
becomes a real tool execution, the `functionResponse` we send back is a JSON
object at the right path, and a `thought` part is filtered out of the answer.

What it cannot prove: whether Gemini picks the right tool for a natural-language
question. That needs a live key. Nothing here fakes that result.
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from google import genai
from google.genai import types

import agent
import llm

failures: list[str] = []
requests_seen: list[dict] = []

TOOL_CALL_RESPONSE = {
    "candidates": [{
        "content": {
            "role": "model",
            "parts": [{
                "functionCall": {
                    "name": "get_open_incidents",
                    "args": {"severity": "SEV1"},
                }
            }],
        },
        "finishReason": "STOP",
        "index": 0,
    }],
    "usageMetadata": {"promptTokenCount": 42, "candidatesTokenCount": 9, "totalTokenCount": 51},
    "modelVersion": "mock-model",
}

TEXT_RESPONSE = {
    "candidates": [{
        "content": {
            "role": "model",
            "parts": [
                {"text": "internal planning that must never surface", "thought": True},
                {"text": "Two SEV1 incidents are open: Emirates NBD and Nordbank."},
            ],
        },
        "finishReason": "STOP",
        "index": 0,
    }],
    "usageMetadata": {"promptTokenCount": 88, "candidatesTokenCount": 14, "totalTokenCount": 102},
    "modelVersion": "mock-model",
}


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"[PASS] {label}")
    else:
        print(f"[FAIL] {label} {detail}".rstrip())
        failures.append(label)


def make_handler(script: list[dict]):
    """Serve one canned response per POST, recording each request body."""

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"_unparseable": raw.decode("utf-8", "replace")}
            parsed["_path"] = self.path
            requests_seen.append(parsed)

            payload = json.dumps(script.pop(0) if script else TEXT_RESPONSE).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    return Handler


def start_server(script: list[dict]) -> tuple[ThreadingHTTPServer, str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(script))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def flatten_parts(body: dict) -> list[dict]:
    parts = []
    for content in body.get("contents", []):
        parts.extend(content.get("parts", []))
    return parts


def run_checks() -> int:
    original_generate = agent.generate
    original_client = llm.get_client
    original_models = llm.model_candidates

    server, base_url = start_server([TOOL_CALL_RESPONSE, TEXT_RESPONSE])
    try:
        client = genai.Client(
            api_key="mock-key",
            http_options=types.HttpOptions(base_url=base_url, timeout=10_000),
        )
        llm.get_client = lambda: client
        llm.model_candidates = lambda: ["mock-model"]
        agent.generate = llm.generate  # the real helper, now pointed at the mock

        result = agent.run("Which clients have an open SEV1?", verbose=False)

        # --- 1. What the SDK put on the wire --------------------------------
        check("two model calls reached the endpoint", len(requests_seen) == 2,
              str(len(requests_seen)))
        first = requests_seen[0] if requests_seen else {}
        check("SDK called generateContent for the configured model",
              "generateContent" in first.get("_path", "")
              and "mock-model" in first.get("_path", ""), first.get("_path", ""))

        declared = first.get("tools", [{}])[0].get("functionDeclarations", [])
        check("all 5 tools left as functionDeclarations", len(declared) == 5,
              str(len(declared)))
        check("tool schemas survived transport",
              any(d["name"] == "get_client_snapshot"
                  and d.get("parameters", {}).get("required") == ["client"]
                  for d in declared), str(declared)[:240])
        check("system instruction was sent",
              "delivery-operations agent"
              in json.dumps(first.get("systemInstruction", {})), str(first.get("systemInstruction"))[:200])

        # --- 2. The parsed functionCall became a real execution -------------
        check("parsed functionCall drove a tool call",
              result["tools_used"] == ["get_open_incidents"], str(result["tools_used"]))
        check("tool ran against the real database",
              '"count": 2' in result["steps"][0]["result"], result["steps"][0]["result"])

        # --- 3. The observation went back over the wire ---------------------
        second = requests_seen[1] if len(requests_seen) > 1 else {}
        responses = [p["functionResponse"] for p in flatten_parts(second)
                     if "functionResponse" in p]
        check("functionResponse part was sent", len(responses) == 1, str(len(responses)))
        check("functionResponse name preserved",
              responses and responses[0].get("name") == "get_open_incidents", str(responses))
        payload = responses[0].get("response") if responses else None
        check("functionResponse payload is a JSON object", isinstance(payload, dict),
              str(type(payload)))
        check("observation carried the incident rows",
              payload is not None and '"count": 2' in json.dumps(payload), str(payload)[:200])
        check("model turn was echoed back verbatim",
              any("functionCall" in p for p in flatten_parts(second)),
              str(flatten_parts(second))[:240])

        # --- 4. The answer the SDK parsed -----------------------------------
        check("answer carries only visible text",
              result["answer"] == "Two SEV1 incidents are open: Emirates NBD and Nordbank.",
              result["answer"])
        check("thought part was filtered out",
              "internal planning" not in result["answer"], result["answer"])
        check("model name came from the fallback helper",
              result["models"] == ["mock-model"], str(result["models"]))
        check("run completed in two turns", result["turns"] == 2 and not result["truncated"],
              f"turns={result['turns']} truncated={result['truncated']}")
        check("no error surfaced", result["error"] is None, str(result["error"]))

        if os.getenv("WIRE_DUMP"):
            print("\n--- second request body, as the SDK serialized it ---")
            print(json.dumps(second.get("contents", []), indent=2)[:1400])
    finally:
        agent.generate = original_generate
        llm.get_client = original_client
        llm.model_candidates = original_models
        server.shutdown()
        server.server_close()

    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1

    print("All checks passed. The real SDK sent valid declarations, executed the parsed"
          " call, and returned the observation as a JSON object.")
    return 0


if __name__ == "__main__":
    sys.exit(run_checks())
