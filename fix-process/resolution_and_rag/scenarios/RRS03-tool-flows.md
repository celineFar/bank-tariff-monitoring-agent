# RRS03: multi-turn tool flows

**What.** The real tools (`resolve_request`, `answer_tariff_query`,
`get_current_tariffs`, `run_tariff_monitoring`) driven through multi-turn flows with a
scripted interpreter: follow-ups, clarification by number, monitoring offers (yes / ok
/ 👍 / no), the whole-family scope question, repeat calls in one turn, and an Armenian
question answered with a number.

**How.** `uv run pytest tests/unit/test_resolution_rag_fixes.py tests/unit/test_tool_flows.py`.

**Pass bar.** All pass.
