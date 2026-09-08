export const LEAGUES = [
  { code: "E0", name: "Premier League" },
  { code: "SP1", name: "La Liga" },
  { code: "I1", name: "Serie A" },
  { code: "D1", name: "Bundesliga" },
  { code: "F1", name: "Ligue 1" },
] as const;

export const API_BASE = process.env.API_URL ?? "http://127.0.0.1:8000";
