import Link from "next/link";
import { formatDate } from "@/lib/weeks";
import type { Fixture } from "@/lib/types";

export function MatchCard({ fixture, tone = "card" }: { fixture: Fixture; tone?: "card" | "inset" }) {
  const href = `/predict?home=${encodeURIComponent(fixture.home)}&away=${encodeURIComponent(fixture.away)}`;
  return (
    <Link
      href={href}
      aria-label={`Predict ${fixture.home} versus ${fixture.away}`}
      className={`pressable lift block rounded-3xl p-5 hover:shadow-xl ${
        tone === "inset" ? "bg-white" : "bg-cream"
      }`}
    >
      <p className="font-mono text-[10px] tracking-[0.25em] text-ember">
        <time dateTime={fixture.date}>{formatDate(fixture.date)}</time>
        {" · "}
        {fixture.round ? `${fixture.round.toUpperCase()} · ` : ""}
        {fixture.league_name.toUpperCase()}
      </p>
      <p className="mt-2 font-display text-2xl uppercase leading-none text-coal">
        {fixture.home} <span className="text-ember">vs</span> {fixture.away}
      </p>
      <span className="mt-3 inline-flex items-center gap-2 rounded-full bg-coal px-4 py-1.5 font-mono text-[10px] tracking-[0.25em] text-cream">
        CALL IT <span aria-hidden="true">→</span>
      </span>
    </Link>
  );
}
