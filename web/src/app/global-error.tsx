"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surfaced to Sentry when configured; console otherwise.
    console.error("unhandled route error:", error);
  }, [error]);

  return (
    <html lang="en">
      <body>
        <div className="mx-auto max-w-6xl px-3 py-4 sm:px-6">
          <section className="rounded-[2rem] bg-cream px-6 py-16 text-center sm:px-12">
            <p className="font-mono text-[11px] tracking-[0.3em] text-ember">500</p>
            <h1 className="mt-2 font-display text-5xl uppercase leading-none text-ember sm:text-7xl">
              Play stopped
            </h1>
            <p className="mx-auto mt-4 max-w-md text-sm leading-relaxed text-coal/70">
              Something broke on our side — not your call. Try again, or head back to the ties.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <button
                type="button"
                onClick={reset}
                className="rounded-full bg-coal px-6 py-2.5 font-mono text-xs tracking-[0.25em] text-cream"
              >
                RETRY
              </button>
              <Link
                href="/"
                className="rounded-full border-2 border-coal/15 px-6 py-2.5 font-mono text-xs tracking-[0.25em] text-coal hover:border-coal"
              >
                HOME
              </Link>
            </div>
          </section>
        </div>
      </body>
    </html>
  );
}
