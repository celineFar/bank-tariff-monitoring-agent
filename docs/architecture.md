# Architecture

```text
FastAPI user trigger ----+
                         +--> ADK intent/product resolution
Daily worker trigger ----+              |
                                        v
                           deterministic pipeline
 discovery -> secure retrieval -> PDF/HTML parse -> OCR fallback
 -> clean/chunk -> PostgreSQL + pgvector -> hybrid retrieval
 -> Gemini evidence-bound extraction -> deterministic validation
 -> snapshot comparison -> HITL routing -> report
```

Gemini is restricted to language-dependent intent resolution and structured extraction.
All security, persistence, validation, comparison, scheduling, and review routing controls
are deterministic application services. The ADK agent receives no raw network, filesystem,
shell, or SQL tool.

## Package boundaries

- `app/agent.py`: ADK root agent and stable instructions.
- `app/config/`: one environment adapter plus nested typed groups shared by API,
  agent, and worker; consumers depend only on the relevant group.
- `app/tools.py`: narrow ADK adapters that call application services.
- `app/api/`: user-trigger, run-status, and HITL review HTTP contracts.
- `app/domain/`: validated tariff/evidence models and pure business rules.
- `app/services/`: pipeline orchestration interfaces and implementations.
- `app/repositories/`: persistence interfaces and PostgreSQL implementations.
- `app/security/`: URL, download, redirect, and logging guardrails.
- `app/worker.py`: daily Asia/Yerevan scheduler entry point.
- `migrations/`: PostgreSQL/pgvector schema.
- `tests/unit/`: deterministic logic tests.
- `tests/eval/`: non-deterministic agent/RAG behavioral evaluation.
