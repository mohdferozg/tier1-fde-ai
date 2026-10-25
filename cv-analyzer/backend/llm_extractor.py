"""Extract structured CV data from raw text using Gemini.

Day 3: takes raw CV text, returns a validated CVAnalysis object.
This module is the boundary between unstructured text and structured data.
"""
import os
import json
import re

from dotenv import load_dotenv
from google import genai

from exceptions import LlmExtractionError
from models import CVAnalysis, CVItem

load_dotenv()


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """You are a CV parser. Extract structured information from the CV text below.

Return ONLY a JSON object with this exact structure:
{
  "technicalSkills": [{"title": "...", "description": "..."}, ...],
  "experience": [{"title": "...", "description": "..."}, ...],
  "projects": [{"title": "...", "description": "..."}, ...]
}

Rules:
- technicalSkills: list of technical skills (e.g., Angular, TypeScript, Python). For each, the description should be a concise summary of the candidate's relevant experience with that skill, based ONLY on what the CV states.
- experience: list of professional roles. The title should be the job title + company (e.g., "Forward Deployed Engineer — PNC Bank"). The description should summarize the role's scope and key contributions.
- projects: list of named projects. The title should be the project name. The description should summarize what the project did and the candidate's contribution.
- Do NOT invent information. If the CV doesn't mention a skill, role, or project, do not include it.
- Do NOT include markdown code fences in your response. Return raw JSON only.

CV TEXT:
"""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

def _get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise LlmExtractionError("GEMINI_API_KEY not set in environment")
    return genai.Client(api_key=api_key)


def _get_fallback_models():
    """Return an ordered list of models to try. Primary first, then fallbacks."""
    primary = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    fallbacks = [
        "gemini-flash-lite-latest",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
    ]
    # Deduplicate while preserving order
    models = [primary]
    for m in fallbacks:
        if m not in models:
            models.append(m)
    return models


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers around JSON."""
    text = text.strip()
    # Match ```json\n{...}\n``` or ```\n{...}\n```
    match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```$", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def extract_cv_data(cv_text: str) -> CVAnalysis:
    """Take raw CV text, return a validated CVAnalysis object.

    Raises:
        LlmExtractionError: if the LLM fails, returns invalid JSON, or the JSON
        doesn't conform to the CVAnalysis schema.
    """
    if not cv_text or not cv_text.strip():
        raise LlmExtractionError("Empty CV text provided")

    client = _get_client()

    prompt = EXTRACTION_PROMPT + cv_text

    errors = []
    response = None
    last_model = None
    for candidate in _get_fallback_models():
        try:
            response = client.models.generate_content(
                model=candidate,
                contents=prompt,
            )
            last_model = candidate
            break
        except Exception as e:
            errors.append(f"{candidate}: {type(e).__name__}: {str(e)[:100]}")

    if response is None:
        raise LlmExtractionError(
            f"All Gemini models failed. Errors: {' | '.join(errors)}"
        )

    raw = response.text.strip() if response.text else ""
    if not raw:
        raise LlmExtractionError("Gemini returned empty response")

    cleaned = _strip_markdown_fences(raw)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise LlmExtractionError(
            f"Gemini returned invalid JSON: {e}. First 200 chars: {cleaned[:200]!r}"
        ) from e

    try:
        return CVAnalysis(**data)
    except Exception as e:
        raise LlmExtractionError(f"JSON didn't match CVAnalysis schema: {e}") from e