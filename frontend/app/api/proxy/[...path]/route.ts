import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const BACKEND =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://127.0.0.1:8000";

async function forward(req: NextRequest, path: string[]) {
  const upstreamUrl = new URL(`${BACKEND}/api/${path.join("/")}`);
  req.nextUrl.searchParams.forEach((value, key) => {
    upstreamUrl.searchParams.set(key, value);
  });

  const cookieStore = await cookies();
  const token = cookieStore.get("lipi.token")?.value;
  const headers = new Headers();
  const contentType = req.headers.get("content-type");
  const authorization = req.headers.get("authorization");

  if (contentType) headers.set("content-type", contentType);
  if (authorization) {
    headers.set("authorization", authorization);
  } else if (token) {
    headers.set("authorization", `Bearer ${token}`);
  }

  const method = req.method;
  const body =
    method === "GET" || method === "HEAD" ? undefined : await req.text();

  try {
    const res = await fetch(upstreamUrl, {
      method,
      headers,
      body,
    });

    const data = await res.text();
    const responseHeaders = new Headers();
    const responseType = res.headers.get("content-type");
    if (responseType) responseHeaders.set("content-type", responseType);

    return new NextResponse(data, {
      status: res.status,
      headers: responseHeaders,
    });
  } catch (err: any) {
    return NextResponse.json(
      { detail: `Proxy error: ${err.message}`, cause: String(err.cause ?? "") },
      { status: 502 }
    );
  }
}

export async function GET(
  req: NextRequest,
  context: { params: { path: string[] } }
) {
  return forward(req, context.params.path);
}

export async function POST(
  req: NextRequest,
  context: { params: { path: string[] } }
) {
  return forward(req, context.params.path);
}

export async function PUT(
  req: NextRequest,
  context: { params: { path: string[] } }
) {
  return forward(req, context.params.path);
}

export async function PATCH(
  req: NextRequest,
  context: { params: { path: string[] } }
) {
  return forward(req, context.params.path);
}
