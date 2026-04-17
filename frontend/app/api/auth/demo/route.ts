import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { getBackendUrl } from "@/lib/backend-url";

const BACKEND = getBackendUrl();

interface AuthResponse {
  access_token: string;
  user_id: string;
  onboarding_complete: boolean;
}

export async function POST() {
  try {
    const res = await fetch(`${BACKEND}/api/auth/demo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      const errorText = await res.text();
      return NextResponse.json(
        { detail: `Auth failed: ${errorText}` },
        { status: res.status }
      );
    }

    const data = (await res.json()) as AuthResponse;
    const cookieStore = await cookies();

    // Set httpOnly JWT token cookie
    cookieStore.set("lipi.token", data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "strict" as const,
      maxAge: 60 * 60 * 24 * 30, // 30 days
      path: "/",
    });

    // Set user_id cookie (not httpOnly, can be read by JS if needed)
    cookieStore.set("lipi.user_id", data.user_id, {
      httpOnly: false,
      sameSite: "strict" as const,
      maxAge: 60 * 60 * 24 * 30,
      path: "/",
    });

    // Return success response (don't expose token to client JS)
    return NextResponse.json({
      success: true,
      onboarding_complete: data.onboarding_complete,
    });
  } catch (err: any) {
    return NextResponse.json(
      { detail: `Proxy error: ${err.message}`, cause: String(err.cause ?? "") },
      { status: 502 }
    );
  }
}
