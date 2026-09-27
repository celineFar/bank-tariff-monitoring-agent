"""Drive the real resolve_request tool with a fake ToolContext (no Gemini)."""

import asyncio
from types import SimpleNamespace

from app.config.models import IntentResolutionSettings
from app.config.seed_catalog import load_seed_catalog
from app.services.intent_resolution import RequestResolver
from app.tools import resolve_request, services
from app.tools._state import (
    MONITOR_AUTHORIZATION_KEY,
    MONITOR_OFFER_KEY,
    ORIGINAL_QUESTION_KEY,
    TARIFF_PLAN_KEY,
)


class Ctx:
    def __init__(self, state, invocation, text):
        self.state = state
        self.invocation_id = invocation
        self.session = SimpleNamespace(
            id="sess",
            events=[
                SimpleNamespace(
                    author="user",
                    invocation_id=invocation,
                    content=SimpleNamespace(parts=[SimpleNamespace(text=text)]),
                )
            ],
        )


def summary(tag, out, state):
    plan = state.get(TARIFF_PLAN_KEY)
    print(
        f"  {tag}: intent={out.get('intent')} cont={out.get('continuation_intent')} "
        f"lang={out.get('language')} product={out.get('product')} "
        f"offering={out.get('offering_id')} clarify={out.get('needs_clarification')} "
        f"status={out.get('status')} reason={out.get('reason_code')}\n"
        f"      plan={'set: ' + plan['operation'] + ' ' + str(plan['fields'][:3]) if plan else None} "
        f"spend={state.get(MONITOR_AUTHORIZATION_KEY)} "
        f"orig_q={state.get(ORIGINAL_QUESTION_KEY)!r}"
    )


async def turn(state, n, text, calls=1):
    print(f"turn {n}: {text!r} (resolve_request x{calls})")
    for i in range(calls):
        ctx = Ctx(state, f"inv-{n}", text)
        out = await resolve_request(text, ctx)
        summary(f"call {i + 1}", out, state)


async def main():
    services.request_resolver = RequestResolver(
        load_seed_catalog(), IntentResolutionSettings()
    )
    services.reviews = None

    print("== same-turn double call after a clarification")
    state = {}
    await turn(state, 1, "What's the mortgage rate?")
    await turn(state, 2, "3", calls=2)

    print("\n== Armenian question, numeric reply")
    state = {}
    await turn(state, 1, "Ինչքա՞ն է հիփոթեքի տոկոսադրույքը")
    await turn(state, 2, "2")

    print("\n== monitoring offer, natural affirmative replies")
    for reply in ("yes", "yes, refresh it", "ok", "sure", "👍"):
        state = {}
        await turn(state, 1, "What's the express mortgage rate?")
        # What get_current_tariffs stores when the value is missing.
        state[MONITOR_OFFER_KEY] = {
            "product": "mortgage",
            "offering_id": "mortgage_express",
            "invocation_id": "inv-1",
        }
        try:
            await turn(state, 2, reply)
        except Exception as exc:  # noqa: BLE001
            print(f"  RAISED {type(exc).__name__}: {exc}; offer now={state.get(MONITOR_OFFER_KEY)}")

    print("\n== 'yes' twice in the same turn")
    state = {}
    await turn(state, 1, "What's the express mortgage rate?")
    state[MONITOR_OFFER_KEY] = {
        "product": "mortgage",
        "offering_id": "mortgage_express",
        "invocation_id": "inv-1",
    }
    await turn(state, 2, "yes", calls=2)


asyncio.run(main())
