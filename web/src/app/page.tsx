"use client";

import { useEffect, useState } from "react";
import { MatchCard } from "@/components/MatchCard";
import { LeagueTabs } from "@/components/LeagueTabs";
import { SeasonRecord } from "@/components/SeasonRecord";
import { BranchPill, GlyphRow, PillCta } from "@/components/Motif";
import { FixtureSchema, type Fixture } from "@/lib/types";

export default function FixturesPage() {
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [league, setLeague] = useState("ALL");
  const [loaded, setLoaded] = useState(false);
  const [backendError, setBackendError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/fixtures")
      .then(async (r) => {
        const body = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(typeof body.backendError === "string" ? body.backendError : `backend ${r.status}`);
        const list = Array.isArray(body.fixtures) ? body.fixtures : [];
        setFixtures(list.filter((f: unknown) => FixtureSchema.safeParse(f).success));
        setLoaded(true);
      })
      .catch((e) => {
        setBackendError(e instanceof Error ? e.message : "backend unreachable");
        setLoaded(true);
      });
  }, []);

  const shown = league === "ALL" ? fixtures : fixtures.filter((f) => f.league === league);

  return (
    <div className="space-y-3">
      {/* HERO — straight from the reference, text tweaked to fit */}
      <section className="rounded-[2rem] bg-cream px-6 py-14 text-center sm:px-12 sm:py-20">
        <h1 className="font-display uppercase leading-[0.95] text-ember">
          <span className="block text-5xl sm:text-8xl">Every fixture</span>
          <span className="mt-2 flex items-center justify-center gap-3 sm:gap-5">
            <span className="hidden h-10 w-28 rounded-full bg-lime sm:block sm:h-14 sm:w-40" aria-hidden />
            <BranchPill />
            <span className="text-5xl sm:text-8xl">has a</span>
          </span>
          <span className="block text-5xl sm:text-8xl">fate</span>
          <span className="mt-2 flex items-center justify-center gap-3 sm:gap-5">
            <span className="text-5xl sm:text-8xl">call it</span>
            <BranchPill />
            <span className="hidden h-10 w-10 rounded-full bg-lime sm:block sm:h-14 sm:w-14" aria-hidden />
          </span>
        </h1>
        <p className="mx-auto mt-8 max-w-xl text-sm leading-relaxed text-coal/70 sm:text-base">
          What decides a match before it&apos;s played? Form, Elo, rest, history. Our fair-play
          XGBoost reads 23 pre-match signals — no odds — and calls home, draw or away.
        </p>
        <div className="mt-8">
          <PillCta href="/predict">Predict a match</PillCta>
        </div>
      </section>

      {/* FIXTURES */}
      <section className="rounded-[2rem] bg-emberdark/40 px-6 py-10 sm:px-10">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
          <h2 className="font-display text-3xl uppercase text-cream sm:text-5xl">Upcoming ties</h2>
          <LeagueTabs active={league} onChange={setLeague} />
        </div>
      {!loaded && <p className="font-mono text-xs tracking-[0.25em] text-cream/80">LOADING…</p>}
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
      {loaded && !backendError && shown.length === 0 && (
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
        <div className="grid gap-3 sm:grid-cols-2">
          {shown.map((f) => (
            <MatchCard key={`${f.date}-${f.home}-${f.away}`} fixture={f} />
          ))}
        </div>
      </section>

      <SeasonRecord />

      {/* BOTTOM SPLIT — reference layout, football copy */}      <section className="grid gap-3 md:grid-cols-5">
        <div className="rounded-[2rem] bg-coal p-8 sm:p-10 md:col-span-2">
          <p className="font-display text-3xl uppercase leading-[1.02] text-cream sm:text-4xl">
            Welcome to the physics of <span className="text-lime">your own form</span>
          </p>
          <p className="mt-8 font-mono text-[10px] tracking-[0.3em] text-cream/60">
            ELO · FORM · REST · H2H
          </p>
        </div>
        <div className="rounded-[2rem] bg-lime p-8 text-center sm:p-10 md:col-span-3">
          <GlyphRow />
          <p className="mx-auto mt-6 max-w-md text-sm leading-relaxed text-coal/80">
            Pick a fixture, get P(H/D/A) — plus an honest read on where the model stands today:
            a fair-play XGB that beats naive but still trails the bookmaker. Numbers on the model page.
          </p>
        </div>
      </section>
    </div>
  );
}
