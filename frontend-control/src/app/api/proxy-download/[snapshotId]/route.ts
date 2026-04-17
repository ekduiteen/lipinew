import { cookies } from "next/headers";
import { NextRequest } from "next/server";

const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ snapshotId: string }> },
) {
  if (!backendUrl) {
    return new Response("Missing BACKEND_URL/NEXT_PUBLIC_API_URL", { status: 500 });
  }

  const token = (await cookies()).get("ctrl_token")?.value;
  if (!token) {
    return new Response("Unauthorized", { status: 401 });
  }

  const { snapshotId } = await params;
  const response = await fetch(`${backendUrl}/api/ctrl/datasets/download/${snapshotId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok || !response.body) {
    return new Response(await response.text(), { status: response.status });
  }

  const headers = new Headers();
  const contentType = response.headers.get("content-type");
  const contentDisposition = response.headers.get("content-disposition");
  if (contentType) {
    headers.set("content-type", contentType);
  }
  if (contentDisposition) {
    headers.set("content-disposition", contentDisposition);
  }

  return new Response(response.body, {
    status: response.status,
    headers,
  });
}
