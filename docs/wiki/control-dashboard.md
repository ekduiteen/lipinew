# Control Dashboard

## Role

`frontend-control/` is the internal enterprise dashboard for moderation, gold records, analytics, exports, audit, and system health.

It is separate from the public frontend and uses admin-only auth and `/api/ctrl/*` backend endpoints.

## Stack

- Next.js 16.2.4
- React 19.2.4
- TypeScript 5
- Axios
- TanStack Query
- lucide-react
- Recharts
- wavesurfer.js
- Tailwind CSS 4

## Pages

| Page/file | Purpose |
|---|---|
| `src/app/login/page.tsx` | admin login |
| `src/app/(dashboard)/dashboard/page.tsx` | analytics/dashboard home |
| `src/app/(dashboard)/moderation/page.tsx` | review queue and labeling |
| `src/app/(dashboard)/gold-records/page.tsx` | curated gold data browser |
| `src/app/(dashboard)/exports/page.tsx` | dataset snapshot creation/download |
| `src/app/(dashboard)/health/page.tsx` | system health |
| `src/app/(dashboard)/audit/page.tsx` | audit log |

## Backend Endpoints

Admin routes:

- `/api/ctrl/auth/login`
- `/api/ctrl/moderation/*`
- `/api/ctrl/datasets/*`
- `/api/ctrl/system/*`

Backend files:

- `backend/routes/admin_auth.py`
- `backend/routes/admin_moderation.py`
- `backend/routes/admin_export.py`
- `backend/routes/admin_system.py`
- `backend/services/admin_auth.py`
- `backend/services/admin_moderation.py`
- `backend/services/admin_export.py`

## Moderation Concepts

- Review queue items are claimable to avoid conflicting reviewer work.
- Queue filters include review type, language, confidence, source, and age.
- Batch approve/reject/skip operations are supported.
- Approved items can become gold records or durable usage/learning state.
- Admin actions should be audited.

## Export Concepts

- Dataset snapshots are versioned export artifacts.
- Filters can include language, dialect, date range, and confidence threshold.
- Archives are stored in MinIO.
- Downloads are authenticated through backend and proxied by control frontend where needed.

## Admin Security

Admin auth is isolated from public teacher auth:

- `AdminAccount`
- `AdminAuditLog`
- admin JWT/dependency layer
- super-admin guard for privileged operations

