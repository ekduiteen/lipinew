# LIPI

LIPI is a **community-powered language data collection platform disguised as a conversation**.

LIPI is the student. Users are the teachers.

Every turn has to do two jobs:
- feel good enough that the teacher wants to come back
- produce language data that is actually worth keeping

## Current Product State

The app is working end-to-end:
- auth
- onboarding
- live Teach screen
- phrase lab capture flow
- WebSocket conversation loop
- STT / LLM / TTS integration
- points / badges / leaderboard
- durable learning queue
- dashboard visibility
- multi-engine backend intelligence layer

The main problems are no longer infrastructure problems. They are product-quality problems:
- STT quality, especially for Newari and mixed turns
- response feel still too rigid or over-confirming
- voice quality and language-specific TTS delivery
- data cleanliness for future fine-tuning

## Live Stack

### Local
- frontend on `http://127.0.0.1:3000`
- backend on `http://127.0.0.1:8000`
- postgres / valkey / minio in Docker

### Remote
- one NVIDIA L40S
- host-level Gemma server on `:8100`
- Docker `backend`, `ml`, `postgres`, `valkey`, `minio`

### Core runtime
- **LLM**: Gemma 4 via an OpenAI-compatible shim
- **STT**: faster-whisper large-v3
- **TTS**: Piper

Current voice direction:
- keep Nepali voice as `ne_NP-google-medium`
- route English through a separate English Piper voice
- do not go back to OmniVoice on the live path

## Intelligence Layer

LIPI now runs as a backend intelligence system, not just a prompt.

Main engines:
- Hearing Engine
- Turn Interpreter
- Input Understanding Layer
- Audio Understanding Sidecar
- Teacher Modeling Layer
- Structured Session Memory
- Correction Graph
- Behavior Policy Engine
- Personality Engine
- Curriculum Engine
- Diversity Engine
- Learning Engine
- Post-Generation Guard
- Training Data Capture System
- Phrase Lab Pipeline

Key files:
- [backend/routes/sessions.py](backend/routes/sessions.py)
- [backend/services/hearing.py](backend/services/hearing.py)
- [backend/services/turn_interpreter.py](backend/services/turn_interpreter.py)
- [backend/services/input_understanding.py](backend/services/input_understanding.py)
- [backend/services/teacher_modeling.py](backend/services/teacher_modeling.py)
- [backend/services/memory_service.py](backend/services/memory_service.py)
- [backend/services/correction_graph.py](backend/services/correction_graph.py)
- [backend/services/behavior_policy.py](backend/services/behavior_policy.py)
- [backend/services/response_orchestrator.py](backend/services/response_orchestrator.py)
- [backend/services/personality.py](backend/services/personality.py)
- [backend/services/curriculum.py](backend/services/curriculum.py)
- [backend/services/diversity.py](backend/services/diversity.py)
- [backend/services/response_cleanup.py](backend/services/response_cleanup.py)
- [backend/services/post_generation_guard.py](backend/services/post_generation_guard.py)
- [backend/services/training_capture.py](backend/services/training_capture.py)
- [backend/services/audio_storage.py](backend/services/audio_storage.py)
- [backend/services/learning.py](backend/services/learning.py)

Every teacher turn now produces structured capture layers:
- raw data
- derived signals
- high-value learning signals

Those are stored alongside the `messages` record using JSONB fields, plus correction graph, session memory, teacher signals, async learning updates, and async speaker-embedding capture into `speaker_embeddings` with lightweight incremental cluster assignment.

LIPI now has two collection modes:
- `Teach`: open-ended student/teacher conversation
- `Phrase Lab`: structured phrase and variation capture for cleaner supervised data

The newest learning direction is also more conservative:
- correction-derived rules are moving toward a review queue instead of being blindly trusted
- audio-understanding sidecar signals are optional enrichment, not a hard dependency for the live path

## Canonical Docs

This repo used to have many overlapping setup/status/handover files. The canonical set is now:

- [CLAUDE.md](CLAUDE.md)
  Product and engineering source of truth.
- [LIPI_PHILOSOPHY.md](LIPI_PHILOSOPHY.md)
  Why LIPI exists and how the student-teacher dynamic should feel.
- [DEV_ONBOARDING.md](DEV_ONBOARDING.md)
  Architecture, services, runtime layout, turn flow, and developer workflow.
- [OPERATIONS.md](OPERATIONS.md)
  Actual deployment, restart, health-check, and remote-server operations guide.
- [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
  Schema reference.
- [PHASE_ROADMAP.md](PHASE_ROADMAP.md)
  Product build order and upcoming work.
- [HANDOVER_TO_CODEX.md](HANDOVER_TO_CODEX.md)
  Short current-state handover for the next engineer.

If you add a new service, architecture change, deployment pattern, or workflow, update one of the docs above instead of creating a new summary file.

## Honest Status

The backend intelligence is much stronger than it was a few weeks ago. The remaining gaps are mostly:
- speech quality
- STT reliability
- delivery tone
- multilingual data quality

The right mindset for the next phase is:

**make LIPI feel like a believable multilingual student whose conversations are worth collecting.**
