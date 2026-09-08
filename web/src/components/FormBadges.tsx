const DOT: Record<string, string> = {
  W: "bg-home",
  D: "bg-draw",
  L: "bg-away",
};

export function FormBadges({ form, label }: { form: string[]; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-[10px] tracking-[0.25em] text-coal/60">{label}</span>
      <span className="flex gap-1">
        {form.map((r, i) => (
          <span
            key={i}
            title={r === "W" ? "Win" : r === "D" ? "Draw" : "Loss"}
            className={`flex h-5 w-5 items-center justify-center rounded-full font-mono text-[10px] font-semibold text-white ${DOT[r] ?? "bg-coal/30"}`}
          >
            {r}
          </span>
        ))}
      </span>
    </div>
  );
}
