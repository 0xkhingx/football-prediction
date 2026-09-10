export const LEAGUES = [
  { code: "E0", name: "Premier League", tag: "EPL" },
  { code: "SP1", name: "La Liga", tag: "LALIGA" },
  { code: "I1", name: "Serie A", tag: "SERIE A" },
  { code: "D1", name: "Bundesliga", tag: "BUNDESLIGA" },
  { code: "F1", name: "Ligue 1", tag: "LIGUE 1" },
] as const;

export const API_BASE = process.env.API_URL ?? "http://127.0.0.1:8000";
