"use client";

import { useEffect, useState } from "react";
import { LeagueTabs } from "@/components/LeagueTabs";

type Row = { team: string; pts: number; title: string; top4: string };

export default function SimulatorPage() {
  const [league, setLeague] = useState("E0");
  const [rows, setRows] = useState<Row[]>([]);
  const [note, setNote] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);

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
      })
      .catch(() => {
        setFailed(true);
        setLoaded(true);
      });
  }, [league]);

  return (
    <div className="space-y-3">
      <section className="rounded-[2rem] bg-cream px-6 py-12 sm:px-12">
        <p className="text-center font-mono text-[11px] tracking-[0.3em] text-ember">2000 SEASONS SIMULATED</p>
        <h1 className="mt-2 text-center font-display text-5xl uppercase leading-none text-ember sm:text-7xl">
          Who lifts it
        </h1>
        <div className="mt-6 flex justify-center">
          <LeagueTabs active={league} onChange={setLeague} />
        </div>
        {!loaded && (
          <p className="mt-8 text-center font-mono text-xs tracking-[0.25em] text-coal/60">LOADING…</p>
        )}
        {loaded && failed && (
          <p role="alert" className="mx-auto mt-8 max-w-xl rounded-3xl bg-coal p-6 text-center font-mono text-xs tracking-[0.2em] text-cream">
            SIMULATION UNAVAILABLE — START THE API AND RE-RUN MAKE SIMULATE
          </p>
        )}
        {loaded && !failed && (
        <div className="mx-auto mt-8 max-w-2xl overflow-hidden rounded-3xl border-2 border-coal/10">
          <div className="overflow-x-auto">
          <table className="w-full bg-white/60 font-mono text-sm">
            <thead>
              <tr className="bg-coal text-left text-cream">
                <th className="px-5 py-3 text-[11px] tracking-[0.25em]">TEAM</th>
                <th className="px-5 py-3 text-right text-[11px] tracking-[0.25em]">PTS</th>
                <th className="px-5 py-3 text-right text-[11px] tracking-[0.25em]">TITLE</th>
                <th className="px-5 py-3 text-right text-[11px] tracking-[0.25em]">TOP 4</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.team} className="border-t border-coal/10 text-coal">
                  <td className="max-w-40 truncate px-5 py-2 font-semibold">{String(r.team)}</td>
                  <td className="px-5 py-2 text-right">{Number(r.pts)}</td>
                  <td className="px-5 py-2 text-right text-ember">{String(r.title)}</td>
                  <td className="px-5 py-2 text-right">{String(r.top4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </div>
        )}
        {note && !failed && (
          <p className="mx-auto mt-4 max-w-xl text-center font-mono text-[10px] tracking-[0.2em] text-coal/50">
            {note.toUpperCase()} RANGES, NOT PRECISION.
          </p>
        )}
      </section>
    </div>
  );
}
