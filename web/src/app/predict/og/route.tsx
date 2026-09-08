import { ImageResponse } from "next/og";
import { API_BASE } from "@/lib/constants";

export const runtime = "edge";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const home = (searchParams.get("home") ?? "Arsenal").toUpperCase();
  const away = (searchParams.get("away") ?? "Chelsea").toUpperCase();

  let call = "H";
  let conf = "";
  let score = "";
  try {
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), 8000);
    const r = await fetch(`${API_BASE}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ home: searchParams.get("home") ?? "Arsenal", away: searchParams.get("away") ?? "Chelsea" }),
      signal: ctl.signal,
    });
    clearTimeout(timer);
    if (r.ok) {
      const b = await r.json();
      call = b.prediction ?? "H";
      conf = typeof b.confidence === "number" ? `${Math.round(b.confidence * 100)}%` : "";
      if (b.scoreline?.shown) score = `${b.scoreline.h}–${b.scoreline.a}`;
    }
  } catch {
    /* static fallback copy below */
  }

  const title = `${home} vs ${away}`;
  const titleSize = title.length > 24 ? 64 : 92;

  return new ImageResponse(
    (
      <div
        style={{
          width: "1200px",
          height: "630px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#E85A24",
        }}
      >
        <div
          style={{
            width: "1080px",
            height: "510px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            background: "#FAF5EC",
            borderRadius: "48px",
          }}
        >
          <div style={{ fontFamily: "monospace", fontSize: 28, letterSpacing: 8, color: "#E85A24" }}>
            MATCHDAY FATE
          </div>
          <div style={{ display: "flex", fontSize: titleSize, fontWeight: 900, color: "#161412", marginTop: 16 }}>
            <span>
              {home} vs {away}
            </span>
          </div>
          <div style={{ display: "flex", fontSize: 64, fontWeight: 900, color: "#E85A24", marginTop: 8 }}>
            <span>
              MODEL CALLS {call}
              {conf ? ` · ${conf}` : ""}
              {score ? ` · ${score}` : ""}
            </span>
          </div>
          <div style={{ fontFamily: "monospace", fontSize: 22, letterSpacing: 4, color: "#16141299", marginTop: 24 }}>
            FAIR-PLAY XGB · NO ODDS · NOT BETTING ADVICE
          </div>
        </div>
      </div>
    ),
    { width: 1200, height: 630 }
  );
}
