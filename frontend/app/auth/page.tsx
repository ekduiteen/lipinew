"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { exchangeGoogleCode, demoLogin, type AuthResponse } from "@/lib/api";
import styles from "./auth.module.css";

const GOOGLE_SCOPE = "openid email profile";

function googleAuthUrl() {
  const base = "https://accounts.google.com/o/oauth2/v2/auth";
  const redirectUri = `${window.location.origin}/auth`;
  const params = new URLSearchParams({
    client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "",
    redirect_uri: redirectUri,
    response_type: "code",
    scope: GOOGLE_SCOPE,
    access_type: "offline",
  });
  return `${base}?${params}`;
}

export default function AuthPage() {
  const router = useRouter();
  const params = useSearchParams();

  // Handle OAuth callback — Google redirects back to /auth?code=...
  useEffect(() => {
    const code = params.get("code");
    if (!code) return;
    const redirectUri = `${window.location.origin}/auth`;
    exchangeGoogleCode(code, redirectUri)
      .then((res: AuthResponse) => {
        localStorage.setItem("lipi.token", res.access_token);
        localStorage.setItem("lipi.user_id", res.user_id);
        router.replace(res.onboarding_complete ? "/home" : "/onboarding");
      })
      .catch((err) => {
        console.error("OAuth exchange failed:", err);
        alert(`Login failed: ${err.message}`);
      });
  }, [params, router]);

  function handleDemoLogin() {
    demoLogin()
      .then((res: AuthResponse) => {
        localStorage.setItem("lipi.token", res.access_token);
        localStorage.setItem("lipi.user_id", res.user_id);
        router.replace(res.onboarding_complete ? "/home" : "/onboarding");
      })
      .catch(() => {});
  }

  return (
    <div className={styles.root}>
      <div className={styles.card}>
        <h1 className={styles.logo}>लिपि</h1>
        <p className={styles.tagNe}>तपाईं बोल्नुहोस्। लिपि सिक्छ।</p>
        <p className={styles.tagEn}>You speak. LIPI learns. Language lives.</p>

        <div className={styles.divider} />

        <button
          className={styles.googleBtn}
          onClick={() => { window.location.href = googleAuthUrl(); }}
        >
          <GoogleIcon />
          <span>Google बाट जारी राख्नुहोस् · Continue with Google</span>
        </button>

        {process.env.NODE_ENV === "development" && (
          <button
            className={styles.demoBtn}
            onClick={handleDemoLogin}
          >
            Demo Login (dev only)
          </button>
        )}

        <p className={styles.terms}>
          जारी राखेर, तपाईं हाम्रो{" "}
          <a href="/terms" className={styles.link}>सेवाका शर्तहरू</a>
          {" "}र{" "}
          <a href="/privacy" className={styles.link}>गोपनीयता नीति</a>
          {" "}मान्नुहुन्छ।
        </p>
        <p className={styles.termsEn}>
          By continuing you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
      <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
    </svg>
  );
}
