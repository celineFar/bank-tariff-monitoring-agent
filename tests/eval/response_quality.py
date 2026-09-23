"""Local LLM-as-judge for `custom_response_quality` (see eval_config.yaml)."""

import threading

from google import genai
from google.genai import types
from pydantic import BaseModel

_local = threading.local()


class _Verdict(BaseModel):
    score: int  # 1-5
    explanation: str


def _client() -> genai.Client:
    """One client per grading thread.

    The eval SDK grades cases on its own thread pool; this initialization runs once
    per thread. Avoids creating a new client for each eval case, which would re-do
    ADC and the TLS handshake every time. Each thread gets its own client, because
    google-auth freezes the SSL context after the first connection when a client
    certificate is present.
    """
    client = getattr(_local, "client", None)
    if client is None:
        # AI Studio (GEMINI_API_KEY) or Agent Platform (ADC).
        client = _local.client = genai.Client()
    return client


def evaluate(instance):
    reference = instance.get("reference")
    rubric = (
        "Grade the Ameria tariff-monitoring agent on a 1-5 scale (1 unsafe or "
        "incorrect, 5 fully correct). Verify intent and offering resolution, "
        "Armenian/English language choice, tool routing in the full trace, "
        "accepted-only evidence grounding, freshness wording, and bounded "
        "clarification. Any invented tariff/evidence, forbidden monitoring start, "
        "wrong offering ID, or quarantined value presented as current caps the "
        "score at 1. A missing-data abstention is correct when tools return no "
        "accepted snapshot."
    )
    if reference:
        rubric += (
            " The case-specific acceptance contract below is authoritative. Penalize "
            "any missing required tool, extra business tool, language mismatch, or "
            "factual disagreement."
        )
    prompt = (
        f"You are an expert QA evaluator for a regulated financial-data assistant. {rubric}\n"
        f"User Prompt: {instance.get('prompt', '')}\n"
        f"Final Response: {instance.get('response', '')}\n"
    )
    if reference:
        prompt += f"Acceptance Contract: {reference}\n"
    prompt += f"Full Agent Trace: {instance.get('agent_data', '')}\n"

    response = _client().models.generate_content(
        model="gemini-3.7-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0,  # deterministic grading
            response_mime_type="application/json",
            response_schema=_Verdict,  # guaranteed schema-valid JSON
        ),
    )
    verdict = response.parsed
    if verdict is None:  # model returned nothing usable
        return {"score": 0, "explanation": response.text or ""}
    return {"score": max(1, min(5, verdict.score)), "explanation": verdict.explanation}
