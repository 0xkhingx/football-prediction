"use client";

import { useEffect, useMemo, useState } from "react";
import { Tabs } from "@/components/interior/tabs";
import { Kbd } from "@/components/Tooltip";
import { trackEvent } from "@/lib/analytics";
import { LEAGUES } from "@/lib/constants";

type Row = { team: string; pts: number; title: string; top4: string; title_raw?: number; top4_raw?: number };

type SortKey = "pts" | "title" | "top4";

const SORT_VALUE: Record<SortKey, (r: Row) => number> = {
  pts: (r) => Number(r.pts) || 0,
  title: (r) => r.title_raw ?? 0,
  top4: (r) => r.top4_raw ?? 0,
};

const SORT_LABEL: Record<SortKey, string> = { pts: "Points", title: "Title chance", top4: "Top-4 chance" };

function titleRank(rows: Row[]): Row[] {
  return [...rows].sort((a, b) => (b.title_raw ?? 0) - (a.title_raw ?? 0));
}

export default function SimulatorPage() {
  const [league, setLeague] = useState("E0");
  const [rows, setRows] = useState<Row[]>([]);
  const [note, setNote] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("pts");
  const [sortDir, setSortDir] = useState<1 | -1>(-1);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === -1 ? 1 : -1));
    } else {
      setSortKey(key);
      setSortDir(-1);
    }
  }

  const sortedRows = useMemo(() => {
    const get = SORT_VALUE[sortKey];
    return [...rows].sort((a, b) => (get(a) - get(b)) * sortDir || String(a.team).localeCompare(String(b.team)));
  }, [rows, sortKey, sortDir]);

  useEffect(() => {
    setLoaded(false);
    setFailed(false);
    fetch(`/api/simulation?league=${league}`)
      .then(async (r) => {
        const b = await r.json().catch(() => ({}));
        if (!r.ok || !Array.isArray(b.table)) throw new Error("simulation unavailable");
        setRows(b.table);
        setNote(typeof b.note === "string" ? b.note : "");
        setLoaded(true);
        trackEvent("simulation_viewed", { league });
      })
      .catch(() => {
        setFailed(true);
        setLoaded(true);
      });
  }, [league]);

  return (
    <div className="space-y-3">
      <section className="rounded-[2rem] bg-cream px-6 py-10 sm:px-12">
        <p className="text-center font-mono text-[11px] tracking-[0.3em] text-ember">2000 SEASONS SIMULATED</p>
        <h1 className="mt-2 text-center font-display text-5xl uppercase leading-none text-ember sm:text-7xl">
          Who lifts it
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-center text-sm leading-relaxed text-coal/75">
          Projected league finishes from 2,000 season simulations — today&apos;s table plus every
          remaining fixture, with form frozen where it stands now.
        </p>
        <div className="mt-6 flex flex-col items-center gap-2">
          <div className="w-full max-w-xl">
            <Tabs
              items={LEAGUES.map((l) => ({ value: l.code, label: l.tag }))}
              value={league}
              onValueChange={setLeague}
              label="League"
            />
          </div>
          <p className="text-center font-mono text-[11px] tracking-[0.15em] text-coal/65">
            {note ? `${note} — RANGES, NOT PRECISION.` : "TITLE CHANCES AS ROUNDED BANDS, NOT EXACT ODDS."}{" "}
            <span className="hidden lg:inline">
              TIP <Kbd>←</Kbd> <Kbd>→</Kbd> SWITCH LEAGUES
            </span>
          </p>
        </div>
        {!loaded && (
          <p className="mt-8 text-center font-mono text-xs tracking-[0.25em] text-coal/60">LOADING…</p>
        )}
        {loaded && failed && (
          <p role="alert" className="mx-auto mt-8 max-w-xl rounded-3xl bg-coal p-6 text-center font-mono text-xs tracking-[0.2em] text-cream">
            SIMULATION UNAVAILABLE — START THE API AND RE-RUN MAKE SIMULATE
          </p>
        )}
        {loaded && !failed && rows.length >= 2 && (
          <div className="mx-auto mt-8 max-w-2xl rounded-3xl bg-coal p-6 text-center" aria-label="Title outlook">
            <p className="font-mono text-[11px] tracking-[0.25em] text-lime">TITLE OUTLOOK</p>
            {(() => {
              const [first, second] = titleRank(rows);
              return (
                <div className="mt-3 flex items-center justify-center gap-6 sm:gap-10">
                  {[
                    { r: first, tag: "FRONTRUNNER" },
                    { r: second, tag: "CHASER" },
                  ].map(({ r, tag }) => (
                    <div key={r.team}>
                      <p className="font-mono text-[10px] tracking-[0.2em] text-cream/60">{tag}</p>
                      <p className="mt-1 font-display text-2xl uppercase leading-none text-cream sm:text-3xl">
                        {r.team}
                      </p>
                      <p className="mt-1 font-mono text-sm text-lime">
                        {r.title} <span className="text-cream/60">TITLE</span>
                      </p>
                      <p className="font-mono text-[11px] text-cream/60">{r.pts} PTS NOW</p>
                    </div>
                  ))}
                </div>
              );
            })()}
          </div>
        )}
        {loaded && !failed && (
        <div className="mx-auto mt-6 max-w-2xl overflow-hidden rounded-3xl border-2 border-coal/10">
          <div className="overflow-x-auto">
          <table className="w-full bg-white/60 font-mono text-sm tabular-nums">
            <thead>
              <tr className="bg-coal text-left text-cream">
                <th scope="col" className="px-3 py-3 text-[11px] tracking-[0.2em]">#</th>
                <th scope="col" className="px-5 py-3 text-[11px] tracking-[0.2em]">TEAM</th>
                {(
                  [
                    { key: "pts", label: "PTS" },
                    { key: "title", label: "TITLE" },
                    { key: "top4", label: "TOP 4" },
                  ] as const
                ).map((c) => (
                  <th
                    key={c.key}
                    scope="col"
                    aria-sort={sortKey === c.key ? (sortDir === -1 ? "descending" : "ascending") : "none"}
                    className="px-5 py-3 text-right text-[11px] tracking-[0.2em]"
                  >
                    <button
                      type="button"
                      onClick={() => toggleSort(c.key)}
                      aria-label={`Sort by ${SORT_LABEL[c.key]}`}
                      className="pressable ml-auto flex min-h-[32px] items-center gap-1 rounded px-1 uppercase hover:text-lime"
                    >
                      {c.label}
                      <span aria-hidden="true" className={sortKey === c.key ? "text-lime" : "text-cream/40"}>
                        {sortKey === c.key ? (sortDir === -1 ? "↓" : "↑") : "↕"}
                      </span>
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sortedRows.map((r, i) => (
                <tr key={r.team} className="border-t border-coal/10 text-coal transition-colors hover:bg-lime/25">
                  <td className="px-3 py-2 text-coal/60">{i + 1}</td>
                  <th scope="row" title={String(r.team)} className="max-w-40 truncate px-5 py-2 text-left font-semibold">{String(r.team)}</th>
                  <td className="px-5 py-2 text-right">{Number(r.pts)}</td>
                  <td className="px-5 py-2 text-right font-semibold text-ember">{String(r.title)}</td>
                  <td className="px-5 py-2 text-right">{String(r.top4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
        )}
        {loaded && !failed && (
          <p className="mx-auto mt-4 max-w-xl text-center text-xs leading-relaxed text-coal/65">
            Bands round the simulated frequency, so 45–50% means roughly that share of the 2,000
            seasons — not a bookmaker price. Full method on the{" "}
            <a href="/model" className="underline decoration-ember decoration-2 underline-offset-2 hover:text-ember">
              model page
            </a>
            .
          </p>
        )}
      </section>
    </div>
  );
}
