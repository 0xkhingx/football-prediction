import { LEAGUES } from "./constants";
import type { Fixture } from "./types";

export type Week = {
  key: string;
  label: string;
  start: string;
  fixtures: Fixture[];
};

const DAY_MS = 86_400_000;

/** Cluster fixtures into weeks: sorted by date, new week on gaps > 4 days.
    Unparseable dates collect in a trailing "date TBC" group instead of
    corrupting real clusters (NaN comparisons are never true). */
export function groupWeeks(fixtures: Fixture[]): Week[] {
  const dated = fixtures.filter((f) => toDate(f.date) !== null);
  const dateless = fixtures.filter((f) => toDate(f.date) === null);
  const sorted = [...dated].sort((a, b) => (a.date < b.date ? -1 : 1));
  const weeks: Fixture[][] = [];
  for (const f of sorted) {
    const last = weeks[weeks.length - 1];
    const prev = last?.[last.length - 1];
    if (!last || !prev || Math.abs(Date.parse(f.date) - Date.parse(prev.date)) > 4 * DAY_MS) {
      weeks.push([f]);
    } else {
      last.push(f);
    }
  }
  if (dateless.length > 0) weeks.push(dateless);
  return weeks
    .filter((fs) => fs.length > 0 && fs[0])
    .map((fs) => ({
      key: typeof fs[0].date === "string" && fs[0].date ? fs[0].date : `tbc-${fs.length}`,
      label: fs[0].date ? weekLabel(fs) : "DATE TBC",
      start: typeof fs[0].date === "string" ? fs[0].date : "",
      fixtures: fs,
    }));
}

function toDate(value: unknown): Date | null {
  if (value instanceof Date && !Number.isNaN(value.getTime())) return value;
  if (typeof value === "number" && Number.isFinite(value)) {
    // Epoch seconds or milliseconds — accept both.
    const ms = value < 1e12 ? value * 1000 : value;
    const d = new Date(ms);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const d = new Date(value.includes("T") ? value : `${value}T12:00:00`);
    if (!Number.isNaN(d.getTime())) return d;
  }
  return null;
}

function fmtDay(iso: unknown): string {
  // Never emit calendar garbage: any unparseable input becomes DATE TBC.
  // (An Invalid Date would otherwise render as "undefined NaN undefined".)
  try {
    const d = toDate(iso);
    if (!d) return "DATE TBC";
    const day = d.getDay();
    const date = d.getDate();
    const month = d.getMonth();
    if (!Number.isInteger(day) || !Number.isInteger(date) || !Number.isInteger(month)) return "DATE TBC";
    const days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
    const months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
    const dayName = days[day];
    const monthName = months[month];
    if (!dayName || !monthName || !Number.isFinite(date)) return "DATE TBC";
    return `${dayName} ${date} ${monthName}`;
  } catch {
    return "DATE TBC";
  }
}

export function formatDate(iso: unknown): string {
  // Safe for card eyebrows: never leak raw garbage like "NaN" or "undefined".
  if (typeof iso !== "string" || iso.trim() === "") return "DATE TBC";
  try {
    const t = Date.parse(`${iso}T12:00:00`);
    if (Number.isNaN(t)) return "DATE TBC";
    return fmtDay(iso);
  } catch {
    return "DATE TBC";
  }
}

function weekLabel(fs: Fixture[]): string {
  if (!fs.length || !fs[0]) return "DATE TBC";
  const first = fmtDay(fs[0].date);
  const last = fmtDay(fs[fs.length - 1]?.date);
  if (first === "DATE TBC" && last === "DATE TBC") return "DATE TBC";
  return first === last ? first : `${first} – ${last}`;
}

/** Index of the nearest week at/after today; clamps to valid range. */
export function nearestWeekIndex(weeks: Week[], today = new Date()): number {
  const t = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  for (let i = 0; i < weeks.length; i++) {
    const start = toDate(weeks[i].start);
    if (start && start.getTime() >= t) return i;
  }
  return Math.max(0, weeks.length - 1);
}

export type LeagueGroup = {
  code: string;
  tag: string;
  name: string;
  fixtures: Fixture[];
};

/** Group a week's fixtures by league in fixed LEAGUES order, always
    including empty leagues (stable layout, no jumping). Unknown codes
    collect under an OTHER tile rather than being dropped. */
export function groupByLeague(fixtures: Fixture[]): LeagueGroup[] {
  const groups: LeagueGroup[] = LEAGUES.map((l) => ({
    code: l.code,
    tag: l.tag,
    name: l.name,
    fixtures: [],
  }));
  const byCode = new Map(groups.map((g) => [g.code, g]));
  let other: LeagueGroup | null = null;
  for (const f of fixtures) {
    const g = byCode.get(f.league);
    if (g) {
      g.fixtures.push(f);
    } else {
      other ??= { code: f.league, tag: f.league.toUpperCase(), name: f.league_name, fixtures: [] };
      other.fixtures.push(f);
    }
  }
  return other ? [...groups, other] : groups;
}

/** Code with the most ties (first on ties) — the default expanded tile. */
export function leadLeague(groups: LeagueGroup[]): string | null {
  let best: LeagueGroup | null = null;
  for (const g of groups) {
    if (!best || g.fixtures.length > best.fixtures.length) best = g;
  }
  return best && best.fixtures.length > 0 ? best.code : null;
}
