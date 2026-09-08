import { API_BASE } from "@/lib/constants";
import { GlyphRow } from "@/components/Motif";

export const revalidate = 3600;

type EvalBody = {
  test_set_size?: number;
  naive?: { log_loss?: number };
  prod_tuned?: { xgboost_tuned?: { log_loss?: number } };
  bookmaker?: { log_loss?: number };
};

async function getEval(): Promise<EvalBody> {
  try {
    const r = await fetch(`${API_BASE}/evaluate`, { next: { revalidate: 3600 } });
    if (!r.ok) return {};
    return (await r.json()) as EvalBody;
  } catch {
    return {};
  }
}

export default async function ModelPage() {
  const data = await getEval();
  const rows = [
    { model: "Naive (training prior)", ll: data.naive?.log_loss },
    { model: "XGB-tuned, fair-play (PROD)", ll: data.prod_tuned?.xgboost_tuned?.log_loss },
    { model: "Bookmaker B365 (benchmark)", ll: data.bookmaker?.log_loss },
  ];
  return (
    <div className="space-y-3">
      <section className="rounded-[2rem] bg-cream px-6 py-12 sm:px-12">
        <p className="text-center font-mono text-[11px] tracking-[0.3em] text-ember">HOW IT WORKS</p>
        <h1 className="mt-2 text-center font-display text-5xl uppercase leading-none text-ember sm:text-7xl">
          Honest numbers
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-center text-sm leading-relaxed text-coal/70">
          {data.test_set_size
            ? `Test set: ${data.test_set_size} matches. Primary metric: log-loss.`
            : "Live model numbers unavailable — start the API to populate this page."}{" "}
          The bookmaker still wins — that&apos;s expected, and disclosed.
        </p>
        <div className="mx-auto mt-8 max-w-2xl overflow-hidden rounded-3xl border-2 border-coal/10">
          <table className="w-full bg-white/60 font-mono text-sm">
            <thead>
              <tr className="bg-coal text-left text-cream">
                <th className="px-5 py-3 text-[11px] tracking-[0.25em]">MODEL</th>
                <th className="px-5 py-3 text-right text-[11px] tracking-[0.25em]">LOG-LOSS ↓</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.model} className="border-t border-coal/10 text-coal">
                  <td className="px-5 py-3">{r.model}</td>
                  <td className="px-5 py-3 text-right">{r.ll?.toFixed(4) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="rounded-[2rem] bg-lime p-8 text-center sm:p-10">
        <GlyphRow />
        <p className="mx-auto mt-6 max-w-xl text-sm leading-relaxed text-coal/80">
          No odds features — only Elo, form, head-to-head, rest, goals, shots and corners.
          Train/serve parity is enforced by a point-in-time test. Research demo, not betting advice.
        </p>
      </section>
    </div>
  );
}
