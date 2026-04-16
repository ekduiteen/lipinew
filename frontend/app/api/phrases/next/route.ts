import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const authHeader = request.headers.get("authorization");

  console.log("Phrase API - Auth header:", authHeader ? "present" : "missing");

  if (!authHeader) {
    console.log("Phrase API - No auth header, returning 401");
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  try {
    const backendUrl = process.env.BACKEND_URL || "http://backend:8000";
    console.log("Phrase API - Forwarding to:", backendUrl);

    const response = await fetch(`${backendUrl}/api/phrases/next`, {
      method: "GET",
      headers: {
        "Authorization": authHeader,
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
