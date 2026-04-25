# LIPI Project Wiki

This wiki is the connective map for LIPI. It links product intent, runtime systems, backend services, frontends, data model, ML stack, and operational docs so a new engineer can rebuild context without reading every root document first.

Start here when the project feels too large.

## Fast Orientation

- LIPI is a language-data collection platform framed as a conversational student.
- Teachers use the public app to teach, correct, record phrases, and contribute heritage language data.
- Backend turns every interaction into structured learning, moderation, analytics, and dataset-export signals.
- Internal reviewers use the control dashboard to approve, reject, curate gold data, and export dataset snapshots.
- ML service owns STT, TTS, and speaker embeddings.
- Postgres is source of truth; Valkey is cache/queue/session context; MinIO stores audio and archives.

## Wiki Map

| Page | Use when |
|---|---|
| [System Overview](system-overview.md) | Need the whole project in one page |
| [Architecture](architecture.md) | Need component boundaries and data flow |
| [Backend](backend.md) | Working in FastAPI routes, services, auth, workers |
| [Conversation Flow](conversation-flow.md) | Debugging Teach/WebSocket turn behavior |
| [Frontend App](frontend-app.md) | Working on public Next.js app, tabs, auth, PWA |
| [Control Dashboard](control-dashboard.md) | Working on admin, moderation, gold records, exports |
| [ML And AI](ml-and-ai.md) | Working on STT, TTS, LLM, language-adaptive ASR |
| [Data Model](data-model.md) | Need table/model ownership and storage rules |
| [API Surface](api-surface.md) | Need endpoint map |
| [Runtime And Ops](runtime-and-ops.md) | Running, deploying, env, health checks |
| [Testing](testing.md) | Finding test suites and verification entry points |
| [Documentation Maintenance](documentation-maintenance.md) | Keeping docs current as code changes |
| [Glossary](glossary.md) | Project terms and concepts |

## Canonical Source Docs

The wiki summarizes and cross-links existing canonical docs rather than replacing them.

- [README.md](../../README.md): current product state and component summary
- [CLAUDE.md](../../CLAUDE.md): engineering north star and constraints
- [DEV_ONBOARDING.md](../../DEV_ONBOARDING.md): detailed developer guide
- [OPERATIONS.md](../../OPERATIONS.md): local/remote runtime operations
- [DATABASE_SCHEMA.md](../../DATABASE_SCHEMA.md): schema reference
- [SYSTEM_ARCHITECTURE.md](../../SYSTEM_ARCHITECTURE.md): deeper architecture doc
- [SYSTEM_PROMPTS.md](../../SYSTEM_PROMPTS.md): prompt strategy
- [UI_UX_DESIGN.md](../../UI_UX_DESIGN.md): public UX and visual system
- [docs/LANGUAGE_ADAPTIVE_ASR.md](../LANGUAGE_ADAPTIVE_ASR.md): latest language-adaptive ASR design

## Current State Notes

This wiki reflects the workspace as of 2026-04-25. Treat this wiki as a context layer over current code, not as a release tag.
