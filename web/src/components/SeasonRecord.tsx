"use client";

import { useEffect, useState } from "react";

type Bucket = { bucket: string; n: number; acc: number | null };
type Tally = { n: number; acc: number; log_loss: number; brier: number };
type Recent = {
  Date: string;
  League: string;
  Home: string;
  Away: string;
  Prediction: string;
  Confidence: number;
  Actual: string;
  Correct: boolean;
  Source: string;
};

const OUTCOME = { H: "Home", D: "Draw", A: "Away" } as const;

export function SeasonRecord() {
  const [tally, setTally] = useState<Tally | null>(null);
  const [buckets, setBuckets] = useState<Bucket[]>([]);
  const [recent, setRecent] = useState<Recent[]>([]);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch("/api/season-record")
      .then(async (r) => {
        const b = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error("record unavailable");
        if (!Number.isFinite(b.tally?.acc) || !Number.isFinite(b.tally?.log_loss) || typeof b.tally?.n !== "number") {
          throw new Error("record unavailable");
        }
        setTally(b.tally);
        if (Array.isArray(b.buckets)) setBuckets(b.buckets);
        if (Array.isArray(b.recent)) setRecent(b.recent.slice(-5).reverse());
      })
      .catch(() => setFailed(true));
  }, []);

  if (failed) return null;
  if (!tally) return null;

  return (
    <section className="rounded-[2rem] bg-coal p-8 sm:p-10">
      <p className="font-mono text-[11px] tracking-[0.3em] text-lime">SEASON RECORD · 2026/27</p>
      <div className="mt-3 flex flex-wrap items-baseline gap-x-8 gap-y-2">
        <p className="font-display text-5xl text-cream sm:text-6xl">{(tally.acc * 100).toFixed(1)}%</p>
        <p className="font-mono text-xs tracking-[0.2em] text-cream/60">
          {tally.n} CALLS · LOG-LOSS {tally.log_loss.toFixed(3)}
        </p>
      </div>
      <div className="mt-6 grid gap-2 sm:grid-cols-5">
        {buckets.map((b) => (
          <div key={b.bucket} className="rounded-2xl bg-white/5 p-3">
            <p className="font-mono text-[10px] tracking-[0.2em] text-cream/60">{b.bucket}</p>
            <p className="mt-1 font-display text-2xl text-cream">
              {b.acc === null ? "—" : `${(b.acc * 100).toFixed(0)}%`}
            </p>
            <p className="font-mono text-[10px] text-cream/50">n={b.n}</p>
          </div>
        ))}
      </div>
      <div className="mt-6 space-y-1">
        {recent.map((r, i) => (
          <p key={i} className="font-mono text-[11px] tracking-wide text-cream/70">
            <span className={r.Correct ? "text-lime" : "text-ember"}>
              {r.Correct ? "✓" : "✗"}
            </span>{" "}
            {r.Home} vs {r.Away} — called {OUTCOME[r.Prediction as keyof typeof OUTCOME]},{" "}
            {r.Actual} ({r.Source})
          </p>
        ))}
      </div>
    </section>
  );
}
