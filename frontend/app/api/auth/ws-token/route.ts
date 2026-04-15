import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const BACKEND =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://127.0.0.1:8000";

interface WSTokenResponse {
  ws_token: string;
}

export async function POST(req: NextRequest) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get("lipi.token")?.value;

    if (!token) {
      return NextResponse.json(
        { detail: "Not authenticated" },
        { status: 401 }
      );
    }

    // Request short-lived WebSocket token from backend
    // Pass the httpOnly cookie via Authorization header
    const res = await fetch(`${BACKEND}/api/auth/ws-token`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!res.ok) {
      const errorText = await res.text();
      return NextResponse.json(
        { detail: `Failed to get WebSocket token: ${errorText}` },
        { status: res.status }
      );
    }

    const data = (await res.json()) as WSTokenResponse;
    return NextResponse.json(data);
  } catch (err: any) {
    return NextResponse.json(
      { detail: `Error: ${err.message}` },
      { status: 500 }
    );
  }
}
