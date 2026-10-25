import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";

async function handleProxy(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const session = await getServerSession(authOptions);
  if (!session || !session.user || !(session.user as any).id) {
    return NextResponse.json({ error: "Unauthorized: Please log in via Discord" }, { status: 401 });
  }

  const resolvedParams = await context.params;
  const userId = (session.user as any).id;
  const subpath = resolvedParams.path.join("/");
  const searchParams = req.nextUrl.search;
  const apiUrl = (process.env.BOT_API_URL || "http://127.0.0.1:8000").trim().replace(/\/+$/, "");
  const apiKey = (process.env.BOT_API_KEY || "").trim().replace(/^["']|["']$/g, "");

  if (!apiKey) {
    console.error("[Backend Proxy] BOT_API_KEY is missing or empty in environment variables!");
  }

  const targetUrl = `${apiUrl}/api/v1/${subpath}${searchParams}`;

  const headers: Record<string, string> = {
    "X-API-Key": apiKey,
    "X-User-Id": String(userId),
  };

  const contentType = req.headers.get("content-type");
  if (contentType) {
    headers["Content-Type"] = contentType;
  }

  let body: any = undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    try {
      body = await req.text();
    } catch {
      body = undefined;
    }
  }

  try {
    const res = await fetch(targetUrl, {
      method: req.method,
      headers,
      body,
      cache: "no-store",
    });

    const data = await res.text();
    if (!res.ok) {
      console.error(`[Backend Proxy] Backend ${targetUrl} returned status ${res.status}:`, data);
    }
    return new NextResponse(data, {
      status: res.status,
      headers: {
        "Content-Type": res.headers.get("Content-Type") || "application/json",
      },
    });
  } catch (err: any) {
    return NextResponse.json(
      { error: "Bot API Unreachable", detail: err.message },
      { status: 502 }
    );
  }
}

export { handleProxy as GET, handleProxy as POST, handleProxy as PUT, handleProxy as DELETE };
