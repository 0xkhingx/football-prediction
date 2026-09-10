"use client";

import { useEffect } from "react";
import { motion, useReducedMotion } from "motion/react";
import { useAccordion, useAutoHeight } from "./interior/accordion";
import type { AccordionHeaderProps, AccordionPanelProps } from "./interior/accordion";
import { MatchCard } from "./MatchCard";
import type { LeagueGroup } from "@/lib/weeks";

const DISCLOSE = { type: "spring", stiffness: 480, damping: 40, mass: 0.6 } as const;

function LeagueTile({
  group,
  open,
  header,
  panel,
}: {
  group: LeagueGroup;
  open: boolean;
  header: AccordionHeaderProps;
  panel: AccordionPanelProps;
}) {
  const { ref, height, ready } = useAutoHeight();
  const reduced = useReducedMotion();
  const empty = group.fixtures.length === 0;

  useEffect(() => {
    const el = ref.current as (HTMLElement & { inert?: boolean }) | null;
    if (!el) return;
    el.inert = !open;
    return () => {
      el.inert = false;
    };
  }, [ref, open]);

  return (
    <div className="overflow-hidden rounded-3xl bg-cream">
      <button
        {...header}
        disabled={empty}
        aria-label={`${group.name}, ${group.fixtures.length} ties`}
        className="pressable relative flex w-full items-center gap-4 px-5 py-4 text-left disabled:cursor-default disabled:opacity-70"
      >
        <span className="hidden font-mono text-[10px] tracking-[0.25em] text-coal/50 sm:inline">
          {group.name.toUpperCase()}
        </span>
        <span className="pointer-events-none absolute left-1/2 -translate-x-1/2 font-display text-2xl uppercase leading-none text-coal sm:text-3xl">
          {group.tag}
        </span>
        <span className="ml-auto font-mono text-[11px] tracking-[0.2em] text-ember">
          {empty ? "NO TIES THIS WEEK" : `${group.fixtures.length} TIES`}
        </span>
        {!empty && (
          <motion.span
            aria-hidden="true"
            className="flex h-8 w-8 items-center justify-center rounded-full bg-coal font-mono text-sm text-cream"
            initial={false}
            animate={{ rotate: open ? 90 : 0 }}
            transition={reduced ? { duration: 0 } : { type: "spring", stiffness: 700, damping: 46, mass: 0.5 }}
          >
            →
          </motion.span>
        )}
      </button>
      <motion.div
        initial={false}
        animate={ready ? { height: open && !empty ? height : 0 } : {}}
        transition={reduced ? { duration: 0 } : DISCLOSE}
        style={{ overflow: "hidden", height: ready ? undefined : 0 }}
      >
        <div {...panel} ref={ref as unknown as React.LegacyRef<HTMLDivElement>}>
          <div className="grid gap-3 px-3 pb-3 sm:grid-cols-2">
            {group.fixtures.map((f) => (
              <MatchCard key={`${f.date}-${f.home}-${f.away}`} fixture={f} tone="inset" />
            ))}
          </div>
        </div>
      </motion.div>
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
  const { isOpen, headerProps, panelProps } = useAccordion({
    items: groups.map((g) => ({ id: g.code })),
    type: "single",
    open: expanded ? [expanded] : [],
    onOpenChange: (next) => {
      if (next.length === 0) {
        if (expanded) onToggle(expanded);
      } else if (next[0]) {
        onToggle(next[0]);
      }
    },
  });

  return (
    <div className="space-y-2">
      {groups.map((g) => (
        <LeagueTile
          key={g.code}
          group={g}
          open={isOpen(g.code)}
          header={headerProps(g.code)}
          panel={panelProps(g.code)}
        />
      ))}
    </div>
  );
}
