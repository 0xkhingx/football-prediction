"use client";

/**
 * Digit animations adapted from transitions.dev (Jakub Antalik, free
 * copy-paste set): spinning-counter reel + number-pop-in. Retuned for UI
 * use — shorter durations, fewer spins — tabular figures throughout.
 */
import { useEffect, useRef } from "react";

const REEL_DUR = 700;
const REEL_STAGGER = 50;
const REEL_SPINS = 2;
const REEL_EASE = "cubic-bezier(0.16, 1, 0.3, 1)";

function isDigit(ch: string): boolean {
  return ch >= "0" && ch <= "9";
}

/** Reel digits that spin to the value on mount/value change. */
export function ReelNumber({ value, className = "" }: { value: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    root.innerHTML = "";
    const strips: Array<{ strip: HTMLSpanElement; digit: number }> = [];
    value.split("").forEach((ch) => {
      if (!isDigit(ch)) {
        const sep = document.createElement("span");
        sep.textContent = ch;
        root.appendChild(sep);
        return;
      }
      const col = document.createElement("span");
      col.className = "t-reel-col";
      const strip = document.createElement("span");
      strip.className = "t-reel-strip";
      for (let k = 0; k < (REEL_SPINS + 1) * 10 + 1; k++) {
        const cell = document.createElement("span");
        cell.className = "t-reel-digit";
        cell.textContent = String(k % 10);
        strip.appendChild(cell);
      }
      col.appendChild(strip);
      root.appendChild(col);
      strips.push({ strip, digit: +ch });
    });
    const cellH = (root.querySelector(".t-reel-digit") as HTMLElement)?.offsetHeight || 0;
    strips.forEach(({ strip, digit }, i) => {
      if (reduced || cellH === 0) {
        strip.style.transform = `translateY(-${digit * cellH}px)`;
        return;
      }
      strip.style.transition = "none";
      strip.style.transform = "translateY(0)";
    });
    if (reduced || cellH === 0) return;
    void root.offsetWidth;
    strips.forEach(({ strip, digit }, i) => {
      strip.style.transition = `transform ${REEL_DUR}ms ${REEL_EASE} ${i * REEL_STAGGER}ms`;
      strip.style.transform = `translateY(-${(REEL_SPINS * 10 + digit) * cellH}px)`;
    });
  }, [value]);

  return (
    <span
      ref={ref}
      className={`t-reel ${className}`}
      style={{ fontVariantNumeric: "tabular-nums" }}
      aria-label={value}
    />
  );
}

/** Blur-and-rise digit pop-in with per-character stagger. Replays on key change. */
export function PopDigits({ value, className = "" }: { value: string; className?: string }) {
  return (
    <span key={value} className={`t-digit-group is-animating ${className}`} aria-label={value}>
      {value.split("").map((ch: string, i: number) => (
        <span key={i} className="t-digit" data-stagger={String(Math.min(i, 4))}>
          {ch}
        </span>
      ))}
    </span>
  );
}
