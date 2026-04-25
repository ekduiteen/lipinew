# Testing

## Backend Tests

Location: `backend/tests/`

Important test areas:

- auth
- health
- sessions/WebSocket
- STT/TTS service integration wrappers
- learning and learning activation
- phrase lab
- points
- response cleanup
- speaker embeddings
- hybrid pivot
- intelligence layer
- turn intelligence
- language-adaptive ASR
- admin control

Run:

```powershell
cd backend
pytest
```

Targeted examples:

```powershell
cd backend
pytest tests/test_language_adaptive_asr.py
pytest tests/test_sessions_ws.py
pytest tests/test_admin_control.py
```

## Public Frontend Tests

Location: `frontend/__tests__/`

Coverage:

- API/proxy behavior
- auth page
- WebSocket client
- orb component

Run:

```powershell
cd frontend
npm test
npm run type-check
npm run build
```

## Control Dashboard Verification

Run:

```powershell
cd frontend-control
npm run build
npm run lint
```

Manual admin checks:

- login
- moderation queue loads
- claim buffer works
- approve/reject/skip actions persist
- gold records page loads
- export snapshot creates and downloads
- audit log records admin actions

## ML Verification

Use health and model info first:

```powershell
curl http://localhost:5001/health
curl http://localhost:5001/models/info
```

Functional checks:

- `/stt` with small audio sample
- `/tts` with Nepali and English text
- `/speaker-embed` with speech sample if embeddings are expected

## Regression Risk Checklist

Before shipping changes, verify the touched lane:

- Conversation change: backend session/WS tests plus manual Teach turn.
- Auth/proxy change: frontend auth tests plus login/demo flow.
- ASR change: language-adaptive ASR tests plus dashboard metrics.
- Learning change: learning activation tests plus review queue side effects.
- Admin change: admin-control tests/build plus moderation/export manual checks.
- Data model change: Alembic migration and schema docs.

