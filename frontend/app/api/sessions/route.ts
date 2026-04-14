import { NextRequest, NextResponse } from "next/server";

// NEXT_PUBLIC_ vars are available server-side too; fallback for server context
const BACKEND =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.BACKEND_URL ||
  "http://localhost:8000";

export async function POST(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const token = searchParams.get("token") ?? "";

  const targetUrl = `${BACKEND}/api/sessions?token=${encodeURIComponent(token)}`;
  console.log("[sessions proxy] forwarding POST to:", targetUrl);

  try {
    const res = await fetch(targetUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    const data = await res.text();
    console.log("[sessions proxy] backend responded:", res.status, data);
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
