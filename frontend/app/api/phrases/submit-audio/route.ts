import { NextRequest, NextResponse } from "next/server";
import { getBackendUrl } from "@/lib/backend-url";

export async function POST(request: NextRequest) {
  const token = request.headers.get("authorization");

  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  try {
    const formData = await request.formData();

    const backendUrl = getBackendUrl();
    const response = await fetch(`${backendUrl}/api/phrases/submit-audio`, {
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
    console.error("Submit audio API error:", error);
    return NextResponse.json(
      { detail: "Failed to submit audio" },
      { status: 500 }
    );
  }
}
