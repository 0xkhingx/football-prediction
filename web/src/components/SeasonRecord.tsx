"use client";

import { useEffect, useState } from "react";
import { PopDigits } from "./AnimatedDigits";

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
  const [mode, setMode] = useState<"simple" | "detailed">("simple");

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

  const pct = (tally.acc * 100).toFixed(1);
  const detailed = mode === "detailed";

  return (
    <section className="rounded-[2rem] bg-coal p-8 sm:p-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="font-mono text-[11px] tracking-[0.3em] text-lime">SEASON RECORD</p>
        <div
          className="flex overflow-hidden rounded-full border border-cream/15 font-mono text-[10px] tracking-[0.15em]"
          role="group"
          aria-label="Record display mode"
        >
          {(["simple", "detailed"] as const).map((m) => (
            <button
              key={m}
              type="button"
              aria-pressed={mode === m}
              onClick={() => setMode(m)}
              className={`px-3 py-1.5 uppercase transition-colors ${
                mode === m ? "bg-lime text-coal" : "text-cream/60 hover:text-cream"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>
      {!detailed && (
        <p className="mt-3 max-w-xl text-sm leading-relaxed text-cream/80">
          I&rsquo;ve predicted {tally.n} matches this season and gotten {pct}% right. The more
          confident I say I am, the more often I&rsquo;m correct.
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-baseline gap-x-8 gap-y-2">
        <p className="font-display text-5xl text-cream sm:text-6xl">
          <PopDigits key={`tally-${tally.acc}`} value={`${pct}%`} />
        </p>
        {detailed ? (
          <p className="font-mono text-xs tracking-[0.2em] text-cream/60">
            {tally.n} CALLS · LOG-LOSS {tally.log_loss.toFixed(3)}
          </p>
        ) : (
          <p className="flex items-center gap-2 font-mono text-xs tracking-[0.2em] text-cream/60">
            {tally.n} CALLS
            <details className="relative inline-block">
              <summary
                className="grid h-5 w-5 cursor-pointer list-none place-items-center rounded-full border border-cream/25 text-[11px] text-cream/70 marker:hidden hover:border-lime hover:text-lime [&::-webkit-details-marker]:hidden"
                aria-label="What is log-loss?"
                title="What is log-loss?"
              >
                ⓘ
              </summary>
              <span className="absolute left-1/2 top-7 z-10 w-56 -translate-x-1/2 rounded-xl border border-cream/15 bg-coal p-3 text-left font-sans text-xs normal-case leading-relaxed tracking-normal text-cream/80 shadow-xl">
                Log-loss {tally.log_loss.toFixed(3)} — a technical accuracy score where lower is
                better. Casual reader? Just look at the big percentage.
              </span>
            </details>
          </p>
        )}
      </div>
      {!detailed && (
        <p className="mt-6 font-mono text-[11px] tracking-[0.2em] text-cream/60">
          HOW OFTEN MY PREDICTIONS CAME TRUE, GROUPED BY HOW CONFIDENT I WAS
        </p>
      )}
      <div className={`grid gap-2 sm:grid-cols-5 ${detailed ? "mt-6" : "mt-2"}`}>
        {buckets.map((b) => (
          <div key={b.bucket} className="rounded-2xl bg-white/5 p-3">
            <p className="font-mono text-[10px] tracking-[0.2em] text-cream/60">{b.bucket}</p>
            <p className="mt-1 font-display text-2xl text-cream">
              {b.acc === null ? (
                "—"
              ) : (
                <PopDigits key={`${b.bucket}-${b.acc}`} value={`${(b.acc * 100).toFixed(0)}%`} />
              )}
            </p>
            <p className="font-mono text-[10px] text-cream/50">
              {detailed ? `n=${b.n}` : `(${b.n} ${b.n === 1 ? "game" : "games"})`}
            </p>
          </div>
        ))}
      </div>
      {!detailed && (
        <p className="mt-6 text-xs leading-relaxed text-cream/60">
          &ldquo;Preseason replay&rdquo; below means I re-ran a past match as if predicting it
          live, before knowing the score.
        </p>
      )}
      <div className={`space-y-1.5 ${detailed ? "mt-6" : "mt-2"}`}>
        {recent.map((r) => (
          <p key={`${r.Date}-${r.Home}-${r.Away}`} className="font-mono text-[11px] tracking-wide">
            <span className={r.Correct ? "text-lime" : "text-ember"}>
              {r.Correct ? "✓" : "✗"}
            </span>{" "}
            <span className="text-cream">
                {r.Home} vs {r.Away}
              </span>{" "}
              <span className="text-cream/50">
                {OUTCOME[r.Prediction as keyof typeof OUTCOME]} called · {r.Actual} ·{" "}
                {r.Source === "live" ? "live call" : "preseason replay"}
              </span>
          </p>
        ))}
      </div>
    </section>
  );
}
