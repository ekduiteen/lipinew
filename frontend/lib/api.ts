/**
 * REST API client — all calls to /api/*
 * In dev: NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
 * In prod: empty string (Caddy proxies /api/* from the same origin)
 */

const BASE = (process.env.NEXT_PUBLIC_BACKEND_URL ?? "") + "/api";

function authHeader(): HeadersInit {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("lipi.token") : null;
  if (!token) {
    console.warn("No JWT token found in localStorage");
  } else {
    console.log("JWT token found, sending Authorization header");
  }
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const headers = { "Content-Type": "application/json", ...authHeader(), ...init?.headers };
  console.log("API request:", path, { headers, ...init });

  try {
    const res = await fetch(`${BASE}${path}`, {
      ...init,
      headers,
    });

    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      console.error("API error response:", res.status, text);
      throw new Error(`${res.status} ${text}`);
    }
    const data = await res.json() as T;
    console.log("API response:", path, data);
    return data;
  } catch (error: any) {
    console.error("API request failed:", error);
    throw error;
  }
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  onboarding_complete: boolean;
}

export async function exchangeGoogleCode(
  code: string,
  redirectUri: string
): Promise<AuthResponse> {
  return request("/auth/google", {
    method: "POST",
    body: JSON.stringify({ code, redirect_uri: redirectUri }),
  });
}

export async function demoLogin(): Promise<AuthResponse> {
  return request("/auth/demo", { method: "POST" });
}

// ─── Onboarding ──────────────────────────────────────────────────────────────

export interface OnboardingPayload {
  first_name: string;
  last_name: string;
  age: number;
  native_language: string;
  other_languages: string[];
  gender: "male" | "female" | "other";
  city_or_village: string;
  education_level: string;
  audio_consent?: boolean;
}

export async function submitOnboarding(payload: OnboardingPayload): Promise<void> {
  return request("/teachers/onboarding", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ─── Session ─────────────────────────────────────────────────────────────────

export interface SessionMeta {
  session_id: string;
  user_id: string;
  started_at: string;
}

export async function createSession(): Promise<SessionMeta> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("lipi.token") : null;
  if (!token) {
    throw new Error("No JWT token found");
  }
  // Use same-origin Next.js API route to avoid CORS on POST
  const res = await fetch(`/api/sessions?token=${encodeURIComponent(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json() as Promise<SessionMeta>;
}

// ─── Stats / leaderboard ─────────────────────────────────────────────────────

export interface TeacherStats {
  total_points: number;
  current_streak: number;
  words_taught: number;
  sessions_completed: number;
  rank: number;
}

export async function getMyStats(): Promise<TeacherStats> {
  return request("/teachers/me/stats");
}

export interface LeaderboardEntry {
  rank: number;
  name: string;
  points: number;
  avatar_initial: string;
}

export async function getLeaderboard(
  period: "weekly" | "monthly" | "all_time" = "weekly"
): Promise<LeaderboardEntry[]> {
  return request(`/leaderboard?period=${period}`);
}
