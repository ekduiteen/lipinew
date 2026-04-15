import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

// NEXT_PUBLIC_ vars are available server-side too; fallback for server context
const BACKEND =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://localhost:8000";

export async function POST(req: NextRequest) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lipi.token")?.value;

  if (!token) {
    return NextResponse.json(
      { detail: "Not authenticated" },
      { status: 401 }
    );
  }

  const targetUrl = `${BACKEND}/api/sessions`;

  try {
    const res = await fetch(targetUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    const data = await res.text();
    return new NextResponse(data, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err: any) {
    console.error("[sessions proxy] fetch failed:", err.message, err.cause ?? "");
    return NextResponse.json(
      { detail: `Proxy error: ${err.message}`, cause: String(err.cause ?? "") },
      { status: 502 }
    );
  }
}
