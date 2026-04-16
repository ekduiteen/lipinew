# Phrase Lab — LIPI Data Collection Module

**Status:** ✅ **FUNCTIONAL** (v1.1 — April 17, 2026)

## What is Phrase Lab?

Phrase Lab is a structured data collection lane that captures **controlled variation** of pre-defined phrases across registers, dialects, and speaking styles.

Unlike the open-ended **Teach** tab (free conversation), Phrase Lab:
- Presents a single bilingual phrase (Nepali primary, English secondary)
- Uses **hold-to-record** for audio capture
- Runs a quality check (hearing engine) before accepting
- Prompts for **variations** (casual, friendly, respectful, elder, local register)

All recordings are stored as WAV, run through STT, tagged with acoustic metadata, and queued for fine-tuning.

---

## User Flow

```
[Phrase Lab] → [Load next phrase] → [Display phrase card]
                                          ↓
                                   [Hold to record]
                                          ↓
                              [blobToWav(): WebM → WAV]
                                          ↓
                                [POST /api/phrases/submit-audio]
                                          ↓
                              ╔═ quality poor? ═╗ ok/good?
                              ║                  ↓
                            [RETRY]         [Variation prompt]
                                                  ↓
                                     [Record / skip variations]
                                                  ↓
                                        [Next phrase]
```

---

## Technical Architecture

### Frontend (`frontend/app/(tabs)/phrase-lab/page.tsx`)

State machine: `LOADING → PROMPT → RECORDING → PROCESSING → SUCCESS_VARIATION → RETRY`

**Critical: Audio Format Conversion**

The ML service uses `soundfile.read()` which **cannot read WebM/Opus** (the format browsers output from `MediaRecorder`). The page converts before upload:

```typescript
async function blobToWav(blob: Blob): Promise<Blob> {
  const arrayBuffer = await blob.arrayBuffer();
  const ctx = new AudioContext({ sampleRate: 16000 });
  const decoded = await ctx.decodeAudioData(arrayBuffer);
  // downmix to mono + re-encode as 16-bit PCM WAV
  return new Blob([encodeWav(mono, 16000)], { type: "audio/wav" });
}
```

File sent to backend: `phrase.wav` (not `.webm`)

**Auth:** Uses `credentials: "include"` — token is in an httpOnly cookie, never in localStorage.

### Backend (`backend/routes/phrases.py`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/phrases/next` | GET | Smart phrase selection for user |
| `/api/phrases/skip` | POST | Mark skipped, auto-return next |
| `/api/phrases/submit-audio` | POST | Primary recording: STT → quality → DB |
| `/api/phrases/submit-variation-audio` | POST | Variation recording |

### Pipeline (`backend/services/phrase_pipeline.py`)

`process_phrase_audio()`:
1. STT via faster-whisper (WAV input)
2. `hearing_svc.analyze_hearing()` — quality label: `poor` / `ok` / `good`
3. If `poor` → return `{status: "retry"}` — user re-records
4. `audio_understanding_svc.extract_audio_signals()` — dialect, tone, emotion, speech rate
5. Create `PhraseSubmissionGroup` + `PhraseSubmission` in DB
6. Update `PhraseMetrics`
7. Enqueue to learning queue (async fine-tuning prep)
8. If STT confidence < 0.6 AND quality not poor → add to reconfirmation queue

### Phrase Generation (`backend/services/phrase_generator.py`)

Background asyncio task (starts at app startup, runs every 5 minutes):
- Checks if active phrase count < 20
- Calls Gemma 4 via vLLM to generate 3 phrases per category (10 categories)
- Inserts with `is_active=True`, `review_status="approved"`
- Logs batches to `phrase_generation_batches` table

Current DB: 30 phrases across 6 categories.

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `phrases` | Phrase library (text_en, text_ne, category, is_active, review_status) |
| `phrase_submission_groups` | Groups primary + variations together per user per phrase |
| `phrase_submissions` | Individual recordings + full acoustic metadata |
| `phrase_skip_events` | Skip reason tracking |
| `phrase_reconfirmation_queue` | Low-confidence STT re-record queue |
| `phrase_metrics` | Per-phrase: submission count, dialect coverage, quality |
| `phrase_generation_batches` | LLM generation batch audit log |

---

## Acoustic Metadata Captured per Submission

```python
primary_language      # ne / en / ne-en-mix
code_switch_ratio     # 0.0–1.0 (% English in Nepali speech)
tone                  # formal / casual / neutral
emotion               # neutral / warm / urgent / etc.
dialect_guess         # kathmandu / newari_mix / terai / etc.
dialect_confidence    # 0.0–1.0
speech_rate           # slow / normal / fast
prosody_pattern       # flat / natural / expressive
stt_confidence        # 0.0–1.0 from faster-whisper
hearing_quality_label # poor / ok / good
```

---

## API Usage

```bash
# Requires auth cookie (sign in first)

# Next phrase
curl -b "lipi.token=<jwt>" http://localhost:8000/api/phrases/next

# Submit recording
curl -b "lipi.token=<jwt>" -X POST \
  -F "phrase_id=<uuid>" \
  -F "audio_file=@recording.wav;type=audio/wav" \
  http://localhost:8000/api/phrases/submit-audio
```

---

## Known Limitations (v1.1)

1. **Variation recording** — UI shows variation buttons but currently just loads next phrase. Full variation re-recording (v2) will prompt user to record each variation style.

2. **Reconfirmation** — Queue is populated but not actively shown to users yet. v2 will inject reconfirmation prompts into the phrase flow.

3. **Admin review** — `review_status` and `is_active` flags exist but there's no admin UI. All LLM-generated phrases are auto-approved for now.

---

## Files

```
frontend/
  app/(tabs)/phrase-lab/
    page.tsx              # State machine + blobToWav() + recording UI

backend/
  routes/phrases.py       # REST endpoints
  services/
    phrase_pipeline.py    # Core processing pipeline
    phrase_generator.py   # Background LLM phrase generation
    audio_storage.py      # MinIO: phrase-lab-audio/{user_id}/{phrase_id}/
    audio_understanding.py# Acoustic/semantic signal extraction
  models/phrases.py       # SQLAlchemy ORM

ml/
  stt.py                  # Uses soundfile — requires WAV/FLAC/OGG input (NOT WebM)
```

---

Last updated: 2026-04-17  
Version: v1.1
