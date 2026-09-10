/** Black pill CTA with circular arrow — straight from the reference. */
export function PillCta({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      className="pressable inline-flex items-center gap-4 rounded-full bg-coal py-2 pl-8 pr-2 font-mono text-xs tracking-[0.25em] text-cream hover:bg-black"
    >
      {children}
      <span aria-hidden="true" className="flex h-10 w-10 items-center justify-center rounded-full bg-cream text-coal">
        →
      </span>
    </a>
  );
}

/** Four glyphs for the model's senses — Elo, Form, Rest, Head-to-head —
    drawn in the site's abstract mark language. Meaning over homage. */
export function GlyphRow() {
  const cls = "h-10 w-10 text-ember sm:h-14 sm:w-14";
  return (
    <div className="flex items-center justify-center gap-6 sm:gap-10" role="img" aria-label="Elo, form, rest and head-to-head signals">
      {/* Elo ladder */}
      <svg viewBox="0 0 48 48" className={cls} fill="currentColor" aria-hidden>
        <rect x="6" y="28" width="8" height="14" rx="2" />
        <rect x="20" y="18" width="8" height="24" rx="2" />
        <rect x="34" y="8" width="8" height="34" rx="2" />
      </svg>
      {/* Form sparkline */}
      <svg viewBox="0 0 48 48" className={cls} fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" aria-hidden>
        <path d="M6 36 L16 28 L24 32 L32 16 L42 20" />
        <circle cx="42" cy="20" r="3" fill="currentColor" stroke="none" />
      </svg>
      {/* Rest hourglass */}
      <svg viewBox="0 0 48 48" className={cls} fill="currentColor" aria-hidden>
        <path d="M8 6h32v4c0 8-7 12-12 14 5 2 12 6 12 14v4H8v-4c0-8 7-12 12-14C15 22 8 18 8 10V6z" />
      </svg>
      {/* Head-to-head target */}
      <svg viewBox="0 0 48 48" className={cls} fill="none" stroke="currentColor" strokeWidth="5" aria-hidden>
        <circle cx="24" cy="24" r="17" />
        <circle cx="24" cy="24" r="6" fill="currentColor" stroke="none" />
      </svg>
    </div>
  );
}
