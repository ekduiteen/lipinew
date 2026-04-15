import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const BACKEND =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://127.0.0.1:8000";

interface AuthResponse {
  access_token: string;
  user_id: string;
  onboarding_complete: boolean;
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.text();
    const res = await fetch(`${BACKEND}/api/auth/google`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
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
