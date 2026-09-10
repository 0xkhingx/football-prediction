"use client";

/**
 * FLOW landing elements: kawaii face overlay for the ball, rotating
 * sticker stamp, hand-drawn marker scribbles. Pure SVG + CSS.
 */

function Asterisk({ x, y }: { x: number; y: number }) {
  const arms = [0, 60, 120];
  return (
    <g transform={`translate(${x} ${y})`} stroke="#161412" strokeWidth="5" strokeLinecap="round">
      {arms.map((a) => (
        <line key={a} x1="-11" y1="0" x2="11" y2="0" transform={`rotate(${a})`} />
      ))}
    </g>
  );
}

/** Kawaii face (asterisk eyes + o mouth) overlaying the hero ball. */
export function BallFace({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 90" className={className} aria-hidden>
      <Asterisk x={38} y={30} />
      <Asterisk x={82} y={30} />
      <circle cx={60} cy={62} r={9} fill="#161412" />
    </svg>
  );
}

/** Pink scalloped sticker with circular text. Slow spin; still when reduced. */
export function Sticker({ className = "" }: { className?: string }) {
  return (
    <div className={`sticker-spin relative h-28 w-28 sm:h-36 sm:w-36 ${className}`} aria-hidden>
      <svg viewBox="0 0 120 120" className="h-full w-full">
        <circle cx="60" cy="60" r="58" fill="#F4A3D3" />
        <circle cx="60" cy="60" r="58" fill="none" stroke="#F4A3D3" strokeWidth="2" strokeDasharray="3 5" opacity="0.6" />
        <defs>
          <path id="sticker-ring" d="M60,60 m-42,0 a42,42 0 1,1 84,0 a42,42 0 1,1 -84,0" />
        </defs>
        <text fontSize="12.5" letterSpacing="3.5" fill="#161412" fontFamily="monospace">
          <textPath href="#sticker-ring">MODEL CALL · FAIR PLAY · NO ODDS ·</textPath>
        </text>
        <text x="60" y="66" textAnchor="middle" fontSize="17" fontWeight="900" fill="#161412" fontFamily="monospace">
          CALL IT
        </text>
      </svg>
    </div>
  );
}

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
