import { NextResponse } from "next/server";
import { API_BASE } from "@/lib/constants";

export async function GET() {
  try {
    const r = await fetch(`${API_BASE}/fixtures`, {
      next: { revalidate: 900 },
      signal: AbortSignal.timeout(25000),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) {
      return NextResponse.json(
        { fixtures: [], backendError: typeof body.detail === "string" ? body.detail : `backend ${r.status}` },
        { status: 502 }
      );
    }
    return NextResponse.json(body);
  } catch {
    return NextResponse.json({ fixtures: [], backendError: "backend unreachable" }, { status: 502 });
  }
}
