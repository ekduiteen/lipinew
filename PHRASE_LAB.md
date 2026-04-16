# Phrase Lab — LIPI Data Collection Module

**Status:** ✅ **FUNCTIONAL** (v1.0.0)

## What is Phrase Lab?

Phrase Lab is a structured data collection lane within LIPI that captures **controlled variation** of pre-defined phrases across different registers, dialects, and speaking styles.

Unlike the open-ended **Teach** tab (free conversation), Phrase Lab presents teachers with:
- A single phrase (bilingual: Nepali + English)
- A **hold-to-record** interface to capture their pronunciation
- Quality checks (audio clarity) before acceptance
- A follow-up prompt for **variations** (casual, friendly, respectful, elder, local register)

All recordings are timestamped, tagged with acoustic metadata, and queued for fine-tuning.

---

## User Flow

```
[Phrase Lab] → [Load next phrase] → [Display phrase card]
                                    ↓
                              [Hold to record]
                                    ↓
                        [Audio quality check]
                                    ↓
                    ╔═ POOR? ═══╗ GOOD?
                    ║            ↓
                   [RETRY]  [Success card]
                            + [Variation prompt]
                                    ↓
                        [Select variation type]
                                    ↓
                        [Record variation audio]
                                    ↓
                        [Load next phrase]
```

---

## Technical Architecture

### Frontend (`frontend/app/(tabs)/phrase-lab/`)

**Page:** `page.tsx` — State machine managing the full flow
- States: `LOADING`, `PROMPT`, `RECORDING`, `PROCESSING`, `SUCCESS_VARIATION`, `RETRY`
- MediaRecorder for browser audio capture
- Sends to `/api/phrases/submit-audio` and `/api/phrases/submit-variation-audio`

**Components:**
1. `HoldToRecordButton.tsx` — Pointer-based recording (mobile + desktop)
2. `PhraseCard.tsx` — Bilingual phrase display (Nepali prominent)
3. `VariationPrompt.tsx` — Button grid for register selection

### Backend (`backend/routes/phrases.py`)

**REST Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/phrases/next` | GET | Fetch next phrase for user (smart selection) |
| `/api/phrases/skip` | POST | Mark phrase as skipped, load next |
| `/api/phrases/submit-audio` | POST | Upload primary recording, return success/retry |
| `/api/phrases/submit-variation-audio` | POST | Upload variation recording |

### Services (`backend/services/`)

**`phrase_pipeline.py`** — Core pipeline
- `get_next_phrase()` — Intelligent phrase selection considering:
  - Reconfirmation queue (low STT confidence)
  - Under-collected phrases (fewest submissions)
  - User skip/completion history
  
- `process_phrase_audio()` — Full pipeline:
  1. STT (faster-whisper large-v3)
  2. Hearing analysis (quality label: poor/ok/good)
  3. Audio understanding (semantic + acoustic signals)
  4. Database ingestion (group + submission records)
  5. Learning queue enqueue (async fine-tuning prep)

**`audio_storage.py`** — MinIO object storage
- Stores phrase audio in `phrase-lab-audio/{user_id}/{phrase_id}/`
- Async to thread to prevent blocking

**`audio_understanding.py`** — Acoustic/semantic extraction
- Calls ML service `/audio-understand` endpoint (1.5s timeout)
- Gracefully fallbacks to heuristics if service unavailable
- Extracts: dialect guess, tone, emotion, speech rate, prosody, code-switch ratio

### Database (`backend/models/phrases.py`)

**Core Tables:**

| Table | Purpose |
|-------|---------|
| `phrases` | Phrase library (text_en, text_ne, category, is_active) |
| `phrase_submission_groups` | Groups primary + variations together |
| `phrase_submissions` | Individual audio submissions (acoustic metadata) |
| `phrase_skip_events` | Skip reason tracking |
| `phrase_reconfirmation_queue` | Low-confidence STT resubmissions |
| `phrase_metrics` | Per-phrase: submission count, dialect coverage, quality |
| `phrase_generation_batches` | (Future) LLM-generated phrases |

---

## Data Pipeline

### Audio Processing

1. **Record** — User holds button, records audio (WebM format)
2. **Store** — Audio saved to MinIO with UUID + timestamp
3. **STT** — faster-whisper transcribes to text (+ confidence)
4. **Quality Check** — Hearing engine checks for clipping/noise
   - If `quality_label == "poor"`: User retries
5. **Semantic Extract** — Audio understanding model returns:
   - `dialect_guess`: e.g., "kathmandu", "newari_mix"
   - `tone`, `emotion`, `speech_rate`, `prosody_pattern`
   - `code_switch_ratio`: % of English vs Nepali

6. **DB Ingestion** — PhraseSubmission created with all signals
7. **Learning Queue** — Async job enqueued for:
   - Speaker embedding clustering
   - Acoustic variation catalog
   - Fine-tuning corpus preparation

### Reconfirmation Logic

If `stt_confidence < 0.6` AND `quality_label != "poor"`:
- Likely a rare dialect or strong accent
- Added to `phrase_reconfirmation_queue`
- Prompts user to re-record on next visit
- Original + reconfirmation paired in learner pipeline

---

## Seed Data (v1)

10 phrases inserted in database:

| Nepali | English | Category |
|--------|---------|----------|
| नमस्ते | Hello | greetings |
| तपाई कस्तो छन्? | How are you? | greetings |
| मेरो नाम ... हो | My name is... | introductions |
| धन्यवाद | Thank you | politeness |
| कृपया | Please | politeness |
| तपाईको नाम के हो? | What is your name? | questions |
| तपाई कहाँबाट हुनुहुन्छ? | Where are you from? | questions |
| तपाई नेपाली बोल्नुहुन्छ? | Do you speak Nepali? | questions |
| शुप्रभात | Good morning | greetings |
| शुभरात्रि | Good night | greetings |

---

## Testing

### Browser Test
1. Open http://localhost:3000
2. Sign in (demo or Google)
3. Click **Phrases** (💬) in BottomNav
4. Phrase card should load with bilingual text
5. Hold microphone button to record
6. After upload, select a variation type
7. Next phrase auto-loads

### API Test
```bash
# Get next phrase (requires JWT token)
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/phrases/next

# Response:
{
  "id": "uuid-here",
  "text_en": "Hello",
  "text_ne": "नमस्ते",
  "category": "greetings"
}
```

---

## Configuration

### Environment Variables
```bash
# ML Service (for audio understanding)
ML_SERVICE_URL=http://localhost:5001

# MinIO (audio storage)
MINIO_ENDPOINT=localhost:9000
MINIO_BUCKET_AUDIO=lipi-audio

# Database (phrase tables)
DATABASE_URL=postgresql+asyncpg://...
```

### Frontend
```typescript
// Next.js API proxy at /api/phrases/* routes to backend
// Auth via JWT token in localStorage: lipi.token
```

---

## Known Limitations (v1)

1. **Audio Understanding Endpoint** — Currently calls `/audio-understand` on ML service
   - If unavailable, gracefully fallbacks to heuristics
   - No variation-specific acoustic tuning yet

2. **Variation Recording** — Currently taps a variation button, loads next phrase
   - Full v2 will re-prompt for recording each variation
   - Could be optimized for rapid multi-variation capture

3. **Phrase Generation** — Placeholder admin endpoint (not user-facing)
   - Future: LLM batch generation + admin review queue

4. **Reconfirmation** — Queued but not actively prompted yet
   - v2 will intelligently inject reconfirmation into user flow

---

## Next Steps (Phase 2+)

1. **Batch Phrase Import** — Script to seed 1000+ phrases from Nepali corpus
2. **Variation Tuning** — Specialized acoustic models per register
3. **Quality Dashboard** — Admin view of submission quality metrics
4. **Speaker Clustering** — Use embeddings to ID unique speakers
5. **Fine-Tuning Pipeline** — Monthly LoRA training on phrase submissions

---

## Files Summary

```
frontend/
  app/(tabs)/phrase-lab/
    page.tsx                          # State machine + orchestration
  components/phrase-lab/
    HoldToRecordButton.tsx            # Recording UI
    PhraseCard.tsx                    # Display bilingual phrase
    VariationPrompt.tsx               # Variation selection grid

backend/
  routes/phrases.py                   # REST endpoints
  services/phrase_pipeline.py         # Core processing pipeline
  services/audio_storage.py           # MinIO integration
  services/audio_understanding.py     # Semantic/acoustic extraction
  models/phrases.py                   # SQLAlchemy ORM

docs/
  PHRASE_LAB.md                       # (This file)
```

---

## Status

✅ **Frontend** — All components built and tested  
✅ **Backend** — All endpoints implemented  
✅ **Database** — Schema created, seed data loaded  
✅ **Audio Storage** — MinIO integration working  
✅ **STT Pipeline** — faster-whisper integrated  
✅ **Learning Queue** — Async ingestion ready  

**Ready for user testing and data collection.**

---

Last updated: 2026-04-17  
Feature completeness: v1.0.0 (Stable)
