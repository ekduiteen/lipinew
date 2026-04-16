import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const token = request.headers.get("authorization");

  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  try {
    const backendUrl = process.env.BACKEND_URL || "http://backend:8000";
    const response = await fetch(`${backendUrl}/api/phrases/next`, {
      method: "GET",
      headers: {
        "Authorization": token,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      return NextResponse.json(
        { detail: `Backend error: ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Phrases API error:", error);
    return NextResponse.json(
      { detail: "Failed to fetch phrase" },
      { status: 500 }
    );
  }
}
