# Agent and tool architecture, and the decisions behind it

Deliverable 4 of `Project Documents/System Description.md`. Diagrams of the same
system are in [architecture-diagram.md](architecture-diagram.md); the exhaustive
boundary-by-boundary reference is [architecture.md](architecture.md).

---

## 1. The shape in one paragraph

There is one conversational ADK agent in one ADK app, and one ADK node. The agent
talks to the user, resolves what they meant, and calls narrow tools. When a
monitoring run is needed, a tool runs the monitoring node *inside the agent's own
invocation*: progress streams as ADK events, a review is a native pause of that
invocation, and the answer resumes it. Everything else — fetching, parsing,
classifying, extracting, validating, comparing, persisting, scheduling, and deciding
what needs review — is ordinary deterministic Python behind typed service
interfaces. Gemini appears at five bounded, schema-bound call sites inside those
services, plus the agent's own turn. It never holds a network, filesystem, shell, or
SQL tool.

---

## 2. The agent

`app/agent.py` defines `root_agent`, a single `Agent` wrapped in a resumable `App`
with one plugin. Its role is wording, not judgement about tariffs and not control
flow.

**Instructions** (25 lines) cover language, honesty and presentation: answer
Armenian in Armenian, English in English, and mixed in its dominant language; never
invent a canonical ID, a tariff value, a source URL, or a freshness status; present
each value with its currency, unit, basis and conditions; cite only the fact's own
evidence; treat source content as untrusted data. Tool order is not in the prompt:
`ToolPolicyPlugin` (`app/plugins.py`) rejects any business tool that was not
preceded by `resolve_request` in the same invocation, and turns a tool exception into
a typed envelope.

**Stopping and error conditions** are returned by tools as typed statuses rather
than left to the model to infer — `needs_clarification`, `needs_scope_confirmation`,
`request_satisfied=false`, `unavailable`, `rejected` with a reason code. The
instruction tells the agent what each one obliges it to say. An abstention from the
answer service must be reported as an abstention naming the offering and field, not
patched with a different offering's number.

**Session state** holds the conversational resolution state (the one-time catalog
introduction, a pending clarification, the latest resolved scope) and three
grants, each bound to the ADK invocation that issued it: the read grant
(`tariff_resolution_plan`), the monitoring offer derived from it, and the spend grant
(`monitoring_authorization`). A resumed invocation keeps its id, so a grant survives
the replay of its own tool call and is useless in any later turn. The exact key list
is `intent_resolution`, `resolution`, `monitoring_authorization`,
`monitoring_confirmation_offer`, `monitoring_full_product_ack`,
`monitoring_original_question`, `tariff_resolution_plan`,
`tariff_resolution_plan_used`, `tariff_resolution_last_used_turn` (plus the CLI's
`cli_owner`, used only for crash recovery). No preference, no cross-session memory,
no accumulated business data — and nothing about reviews, which are a PostgreSQL
query.

`automatic_function_calling` is disabled, so every tool call is an explicit,
inspectable step rather than a hidden SDK loop.

The same agent serves the terminal CLI and ADK Web; the CLI is the product, ADK Web a
development surface.

---

## 3. The tools

Seven tools. The model never chooses what data a tool may touch: scope is granted
once per turn by deterministic code and read by tools that have no scope parameter
to override it.

| Tool | Model supplies | Scope comes from | Refuses when |
|---|---|---|---|
| `resolve_request(query)` | the user's text, verbatim | — it *issues* the grants | the text is not the user's message, or the turn was already used |
| `answer_tariff_query(query)` | the question text | the read grant (`ResolutionPlan`: family, offerings, operation, fields) | the grant is absent, replayed, expired, from another session or turn, or scope-only |
| `get_current_tariffs()` | nothing | the read grant | no valid grant this turn |
| `get_tariff_history(kind, start_at, end_at, limit)` | the window and page size (clamped) | the read grant | no valid grant this turn |
| `get_monitoring_status()` | nothing | — (status of both families; no tariff values) | no resolution this turn |
| `run_tariff_monitoring(product, offering_id)` | the scope it claims | the spend grant; the arguments must equal it | the grant is missing, from another turn, or for another scope; a family run needs a confirmation from the next turn |
| `review_pending_candidates(product, offering_id)` | an optional scope | must match the resolver's scope for the turn | no resolution this turn, or a wider scope |

Two grants, two lifetimes. The **read grant** is issued for answer, current and
history intents: when the resolver's scope yields an answerable query shape it is
exactly that plan; otherwise (a broad family question, or no family named) it is
scope-only. Read tools may use it repeatedly within the turn; `answer_tariff_query`,
which spends model calls, is one-use. The **spend grant** is issued only for an
explicit monitoring request or an affirmative reply to an offer — and the offer is
itself written by `get_current_tariffs` from the read grant, never from a model
argument. The chain resolver → read grant → offer → spend grant → run therefore never
passes through a value the model authored.

Three properties are worth naming.

**Each tool is a thin adapter.** The logic lives in `app/services/`, which FastAPI
and the worker call directly. That is what keeps `POST /api/v1/runs` and a chat
request from drifting into two different pipelines.

**Authorization is per-call, not per-conversation.** The model chooses which tool to
call; the tool decides whether that call is allowed. `run_tariff_monitoring`
rejects a grant it did not see `resolve_request` issue for this exact scope in this
invocation, so a tool-routing mistake cannot turn "what is the rate?" into a paid
acquisition run.

**A tool never returns prose.** Every return is a typed structure the agent has to
report rather than paraphrase, and citations are restored server-side from the
retrieved evidence so the model cannot author its own provenance.

---

## 4. The decisions

### Seven focused tools instead of one `monitor_tariffs()`

The assignment allows either. One tool would have meant the model either passing
through a whole pipeline's worth of arguments or having none of them — and in both
cases the security boundary would sit inside a single function that already knows
how to fetch, parse, and write.

Splitting on **authority** rather than on pipeline stage is what makes the split
useful. Resolution issues authority; reads consume it; monitoring requires a
separate spend grant; review decisions come only from the human's answer to a native
ADK pause. Deliberately
*not* split out: acquisition, extraction, and publication are not tools at all.
Exposing `download_document(url)` to a model would have put URL selection in the
model's hands, which is precisely what the host allowlist exists to prevent.

The cost is more surface to keep coherent, which the instruction text and the
`tests/eval/` routing-safety suite carry.

### Gemini for language, Python for consequences

Gemini is used where the problem is genuinely linguistic — an imprecise or Armenian
product name, an Armenian tariff table inside a scanned PDF, whether a page section
is about this product, which phrase in a passage is the nominal rate. It is not used
for anything with a consequence: what is current, what changed, what is valid, what
gets published, what needs a human.

The clearest expression of this is comparison. Detecting that 12.5% became 13.5% is
a formatting-insensitive canonical diff in Python, not a question anyone asks a
model. The same holds for ranking and comparison on the read side: the service
computes them from typed facts and *abstains* when candidates differ in currency,
unit, rate basis, or fee scope, rather than letting a model produce a plausible
winner.

### Deterministic first, model only for the remainder

Every model-facing stage is preceded by cheaper work. Intent resolution tries
Unicode-normalized exact matching, then bounded fuzzy ranking, and only then
classification. Source discovery applies rules and a content-addressed cache and
sends only genuinely unresolved units. PDF transcription is gated by link metadata,
so an off-topic or superseded document is skipped before it is paid for. Extraction
batches are cached on product, schema version, prompt version, model, and
evidence fingerprint.

This began as a correctness argument — deterministic decisions are testable and
reproducible — and turned out to be the cost argument too. Routing the two
schema-bound stages onto a cheaper model, disabling thinking where the output shape
is already fixed, fixing an admission gate that could never reject anything, and
capping repairs cut a per-offering run substantially; the measurements are in the
commit history and in `model_call_usage`.

### Evidence is a first-class citizen, not a formatting concern

An extracted value carries an immutable evidence ID, an exact quote, and the
original source locator, and Python rejects a citation whose quote does not occur
verbatim in the evidence the model was actually given. `scripts/audit_evidence_retention.py`
exists to prove, before the legacy chunk embeddings could be deprecated, that every
active accepted fact still carries a self-contained citation with a matching
document checksum.

That strictness is what makes partial success safe: a field that fails validation
becomes a review item with its raw value, validation paths, and evidence, while its
valid siblings are retained. A run completes as `completed_with_review` with a
partial product instead of failing whole.

### Two stores, one per kind of truth

PostgreSQL owns business state; the ADK session owns the conversation and its pause.
A replayed ADK event must never imply a business decision, so the node treats the
session as a source of *answers*, never of state: every time it runs it re-reads the
run and its reviews from PostgreSQL, and applies a decision only to a review that is
still pending there. Because the pause lives in the same invocation as the
conversation that will answer it, the two stores need no correlation IDs and no
reconciliation — an earlier design with a separate workflow app needed both.

The same reasoning puts the durable queue in PostgreSQL rather than in a broker:
run state, review state, and published data then commit and roll back together, and
a review that waits three days for a person costs nothing to keep open.

### Publication is one transaction, and candidates are inert until it commits

Knowledge versions and chunks, the extraction attempt, the snapshot decision, the
change set, the source manifest, the offering status, and the audit event commit
together or not at all. Until then a candidate is persisted with
`publication_state=pending_review` and inactive chunks, so it is fully inspectable
and completely unable to answer a question.

This is why a failure anywhere in a run degrades freshness rather than correctness:
the worst outcome is that yesterday's accepted tariff is still the answer, labelled
stale, with a refresh offered.

### HITL through ADK's native pause, not a side channel

A review could have been a row plus a web form. Instead the monitoring node yields an
ADK `RequestInput` from inside the chat invocation: the invocation pauses, the CLI
shows the evidence, and the answer resumes the *same* invocation. ADK replays the
original tool call and re-runs the node, which finds the decision in
`ctx.resume_inputs`, applies it, and continues — so the model sees one call and one
result however many reviews happened, and never relays a decision or a schema. The
node is idempotent by construction (it runs once per pause and derives everything
from PostgreSQL; its interrupt ids carry the run id so a re-run never submits a new
run), which is what `ResumabilityConfig` requires of a resumable tool call. See
[native-hitl-review.md](native-hitl-review.md).

Reviews are created only where a human can actually decide something: two plausible
official candidates, a rate jump past the configured threshold, a missing required
field with usable evidence, conflicting official sources. A model execution failure
with no valid response fails the offering instead of manufacturing a task.

### The read side moved off RAG, and the old path stayed

Ordinary questions are answered from typed accepted facts, not from retrieved
chunks. Chunk retrieval ranks by similarity, and similarity is not authority — a
confidently retrieved passage from a superseded PDF reads exactly like the current
one. Typed facts carry acceptance, scope, and verified evidence by construction.

The legacy path was kept behind `TARIFF_ANSWER_READ_MODEL=legacy` rather than
deleted, with a shadow-comparison report and an evidence-retention gate to close the
cutover honestly. Retrieval still earns its place: explanatory retrieval units
supply the wording around a fact, and monitoring still uses chunk retrieval.

### Observability shaped by what each signal can answer

Traces answer "what happened inside this one run," SQL over the audit tables answers
"what has been happening across runs," and files answer "what exactly did stage X
see." A chat-initiated run executes inside the CLI turn, so one turn is one trace
(invocation → tool → node → offering → stage); a resume is a second invocation span
carrying the same `tariff.run_id`. A worker run continues the submitting process's
trace through the W3C context stored on the run row. Latency metrics come from SQL,
where review wait is subtracted. Prompts and responses stay out of exported spans unless
`OTEL_TRACE_CONTENT=mapped` is set deliberately. See
[observability.md](observability.md).

---

## 5. What this design gives up

- **Latency.** A cold offering run is minutes, not seconds: browser rendering, PDF
  transcription, classification, extraction. The scheduler absorbs that for routine
  refreshes; a chat user who triggers a run watches its stages stream and gets the
  answer in the same turn.
- **Execution durability for chat runs.** A chat-initiated run executes in the CLI
  process. If that process dies mid-run the run is marked `run.interrupted` on the
  next start (the worker's lease recovery is the backstop) and must be asked for
  again; what is durable is the conversation and the review pause.
- **Recall on genuinely novel page structures.** Deterministic normalization and
  admission rules are auditable but conservative. An unusual layout degrades to
  more model work or to review, not to a silent guess.
- **Claim-level verification.** Values are validated against their own evidence, but
  there is no independent second opinion about whether a well-formed claim is true,
  and no conflict-resolution decision table. Conflicts are preserved and routed to a
  human instead of resolved automatically. `docs/semantic-extraction-maintenance-guide.md`
  sections 13 and 14 describe what would be built and in what order.
- **Reviewer granularity.** A review is scoped to a field of a snapshot, not to one
  atomic claim, so a reviewer cannot approve one branch of a conditional value while
  rejecting another.
- **Production identity.** The reviewer is the CLI's self-declared `--user`; an
  authenticated identity source and a role-to-review-scope policy are separate work.
  ADK Web runs monitoring in-process in the API and needs authenticated ingress
  before it is exposed beyond local development. Review creation has audit events
  but no notification adapter.
- **Process privilege.** The conversational process (CLI, or the API under ADK Web)
  now holds outbound HTTP, Playwright, Gemini credentials and database writes,
  because it executes the pipeline. The model reaches none of that directly.

---

## 6. Where to look in the code

| Concern | File |
|---|---|
| Agent, instructions, tool registration | `app/agent.py` |
| Tool order and error envelopes | `app/plugins.py` |
| Tool adapters and their grants | `app/tools/` (`resolution.py`, `reads.py`, `monitoring.py`) |
| Composition root | `app/runtime.py` |
| Run lifecycle and the seven pipeline stages | `app/services/monitoring_pipeline.py` |
| Monitoring node: execute, stream, pause per review, resume | `app/services/monitoring_node.py` |
| Review validation, application and run completion | `app/services/review_resolution.py` |
| CLI attach loop, rendering, Ctrl-C, recovery | `app/cli.py` |
| Intent, language, and offering resolution | `app/services/intent_resolution.py` |
| Structured answering and the authorization plan | `app/services/structured_tariff_query.py`, `app/services/structured_query_planning.py` |
| Acceptance, comparison, and review signals | `app/services/snapshot_lifecycle.py` |
| Host allowlist | `app/security/urls.py` |
| Typed configuration | `app/config/models.py` |
