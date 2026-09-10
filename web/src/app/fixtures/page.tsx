"use client";

import { useEffect, useMemo, useState } from "react";
import { LeagueAccordion } from "@/components/LeagueAccordion";
import { SeasonRecord } from "@/components/SeasonRecord";
import { PillCta } from "@/components/Motif";
import { Kbd } from "@/components/Tooltip";
import { FixtureSchema, type Fixture } from "@/lib/types";
import { groupByLeague, groupWeeks, leadLeague, nearestWeekIndex } from "@/lib/weeks";

export default function FixturesPage() {
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [weekIdx, setWeekIdx] = useState<number | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/fixtures")
      .then(async (r) => {
        const body = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(typeof body.backendError === "string" ? body.backendError : `backend ${r.status}`);
        const list = Array.isArray(body.fixtures) ? body.fixtures : [];
        const valid = list.filter((f: unknown) => FixtureSchema.safeParse(f).success);
        setFixtures(valid);
        if (valid.length > 0) {
          const weeks = groupWeeks(valid);
          const wi = nearestWeekIndex(weeks);
          setWeekIdx((prev) => prev ?? wi);
          const w = weeks[wi];
          setExpanded((prev) => prev ?? (w ? leadLeague(groupByLeague(w.fixtures)) : null));
        }
        setLoaded(true);
      })
      .catch((e) => {
        setBackendError(e instanceof Error ? e.message : "backend unreachable");
        setLoaded(true);
      });
  }, []);

  const weeks = useMemo(() => groupWeeks(fixtures), [fixtures]);
  const week = weekIdx === null ? null : (weeks[weekIdx] ?? null);
  const groups = useMemo(() => (week ? groupByLeague(week.fixtures) : []), [week]);

  function goWeek(next: number) {
    const clamped = Math.max(0, Math.min(weeks.length - 1, next));
    setWeekIdx(clamped);
    const w = weeks[clamped];
    setExpanded(w ? leadLeague(groupByLeague(w.fixtures)) : null);
  }

  return (
    <div className="space-y-3">
      <SeasonRecord />

      {/* FIXTURES — this week only, league accordion, pager for the rest */}
      <section className="rounded-[2rem] bg-emberdark/40 px-6 py-10 sm:px-10">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl uppercase text-cream sm:text-5xl">This week</h1>
            {week && (
              <p className="mt-1 font-mono text-[11px] tracking-[0.25em] text-cream/70">
                {week.label} · {week.fixtures.length} TIES · TAP A LEAGUE
              </p>
            )}
          </div>
        </div>
        {week && weeks.length > 1 && (
          <div className="mb-5 flex items-center gap-2" role="group" aria-label="Fixture week">
            <button
              type="button"
              disabled={weekIdx === 0}
              onClick={() => goWeek((weekIdx ?? 0) - 1)}
              className="pressable rounded-full bg-cream px-4 py-1.5 font-mono text-[11px] tracking-[0.2em] text-coal disabled:opacity-40"
            >
              ← PREV
            </button>
            <span className="font-mono text-[11px] tracking-[0.2em] text-cream/70">
              {(weekIdx ?? 0) + 1} / {weeks.length}
            </span>
            <button
              type="button"
              disabled={weekIdx === weeks.length - 1}
              onClick={() => goWeek((weekIdx ?? 0) + 1)}
              className="pressable rounded-full bg-cream px-4 py-1.5 font-mono text-[11px] tracking-[0.2em] text-coal disabled:opacity-40"
            >
              NEXT →
            </button>
          </div>
        )}
        {week && (
          <p className="mb-5 font-mono text-[10px] tracking-[0.2em] text-cream/60">
            TIP <Kbd>↑</Kbd> <Kbd>↓</Kbd> MOVE · <Kbd>ENTER</Kbd> OPENS A LEAGUE
          </p>
        )}
      {!loaded && (
        <div className="grid gap-3 sm:grid-cols-2" aria-hidden>
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="rounded-3xl bg-cream p-5">
              <div className="skeleton h-3 w-2/3 rounded-full bg-coal/15" />
              <div className="skeleton mt-3 h-7 w-5/6 rounded-lg bg-coal/15" />
              <div className="skeleton mt-4 h-7 w-24 rounded-full bg-coal/15" />
            </div>
          ))}
        </div>
      )}
      {loaded && backendError && (
        <div className="rounded-3xl bg-coal p-8 text-center" role="alert">
          <p className="font-display text-3xl uppercase text-cream">Can&apos;t reach the model</p>
          <p className="mx-auto mt-2 max-w-md font-mono text-xs tracking-[0.2em] text-cream/60">
            {backendError.toUpperCase()} — START THE API OR TRY MANUAL PREDICT
          </p>
          <div className="mt-5">
            <PillCta href="/predict">Manual predictor</PillCta>
          </div>
        </div>
      )}
      {loaded && !backendError && !week && (
          <div className="rounded-3xl bg-cream p-8 text-center">
            <p className="font-display text-3xl uppercase text-coal">Offseason — no ties right now</p>
            <p className="mx-auto mt-2 max-w-md text-sm text-coal/70">
              Pick any matchup manually and the model will still call it from history.
            </p>
            <div className="mt-5">
              <PillCta href="/predict">Manual predictor</PillCta>
            </div>
          </div>
        )}
        {week && (
          <LeagueAccordion
            groups={groups}
            expanded={expanded}
            onToggle={(code) => setExpanded((prev) => (prev === code ? null : code))}
          />
        )}
      </section>
    </div>
  );
}
