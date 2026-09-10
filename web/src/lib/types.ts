import { z } from "zod";

export const FixtureSchema = z.object({
  date: z.string(),
  league: z.string(),
  league_name: z.string(),
  home: z.string(),
  away: z.string(),
  round: z.string().optional(),
});
export type Fixture = z.infer<typeof FixtureSchema>;

export const PredictionSchema = z.object({
  home: z.string(),
  away: z.string(),
  prediction: z.union([z.literal("H"), z.literal("D"), z.literal("A")]),
  confidence: z.number(),
  pH: z.number(),
  pD: z.number(),
  pA: z.number(),
  model: z.string(),
  call: z.boolean(),
  call_label: z.string(),
  form_home: z.array(z.string()),
  form_away: z.array(z.string()),
  h2h: z.object({ date: z.string(), home_goals: z.number(), away_goals: z.number() }).nullable(),
  scoreline: z
    .object({ shown: z.boolean(), h: z.number(), a: z.number(), p: z.number(), reason: z.string() })
    .nullable(),
  resolved: z.record(z.object({ from: z.string(), to: z.string(), via: z.string() })).nullable().optional(),
});
export type Prediction = z.infer<typeof PredictionSchema>;

export const OUTCOME_LABEL: Record<string, string> = {
  H: "Home win",
  D: "Draw",
  A: "Away win",
};
