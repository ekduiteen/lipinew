# Frontend App

## Role

`frontend/` is the public teacher-facing app. It handles authentication UX, onboarding, live teaching, phrase collection, heritage capture, ranks, settings, and PWA/Android wrapper support.

## Stack

- Next.js 14.2.15
- React 18.3.1
- TypeScript 5.6
- CSS Modules and global CSS
- `next-pwa`
- Capacitor 8 Android wrapper
- Jest + Testing Library

## App Routes

| Route/file | Purpose |
|---|---|
| `app/page.tsx` | root routing/entry |
| `app/auth/page.tsx` | login/auth UX |
| `app/onboarding/page.tsx` | teacher profile setup |
| `app/(tabs)/home/page.tsx` | main home/dashboard tab |
| `app/(tabs)/teach/page.tsx` | live Teach conversation |
| `app/(tabs)/heritage/page.tsx` | heritage capture |
| `app/(tabs)/phrase-lab/page.tsx` | phrase recording and variation capture |
| `app/(tabs)/ranks/page.tsx` | leaderboard/ranks |
| `app/(tabs)/settings/page.tsx` | settings |
| `app/(tabs)/settings/dashboard/page.tsx` | embedded dashboard/status |

## API Proxy Layer

Frontend keeps auth cookies httpOnly and routes browser calls through Next endpoints where needed:

- `app/api/auth/google/route.ts`
- `app/api/auth/demo/route.ts`
- `app/api/auth/ws-token/route.ts`
- `app/api/proxy/[...path]/route.ts`
- `app/api/sessions/route.ts`
- `app/api/phrases/*/route.ts`
- `app/api/heritage/[...path]/route.ts`

`frontend/lib/api.ts` wraps REST calls.

`frontend/lib/websocket.ts` connects directly to backend WebSocket after obtaining a short-lived token.

## Key Components

- `components/orb/Orb.tsx`: animated LIPI state indicator.
- `components/ui/BottomNav.tsx`: tab navigation.
- `components/ui/LipiPrimitives.tsx`: shared public UI primitives.
- `components/theme/ThemeProvider.tsx`: theme state.
- `components/phrase-lab/*`: phrase recording UX.

## Environment

Important frontend env vars:

- `BACKEND_URL`: server-side backend target for Next routes.
- `NEXT_PUBLIC_API_URL`: public API URL when needed.
- `NEXT_PUBLIC_WS_URL`: browser WebSocket URL.
- `NEXT_PUBLIC_AUTH_ORIGIN`
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
- `NEXTAUTH_URL`
- `NEXTAUTH_SECRET`

## Android Wrapper

Capacitor files live under:

- `frontend/capacitor.config.ts`
- `frontend/android/`
- `frontend/public/manifest.webmanifest`
- icon assets under `frontend/public/icons/` and `frontend/icons/`

## Tests

Frontend tests live in `frontend/__tests__/`:

- API/proxy behavior
- auth page
- WebSocket client
- orb component

