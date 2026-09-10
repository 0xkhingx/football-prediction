"use client";

import { MatchCard } from "./MatchCard";
import type { LeagueGroup } from "@/lib/weeks";

export function LeagueAccordion({
  groups,
  expanded,
  onToggle,
}: {
  groups: LeagueGroup[];
  expanded: string | null;
  onToggle: (code: string) => void;
}) {
  return (
    <div className="space-y-2">
      {groups.map((g) => {
        const open = expanded === g.code;
        const empty = g.fixtures.length === 0;
        return (
          <div key={g.code} className="overflow-hidden rounded-3xl bg-cream">
            <button
              type="button"
              aria-expanded={open}
              aria-label={`${g.name}, ${g.fixtures.length} ties`}
              disabled={empty}
              onClick={() => onToggle(g.code)}
              className="pressable flex w-full items-center gap-4 px-5 py-4 text-left disabled:cursor-default disabled:opacity-70"
            >
              <span className="font-display text-2xl uppercase leading-none text-coal sm:text-3xl">
                {g.tag}
              </span>
              <span className="font-mono text-[10px] tracking-[0.25em] text-coal/50">
                {g.name.toUpperCase()}
              </span>
              <span className="ml-auto font-mono text-[11px] tracking-[0.2em] text-ember">
                {empty ? "NO TIES THIS WEEK" : `${g.fixtures.length} TIES`}
              </span>
              {!empty && (
                <span
                  aria-hidden="true"
                  className="flex h-8 w-8 items-center justify-center rounded-full bg-coal font-mono text-sm text-cream transition-transform duration-200"
                  style={{ transform: open ? "rotate(90deg)" : "none" }}
                >
                  →
                </span>
              )}
            </button>
            {open && !empty && (
              <div className="grid gap-3 px-3 pb-3 sm:grid-cols-2">
                {g.fixtures.map((f) => (
                  <MatchCard key={`${f.date}-${f.home}-${f.away}`} fixture={f} tone="inset" />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
