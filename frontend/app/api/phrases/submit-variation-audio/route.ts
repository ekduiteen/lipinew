import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const token = request.headers.get("authorization");

  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  try {
    const formData = await request.formData();

    const backendUrl = process.env.BACKEND_URL || "http://backend:8000";
    const response = await fetch(`${backendUrl}/api/phrases/submit-variation-audio`, {
      method: "POST",
      headers: {
        "Authorization": token,
      },
      body: formData,
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
    console.error("Submit variation audio API error:", error);
    return NextResponse.json(
      { detail: "Failed to submit variation audio" },
      { status: 500 }
    );
  }
}
