"use client";

import Link from "next/link";

const OUTLINE =
  "rounded-full border border-cream/60 px-3 py-2 font-mono text-[10px] tracking-[0.2em] text-cream hover:border-cream sm:px-4";

/** FLOW pill nav, app-wide: lime logo, MENU pill, outlined destinations. */
export function NavBar() {
  return (
    <nav aria-label="Primary" className="relative flex items-center justify-between gap-2">
      <Link href="/" className="font-display text-sm leading-none tracking-wide text-lime sm:text-base">
        MATCHDAY
        <span className="block text-[10px] tracking-[0.3em]">FATE</span>
      </Link>
      <Link
        href="/fixtures"
        className="pressable absolute left-1/2 -translate-x-1/2 rounded-full bg-lime px-5 py-2.5 font-mono text-xs tracking-[0.25em] text-coal sm:px-6"
      >
        MENU
      </Link>
      <div className="flex gap-1.5 sm:gap-2">
        <Link href="/predict" className={OUTLINE}>
          PREDICT
        </Link>
        <Link href="/simulator" className={OUTLINE}>
          SIM
        </Link>
        <Link href="/model" className={OUTLINE}>
          MODEL
        </Link>
      </div>
    </nav>
  );
}
