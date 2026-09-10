"use client";

import { useId, useState } from "react";

/**
 * Zero-dependency tooltip in Matchday Fate tokens. Shows on hover and
 * keyboard focus, dismisses on Escape. For short explanations only —
 * anything interactive belongs in a popover, not here.
 */
export function Tooltip({ tip, children }: { tip: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      onKeyDown={(e) => {
        if (e.key === "Escape") setOpen(false);
      }}
    >
      <span aria-describedby={id} className="inline-flex">
        {children}
      </span>
      {open && (
        <span
          role="tooltip"
          id={id}
          className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 w-48 -translate-x-1/2 rounded-xl bg-coal px-3 py-2 text-center font-mono text-[10px] leading-relaxed tracking-wide text-cream shadow-xl"
        >
          {tip}
        </span>
      )}
    </span>
  );
}

/** Tiny keyboard hint, e.g. <Kbd>←</Kbd> <Kbd>→</Kbd> switch leagues. */
export function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="rounded-md border border-current px-1.5 py-0.5 font-mono text-[10px] opacity-70">
      {children}
    </kbd>
  );
}
