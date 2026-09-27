# RRS04: answer path on the dev database

**What.** The structured answer path against the dev database (`tariff_monitor`,
port 5434; only `overdraft` is published), with plans built from interpretations:
the currency rule ("repayment term in AMD"), the field finder ("What documents do I
need for the overdraft?"), `overview`, and history.

**How.** `uv run python fix-process/resolution_and_rag/probes/rrs04_answer_path.py`.
Read-only. The field finder makes one query-embedding call.

**Pass bar.** Each question answers with the expected fields; no call embeds units.
