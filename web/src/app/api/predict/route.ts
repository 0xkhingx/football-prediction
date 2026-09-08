import { NextResponse } from "next/server";
import { z } from "zod";
import { API_BASE } from "@/lib/constants";

const Body = z.object({ home: z.string().min(2), away: z.string().min(2), date: z.string().optional() });

export async function POST(req: Request) {
  const parsed = Body.safeParse(await req.json().catch(() => ({})));
  if (!parsed.success) {
    return NextResponse.json({ detail: "home and away required" }, { status: 422 });
  }
  try {
    const r = await fetch(`${API_BASE}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed.data),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) {
      return NextResponse.json(
        { detail: typeof body.detail === "string" ? body.detail : `backend ${r.status}` },
        { status: 502 }
      );
    }
    return NextResponse.json(body);
  } catch {
    return NextResponse.json({ detail: "backend unreachable" }, { status: 502 });
  }
}
