"use client";

import { LEAGUES } from "@/lib/constants";

export function LeagueTabs({ active, onChange }: { active: string; onChange: (code: string) => void }) {
  const codes = ["ALL", ...LEAGUES.map((l) => l.code)];
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="League filter">
      {codes.map((c) => (
        <button
          key={c}
          type="button"
          aria-pressed={active === c}
          onClick={() => onChange(c)}
          className={`pressable rounded-full px-4 py-1.5 font-mono text-[11px] tracking-[0.2em] ${
            active === c ? "bg-coal text-cream" : "bg-cream text-coal hover:bg-white"
          }`}
        >
          {c}
        </button>
      ))}
    </div>
  );
}
