import { NextResponse } from "next/server";
import { API_BASE } from "@/lib/constants";

export async function GET() {
  try {
    const r = await fetch(`${API_BASE}/season-record`, {
      next: { revalidate: 3600 },
      signal: AbortSignal.timeout(55000),
    });
    if (!r.ok) return NextResponse.json({ error: "record unavailable" }, { status: 502 });
    return NextResponse.json(await r.json());
  } catch {
    return NextResponse.json({ error: "record unavailable" }, { status: 502 });
  }
}
