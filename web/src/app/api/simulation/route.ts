import { NextResponse } from "next/server";
import { API_BASE } from "@/lib/constants";

export async function GET(req: Request) {
  const league = new URL(req.url).searchParams.get("league") ?? "E0";
  try {
    const r = await fetch(`${API_BASE}/simulation?league=${league}`, {
      next: { revalidate: 3600 },
      signal: AbortSignal.timeout(55000),
    });
    if (!r.ok) return NextResponse.json({ error: "simulation unavailable" }, { status: 502 });
    return NextResponse.json(await r.json());
  } catch {
    return NextResponse.json({ error: "simulation unavailable" }, { status: 502 });
  }
}
