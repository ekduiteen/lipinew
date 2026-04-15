import { NextResponse } from "next/server";

const BACKEND =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://127.0.0.1:8000";

export async function POST() {
  try {
    const res = await fetch(`${BACKEND}/api/auth/demo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

    const data = await res.text();
    return new NextResponse(data, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err: any) {
    return NextResponse.json(
      { detail: `Proxy error: ${err.message}`, cause: String(err.cause ?? "") },
      { status: 502 }
    );
  }
}
