# Documentation Maintenance

## Purpose

This wiki should stay small enough to navigate and current enough to trust. Detailed implementation docs remain in canonical root files. The wiki explains connections.

## Update Rules

Update this wiki when:

- adding/removing a major component
- changing an endpoint path or route behavior
- adding a backend service that changes turn flow, learning, moderation, or exports
- adding a model/table/migration
- changing public or control frontend navigation
- changing local/remote runtime expectations
- changing ML provider behavior or env requirements

## Which File To Update

| Change | Update |
|---|---|
| Product mode or app boundary | `system-overview.md`, `architecture.md` |
| Backend route/service | `backend.md`, `api-surface.md` |
| WebSocket/Teach behavior | `conversation-flow.md` |
| Public frontend page/proxy | `frontend-app.md` |
| Control dashboard page/admin API | `control-dashboard.md`, `api-surface.md` |
| Model/table/migration | `data-model.md`, root `DATABASE_SCHEMA.md` |
| STT/TTS/LLM/language ASR | `ml-and-ai.md`, `docs/LANGUAGE_ADAPTIVE_ASR.md` if relevant |
| Env/deploy/health | `runtime-and-ops.md`, root `OPERATIONS.md` |
| Test suite change | `testing.md` |

## Canonical Docs Still Matter

Do not duplicate huge reference material here. Link to:

- `DEV_ONBOARDING.md` for detailed dev setup and conventions.
- `DATABASE_SCHEMA.md` for table details.
- `OPERATIONS.md` for exact deploy/run commands.
- `SYSTEM_PROMPTS.md` for prompt design.
- `UI_UX_DESIGN.md` for screen design and interaction rules.

## Stale Doc Signals

Fix docs when you see:

- model names disagree across README, compose, env, and ops docs
- endpoint listed in wiki but route decorator changed
- page listed in wiki but route removed
- DB model added without schema doc update
- operational port/env value changed in compose but not docs
- tests added but no wiki mention for the subsystem

## Recommended Commit Habit

When code change changes a concept, include the matching wiki update in the same commit. For large features, update the wiki first as an architecture note, then refine after implementation.

