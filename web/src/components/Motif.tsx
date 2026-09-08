/** Black pill with a git-branch graph — the reference's signature motif. */
export function BranchPill({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full bg-coal px-4 py-2 sm:px-6 sm:py-3 ${className}`}
      aria-hidden
    >
      <svg viewBox="0 0 120 36" className="h-5 w-auto sm:h-7" fill="none">
        <line x1="14" y1="18" x2="46" y2="18" stroke="#E7EF45" strokeWidth="3" />
        <line x1="46" y1="18" x2="66" y2="8" stroke="#E7EF45" strokeWidth="3" />
        <line x1="46" y1="18" x2="66" y2="28" stroke="#E7EF45" strokeWidth="3" />
        <line x1="66" y1="8" x2="96" y2="8" stroke="#E7EF45" strokeWidth="3" />
        <line x1="66" y1="28" x2="96" y2="28" stroke="#E7EF45" strokeWidth="3" />
        <circle cx="14" cy="18" r="7" fill="#E7EF45" />
        <circle cx="46" cy="18" r="7" fill="#E85A24" />
        <circle cx="66" cy="8" r="6" fill="#E85A24" />
        <circle cx="66" cy="28" r="6" fill="#E7EF45" />
        <circle cx="96" cy="8" r="7" fill="#FAF5EC" />
        <circle cx="96" cy="28" r="7" fill="#FAF5EC" />
      </svg>
    </span>
  );
}

/** Black pill CTA with circular arrow — straight from the reference. */
export function PillCta({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      className="inline-flex items-center gap-4 rounded-full bg-coal py-2 pl-8 pr-2 font-mono text-xs tracking-[0.25em] text-cream transition hover:bg-black"
    >
      {children}
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-cream text-coal">
        →
      </span>
    </a>
  );
}

/** Four abstract orange glyphs for the lime card, echoing the reference. */
export function GlyphRow() {
  return (
    <div className="flex items-center justify-center gap-6 sm:gap-10" aria-hidden>
      <svg viewBox="0 0 48 48" className="h-10 w-10 text-ember sm:h-14 sm:w-14" fill="currentColor">
        <circle cx="24" cy="12" r="9" />
        <circle cx="12" cy="24" r="9" />
        <circle cx="36" cy="24" r="9" />
        <circle cx="24" cy="36" r="9" />
      </svg>
      <svg viewBox="0 0 48 48" className="h-10 w-10 text-ember sm:h-14 sm:w-14" fill="currentColor">
        <path d="M8 6h32l-10 12v6l-6 8h-8l-6-8v-6L8 6z" opacity="0" />
        <path d="M8 6h32v4c0 8-7 12-12 14 5 2 12 6 12 14v4H8v-4c0-8 7-12 12-14C15 22 8 18 8 10V6z" />
      </svg>
      <svg viewBox="0 0 48 48" className="h-10 w-10 text-ember sm:h-14 sm:w-14" fill="currentColor">
        <circle cx="15" cy="15" r="9" />
        <circle cx="33" cy="15" r="9" />
        <circle cx="15" cy="33" r="9" />
        <circle cx="33" cy="33" r="9" />
      </svg>
      <svg viewBox="0 0 48 48" className="h-10 w-10 text-ember sm:h-14 sm:w-14" fill="none" stroke="currentColor" strokeWidth="5">
        <circle cx="24" cy="24" r="17" />
        <circle cx="24" cy="24" r="6" fill="currentColor" stroke="none" />
      </svg>
    </div>
  );
}
