"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { GlyphRow, PillCta } from "@/components/Motif";
import { ScribbleArrow, ScribbleCircle, ScribbleUnderline } from "@/components/Flow";
import { LEAGUES } from "@/lib/constants";

function Ticker() {
  const items = [...LEAGUES.map((l) => l.tag), "LIVE 2026/27", "FAIR PLAY", "NO ODDS"];
  const row = [...items, ...items];
  return (
    <div className="overflow-hidden rounded-[2rem] bg-coal py-4" aria-hidden>
      <div className="ticker flex w-max items-center gap-8 whitespace-nowrap px-4">
        {row.map((t, i) => (
          <span key={i} className="font-mono text-xs tracking-[0.3em] text-cream">
            {t} <span className="text-lime">·</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function TallyLine() {
  const [text, setText] = useState<string | null>(null);
  useEffect(() => {
    fetch("/api/season-record")
      .then((r) => r.json())
      .then((b) => {
        if (b.tally && typeof b.tally.acc === "number" && typeof b.tally.n === "number") {
          setText(`${(b.tally.acc * 100).toFixed(1)}% ACROSS ${b.tally.n} CALLS — HONEST NUMBERS ON THE MODEL PAGE`);
        }
      })
      .catch(() => {});
  }, []);
  if (!text) return null;
  return (
    <p className="text-center font-mono text-[11px] tracking-[0.25em] text-cream/80">
      <Link href="/model" className="underline decoration-lime decoration-2 underline-offset-4 hover:text-cream">
        {text}
      </Link>
    </p>
  );
}

export default function HomePage() {
  return (
    <div className="space-y-3">
      {/* HERO — FLOW full-bleed: blurple field, giant white type, real ball with face */}
      <section className="-mx-3 bg-[var(--flow-bg)] px-6 py-14 text-center sm:-mx-6 sm:px-12 sm:py-20">
        <div className="relative mx-auto max-w-5xl">
          <h1 className="font-display uppercase leading-[0.9] text-white">
            <span className="block text-6xl sm:text-9xl">Every fixture</span>
            <span className="block text-6xl sm:text-9xl">has a fate</span>
            <span className="block text-6xl text-lime sm:text-9xl">Call it</span>
          </h1>
          <div className="relative mt-8 inline-block">
            <PillCta href="/fixtures">See fixtures</PillCta>
            <ScribbleUnderline className="absolute -bottom-5 left-1/2 h-5 w-56 -translate-x-1/2" />
          </div>
          <div className="relative mx-auto mt-10 w-fit">
            <TallyLine />
            <ScribbleCircle className="pointer-events-none absolute -inset-x-8 -inset-y-3 h-[calc(100%+24px)] w-[calc(100%+64px)]" />
          </div>
          <ScribbleArrow className="pointer-events-none absolute bottom-10 left-6 hidden h-28 w-28 lg:block" aria-hidden />
        </div>
      </section>

      <Ticker />

      {/* BOTTOM SPLIT — reference layout, football copy */}
      <section className="grid gap-3 md:grid-cols-5">
        <div className="rounded-[2rem] bg-coal p-8 sm:p-10 md:col-span-2">
          <p className="font-display text-3xl uppercase leading-[1.02] text-cream sm:text-4xl">
            Welcome to the physics of <span className="text-lime">form</span>
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
