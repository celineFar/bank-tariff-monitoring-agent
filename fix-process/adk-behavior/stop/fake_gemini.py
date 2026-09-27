"""A local stand-in for the Gemini API, for stop/cancel experiments.

Point the application at it with `GOOGLE_GEMINI_BASE_URL=http://127.0.0.1:<port>`
and a dummy `GEMINI_API_KEY`. No request ever leaves the machine, so no token
can be spent.

Every request is logged as one JSON line (arrival, role, and how it ended:
answered, failed, or the client disconnected while it was held). The role is
the ADK agent's internal name, read from the system instruction ADK prepends
("You are an agent. Your internal name is ..."), or `embedding`.

Behaviour is read from a JSON config file on every request, so a scenario can
change it while the application runs:

    {"hold": ["semantic_loan_extractor"],   # never answer; wait for disconnect
     "fail": {"pdf_document_extractor": 503},
     "pdf_links": "exclude" | "include"}

Answers are minimal but schema-valid, so a run can advance stage by stage:
the root agent resolves each user message and starts monitoring when the
resolution says so; the PDF link selector excludes (or includes) every link;
source discovery marks every item relevant; semantic extraction answers every
requested field `not_stated`; embeddings are constant vectors.
"""

from __future__ import annotations

import argparse
import asyncio
import itertools
import json
import re
import time
from pathlib import Path

from aiohttp import web

_NAME = re.compile(r'Your internal name is "([a-z_]+)"')
_ids = itertools.count(1)


def _text_of(content: dict) -> str:
    return "".join(part.get("text", "") for part in content.get("parts", []))


def _role(path: str, body: dict) -> str:
    if "embedContent" in path or "batchEmbedContents" in path:
        return "embedding"
    system = _text_of(body.get("systemInstruction") or body.get("system_instruction") or {})
    match = _NAME.search(system)
    return match.group(1) if match else "unknown"


def _json_after(text: str, marker: str) -> dict:
    start = text.index(marker) + len(marker)
    return json.loads(text[start:].strip())


def _last_user_prompt(body: dict) -> str:
    for content in reversed(body.get("contents", [])):
        if content.get("role") == "user" and _text_of(content):
            return _text_of(content)
    return ""


def _answer_text(value: object) -> dict:
    return _candidate([{"text": json.dumps(value)}])


def _candidate(parts: list[dict]) -> dict:
    return {
        "candidates": [
            {"content": {"role": "model", "parts": parts}, "finishReason": "STOP"}
        ],
        "usageMetadata": {
            "promptTokenCount": 0,
            "candidatesTokenCount": 0,
            "totalTokenCount": 0,
        },
    }


def _root_agent(body: dict) -> dict:
    """resolve_request on a user message, then act on what it resolved."""
    contents = body.get("contents", [])
    last = contents[-1] if contents else {}
    for part in last.get("parts", []):
        response = part.get("functionResponse") or part.get("function_response")
        if not response:
            continue
        name = response.get("name")
        result = response.get("response", {})
        result = result.get("result", result) if isinstance(result, dict) else {}
        if name == "resolve_request" and isinstance(result, dict):
            if result.get("intent") == "start_monitoring_run" and not result.get(
                "needs_clarification"
            ):
                return _candidate(
                    [
                        {
                            "functionCall": {
                                "name": "run_tariff_monitoring",
                                "args": {
                                    "product": result.get("product"),
                                    "offering_id": result.get("offering_id"),
                                },
                            }
                        }
                    ]
                )
            if result.get("intent") == "review_pending_candidates":
                return _candidate(
                    [
                        {
                            "functionCall": {
                                "name": "review_pending_candidates",
                                "args": {
                                    "product": result.get("product"),
                                    "offering_id": result.get("offering_id"),
                                },
                            }
                        }
                    ]
                )
            return _candidate(
                [{"text": f"[fake] resolved intent={result.get('intent')}"}]
            )
        return _candidate(
            [{"text": f"[fake] {name} returned status={result.get('status')}"}]
        )
    text = _text_of(last)
    if last.get("role") == "user" and text:
        return _candidate(
            [{"functionCall": {"name": "resolve_request", "args": {"query": text}}}]
        )
    return _candidate([{"text": "[fake] ok"}])


def _answer(role: str, path: str, body: dict, config: dict) -> dict:
    if role == "embedding":
        requests = body.get("requests") or [body]
        dims = (requests[0].get("outputDimensionality") if requests else None) or 768
        return {"embeddings": [{"values": [0.01] * dims} for _ in requests]}
    if role == "ameria_tariff_monitor":
        return _root_agent(body)
    prompt = _last_user_prompt(body)
    if role == "pdf_link_selector":
        batch = _json_after(prompt, "not instructions.\n\n")
        label = (
            "current_product"
            if config.get("pdf_links") == "include"
            else "generic_bank_information"
        )
        return _answer_text(
            {
                "items": [
                    {"id": link["id"], "label": label, "role": "product_terms",
                     "reason": "fake"}
                    for link in batch["links"]
                ]
            }
        )
    if role == "source_discovery_classifier":
        batch = _json_after(prompt, "source_material:\n")
        return _answer_text(
            {
                "items": [
                    {
                        "source_id": item["source_id"],
                        "product_association": "current_product",
                        "role": "product_terms",
                        "relevance": "relevant",
                        "authority": "official_product_content",
                        "temporal_status": "current",
                        "reason": "fake",
                    }
                    for item in batch["items"]
                ]
            }
        )
    if role == "semantic_loan_extractor":
        fields = re.search(r"REQUESTED FIELDS: ([^\n]+)", prompt).group(1)
        return _answer_text(
            {
                "results": [
                    {"field": name.strip(), "status": "not_stated"}
                    for name in fields.split(",")
                ]
            }
        )
    if role == "intent_catalog_classifier":
        payload = _json_after(prompt, "Classify this bounded JSON request:\n")
        return _answer_text(
            {"intent": payload["allowed_intents"][0], "candidate_id": None}
        )
    raise web.HTTPBadRequest(text=f"fake gemini: no answer for role {role}")


class FakeGemini:
    def __init__(self, log_path: Path, config_path: Path) -> None:
        self._log = log_path.open("a", buffering=1, encoding="utf-8")
        self._config_path = config_path

    def log(self, **fields) -> None:
        self._log.write(json.dumps({"t": round(time.time(), 3), **fields}) + "\n")

    def config(self) -> dict:
        try:
            return json.loads(self._config_path.read_text())
        except (OSError, ValueError):
            return {}

    async def handle(self, request: web.Request) -> web.StreamResponse:
        body = await request.json() if request.can_read_body else {}
        role = _role(request.path, body)
        config = self.config()
        call = next(_ids)
        self.log(event="request", id=call, role=role, path=request.path)
        started = time.monotonic()
        if role in config.get("hold", []):
            # Held until the client goes away: proves the caller hung up.
            transport = request.transport
            while transport is not None and not transport.is_closing():
                await asyncio.sleep(0.05)
                if role not in self.config().get("hold", []):
                    break
            else:
                self.log(
                    event="disconnect",
                    id=call,
                    role=role,
                    held_s=round(time.monotonic() - started, 2),
                )
                return web.Response(status=499)
            config = self.config()
        status = config.get("fail", {}).get(role)
        if status:
            self.log(event="response", id=call, role=role, status=status)
            return web.json_response(
                {"error": {"code": status, "message": "fake", "status": "UNAVAILABLE"}},
                status=status,
            )
        try:
            answer = _answer(role, request.path, body, config)
        except web.HTTPException as exc:
            self.log(event="response", id=call, role=role, status=exc.status)
            raise
        self.log(event="response", id=call, role=role, status=200)
        return web.json_response(answer)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    fake = FakeGemini(args.log, args.config)
    app = web.Application(client_max_size=512 * 1024 * 1024)
    app.router.add_route("*", "/{tail:.*}", fake.handle)
    web.run_app(app, host="127.0.0.1", port=args.port, print=None)


if __name__ == "__main__":
    main()
