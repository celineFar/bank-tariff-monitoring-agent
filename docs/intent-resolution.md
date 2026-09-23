# Intent and catalog resolution

`RequestResolver` is the only natural-language boundary that selects a tariff intent,
product family, or offering. Typed API and scheduler commands already contain canonical
IDs and do not invoke it.

## Resolution order

1. Normalize Unicode with NFKC, case folding, punctuation/separator collapse, trimming,
   and whitespace collapse. Reviewed Armenian grammatical suffixes are stripped only for
   catalog token matching; the original request and detected language remain unchanged.
2. Detect English, Armenian, or mixed-script input. Mixed input uses English labels by
   default while retaining its `mixed` language classification.
3. Classify the request into the approved eight-value intent taxonomy using deterministic
   English and Armenian patterns.
4. Match canonical IDs, localized primary names, aliases, synonyms, and checked-in
   transliterations exactly.
5. If exact matching is insufficient, rank catalog entries with bounded string similarity.
   A fuzzy winner is accepted only when both the configured minimum score and minimum gap
   are met.
6. Only then, call the tool-free Gemini classifier with an explicit list of allowed intent
   values and candidate IDs. Python rejects any output outside those lists.
7. If model/API/structured-output validation fails or candidates remain tied, return a
   typed clarification. Never guess a family or offering.

The thresholds are configured by `INTENT_FUZZY_MIN_SCORE`, `INTENT_FUZZY_MIN_GAP`,
`INTENT_MAX_CANDIDATES`, and `INTENT_CLASSIFIER_MAX_ATTEMPTS`.

## Intent taxonomy

- `list_supported_products`
- `answer_indexed_tariff_question`
- `get_current_tariffs`
- `start_monitoring_run`
- `get_run_status`
- `get_change_history`
- `unsupported_or_general`
- `clarification_response`

List, status, history, and unsupported/general requests do not require product scope.
Broad current-tariff overviews may also remain family-wide or catalog-wide. A current or
indexed question asking for one rate, fee, amount, term, or other scalar cannot stop at a
family: it returns all configured offerings in that family as clarification choices.
Family-wide monitoring remains valid and covers every enabled offering in that family.

## Session state

Only conversational resolution state is stored in the ADK session:

- whether the short introduction has been shown;
- a pending clarification with bounded canonical options; and
- the latest resolved family/offering.

A clarification reply can select an option by number, canonical ID, complete label, or an
unambiguous phrase such as “the express one.” The resulting
`clarification_response` retains the original `continuation_intent`, clears pending state,
and updates the latest scope. Invalid serialized state is discarded rather than trusted.
An explicit new tariff intent or cancellation replaces and clears pending clarification;
an ambiguous short reply keeps the same bounded choices. The first resolver result also
returns a short catalog introduction generated from the checked-in catalog. It names both
families and up to three offerings per family, offers the full list, and is suppressed on
later turns. A list request returns all thirteen configured offerings.

If the agent has just offered a refresh for stale or missing accepted data, an explicit
affirmative reply resolves to `start_monitoring_run` for the last canonical scope and
creates the same one-use authorization as a direct refresh request. An affirmative reply
without a prior resolved scope cannot authorize monitoring.

No personal preference or cross-session memory is created.

## Agent routing and wording

The root instruction requires `resolve_request` before every business tool. Armenian
input receives Armenian output, English receives English, and mixed input uses its
dominant language. Broad family monitoring covers every enabled offering; broad overview
reads cover all indexed offerings; single-value family questions clarify the offering.
Current values come only from accepted snapshots. Stale values state their accepted time
and seven-day threshold, missing values are not invented, and pending-review candidate
values stay hidden. Unsupported requests produce a short capability-boundary response
without financial advice or unrelated tools.

## Monitoring authorization

`resolve_request` does not acquire sources or submit runs. When—and only when—it resolves
`start_monitoring_run` without ambiguity, it writes a temporary, one-use authorization for
the exact family/offering scope. `start_tariff_monitoring` requires and consumes that
authorization before calling `RunService`.

This tool-level check prevents an LLM tool-routing error from turning catalog, current,
history, status, indexed-question, clarification, or unsupported intents into a monitoring
run. Typed `POST /api/v1/runs` and scheduler entry points bypass natural-language
classification because their canonical commands are already trusted application inputs.

## Gemini boundary

The fallback classifier has no tools. Its prompt contains only the bounded request,
detected language, allowed enum values, and supplied catalog candidates. The Pydantic
response is validated again by Python. A nonexistent candidate, disallowed intent,
missing final response, malformed JSON, or exhausted API call becomes clarification or a
safe unresolved result; it never becomes a business action.

The versioned behavioral suite in `tests/eval/` covers all eight intents, all thirteen
offerings, Armenian/English requests, fuzzy aliases, ambiguity, stale wording, and routing
safety. Multi-turn clarification continuation remains a deterministic session test because
ADK 2.9.2 does not permit state-bearing initialization events in an eval case.
