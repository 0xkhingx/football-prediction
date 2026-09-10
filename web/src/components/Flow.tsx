"use client";

/**
 * FLOW landing elements: hand-drawn marker scribbles. Pure SVG + CSS.
 */

const MARKER = {
  stroke: "#161412",
  strokeWidth: 7,
  strokeLinecap: "round",
  fill: "none",
} as const;

/** Wavy underline for the CTA. */
export function ScribbleUnderline({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 220 24" className={className} aria-hidden {...MARKER}>
      <path d="M6 14 C 50 6, 90 20, 130 12 S 200 10, 214 14" />
    </svg>
  );
}

/** Loose hand circle (e.g. around the tally line). */
export function ScribbleCircle({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 80" className={className} aria-hidden {...MARKER}>
      <path d="M100 8 C 150 8, 192 20, 190 40 C 188 62, 140 72, 95 71 C 50 70, 10 60, 12 40 C 14 20, 60 9, 105 10" />
    </svg>
  );
}

/** Curved arrow pointing down-right at the ball. */
export function ScribbleArrow({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 120" className={className} aria-hidden {...MARKER}>
      <path d="M14 12 C 50 20, 80 45, 88 92" />
      <path d="M72 78 L88 92 L70 100" />
    </svg>
  );
}
