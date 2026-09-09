import { useEffect, useState } from "react";
import { pct } from "@/lib/format";
import type { Prediction } from "@/lib/types";
import { OUTCOME_LABEL } from "@/lib/types";

const BAR_COLOR: Record<string, string> = {
  H: "bg-home",
  D: "bg-draw",
  A: "bg-away",
};

export function ProbBar({ prediction }: { prediction: Prediction }) {
  const rows = [
    { key: "H", label: "HOME", value: prediction.pH },
    { key: "D", label: "DRAW", value: prediction.pD },
    { key: "A", label: "AWAY", value: prediction.pA },
  ];
  // Grow bars from zero on each new matchup (decorative; disabled under reduced motion).
  const [grown, setGrown] = useState(false);
  useEffect(() => {
    setGrown(false);
    const frame = requestAnimationFrame(() => requestAnimationFrame(() => setGrown(true)));
    return () => cancelAnimationFrame(frame);
  }, [prediction.home, prediction.away]);
  return (
    <div className="space-y-3">
      {rows.map((r, i) => (
        <div key={r.key}>
          <div className="mb-1 flex justify-between font-mono text-xs tracking-[0.2em] text-coal/70">
            <span>
              {r.label}{" "}
              {prediction.prediction === r.key && (
                <span className="text-ember">
                  ●<span className="sr-only"> (model pick)</span>
                </span>
              )}
            </span>
            <span>{pct(r.value)}</span>
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-coal/10">
            <div
              className={`bar-grow h-full rounded-full ${BAR_COLOR[r.key]}`}
              style={{
                width: grown ? `${Math.min(100, Math.max(0, r.value * 100))}%` : "0%",
                transitionDelay: `${i * 60}ms`,
              }}
            />
          </div>
        </div>
      ))}
      <p className="pt-1 font-display text-2xl uppercase text-coal">
        {OUTCOME_LABEL[prediction.prediction]} · {pct(prediction.confidence)}
      </p>
      <p
        className={`inline-block rounded-full px-4 py-1.5 font-mono text-[11px] tracking-[0.25em] ${
          prediction.call ? "bg-coal text-lime" : "bg-coal/10 text-coal/70"
        }`}
      >
        {prediction.call_label}
      </p>
    </div>
  );
}
