import { NextResponse } from "next/server";

export async function GET() {
  const apiUrl = process.env.BOT_API_URL || "http://127.0.0.1:8000";

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2500);

    const res = await fetch(`${apiUrl}/health`, {
      signal: controller.signal,
      cache: "no-store",
    });

    clearTimeout(timeout);

    if (res.ok) {
      const data = await res.json();
      return NextResponse.json({
        status: data.status === "healthy" ? "online" : "starting",
        raw: data,
      });
    }

    return NextResponse.json({ status: "offline" }, { status: 503 });
  } catch {
    return NextResponse.json({ status: "offline" }, { status: 503 });
  }
}
