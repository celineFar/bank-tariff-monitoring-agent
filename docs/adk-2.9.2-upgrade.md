# ADK 2.9.2 Upgrade Notes

## Scope

Phase A upgrades the runtime and evaluation dependency constraints from
`google-adk>=2.6.0,<3.0.0` to `google-adk>=2.9.2,<3.0.0`. It deliberately does not change
the configured Gemini generation or embedding model IDs.

## Recorded baseline

- Date: 2026-09-20
- Python: 3.13.13
- agents-cli: 1.5.0
- agents-cli manifest: ADK template, `app/` agent directory, A2A enabled, no deployment
  target
- ADK before upgrade: 2.9.0
- Git branch: `agent-scraper`
- Pre-upgrade test result: 223 passed, 11 skipped, 3 failed, 5 warnings

`agents-cli info` was attempted twice but did not return output in this local environment.
The process was stopped rather than left running. The equivalent noninteractive version and
project configuration facts above were obtained from `agents-cli --version` and
`agents-cli-manifest.yaml`.

The three pre-upgrade failures are environment-dependent integration tests:

1. `tests/integration/test_agent.py::test_agent_stream` requires configured Gemini or
   Vertex AI credentials.
2. `tests/integration/test_server_e2e.py::test_adk_run_sse` reaches the same unconfigured
   model/session infrastructure.
3. `tests/integration/test_server_e2e.py::test_a2a_chat_stream` requires the configured
   PostgreSQL host, which is not resolvable in this environment.

All collected unit tests passed. PostgreSQL-marked tests without an available test database
were skipped as designed.

## Compatibility verification

After `uv sync`, the installed and locked ADK version is 2.9.2. Import/construction smoke
checks covered:

- `App` and `ResumabilityConfig(is_resumable=True)`;
- `Runner`/`InMemoryRunner`;
- graph `Workflow`;
- `RequestInput` from `google.adk.events.request_input`;
- ADK Web/FastAPI construction imports;
- the existing A2A route adapter; and
- the existing `shared://session` service registration.

`ResumabilityConfig` remains marked experimental by ADK 2.9.2. The monitoring workflow must
therefore keep all publication authority in the deterministic business repositories and use
ADK session/event state only as resumable execution state.

## Post-upgrade result

The same full command was run after the upgrade:

```text
uv run pytest tests/unit tests/integration
```

Result: 223 passed, 11 skipped, 3 failed, 5 warnings. The same three environment-dependent
tests failed for the same missing credentials/database connectivity reasons. No new failure
was introduced by ADK 2.9.2.

## Operational notes

- `uv` can be intermittently denied by Windows when invoked as a later command in a compound
  PowerShell statement immediately after environment mutation. Running it as the sole command
  is reliable and is the convention for subsequent phases.
- A live credentialed ADK/A2A smoke test remains an environment gate, not an ADK upgrade code
  regression.
- Deployment remains out of scope and requires separate explicit approval.
