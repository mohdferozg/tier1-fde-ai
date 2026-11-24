"""Gemini calls with a model fallback chain — one helper for every agent turn.

The RAG lab learned this the hard way on Day 6/9: a single hardcoded model name
plus an occasional 503/504 means the whole pipeline is down. Every agent turn
is a network call, and an agent makes several per question, so the fallback
chain is not optional here — it is the difference between one retry and six.
"""
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

DEFAULT_TIMEOUT_MS = int(os.getenv("GEMINI_TIMEOUT_MS", "30000"))


def get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    return genai.Client(api_key=api_key)


def model_candidates() -> list[str]:
    """Primary model from the environment, then known-good fallbacks."""
    primary = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    models = [
        primary,
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ]
    seen = set()
    return [m for m in models if not (m in seen or seen.add(m))]


def generate(
    contents,
    tools: types.Tool | None = None,
    temperature: float = 0.2,
    timeout_ms: int | None = None,
    system_instruction: str | None = None,
) -> tuple[types.GenerateContentResponse, str]:
    """One Gemini call, trying several models in order. First success wins.

    Args:
        contents: Conversation so far (`str` or a list of `types.Content`).
        tools: Optional tool declarations. Automatic function calling is always
            disabled — this agent runs the tool loop itself so every step is
            observable and logged.
        temperature: Sampling temperature.
        timeout_ms: Per-request timeout. Defaults to GEMINI_TIMEOUT_MS (30s).
        system_instruction: Behaviour rules for the model.

    Returns:
        (response, model_name) for the first model that answered.

    Raises:
        RuntimeError: If every candidate model failed.
    """
    client = get_client()
    config_kwargs = {
        "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
        "temperature": temperature,
        "http_options": types.HttpOptions(timeout=timeout_ms or DEFAULT_TIMEOUT_MS),
    }
    if tools is not None:
        config_kwargs["tools"] = [tools]
    if system_instruction is not None:
        config_kwargs["system_instruction"] = system_instruction
    config = types.GenerateContentConfig(**config_kwargs)

    errors = []
    for candidate in model_candidates():
        try:
            response = client.models.generate_content(
                model=candidate,
                contents=contents,
                config=config,
            )
            print(f"[INFO] Responded using: {candidate}")
            return response, candidate
        except Exception as e:
            errors.append(f"{candidate}: {type(e).__name__}: {str(e)[:80]}")

    raise RuntimeError(f"All Gemini models failed. Errors: {' | '.join(errors)}")


def extract_text(response: types.GenerateContentResponse) -> str:
    """Collect visible text parts, skipping model 'thought' parts."""
    parts: list[str] = []
    for candidate in response.candidates or []:
        content = candidate.content
        if content is None:
            continue
        for part in content.parts or []:
            if part.text and not part.thought:
                parts.append(part.text)
    return "".join(parts).strip()


if __name__ == "__main__":
    print("Models in fallback order:", model_candidates())
    response, model = generate("Reply with exactly: connectivity ok")
    print(f"Model: {model}")
    print(f"Text: {extract_text(response)}")
