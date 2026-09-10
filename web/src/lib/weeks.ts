import { LEAGUES } from "./constants";
import type { Fixture } from "./types";

export type Week = {
  key: string;
  label: string;
  start: string;
  fixtures: Fixture[];
};

const DAY_MS = 86_400_000;

/** Cluster fixtures into weeks: sorted by date, new week on gaps > 4 days. */
export function groupWeeks(fixtures: Fixture[]): Week[] {
  const sorted = [...fixtures].sort((a, b) => (a.date < b.date ? -1 : 1));
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
  return weeks.map((fs) => ({
    key: fs[0].date,
    label: weekLabel(fs),
    start: fs[0].date,
    fixtures: fs,
  }));
}

function fmtDay(iso: string): string {
  const d = new Date(`${iso}T12:00:00`);
  const days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
  const months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
  return `${days[d.getDay()]} ${d.getDate()} ${months[d.getMonth()]}`;
}

export function formatDate(iso: string): string {
  const t = Date.parse(`${iso}T12:00:00`);
  return Number.isNaN(t) ? iso : fmtDay(iso);
}

function weekLabel(fs: Fixture[]): string {
  const first = fmtDay(fs[0].date);
  const last = fmtDay(fs[fs.length - 1].date);
  return first === last ? first : `${first} – ${last}`;
}

/** Index of the nearest week at/after today; clamps to valid range. */
export function nearestWeekIndex(weeks: Week[], today = new Date()): number {
  const t = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  for (let i = 0; i < weeks.length; i++) {
    if (Date.parse(`${weeks[i].start}T12:00:00`) >= t) return i;
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
