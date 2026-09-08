export function pct(x: number): string {
  if (!Number.isFinite(x)) return "—";
  const clamped = Math.min(1, Math.max(0, x));
  return `${(clamped * 100).toFixed(1)}%`;
}
