# 1 · Agent and chat

[← Guide](README.md) · Deep dives: [agent-and-tool-architecture.md](../../docs/agent-and-tool-architecture.md), [intent-resolution.md](../../docs/intent-resolution.md), [native-hitl-review.md](../../docs/native-hitl-review.md)

## The ADK agent

| What | Where |
|---|---|
| Model name (chat, interpreter, extraction) | [MODEL](../../app/agent.py#L24), from `MODEL_NAME` via [ModelSettings.generation_model](../../app/config/models.py#L63) |
| Prompt (language, honesty, presentation only) | [INSTRUCTION](../../app/agent.py#L28) |
| Tool list | [TOOLS](../../app/agent.py#L55) |
| Agent object (retries, no auto function calling) | [root_agent](../../app/agent.py#L65) |
| App (plugin, resumable, needed for review pauses) | [app](../../app/agent.py#L76) |
| Tool-order policy: business tools rejected unless `resolve_request` ran in this invocation | [ToolPolicyPlugin.before_tool_callback](../../app/plugins.py#L38), list [BUSINESS_TOOLS](../../app/plugins.py#L22) |
| Tool exception → `{"status":"error"}` envelope | [ToolPolicyPlugin.on_tool_error_callback](../../app/plugins.py#L64) |
| Token/cost callbacks on every model call | [adk_usage_callbacks](../../app/services/model_call_usage.py#L382) |

The tool order is enforced in code (the plugin), not by the prompt. The model never gets a URL, SQL or filesystem tool.

## The 7 tools ([app/tools/](../../app/tools/__init__.py))

| Tool | Does | Code |
|---|---|---|
| resolve_request | Called first on every message. One Gemini interpreter call, validated by code; issues the **read grant** and/or **spend grant** | [resolve_request](../../app/tools/resolution.py#L48) |
| answer_tariff_query | Answers the question from accepted typed facts | [answer_tariff_query](../../app/tools/reads.py#L56) |
| get_current_tariffs | Freshness + per-field status only (no values) | [get_current_tariffs](../../app/tools/reads.py#L91) |
| get_tariff_history | Past snapshots/changes with compact citations | [get_tariff_history](../../app/tools/reads.py#L128) |
| run_tariff_monitoring | Checks the spend grant, asks to confirm a whole-family run, then runs the monitoring node | [run_tariff_monitoring](../../app/tools/monitoring.py#L37) |
| review_pending_candidates | Runs the monitoring node in review-only mode | [review_pending_candidates](../../app/tools/monitoring.py#L148) |
| get_monitoring_status | Read-only run status | [get_monitoring_status](../../app/tools/monitoring.py#L185) |

Shared tool plumbing:
- Session-state keys (the grants live here): [_state.py](../../app/tools/_state.py#L15), e.g. [TARIFF_PLAN_KEY](../../app/tools/_state.py#L20) (read grant) and [MONITOR_AUTHORIZATION_KEY](../../app/tools/_state.py#L23) (spend grant)
- How tools reach the services (set once at startup): [ToolServices](../../app/tools/_services.py#L14), [configure_services](../../app/tools/_services.py#L30)
- Where the read grant is built (30-minute lifetime): [issue_read_grant](../../app/services/structured_query_planning.py#L51), [PLAN_LIFETIME](../../app/services/structured_query_planning.py#L24)
- Where the spend grant is issued: [resolution.py](../../app/tools/resolution.py#L119)
- Whole-family confirmation (`needs_scope_confirmation`): [monitoring.py](../../app/tools/monitoring.py#L104)

## Understanding the request (intent resolution)

Gemini proposes the intent, scope and query shape. Code validates it against the catalog and the enums, then decides.

| Step | Where |
|---|---|
| Interpreter prompt | [INTERPRETER_INSTRUCTION](../../app/services/intent_resolution.py#L98) |
| Interpreter (tool-free ADK agent, strict JSON) | [AdkRequestInterpreter](../../app/services/intent_resolution.py#L206) |
| One turn: interpret → validate → next state | [RequestResolver.resolve_turn](../../app/services/intent_resolution.py#L330) |
| Shape only, for the typed `/questions` API | [RequestResolver.shape_for](../../app/services/intent_resolution.py#L376) |
| Validator: scope, clarification, route | [InterpretationValidator.validate](../../app/services/interpretation_validation.py#L143) |
| Conversation state (pending clarification, last scope) | [next_state](../../app/services/interpretation_validation.py#L593) |
| Output contract the model must return | [RequestInterpretation](../../app/domain/interpretation.py#L103) |
| Intents | [InterpretedIntent](../../app/domain/interpretation.py#L38), [RequestIntent](../../app/domain/intent.py#L17) |
| Intent → tool route | [route_for](../../app/domain/interpretation.py#L152) |
| Query shape (compare, rank, overview…) | [QueryShape](../../app/domain/query_shape.py#L46) |
| Synonyms / Armenian names / transliterations | [seed_catalog.yaml](../../app/config/seed_catalog.yaml), models in [catalog.py](../../app/domain/catalog.py#L111) |

If the interpreter fails or returns invalid output, the turn is `unavailable`. Nothing is guessed.

## The monitoring node (a run inside the chat)

[build_monitoring_node](../../app/services/monitoring_node.py#L160) builds an ADK `FunctionNode` that the monitoring tools run with `tool_context.run_node(...)`. It does:

1. submit the run (or find the paused one): [RunService](../../app/services/run_service.py#L45)
2. claim it and stream pipeline progress as partial events: [_progress_event](../../app/services/monitoring_node.py#L566), [stream_progress](../../app/services/monitoring_progress.py#L157)
3. or follow a run another process owns: [_follow](../../app/services/monitoring_node.py#L584)
4. pause once per pending review with a `RequestInput`: [_run_to_review](../../app/services/monitoring_node.py#L446), [_review_request](../../app/services/monitoring_node.py#L532), ids from [review_interrupt_id](../../app/services/monitoring_node.py#L143)
5. close the run and answer the original question: [_with_answer](../../app/services/monitoring_node.py#L721), result model [MonitoringResult](../../app/services/monitoring_node.py#L121)

ADK re-runs the node from the top on every resume, so each branch re-reads its state from PostgreSQL.
Lease and cancellation: [execute_with_lease](../../app/services/run_lease.py#L49), [stop_run](../../app/services/run_lease.py#L106).
Progress stage labels shown in the CLI: [STAGE_LABELS](../../app/services/monitoring_progress.py#L163).

## The CLI (`./tariff-chat`)

| What | Where |
|---|---|
| Entry / args (`--session`, `--new`, `--verbose`) | [main](../../app/cli.py#L1077), [chat](../../app/cli.py#L997), [cli_entry.py](../../app/cli_entry.py) |
| One user message → one invocation | [ChatSession.converse](../../app/cli.py#L463) |
| Progress lines + timer | [ProgressRenderer](../../app/cli.py#L241) |
| Ctrl-C (cancel turn, rewind) | [ChatSession.interrupt](../../app/cli.py#L414), [ChatSession.rewind](../../app/cli.py#L548) |
| Detect a review pause in events | [pending_review](../../app/cli.py#L184) |
| Review panel (evidence, passages) | [_show_review](../../app/cli.py#L666) |
| Review prompt, reply validation | [_ask_review_decision](../../app/cli.py#L793), [ChatSession.ask](../../app/cli.py#L523) |
| Error display | [_print_api_error](../../app/cli.py#L939) |

ADK session storage (PostgreSQL): [get_session_service](../../app/app_utils/services.py#L45). This file is generated ADK plumbing; leave it alone unless the task requires it.
