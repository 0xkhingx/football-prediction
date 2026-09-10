"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { LoadingButton } from "@/components/interior/loading-button";
import { CopyButton } from "@/components/interior/copy-button";
import { ReelNumber } from "@/components/AnimatedDigits";
import { Tooltip } from "@/components/Tooltip";
import { ProbBar } from "@/components/ProbBar";
import { FormBadges } from "@/components/FormBadges";
import { PredictionSchema, type Prediction } from "@/lib/types";

export function callText(r: Pick<Prediction, "home" | "away" | "prediction" | "confidence">): string {
  return `${r.home} vs ${r.away} — MODEL CALLS ${r.prediction} ${Math.round(r.confidence * 100)}% (Matchday Fate, fair-play XGB, no odds)`;
}

function ShareRow({ result }: { result: Prediction }) {
  const text = callText(result);
  const og = `/predict/og?home=${encodeURIComponent(result.home)}&away=${encodeURIComponent(result.away)}`;
  const linkCls =
    "rounded-full border-2 border-coal/15 px-4 py-1.5 font-mono text-[10px] tracking-[0.25em] text-coal hover:border-coal";
  return (
    <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
      <CopyButton value={text} label="COPY CALL" copiedLabel="COPIED" />
      <a className={linkCls} href={og} target="_blank" rel="noreferrer">
        CARD ↗
      </a>
      <a
        className={linkCls}
        href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`}
        target="_blank"
        rel="noreferrer"
      >
        X ↗
      </a>
      <a
        className={linkCls}
        href={`https://wa.me/?text=${encodeURIComponent(text)}`}
        target="_blank"
        rel="noreferrer"
      >
        WHATSAPP ↗
      </a>
    </div>
  );
}

function PredictInner() {
  const params = useSearchParams();
  const [home, setHome] = useState(params.get("home") ?? "Arsenal");
  const [away, setAway] = useState(params.get("away") ?? "Chelsea");
  const [result, setResult] = useState<Prediction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [shaking, setShaking] = useState(false);
  const autoRan = useRef(false);

  function shake() {
    setShaking(false);
    requestAnimationFrame(() =>
      requestAnimationFrame(() => {
        setShaking(true);
        setTimeout(() => setShaking(false), 350);
      }),
    );
  }

  async function doPredict(h: string, a: string): Promise<Prediction> {
    const homeTeam = h.trim();
    const awayTeam = a.trim();
    setHome(homeTeam);
    setAway(awayTeam);
    if (homeTeam.toLowerCase() === awayTeam.toLowerCase()) {
      throw new Error("Pick two different teams.");
    }
    const r = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ home: homeTeam, away: awayTeam }),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof body.detail === "string" ? body.detail : "prediction failed");
    const parsed = PredictionSchema.safeParse(body);
    if (!parsed.success) throw new Error("bad response from model");
    return parsed.data;
  }

  async function run(h: string, a: string) {
    setBusy(true);
    setError(null);
    try {
      setResult(await doPredict(h, a));
    } catch (e) {
      setError(e instanceof Error ? e.message : "prediction failed");
      shake();
      throw e;
    } finally {
      setBusy(false);
    }
  }

  // Arriving via a fixture card (?home=&away=) predicts immediately, once.
  useEffect(() => {
    if (autoRan.current) return;
    const h = params.get("home");
    const a = params.get("away");
    if (h && a) {
      autoRan.current = true;
      run(h, a).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const inputCls =
    "mt-2 w-full rounded-full border-2 border-coal/15 bg-cream px-5 py-3 font-display text-xl uppercase tracking-wide text-coal outline-none placeholder:text-coal/30 focus:border-coal";

  return (
    <div className="space-y-3">
      <section className="rounded-[2rem] bg-cream px-6 py-12 sm:px-12">
        <p className="text-center font-mono text-[11px] tracking-[0.3em] text-ember">MANUAL PREDICTOR</p>
        <h1 className="mt-2 text-center font-display text-5xl uppercase leading-none text-ember sm:text-7xl">
          Name your tie
        </h1>
        <div className={`mx-auto mt-8 grid max-w-2xl gap-3 sm:grid-cols-2 ${shaking ? "is-shaking" : ""}`}>
          <label className="block" htmlFor="home-team">
            <span className="font-mono text-[11px] tracking-[0.3em] text-coal/60">HOME</span>
            <input id="home-team" value={home} disabled={busy} onChange={(e) => setHome(e.target.value)} className={inputCls} placeholder="Arsenal" />
          </label>
          <label className="block" htmlFor="away-team">
            <span className="font-mono text-[11px] tracking-[0.3em] text-coal/60">AWAY</span>
            <input id="away-team" value={away} disabled={busy} onChange={(e) => setAway(e.target.value)} className={inputCls} placeholder="Chelsea" />
          </label>
        </div>
        <div className="mt-6 text-center">
          <LoadingButton
            onAction={() => run(home, away)}
            pendingLabel="Reading form…"
            successLabel="Called"
            errorLabel="Retry"
            disabled={busy}
            onError={(e) => setError(e instanceof Error ? e.message : "prediction failed")}
          >
            Call it
          </LoadingButton>
        </div>
        {error && <p role="alert" className="mt-4 text-center text-sm text-away">{error}</p>}
        {result && (
          <div className="mx-auto mt-8 max-w-2xl rounded-3xl border-2 border-coal/10 bg-white/60 p-6">
          <p className="mb-4 text-center font-display text-2xl uppercase text-coal">
            {result.home} <span className="text-ember">vs</span> {result.away}
          </p>
          <div className="mb-4 flex flex-wrap justify-center gap-4">
            <Tooltip tip="Last 5 results, oldest first. W win · D draw · L loss.">
              <span className="flex flex-wrap justify-center gap-4">
                <FormBadges form={result.form_home} label={result.home.slice(0, 3).toUpperCase()} />
                <FormBadges form={result.form_away} label={result.away.slice(0, 3).toUpperCase()} />
              </span>
            </Tooltip>
          </div>
          {result.h2h && (
            <p className="mb-4 text-center font-mono text-xs tracking-[0.2em] text-coal/60">
              LAST MEETING {result.h2h.date}: {result.home} {result.h2h.home_goals}–{result.h2h.away_goals}{" "}
              {result.away}
            </p>
          )}
          <ProbBar prediction={result} />
          {result.scoreline?.shown ? (
            <p className="mt-3 text-center font-display text-xl uppercase text-coal">
              Model&apos;s scoreline: {result.scoreline.h}–{result.scoreline.a}{" "}
              <span className="text-ember">
                <ReelNumber value={`${(result.scoreline.p * 100).toFixed(1)}%`} />
              </span>
            </p>
          ) : (
            <p className="mt-3 text-center font-mono text-[10px] tracking-[0.25em] text-coal/50">
              {(result.scoreline?.reason ?? "No scoreline stamped").toUpperCase()}
            </p>
          )}
          <p className="mt-4 text-center font-mono text-[10px] tracking-[0.25em] text-coal/50">
            MODEL: {result.model}
          </p>
          <ShareRow result={result} />
          </div>
        )}
      </section>
    </div>
  );
}

export default function PredictClient() {
  return (
    <Suspense>
      <PredictInner />
    </Suspense>
  );
}
