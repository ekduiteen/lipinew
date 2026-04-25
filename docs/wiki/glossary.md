# Glossary

## Product Terms

LIPI: the student persona and product.

Teacher: public user contributing language knowledge.

Teach: open-ended live conversation mode.

Heritage: guided capture of cultural, dialect, register, and regional language data.

Phrase Lab: structured phrase and variation recording flow.

Gold Curation: internal moderation workflow that turns raw/derived items into trusted data.

Control Dashboard: internal admin app in `frontend-control/`.

## Data Terms

Turn: one teacher audio input plus LIPI response cycle.

Session Language Contract: per-session country/language/script/teaching-mode/consent contract.

Teacher Signal: structured learning signal derived from teacher behavior.

Correction Event: high-value teacher correction or approved correction state.

Usage Rule: durable approved language rule used in future prompts.

Review Queue Item: uncertain or high-value item waiting for human moderation.

Gold Record: moderated, trusted record suitable for curated datasets.

Dataset Snapshot: versioned export archive created by admin flow.

Training Tier: quality/eligibility classification for training use.

## Intelligence Terms

Hearing Engine: classifies how LIPI should hear/respond to audio input.

Turn Interpreter: converts raw turn information into structured interpretation.

Input Understanding: intent/entity/language understanding layer.

Keyterm Boosting: feeding likely important words into STT/prompt context.

Transcript Repair: cautious correction of low-confidence critical words.

Behavior Policy: turn-level goal and response family selection.

Response Orchestrator: coordinates policy, prompt, and response shape.

Post-Generation Guard: checks generated text before delivery/TTS.

Memory Snapshot: durable cross-session memory about teacher/language/topic/style.

## Infrastructure Terms

Valkey: Redis-compatible cache/queue service used by LIPI. Project convention says Valkey, not Redis.

MinIO: S3-compatible object storage for audio and archive artifacts.

vLLM: OpenAI-compatible model serving layer.

ML Service: FastAPI service exposing STT/TTS/speaker embedding.

Piper: local TTS provider/fallback.

Coqui XTTSv2: optional multilingual TTS provider.

faster-whisper: STT engine.

