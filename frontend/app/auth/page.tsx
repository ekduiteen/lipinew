"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { exchangeGoogleCode, demoLogin, type AuthResponse } from "@/lib/api";
import Orb from "@/components/orb/Orb";

const GOOGLE_SCOPE = "openid email profile";

function getCanonicalAuthOrigin() {
  const configured =
    process.env.NEXT_PUBLIC_AUTH_ORIGIN ||
    process.env.NEXTAUTH_URL ||
    "http://localhost:3000";
  try {
    return new URL(configured).origin;
  } catch {
    return "http://localhost:3000";
  }
}

function googleAuthUrl() {
  const base = "https://accounts.google.com/o/oauth2/v2/auth";
  const redirectUri = `${getCanonicalAuthOrigin()}/auth`;
  const params = new URLSearchParams({
    client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "",
    redirect_uri: redirectUri,
    response_type: "code",
    scope: GOOGLE_SCOPE,
    access_type: "offline",
  });
  return `${base}?${params}`;
}

function AuthPageInner() {
  const router = useRouter();
  const params = useSearchParams();

  useEffect(() => {
    const code = params.get("code");
    if (!code) return;
    const redirectUri = `${getCanonicalAuthOrigin()}/auth`;
    exchangeGoogleCode(code, redirectUri)
      .then((res: AuthResponse) => {
        router.replace(res.onboarding_complete ? "/home" : "/onboarding");
      })
      .catch((err) => {
        console.error("OAuth exchange failed:", err);
      });
  }, [params, router]);

  function handleDemoLogin() {
    demoLogin()
      .then((res: AuthResponse) => {
        router.replace(res.onboarding_complete ? "/home" : "/onboarding");
      })
      .catch(() => {});
  }

  return (
    <div style={{
      position: "fixed",
      inset: 0,
      display: "flex",
      flexDirection: "column",
      justifyContent: "space-between",
      padding: "64px 28px 48px",
      background: "var(--bg)",
      overflowY: "auto",
    }}>
      {/* Top bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.65rem",
          letterSpacing: "0.12em",
          color: "var(--fg-muted)",
          textTransform: "uppercase",
        }}>⁄ 001 · Welcome</span>
        <span style={{
          fontFamily: "var(--font-mono)",
          fontSize: "0.65rem",
          letterSpacing: "0.1em",
          color: "var(--fg-muted)",
        }}>v 1.0</span>
      </div>

      {/* Center: Orb + wordmark + tagline */}
      <div style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 28,
      }}>
        <Orb state="idle" size={180} />

        <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{
            fontFamily: "var(--font-serif)",
            fontSize: 68,
            lineHeight: 0.9,
            color: "var(--fg)",
            letterSpacing: "-0.03em",
            fontWeight: 400,
          }}>
            लिपि
          </div>
          <div style={{
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            letterSpacing: "0.32em",
            color: "var(--fg-muted)",
            textTransform: "uppercase",
          }}>
            L · I · P · I
          </div>
        </div>

        <div style={{ maxWidth: 280, textAlign: "center" }}>
          <p style={{
            fontFamily: "var(--font-serif)",
            fontSize: 21,
            lineHeight: 1.35,
            color: "var(--fg)",
            letterSpacing: "-0.01em",
          }}>
            You speak.<br />
            <em style={{ color: "var(--fg-muted)" }}>LIPI listens.</em><br />
            Language lives.
          </p>
          <p style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
            तपाईं बोल्नुहोस्। लिपि सिक्छ।
          </p>
        </div>
      </div>

      {/* Bottom: CTAs */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <button
          onClick={() => { window.location.href = googleAuthUrl(); }}
          style={{
            width: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            padding: "16px 24px",
            background: "var(--accent)",
            color: "var(--accent-fg)",
            border: "none",
            borderRadius: "var(--radius-full)",
            fontFamily: "var(--font-sans)",
            fontSize: "var(--text-body)",
            fontWeight: 600,
            cursor: "pointer",
            boxShadow: "var(--shadow-subtle)",
          }}
        >
          <GoogleIcon />
          Continue with Google
        </button>

        <button
          onClick={handleDemoLogin}
          style={{
            width: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            padding: "16px 24px",
            background: "var(--bg-card)",
            color: "var(--fg)",
            border: "1px solid var(--rule)",
            borderRadius: "var(--radius-full)",
            fontFamily: "var(--font-sans)",
            fontSize: "var(--text-body)",
            fontWeight: 500,
            cursor: "pointer",
            boxShadow: "var(--shadow-subtle)",
          }}
        >
          <PhoneIcon />
          Demo Login
        </button>

        <p style={{
          textAlign: "center",
          marginTop: 8,
          fontFamily: "var(--font-mono)",
          fontSize: "0.65rem",
          letterSpacing: "0.08em",
          color: "var(--fg-subtle)",
        }}>
          by continuing you join 12,401 teachers
        </p>
      </div>
    </div>
  );
}

export default function AuthPage() {
  return (
    <Suspense fallback={null}>
      <AuthPageInner />
    </Suspense>
  );
}

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 18 18" fill="none">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
      <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
    </svg>
  );
}

function PhoneIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
      <rect x="3" y="1" width="10" height="14" rx="2" stroke="currentColor" strokeWidth="1.3"/>
      <circle cx="8" cy="12.5" r="0.7" fill="currentColor"/>
    </svg>
  );
}
