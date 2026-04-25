# API Surface

Endpoint map extracted from backend route decorators.

## Public Backend

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | backend dependency health |
| `GET` | `/` | root/info |
| `POST` | `/auth/google` | exchange Google auth |
| `POST` | `/auth/demo` | demo login |
| `POST` | `/auth/demo-admin` | demo/admin helper |
| `POST` | `/auth/refresh` | refresh public token |
| `POST` | `/auth/ws-token` | issue short-lived WebSocket token |
| `POST` | `/teachers/onboarding` | save teacher profile |
| `GET` | `/teachers/me/stats` | teacher stats |
| `GET` | `/teachers/me/badges` | teacher badges |
| `GET` | `/leaderboard` | leaderboard entries |
| `GET` | `/dashboard/overview` | system/quality dashboard |
| `GET` | `/dashboard/language-adaptive` | language-adaptive ASR dashboard |

## Sessions And Teach

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/sessions` | create teaching session |
| `POST` | `/api/sessions/{session_id}/messages/{message_id}/correction` | submit transcript/language correction |
| `WS` | `/ws/session/{session_id}` | live audio conversation loop |

## Phrase Lab

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/phrases/next` | fetch next phrase |
| `POST` | `/api/phrases/submit-audio` | submit phrase audio |
| `POST` | `/api/phrases/submit-variation-audio` | submit variation audio |
| `POST` | `/api/phrases/skip` | skip phrase |
| `POST` | `/api/phrases/generate` | generate phrase batch |
| `POST` | `/api/phrases/review/{phrase_id}` | review phrase |

## Heritage

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/heritage/sessions/create` | create guided heritage session |
| `POST` | `/heritage/sessions/{session_id}/submit_primary` | submit primary response |
| `POST` | `/heritage/sessions/{session_id}/submit_followup` | submit follow-up response |

## Control/Admin

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/ctrl/auth/login` | admin login |
| `GET` | `/api/ctrl/moderation/next` | next review item |
| `GET` | `/api/ctrl/moderation/queue` | filtered queue |
| `POST` | `/api/ctrl/moderation/claim-buffer` | claim batch for reviewer |
| `POST` | `/api/ctrl/moderation/label/{item_id}` | label/approve item |
| `POST` | `/api/ctrl/moderation/batch/approve` | batch approve |
| `POST` | `/api/ctrl/moderation/reject/{item_id}` | reject item |
| `POST` | `/api/ctrl/moderation/batch/reject` | batch reject |
| `POST` | `/api/ctrl/moderation/batch/skip` | batch skip/release |
| `GET` | `/api/ctrl/moderation/gold` | gold records |
| `GET` | `/api/ctrl/datasets/` | dataset snapshot list |
| `POST` | `/api/ctrl/datasets/snapshot` | create snapshot |
| `GET` | `/api/ctrl/datasets/download/{snapshot_id}` | download snapshot |
| `GET` | `/api/ctrl/system/health` | admin health |
| `GET` | `/api/ctrl/system/audit` | audit logs |
| `GET` | `/api/ctrl/system/metrics/real` | real metrics |
| `GET` | `/api/ctrl/system/stats/summary` | summary stats |
| `GET` | `/api/ctrl/system/stats/timeseries` | timeseries stats |
| `GET` | `/api/ctrl/system/keyterm-seeds` | keyterm seeds |
| `POST` | `/api/ctrl/system/keyterm-seeds` | create keyterm seed |
| `GET` | `/api/ctrl/system/intelligence/overview` | intelligence overview |

## ML Service

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | ML readiness |
| `POST` | `/stt` | speech-to-text |
| `POST` | `/tts` | text-to-speech WAV |
| `POST` | `/speaker-embed` | speaker embedding |
| `GET` | `/models/info` | model/provider information |

