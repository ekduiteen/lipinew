# ML And AI

## Runtime Split

Backend owns orchestration and product decisions. ML service owns model execution.

| Layer | Directory | Responsibility |
|---|---|---|
| Backend integration | `backend/services/stt.py`, `backend/services/tts.py`, `backend/services/llm.py` | HTTP calls, fallback behavior, product metadata |
| ML service | `ml/` | STT, TTS, speaker embedding endpoints |
| Prompt system | `backend/services/prompt_builder.py`, `SYSTEM_PROMPTS.md` | dynamic student behavior |
| Language ASR logic | backend language/country services and configs | candidate languages, normalization, drift, training tiers |

## ML Service Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | model/device readiness |
| `POST /stt` | transcribe uploaded audio, return candidates and confidence |
| `POST /tts` | synthesize WAV audio from text/language |
| `POST /speaker-embed` | return speaker embedding metadata |
| `GET /models/info` | loaded model/provider details |

## STT

Current STT stack:

- faster-whisper large-v3
- language hints and keyterm prompt hints from backend
- candidate language selection from session language contract
- ASR candidate persistence and error classification in backend

Important files:

- `ml/stt.py`
- `backend/services/stt.py`
- `backend/services/keyterm_service.py`
- `backend/config/country_profiles.json`
- `backend/config/language_profiles.json`
- `docs/LANGUAGE_ADAPTIVE_ASR.md`

## TTS

Current TTS stack supports provider routing:

- Coqui XTTSv2 if configured
- Piper fallback
- Nepali Piper voice: `ne_NP-google-medium`
- English Piper voice: `en_US-lessac-medium`

Important files:

- `ml/tts.py`
- `ml/tts_provider.py`
- `ml/tts_piper.py`
- `ml/tts_coqui.py`
- `backend/services/tts.py`

## LLM

Backend calls an OpenAI-compatible endpoint through `backend/services/llm.py`.

Config:

- `VLLM_URL`
- `VLLM_MODEL`
- `VLLM_TIMEOUT`
- optional Groq fallback settings

Docs name Gemma 4 as current direction. Some compose comments still mention older Qwen defaults, so verify `.env`, remote service, and `README.md` before changing model assumptions.

## Prompt And Response Intelligence

Prompt behavior is not static. It combines:

- teacher profile
- register preference
- session language contract
- cross-session memory
- approved usage rules
- curriculum/diversity goals
- behavior policy
- conversation history

Guard/cleanup services reduce repetition, bad language drift, and unsuitable output before TTS.

