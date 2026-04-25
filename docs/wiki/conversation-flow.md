# Conversation Flow

## User-Facing Flow

1. Teacher opens public app.
2. Teacher authenticates through Google or demo flow.
3. Teacher completes onboarding if needed.
4. Teach screen creates a session.
5. Frontend requests a short-lived WebSocket token.
6. Teacher records/sends audio frames.
7. LIPI streams transcript, response tokens, TTS start/end, audio, and turn-saved metadata.

Frontend files:

- `frontend/app/(tabs)/teach/page.tsx`
- `frontend/lib/api.ts`
- `frontend/lib/websocket.ts`
- `frontend/components/orb/Orb.tsx`

Backend file:

- `backend/routes/sessions.py`

## Backend Turn Pipeline

Per WebSocket audio frame:

1. Receive binary audio.
2. Reject oversized frames.
3. Load session memory from Valkey/topic memory.
4. Prepare keyterms from session memory, long-term memory, teacher history, and admin seeds.
5. Call STT through `services.stt`.
6. Run hearing/mode classification.
7. Repair transcript if safe and enabled.
8. Interpret the turn and extract input understanding.
9. Load/refresh curriculum and diversity state.
10. Apply behavior policy and response orchestration.
11. Build prompt with teacher profile, session contract, memory, and approved rules.
12. Call LLM through `services.llm`.
13. Clean and guard response.
14. Synthesize TTS through `services.tts`.
15. Store audio and messages.
16. Persist turn intelligence and training capture signals.
17. Award points/badges where eligible.
18. Queue async learning.
19. Send final metadata to client.

## Message Types Over WebSocket

Client sends:

- binary audio frames

Server sends:

- `transcript`: STT text/language/confidence and metadata
- `token`: streamed LLM token text
- `tts_start`: response text and turn index
- binary WAV audio
- `tts_end`: audio complete
- `turn_saved`: persisted IDs/points/metadata
- `empty_audio`: no usable audio/response audio
- `error`: frame or runtime error metadata

## Session Language Contract

Session creation now carries explicit language/runtime constraints:

- country code
- base ASR languages
- target language
- bridge language
- script
- dialect label
- teaching mode
- code switching permission
- training consent
- drift policy and ASR strategy from country profile
- language profile summary

This contract drives STT candidate selection, normalization, correction tiering, and prompt behavior.

## Correction Flow

Teachers can correct message transcripts through:

- `POST /api/sessions/{session_id}/messages/{message_id}/correction`

Actions:

- `accept`
- `edit`
- `wrong_language`
- `skip`

Backend then:

- normalizes text for training
- classifies ASR error type/family
- assigns training tier/eligibility
- applies teacher correction to message state
- persists correction metadata

## Main Failure Points

| Symptom | Likely area |
|---|---|
| WebSocket closes immediately | auth token, origin/CORS, backend exception |
| No transcript | frontend audio capture, ML `/stt`, language hints |
| Bad transcript language | session contract, country/language profiles, STT candidate selection |
| Repetitive LIPI reply | behavior policy, response orchestrator, prompt context |
| No audio reply | ML `/tts`, TTS provider, response cleanup empty output |
| Turn not visible later | message store, DB commit, learning queue failure |

