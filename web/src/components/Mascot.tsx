"use client";

import Image from "next/image";
import { Tooltip } from "./Tooltip";

/**
 * Oracle mascot — DiceBear "Bottts Neutral" (Pablo Stanley, free for
 * personal + commercial use; license metadata embedded in each SVG).
 * Variants: oracle (default), happy (correct call), shocked (miss).
 */
export type MascotMood = "oracle" | "happy" | "shocked";

const SRC: Record<MascotMood, string> = {
  oracle: "/mascot/oracle.svg",
  happy: "/mascot/happy.svg",
  shocked: "/mascot/shocked.svg",
};

const ALT: Record<MascotMood, string> = {
  oracle: "Oracle, the Matchday Fate predictor bot",
  happy: "Oracle celebrating a correct call",
  shocked: "Oracle surprised by a missed call",
};

export function Mascot({
  mood = "oracle",
  size = 120,
  className = "",
}: {
  mood?: MascotMood;
  size?: number;
  className?: string;
}) {
  return (
    <Image
      src={SRC[mood]}
      alt={ALT[mood]}
      width={size}
      height={size}
      className={`rounded-full ${className}`}
    />
  );
}

/** Floating hero mascot with tooltip CTA. Gentle bob; still under reduced motion. */
export function HeroMascot() {
  return (
    <div className="mascot-float">
      <Tooltip tip="Ask me anything — I read 23 pre-match signals. No odds, no tips.">
        <a href="/predict" aria-label="Ask the oracle to predict a match">
          <Mascot
            mood="oracle"
            size={132}
            className="ring-4 ring-coal/10 transition-transform duration-200 hover:scale-105"
          />
        </a>
      </Tooltip>
    </div>
  );
}
