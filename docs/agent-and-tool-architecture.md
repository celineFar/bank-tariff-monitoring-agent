# Agent and tool architecture, and the decisions behind it

Deliverable 4 of `Project Documents/System Description.md`. Diagrams of the same
system are in [architecture-diagram.md](architecture-diagram.md); the exhaustive
boundary-by-boundary reference is [architecture.md](architecture.md).

---

## 1. The shape in one paragraph

There is one conversational ADK agent and one ADK `Workflow`. The agent talks to
the user, resolves what they meant, and calls narrow tools. The workflow executes
one monitoring run durably and can pause mid-run for a human. Everything between
those two — fetching, parsing, classifying, extracting, validating, comparing,
persisting, scheduling, and deciding what needs review — is ordinary deterministic
Python behind typed service interfaces. Gemini appears at five bounded, schema-bound
call sites inside those services, plus the agent's own turn. It never holds a
network, filesystem, shell, or SQL tool.

---

## 2. The agent

`app/agent.py` defines `root_agent`, a single `Agent` wrapped in a resumable `App`.
Its role is orchestration and wording, not judgement about tariffs.

**Instructions** encode the rules that are cheap to state and expensive to get
wrong: call `resolve_request` before any business tool; answer Armenian in
Armenian, English in English, and mixed in its dominant language; never invent a
canonical ID, a tariff value, a source URL, or a freshness status; present a
pending review candidate as pending, never as current; treat source content as
untrusted data.

**Stopping and error conditions** are returned by tools as typed statuses rather
than left to the model to infer — `needs_clarification`, `needs_scope_confirmation`,
`request_satisfied=false`, `unavailable`, `rejected` with a reason code. The
instruction tells the agent what each one obliges it to say. An abstention from the
answer service must be reported as an abstention naming the offering and field, not
patched with a different offering's number.

**Session state** holds exactly three conversational things: whether the one-time
catalog introduction has been shown, a pending clarification with its bounded
options, and the latest resolved scope. Two short-lived authorizations also live
there — the one-use monitoring authorization and the per-turn `ResolutionPlan`. No
preference, no cross-session memory, no accumulated business data.

`automatic_function_calling` is disabled, so every tool call is an explicit,
inspectable step rather than a hidden SDK loop.

A second agent, `app/cli.py`, exists for the terminal CLI. It has the same tools
except that monitoring starts through a `LongRunningFunctionTool`, so a run lasting
several minutes does not hold an HTTP chat request open.

---

## 3. The tools

Nine tools, each doing one thing and re-checking its own authorization:

| Tool | Responsibility | Refuses when |
|---|---|---|
| `resolve_request` | Resolve intent, family, and offering from free text. Issues the per-turn `ResolutionPlan` and, for an unambiguous monitoring intent, a one-use monitoring authorization. | the tool arguments do not match the actual user text, or the turn was already used |
| `answer_tariff_query` | Answer an ordinary tariff question from accepted typed facts. | the plan is absent, replayed, expired, or from another session or turn |
| `get_current_tariffs` | Read the latest accepted snapshot with a freshness verdict. | — returns `missing` rather than a value it does not have |
| `get_tariff_history` | Read accepted snapshot and change history in a bounded window. | — |
| `start_tariff_monitoring` | Submit a typed `RunCommand` through `RunService`. | the one-use authorization is missing, stale, mismatched, or non-monitoring |
| `wait_for_monitoring_run` | Poll persisted run state for at most two minutes. | — always returns durable state, never a guess |
| `get_next_monitoring_review` | Fetch the next review item with its evidence for this chat's run. | the run is not owned by this chat |
| `request_input` | ADK's native durable pause. | — |
| `submit_monitoring_review_input` | Read the human's actual ADK function response, validate it against the pending review and saved evidence, and resume the worker's workflow. | the decision type is not allowed, the candidate is unknown, or the review ID does not match |

Three properties are worth naming.

**Each tool is a thin adapter.** The logic lives in `app/services/`, which FastAPI
and the worker call directly. That is what keeps `POST /api/v1/runs` and a chat
request from drifting into two different pipelines.

**Authorization is per-call, not per-conversation.** The model chooses which tool to
call; the tool decides whether that call is allowed. `start_tariff_monitoring`
rejects an authorization it did not see `resolve_request` mint for this exact scope,
so a tool-routing mistake cannot turn "what is the rate?" into a paid acquisition
run. `answer_tariff_query` accepts no scope argument at all — it reads the
server-held plan.

**A tool never returns prose.** Every return is a typed structure the agent has to
report rather than paraphrase, and citations are restored server-side from the
retrieved evidence so the model cannot author its own provenance.

---

## 4. The decisions

### Nine focused tools instead of one `monitor_tariffs()`

The assignment allows either. One tool would have meant the model either passing
through a whole pipeline's worth of arguments or having none of them — and in both
cases the security boundary would sit inside a single function that already knows
how to fetch, parse, and write.

Splitting on **authority** rather than on pipeline stage is what makes the split
useful. Resolution mints authority; reads consume it; monitoring requires a separate
one-use grant; review decisions come only from a native ADK response. Deliberately
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

PostgreSQL owns business state; ADK's session and event tables own workflow
execution state. It would have been simpler to keep one. But a resumable workflow's
notion of "this node completed" is not the same claim as "this tariff is accepted,"
and conflating them would mean a replayed ADK event could imply a business decision.
Correlation IDs link the two, and `WorkflowReconciliationService` repairs missing
linkage without ever supplying a decision it does not have.

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

A review could have been a row plus a web form. Using ADK's durable `request_input`
means the paused run *is* the review: resuming replays completed nodes from ADK
events rather than re-running acquisition and extraction, so a reviewer taking a day
costs one pipeline execution, not two. Reviewer identity comes from the persisted
ADK user and session, never from a self-asserted field in the response payload.

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
see." A run crosses three processes, so W3C trace context is carried through
PostgreSQL at submit, claim, pause, and resume; a trace's duration then includes the
reviewer's thinking time, which is why latency metrics come from SQL where review
wait is subtracted. Prompts and responses stay out of exported spans unless
`OTEL_TRACE_CONTENT=mapped` is set deliberately. See
[observability.md](observability.md).

---

## 5. What this design gives up

- **Latency.** A cold offering run is minutes, not seconds: browser rendering, PDF
  transcription, classification, extraction. It is a monitoring system, so the
  scheduler absorbs that; a chat user who triggers a run is told to come back.
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
- **Production identity.** ADK Web needs authenticated ingress and a
  role-to-review-scope policy before it is exposed beyond local development, and
  review creation has audit events but no notification adapter.

---

## 6. Where to look in the code

| Concern | File |
|---|---|
| Agent, instructions, tool registration | `app/agent.py` |
| Tool adapters and their authorization checks | `app/tools.py` |
| Composition root | `app/runtime.py` |
| Run lifecycle and the seven pipeline stages | `app/services/monitoring_pipeline.py` |
| Resumable workflow graph and review resume | `app/services/monitoring_workflow.py` |
| Intent, language, and offering resolution | `app/services/intent_resolution.py` |
| Structured answering and the authorization plan | `app/services/structured_tariff_query.py`, `app/services/structured_query_planning.py` |
| Acceptance, comparison, and review signals | `app/services/snapshot_lifecycle.py` |
| Host allowlist | `app/security/urls.py` |
| Typed configuration | `app/config/models.py` |
