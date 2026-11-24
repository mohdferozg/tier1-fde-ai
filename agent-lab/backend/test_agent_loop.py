"""Offline test of the agent loop plumbing. No network, no API key.

`agent.generate` is replaced with a scripted fake, so this proves the loop
itself: tool call → execute → function_response → next turn → final answer,
plus error recovery and the turn budget.
"""
import json
import sys

from google.genai import types

import agent
import llm

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"[PASS] {label}")
    else:
        print(f"[FAIL] {label} {detail}".rstrip())
        failures.append(label)


def model_turn(*calls) -> types.GenerateContentResponse:
    parts = [types.Part(function_call=types.FunctionCall(name=n, args=a)) for n, a in calls]
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=parts))]
    )


def text_turn(text: str) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(content=types.Content(role="model", parts=[types.Part(text=text)]))
        ]
    )


class FakeLLM:
    """Replays a script of model turns and records what the loop sends back."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def __call__(self, contents, tools=None, system_instruction=None, **kwargs):
        self.calls.append(list(contents))
        if not self.script:
            raise AssertionError("agent requested more turns than the script allows")
        return self.script.pop(0), "fake-model"


class AlwaysTools:
    def __init__(self):
        self.calls = 0

    def __call__(self, contents, tools=None, system_instruction=None, **kwargs):
        self.calls += 1
        return model_turn(("list_clients", {})), "fake-model"


def function_responses(contents) -> list:
    found = []
    for content in contents:
        for part in content.parts or []:
            if part.function_response:
                found.append(part.function_response)
    return found


def main() -> int:
    original_generate = agent.generate
    try:
        # --- 1. Tool call, then answer -------------------------------------
        fake = FakeLLM([
            model_turn(("get_open_incidents", {"severity": "SEV1"})),
            text_turn("Two SEV1 incidents are open: Emirates NBD and Nordbank."),
        ])
        agent.generate = fake
        result = agent.run("Which clients have open SEV1s?", verbose=False)

        check("answer text is returned", "Two SEV1 incidents" in result["answer"], result["answer"])
        check("one tool executed", result["tools_used"] == ["get_open_incidents"],
              str(result["tools_used"]))
        check("tool step marked ok", result["steps"][0]["ok"] is True)
        check("two model turns", result["turns"] == 2, str(result["turns"]))
        check("not truncated", result["truncated"] is False)
        check("model name recorded", result["models"] == ["fake-model"], str(result["models"]))
        check("step records which model ran the call",
              result["steps"][0]["model"] == "fake-model", str(result["steps"][0]))

        # --- 2. The observation really reaches the model ---------------------
        second_call = fake.calls[1]
        responses = function_responses(second_call)
        check("function_response fed back to the model", len(responses) == 1, str(responses))
        check("tool name preserved", responses[0].name == "get_open_incidents")
        payload = json.dumps(responses[0].response, default=str)
        check("tool payload carried the real rows", "\"count\": 2" in payload, payload[:200])

        # --- 3. Tool errors are data, not crashes ---------------------------
        fake = FakeLLM([
            model_turn(("get_client_snapshot", {"client": "HSBC"})),
            text_turn("I could not find a client called HSBC."),
        ])
        agent.generate = fake
        result = agent.run("How is HSBC doing?", verbose=False)

        check("failing tool does not break the loop", result["error"] is None, str(result["error"]))
        check("failed step flagged", result["steps"][0]["ok"] is False)
        check("error text is in the trace", "Known clients" in result["steps"][0]["result"],
              result["steps"][0]["result"])
        error_payload = json.dumps(function_responses(fake.calls[1])[0].response, default=str)
        check("error returned to the model", "error" in error_payload, error_payload[:200])

        # --- 4. Parallel calls in a single turn -----------------------------
        fake = FakeLLM([
            model_turn(("list_clients", {}), ("get_open_incidents", {"severity": "SEV1"})),
            text_turn("Done."),
        ])
        agent.generate = fake
        result = agent.run("Compare clients and SEV1s.", verbose=False)

        check("both tools executed in one turn", result["tools_used"] == [
            "list_clients", "get_open_incidents"], str(result["tools_used"]))
        check("two function_responses in one message",
              len(function_responses(fake.calls[1])) == 2,
              str(len(function_responses(fake.calls[1]))))

        # --- 5. A list-returning tool still serializes ----------------------
        fake = FakeLLM([
            model_turn(("list_clients", {})),
            text_turn("Six clients."),
        ])
        agent.generate = fake
        result = agent.run("List the clients.", verbose=False)

        list_payload = function_responses(fake.calls[1])[0].response
        check("list-returning tool completes the loop", result["error"] is None, str(result["error"]))
        check("list result is wrapped in a JSON object", isinstance(list_payload, dict)
              and isinstance(list_payload.get("result"), list), str(type(list_payload)))

        # --- 6. Turn budget stops a looping model ---------------------------
        agent.generate = AlwaysTools()
        result = agent.run("Loop forever.", max_turns=2, verbose=False)

        check("turn budget truncates the run", result["truncated"] is True)
        check("budget respected", result["turns"] == 2, str(result["turns"]))
        check("tools capped at budget", len(result["tools_used"]) == 2,
              str(result["tools_used"]))

        # --- 7. The fallback chain is real ----------------------------------
        candidates = llm.model_candidates()
        check("no retired model left in the chain",
              not any(c.startswith("gemini-2.5") for c in candidates), str(candidates))
        check("chain ends on the lite tier that survives a demand spike",
              candidates[-1].endswith("flash-lite"), str(candidates))
        check("SDK retries pinned so the chain owns retrying",
              llm.DEFAULT_ATTEMPTS == 1, str(llm.DEFAULT_ATTEMPTS))

        sent: list[tuple[str, types.GenerateContentConfig]] = []

        class RecordingClient:
            class models:
                @staticmethod
                def generate_content(model, contents, config):
                    sent.append((model, config))
                    return text_turn("ok")

        original_client = llm.get_client
        llm.get_client = lambda: RecordingClient()  # type: ignore[assignment]
        try:
            llm.generate("ping", timeout_ms=1234)
        finally:
            llm.get_client = original_client  # type: ignore[assignment]

        tried_model, config = sent[0]
        check("first request goes to the primary candidate",
              tried_model == candidates[0], tried_model)
        check("timeout is forwarded to the SDK",
              config.http_options.timeout == 1234, str(config.http_options.timeout))
        check("one SDK attempt per model",
              config.http_options.retry_options.attempts == 1,
              str(config.http_options.retry_options))
        check("automatic function calling stays disabled",
              config.automatic_function_calling.disable is True)
    finally:
        agent.generate = original_generate

    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1

    print("All checks passed. The loop handles calls, errors, parallel calls, and budgets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
