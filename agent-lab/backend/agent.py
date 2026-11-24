"""The agent loop: model → tool call → observation → model → final answer.

Nothing here is magic. A "tool call" is the model returning a function name and
a JSON blob instead of prose. We run the function ourselves, hand the result
back as a `function_response` part, and call the model again. Repeat until it
answers or the turn budget runs out.
"""
import json
import os
import sys
import time

from dotenv import load_dotenv
from google.genai import types

from llm import extract_text, generate
from tools import TOOL_DECLARATIONS, execute_tool

load_dotenv()

MAX_TURNS = int(os.getenv("AGENT_MAX_TURNS", "6"))

SYSTEM_PROMPT = """You are the delivery-operations agent for a forward-deployed engineering team.

You have tools. Use them. Do not answer from memory.

RULES:
1. Every claim about clients, SLAs, incidents, escalation contacts, or the current time MUST come from a tool result.
2. Make several tool calls in one turn when the question needs several facts. Independent calls are cheap — batching beats serial round-trips.
3. If a tool returns {"error": ...}, read the message, fix the arguments, and retry once. Never repeat an identical failing call.
4. If the data does not answer the question, say so plainly instead of guessing.
5. Answer with what the data shows, then the action you recommend. No preamble, no restating the question.
"""


def run(question: str, max_turns: int = MAX_TURNS, verbose: bool = True) -> dict:
    """Answer a question by letting Gemini call tools until it can respond.

    Args:
        question: The user's question.
        max_turns: Hard cap on model round-trips (cost guard).
        verbose: Print each turn and tool call as it happens.

    Returns:
        dict with keys: question, answer, steps, tools_used, models, turns,
        latency_s, truncated, error (None unless the LLM call itself failed).
    """
    question = (question or "").strip()
    if not question:
        raise ValueError("question is required")

    contents = [types.Content(role="user", parts=[types.Part(text=question)])]
    tool = types.Tool(function_declarations=TOOL_DECLARATIONS)

    steps: list[dict] = []
    models_used: list[str] = []
    start = time.time()

    for turn in range(1, max_turns + 1):
        try:
            response, model = generate(
                contents,
                tools=tool,
                system_instruction=SYSTEM_PROMPT,
            )
        except RuntimeError as e:
            return _result(question, f"Agent call failed: {e}", steps, models_used,
                           turn, start, truncated=False, error=str(e))

        models_used.append(model)
        calls = response.function_calls or []

        if not calls:
            return _result(question, extract_text(response) or "(the model returned no text)",
                           steps, models_used, turn, start)

        if verbose:
            print(f"[INFO] Turn {turn} — {model} requested {len(calls)} tool call(s)")

        # Echo the model turn back verbatim. Gemini 3 attaches thought
        # signatures to parts; dropping them breaks the next request.
        if response.candidates and response.candidates[0].content is not None:
            contents.append(response.candidates[0].content)

        response_parts = []
        for call in calls:
            args = dict(call.args or {})
            call_start = time.time()
            outcome = execute_tool(call.name, args)
            duration_ms = int((time.time() - call_start) * 1000)
            ok = not (isinstance(outcome, dict) and "error" in outcome)

            steps.append({
                "turn": turn,
                "model": model,
                "tool": call.name,
                "arguments": args,
                "ok": ok,
                "duration_ms": duration_ms,
                "result": _summarize(outcome),
            })
            if verbose:
                status = "ok" if ok else "error"
                print(f"[TOOL] {call.name}({json.dumps(args)}) -> {status} in {duration_ms}ms")

            payload = {"result": outcome} if ok else outcome
            response_parts.append(
                types.Part.from_function_response(name=call.name, response=payload)
            )

        contents.append(types.Content(role="user", parts=response_parts))

    return _result(
        question,
        f"I stopped after {max_turns} turns without a final answer. "
        "Last tool results are in the trace.",
        steps, models_used, max_turns, start, truncated=True,
    )


def _result(question, answer, steps, models_used, turns, start, truncated=False, error=None):
    return {
        "question": question,
        "answer": answer,
        "steps": steps,
        "tools_used": [s["tool"] for s in steps],
        "models": _unique(models_used),
        "turns": turns,
        "latency_s": round(time.time() - start, 2),
        "truncated": truncated,
        "error": error,
    }


def _unique(models: list[str]) -> list[str]:
    seen = set()
    return [m for m in models if not (m in seen or seen.add(m))]


def _summarize(outcome, limit: int = 240) -> str:
    """Compact one-line view of a tool result for the trace."""
    text = json.dumps(outcome, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Ask the delivery-ops agent a question.")
    parser.add_argument("question", nargs="+", help="The question to ask.")
    parser.add_argument("--max-turns", type=int, default=MAX_TURNS,
                        help=f"Model round-trip budget (default {MAX_TURNS}).")
    parser.add_argument("--json", action="store_true", help="Print the full trace as JSON.")
    args = parser.parse_args(argv)

    question = " ".join(args.question)
    result = run(question, max_turns=args.max_turns)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 0 if result["error"] is None else 1

    print()
    print("Answer:")
    print(result["answer"])
    print()
    print(f"Tools used: {result['tools_used'] or 'none'}")
    print(f"Models: {result['models']}")
    print(f"Turns: {result['turns']} | Latency: {result['latency_s']}s"
          f"{' | TRUNCATED' if result['truncated'] else ''}")
    return 0 if result["error"] is None else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
