"""Deterministic fact coverage for `fact_coverage` (see seed_url_eval_config.yaml).

Reads the case's `metadata.required_facts` (each fact passes when any of its
regex alternatives matches the final response) and `metadata.forbidden_claims`
(any match fails the case). No model call, so it grades the same way every time.
"""

import re


def _response_text(response) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return "\n".join(part.get("text") or "" for part in response.get("parts") or [])
    return str(response or "")


def evaluate(instance):
    metadata = instance.get("metadata") or {}
    required = metadata.get("required_facts") or []
    forbidden = metadata.get("forbidden_claims") or []
    text = _response_text(instance.get("response"))
    flags = re.IGNORECASE | re.DOTALL

    missing = [
        fact["id"]
        for fact in required
        if not any(re.search(pattern, text, flags) for pattern in fact["any_of"])
    ]
    violations = [
        claim["id"]
        for claim in forbidden
        if any(re.search(pattern, text, flags) for pattern in claim["any_of"])
    ]
    covered = len(required) - len(missing)
    score = covered / len(required) if required else 1.0
    if violations:
        score = 0.0
    explanation = f"{covered}/{len(required)} required facts present"
    if missing:
        explanation += f"; missing: {', '.join(missing)}"
    if violations:
        explanation += f"; forbidden claims made: {', '.join(violations)}"
    return {"score": round(score, 3), "explanation": explanation}
