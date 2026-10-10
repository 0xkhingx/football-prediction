import Link from "next/link";
import { formatDate } from "@/lib/weeks";
import type { Fixture } from "@/lib/types";

export function MatchCard({ fixture, tone = "card" }: { fixture: Fixture; tone?: "card" | "inset" }) {
  const href = `/predict?home=${encodeURIComponent(fixture.home)}&away=${encodeURIComponent(fixture.away)}`;
  // Runtime guards: schema-validated data should always be strings, but a
  // malformed backend row must degrade to labels, never crash or print NaN.
  const leagueLabel =
    typeof fixture.league_name === "string" && fixture.league_name.trim() !== ""
      ? fixture.league_name.toUpperCase()
      : typeof fixture.league === "string" && fixture.league.trim() !== ""
        ? fixture.league.toUpperCase()
        : "LEAGUE TBC";
  const roundLabel =
    typeof fixture.round === "string" && fixture.round.trim() !== "" ? `${fixture.round.toUpperCase()} · ` : "";
  return (
    <Link
      href={href}
      aria-label={`Predict ${fixture.home} versus ${fixture.away}`}
      className={`pressable lift block rounded-3xl p-5 hover:shadow-xl ${
        tone === "inset" ? "bg-white" : "bg-cream"
      }`}
    >
      <p className="font-mono text-[11px] tracking-[0.22em] text-coal/70">
        <time dateTime={typeof fixture.date === "string" ? fixture.date : undefined}>
          {formatDate(fixture.date)}
        </time>
        {" · "}
        {roundLabel}
        {leagueLabel}
      </p>
      <p className="mt-2 font-display text-2xl uppercase leading-none text-coal">
        {fixture.home} <span className="text-ember">vs</span> {fixture.away}
      </p>
      <span className="mt-3 inline-flex min-h-[36px] items-center gap-2 rounded-full bg-coal px-4 py-1.5 font-mono text-[11px] tracking-[0.22em] text-cream">
        VIEW PREDICTION <span aria-hidden="true">→</span>
      </span>
    </Link>
  );
}
