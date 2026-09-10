"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

const ITEMS = [
  { href: "/", label: "HOME", hint: "LANDING" },
  { href: "/fixtures", label: "FIXTURES", hint: "THIS WEEK" },
  { href: "/predict", label: "PREDICT", hint: "NAME YOUR TIE" },
  { href: "/simulator", label: "SIMULATOR", hint: "TITLE ODDS" },
  { href: "/model", label: "MODEL", hint: "HONEST NUMBERS" },
];

function GitHubIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-4 w-4" fill="currentColor" aria-hidden>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
    </svg>
  );
}

/** FLOW pill nav, app-wide: lime logo, MENU dropdown, GitHub icon. */
export function NavBar() {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open ]);

  return (
    <nav aria-label="Primary" ref={rootRef} className="relative flex items-center justify-between gap-2">
      <Link href="/" className="font-display text-sm leading-none tracking-wide text-lime sm:text-base">
        MATCHDAY
        <span className="block text-[10px] tracking-[0.3em]">FATE</span>
      </Link>
      <button
        type="button"
        aria-expanded={open}
        aria-controls="nav-menu"
        onClick={() => setOpen((v) => !v)}
        className="pressable absolute left-1/2 -translate-x-1/2 rounded-full bg-lime px-5 py-2.5 font-mono text-xs tracking-[0.25em] text-coal sm:px-6"
      >
        MENU
      </button>
      <Link
        href="https://github.com/0xkhingx/football-prediction"
        target="_blank"
        rel="noreferrer"
        aria-label="GitHub repository"
        className="pressable rounded-full border border-cream/60 p-2.5 text-cream hover:border-cream"
      >
        <GitHubIcon />
      </Link>
      {/*
        Always mounted: first tap pays no mount cost. Visibility handled
        with opacity/translate/pointer-events; inert keeps hidden links
        out of keyboard reach. 120ms entrance for tap-instant feel.
      */}
      <div
        id="nav-menu"
        role="menu"
        aria-hidden={!open}
        ref={(el) => {
          if (el) (el as HTMLElement & { inert?: boolean }).inert = !open;
        }}
        className={`absolute left-0 right-0 top-full z-50 mt-2 overflow-hidden rounded-3xl bg-coal p-2 shadow-2xl transition-[opacity,transform] duration-120 ease-out ${
          open ? "visible opacity-100" : "invisible -translate-y-1 opacity-0"
        }`}
      >
          {ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              role="menuitem"
              onClick={() => setOpen(false)}
              className="flex items-center justify-between rounded-2xl px-5 py-3 font-mono text-xs tracking-[0.25em] text-cream hover:bg-white/10"
            >
              <span>{item.label}</span>
              <span className="text-[10px] text-cream/50">{item.hint}</span>
            </Link>
          ))}
        </div>
    </nav>
  );
}
