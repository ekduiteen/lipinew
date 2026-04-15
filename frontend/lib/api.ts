/**
 * REST API client — all calls to /api/*
 * Tokens are stored in httpOnly cookies, automatically sent with requests.
 * No manual Authorization header needed — fetch auto-sends cookies.
 */

const BASE = "/api/proxy";

function authHeader(): HeadersInit {
  // httpOnly cookies are automatically sent by fetch, no need to set Authorization header
  // The cookie transport is more secure than reading from localStorage
  return {};
}

async function request<T>(
  path: string,
  init?: RequestInit & { skipAuth?: boolean }
): Promise<T> {
  const auth = init?.skipAuth ? {} : authHeader();
  const headers = { "Content-Type": "application/json", ...auth, ...init?.headers };
  console.log("API request:", path, { headers, ...init });

  try {
    const res = await fetch(`${BASE}${path}`, {
      ...init,
      headers,
    });

    if (!res.ok) {
      const text = await res.text().catch(() => res.statusText);
      console.error("API error response:", res.status, text);
      throw new Error(`HTTP ${res.status}: ${text}`);
    }
    const data = await res.json() as T;
    console.log("API response:", path, data);
    return data;
  } catch (error: any) {
    console.error("API request failed:", error);
    console.error("Full error details:", error.message, error.stack);
    throw error;
  }
}

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface AuthResponse {
  success: true;
  onboarding_complete: boolean;
}

export async function exchangeGoogleCode(
  code: string,
  redirectUri: string
): Promise<AuthResponse> {
  // Calls Next.js proxy which sets httpOnly cookies and returns success
  const res = await fetch("/api/auth/google", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, redirect_uri: redirectUri }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json() as Promise<AuthResponse>;
}

export async function demoLogin(): Promise<AuthResponse> {
  // Calls Next.js proxy which sets httpOnly cookies and returns success
  const res = await fetch("/api/auth/demo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json() as Promise<AuthResponse>;
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
  // httpOnly cookie is automatically sent with this request
  const res = await fetch(`/api/sessions`, {
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

// ─── Dashboard ──────────────────────────────────────────────────────────────

export interface ServiceStatus {
  ok: boolean;
  detail: Record<string, unknown> | null;
}

export interface QueueStatus {
  pending: number;
  processing: number;
  dead_letter: number;
}

export interface DataSummary {
  total_sessions: number;
  total_messages: number;
  total_teacher_turns: number;
  total_lipi_turns: number;
  total_vocabulary_entries: number;
  avg_stt_confidence: number | null;
}

export interface QualityReport {
  recent_teacher_language_counts: Record<string, number>;
  recent_low_confidence_turns: number;
  recent_learning_eligible_turns: number;
  recent_confused_replies: number;
  recent_hindi_mixed_replies: number;
}

export interface RecentSample {
  teacher_text: string;
  teacher_language: string | null;
  stt_confidence: number | null;
  lipi_text: string;
}

export interface DashboardOverview {
  system: {
    database: ServiceStatus;
    valkey: ServiceStatus;
    vllm: ServiceStatus;
    ml: ServiceStatus;
  };
  queues: QueueStatus;
  data: DataSummary;
  quality: QualityReport;
  recent_samples: RecentSample[];
}

export async function getDashboardOverview(): Promise<DashboardOverview> {
  return request("/dashboard/overview");
}
