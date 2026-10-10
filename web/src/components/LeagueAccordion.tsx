"use client";

import { useId, useRef } from "react";
import { MatchCard } from "./MatchCard";
import type { LeagueGroup } from "@/lib/weeks";

function LeagueTile({
  group,
  open,
  onToggle,
  onKeyDown,
  headerId,
  panelId,
  register,
}: {
  group: LeagueGroup;
  open: boolean;
  onToggle: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  headerId: string;
  panelId: string;
  register: (code: string, el: HTMLButtonElement | null) => void;
}) {
  const empty = group.fixtures.length === 0;

  return (
    <div className="overflow-hidden rounded-3xl bg-cream">
      <button
        type="button"
        id={headerId}
        ref={(el) => register(group.code, el)}
        aria-expanded={open}
        aria-controls={panelId}
        disabled={empty}
        onClick={onToggle}
        onKeyDown={onKeyDown}
        aria-label={`${group.name}, ${group.fixtures.length} ties`}
        className="relative flex w-full items-center gap-4 px-5 py-4 text-left disabled:cursor-default disabled:opacity-70"
      >
        <span className="pointer-events-none absolute left-1/2 -translate-x-1/2 font-display text-2xl uppercase leading-none text-coal sm:text-3xl">
          {group.tag}
        </span>
        <span className="sr-only">{group.name}</span>
        <span className="ml-auto font-mono text-[11px] tracking-[0.2em] text-coal/70">
          {empty ? "NO TIES THIS WEEK" : `${group.fixtures.length} TIES`}
        </span>
        {!empty && (
          <span
            aria-hidden="true"
            className="flex h-8 w-8 items-center justify-center rounded-full bg-coal font-mono text-sm text-cream"
          >
            {open ? "−" : "+"}
          </span>
        )}
      </button>
      {open && !empty && (
        <div id={panelId} role="region" aria-labelledby={headerId} className="panel-enter">
          <div className="grid gap-3 px-3 pb-3 sm:grid-cols-2">
            {group.fixtures.map((f) => (
              <MatchCard key={`${f.date}-${f.home}-${f.away}`} fixture={f} tone="inset" />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function LeagueAccordion({
  groups,
  expanded,
  onToggle,
}: {
  groups: LeagueGroup[];
  expanded: string | null;
  onToggle: (code: string) => void;
}) {
  const base = useId();
  const headers = useRef(new Map<string, HTMLButtonElement>());

  function register(code: string, el: HTMLButtonElement | null) {
    if (el) headers.current.set(code, el);
    else headers.current.delete(code);
  }

  function focusCode(code: string) {
    headers.current.get(code)?.focus();
  }

  function onKeyDown(e: React.KeyboardEvent) {
    const order = groups.map((g) => g.code);
    const active = document.activeElement;
    const at = Array.from(headers.current.values()).indexOf(active as HTMLButtonElement);
    if (e.key === "ArrowDown" || e.key === "ArrowRight") {
      e.preventDefault();
      focusCode(order[(at + 1 + order.length) % order.length]);
    } else if (e.key === "ArrowUp" || e.key === "ArrowLeft") {
      e.preventDefault();
      focusCode(order[(at - 1 + order.length) % order.length]);
    } else if (e.key === "Home") {
      e.preventDefault();
      focusCode(order[0]);
    } else if (e.key === "End") {
      e.preventDefault();
      focusCode(order[order.length - 1]);
    }
  }

  const live = groups.filter((g) => g.fixtures.length > 0);
  const idle = groups.filter((g) => g.fixtures.length === 0);

  return (
    <div className="space-y-2">
      {live.map((g) => (
        <LeagueTile
          key={g.code}
          group={g}
          open={expanded === g.code}
          onToggle={() => onToggle(g.code)}
          onKeyDown={onKeyDown}
          headerId={`${base}-header-${g.code}`}
          panelId={`${base}-panel-${g.code}`}
          register={register}
        />
      ))}
      {idle.length > 0 && (
        <details className="rounded-3xl bg-cream/60 px-5 py-4">
          <summary className="cursor-pointer font-mono text-[11px] tracking-[0.2em] text-coal/70 hover:text-coal">
            {idle.length === 1
              ? `1 OTHER LEAGUE — NO FIXTURES THIS WEEK`
              : `${idle.length} OTHER LEAGUES — NO FIXTURES THIS WEEK`}
          </summary>
          <p className="mt-2 text-sm leading-relaxed text-coal/70">
            {idle.map((g) => g.name).join(" · ")}
          </p>
        </details>
      )}
    </div>
  );
}
