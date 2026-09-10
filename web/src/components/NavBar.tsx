"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINK = "font-mono text-[11px] tracking-[0.2em] text-ember hover:text-coal";

/** Flow pill nav on the landing route, standard pill everywhere else. */
export function NavBar() {
  const pathname = usePathname();
  if (pathname === "/") {
    return (
      <nav aria-label="Primary" className="flex items-center justify-between gap-2">
        <Link href="/" className="font-display text-sm leading-none tracking-wide text-lime sm:text-base">
          MATCHDAY
          <span className="block text-[10px] tracking-[0.3em]">FATE</span>
        </Link>
        <Link
          href="/fixtures"
          className="pressable rounded-full bg-lime px-6 py-2.5 font-mono text-xs tracking-[0.25em] text-coal"
        >
          MENU
        </Link>
        <div className="flex gap-2">
          <Link
            href="/predict"
            className="rounded-full border border-cream/60 px-4 py-2 font-mono text-[10px] tracking-[0.2em] text-cream hover:border-cream"
          >
            PREDICT
          </Link>
          <Link
            href="/model"
            className="rounded-full border border-cream/60 px-4 py-2 font-mono text-[10px] tracking-[0.2em] text-cream hover:border-cream"
          >
            MODEL
          </Link>
        </div>
      </nav>
    );
  }
  return (
    <nav aria-label="Primary" className="flex items-center justify-between rounded-full bg-cream px-4 py-3 sm:px-8">
      <div className="flex gap-3 sm:gap-8">
        <Link href="/fixtures" className={NAV_LINK}>
          Fixtures
        </Link>
        <Link href="/predict" className={NAV_LINK}>
          Predict
        </Link>
      </div>
      <Link href="/" className="font-display text-sm tracking-wide text-ember sm:text-lg">
        MATCHDAY FATE
      </Link>
      <div className="flex gap-3 sm:gap-8">
        <Link href="/simulator" className={NAV_LINK}>
          Simulator
        </Link>
        <Link href="/model" className={NAV_LINK}>
          Model
        </Link>
      </div>
    </nav>
  );
}
