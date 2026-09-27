# Intent and catalog resolution

`RequestResolver` is the only natural-language boundary that selects a tariff intent,
product family, offering, and the shape of a tariff question. Typed API and scheduler
commands already contain canonical IDs and do not choose a scope through it.

## Resolution order

Every chat turn makes one tool-free Gemini call, the *request interpreter*
(`AdkRequestInterpreter`), and code checks what it proposes:

1. **Build the request.** It holds:
   - the message, verbatim;
   - a bounded conversation context (below);
   - the whole checked-in catalog: 2 families and the enabled offerings, with
     English and Armenian names, aliases, synonyms and transliterations;
   - the allowed values: intents, reply kinds, operations, the field-path taxonomy
     with labels, rank directions and currencies.
2. **Interpret.** The call returns a `RequestInterpretation`
   (`app/domain/interpretation.py`), in which every value is an enum or a bounded
   string:
   - `intent`, and `replies_to` / `accepts` for a reply to a pending question;
   - `language`;
   - `product`, `offering_ids`, `family_wide`;
   - `standalone_question`: the request as one self-contained question;
   - `query`: operation, fields, rank field and direction, currency;
   - an optional clarification request.

   The temperature is 0 and there is no thinking budget. The model is the configured
   `generation_model`.
3. **Validate** (`InterpretationValidator`, `app/services/interpretation_validation.py`).
   Code derives everything with authority:
   - **V1:** IDs exist and are enabled; offerings decide the family; offerings from
     two families ask for the family.
   - **V2:** the operation matches the scope. `single` means one offering; `compare`
     and `overview` mean 2 or more offerings or the whole family; `family_rank`
     needs one rankable field and a direction, otherwise it becomes an `overview` of
     that field.
   - **V3:** a family-wide read only when the user asked about the family, and never
     for a single value. This also applies to a reply given to a clarification that
     asked for one value.
   - **V4:** a reply to a monitoring offer or scope question counts only when such a
     question was asked in the previous turn, and its scope is the offer's.
   - **V5:** an offering named verbatim in the message (the exact catalog matcher)
     that the interpretation replaced with another, without context to explain it,
     becomes a clarification between the two.
   - **V6:** a message with no letters ("2", "👍") keeps the conversation's language.
     Otherwise the script decides between English and Armenian, and the interpreter
     only settles `mixed`.
   - **V9:** the standalone question is the question of record, falling back to the
     message.
   - **V10:** clarification options are built from catalog labels, in catalog order:
     all offerings of one family, or both families, never a mix.
4. **Fail closed.** If the call fails, or its output is outside the schema or the
   catalog, the turn is *unavailable* (`InterpretationUnavailable`). There is no
   keyword fallback: the chat agent runs on the same model, and a guess would never
   be authority for a scope.

`INTENT_CLASSIFIER_MAX_ATTEMPTS` bounds the attempts of the interpreter call.

## Intent taxonomy

- `list_supported_products`
- `answer_indexed_tariff_question`: any tariff value or condition, including "current"
  values, comparisons, listings and rankings
- `get_current_tariffs`: freshness and coverage (whether stored data is up to date,
  which fields are stored), never values
- `start_monitoring_run`: an explicit request to check the bank's site now; a question
  that merely mentions refreshing is not one
- `get_run_status`
- `get_change_history`
- `review_pending_candidates`
- `unsupported_or_general`
- `clarification_response`: produced by code for a reply to a clarification; the
  resolved intent is its `continuation_intent`

Each resolution carries `route`, the tool that serves its intent, decided by code.

## Session state

Only conversational resolution state is stored in the ADK session:

- whether the short introduction has been shown;
- a pending clarification: the standalone question, its intent, whether it asked for one
  value, and its bounded canonical options;
- the latest resolved family and offerings, and the previous standalone question (for
  follow-ups such as "what about the term?" or "refresh it");
- the conversation language.

The interpreter sees this as its context, together with a monitoring offer or scope
question made in the previous turn. A clarification reply can select an option any way
the user phrases it: a number, "option 3", a label, "the express one", or an offering
that was not among the options. The resulting `clarification_response` keeps the
original `continuation_intent`, clears the pending state, and records the new scope. A
new request replaces the pending clarification. Invalid serialized state is discarded
rather than trusted. The first resolver result also returns a short catalog
introduction; a list request returns all thirteen configured offerings.

## Agent routing and wording

`resolve_request` takes no arguments: it reads the user's message itself. It runs once
per turn; a repeat call in the same turn returns the first result and changes nothing.
The agent follows the result's `route`. Armenian input receives Armenian output, English
receives English, and mixed input uses its dominant language. An unavailable
interpretation is reported as such, and the user is asked to rephrase.

## Monitoring authorization

`resolve_request` never acquires sources or submits runs. It writes a spend grant, for
the exact family/offering scope and bound to the current ADK invocation, only in two
cases:

- it resolves `start_monitoring_run` without ambiguity; or
- the user explicitly accepts (`accepts = true`) the monitoring offer made in the
  immediately preceding turn.

`run_tariff_monitoring` requires a grant from this invocation whose scope equals its
arguments. A whole-family run also requires an explicit yes to the scope question, in
the turn after it was asked; any other message, including another refresh request, is
not a confirmation. The offer is written by `get_current_tariffs` from the turn's read
grant, never from a tool argument, and any resolved turn clears it.

`review_pending_candidates` needs a resolution in the same turn but no spend grant:
reviewing starts no run.

## Gemini boundary

The interpreter has no tools and holds no privilege. Its input is the bounded request
above; its output is a proposal, and the interpreter never supplies a scope or a spend
grant itself. Grants, clarification options, the plan's bounds, the method and the
route are decided by code from the catalog and the session state. The chat model passes
no scope and no text to any business tool.

## Testing

The interpretation case set, `tests/fixtures/interpretation_cases.py`, covers:

- all intents and all thirteen offerings;
- English, Armenian, mixed and transliterated input;
- follow-ups, clarification replies and monitoring offers;
- the whole-family confirmation;
- safety cases (injected claims, a refresh question, a single value at family scope).

It is recorded from the live interpreter by `scripts/record_interpretations.py`, which
needs `GEMINI_API_KEY`. The unit tests (`tests/unit/test_interpretation_cases.py`,
`tests/unit/test_tool_flows.py`) replay the recordings offline. Re-record after
changing the interpreter instruction, the catalog, or the context shape.
