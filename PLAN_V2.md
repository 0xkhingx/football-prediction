# Football Prediction — v2 Build Plan (locked)

Baseline: prod XGB-tuned, 23 fair-play features (no odds), test LL 0.985 vs B365 0.965
(test set 2024/25, n=1752). FastAPI + Next.js 14, 13/13 pytest green. Season 2025/26 live.

## Preconditions (all verified green)
- [x] API responds: `GET localhost:8000/health` → `model: no_odds_xgb_tuned.joblib`
- [x] `suppressHydrationWarning` on `<body>` in `web/src/app/layout.tsx` (Grammarly attrs)
- [x] Web predict returns 200 end-to-end (route registered + backend up)

## Step 1 — Data refresh (S) — DONE 2026-09-08
`data_pull.py`: `range(15, 25)` → `range(15, 26)` (adds 2526). Re-run
pull → clean → features → split. Archive `models/evaluation.json` →
`models/evaluation_2425_locked.json` BEFORE regenerating (2425 stays the
locked benchmark; 2526-partial is live validation, never blended into the headline).
Retrain prod tuned on rolled splits (train ..2324, val 2425, test 2526-partial),
re-evaluate, update registry. Cadence from here: frozen weights + weekly
`make refresh` state update, monthly retrain. Manual first; scheduler only after
the loop earns it. Hosting (API Render/Fly, web Vercel) is critical path for testers.
- Promoted-side check: `TEAM_NAME_MAP` name variants resolve; rare-team `'Other'` rule sane.
- Accept: pipeline end-to-end with no schema breaks; split boundaries per above.

### Step 1 amendments (as-built, supersede the above where they differ)
- football-data.co.uk is host-blocked (503 on all routes/UAs), so 2526-full
  (1751 played) + 2627-partial (97 played) came from openfootball/football.json
  via new `src/pull_openfootball.py` (explicit team map, fail-loud unknowns,
  unplayed 2627 fixtures -> `data/fixtures_2627.csv`).
- Rolled splits as built: train ..2425 (18011) / val 2526-full (1751) /
  test 2627-partial (97). The 2425-locked number is the OLD model's archived
  reference — it cannot re-test a model trained on ..2425 data, so the Step 2
  gate uses walk-forward + val-2526 + 2627-live, with 2425-locked kept as the
  stable comparison point.
- Bugs fixed en route: ISO day/month swap in `clean.py` (+ `tests/test_dates.py`),
  verifier sort aligned to featurizer order (2653 phantom violations resolved).

## Step 2 — ML batch experiment (M-with-ripple, BEFORE product builds) — DONE 2026-09-08
Candidates: rest-diff, congestion-14d, season-stage, derby flag + PPG-momentum
(skeptic's entry). A feature-count change ripples through config/inference/parity
tests/registry/SHAP/explanations/model page — decide the final set ONCE, here.
- **Ship rule (no fixed number):** consistent gain sign across walk-forward folds
  AND paired-bootstrap 95% CI on locked-2425 reference excludes zero.
- **Positive control first:** run odds features through the same harness (~0.02 known
  gain must flag SHIP). Control fails → harness broken, fix harness. Control passes
  + all four fail → features dead, keep 23 columns, no bar-lowering either way.
- Accept: per-candidate walk-forward + locked-test deltas logged; merged in ONE batch.

### Step 2 outcome (as-run, `experiments/results_batch.json`)
- Positive control (B365 odds): gain +0.0159, CI [+0.0130, +0.0190], 5/5 folds
  -> SHIP. Harness validated (known effect detected at expected size).
- restdiff +0.0002 3/6, congestion +0.0005 3/6, gameno +0.0005 3/6,
  derby +0.0003 3/6, ppg +0.0002 2/6, joint -0.0002 1/6 -> ALL REJECT
  (every CI crosses zero; joint actively worse).
- Verdict: features dead, prod stays 23 columns, no bar-lowering. Harness bugs
  fixed en route (odds-row skip granularity, pooled-delta sign convention) —
  both surfaced by the control behaving impossibly, exactly as designed.

## Steps 3–8 — product, in order (each with acceptance test, pytest+tsc+build green)
- Step 3 honesty gate DONE (t=0.45, val coverage 0.67/acc 0.577; API + badge).
- Step 4 form badges + H2H DONE (last-5 W/D/L, last meeting, API + UI).
- Step 5 scorelines DONE (Dixon-Coles, val LL 1.072 vs naive ~1.08; conditional-
  on-XGB stamping instead of suppression UX — conflict case solved by design).
- Step 6 scoreboard DONE (97 backfilled 2627 calls, labeled; tally acc 0.546 /
  LL 0.946; buckets monotonic 70%+ -> 1.00 down to <45% -> 0.42; API + home UI).
- Step 7 simulator DONE (2000 sims/league, title sums 1.0 / top4 sums 4.0 every
  league; /simulator page; rare/unknown-team resolve rule regression-tested).
- Step 8 share cards DONE (/predict/og renders live-call PNG, verified visually;
  X/WhatsApp share row on predict page).

## Original step specs (kept for reference; status above is authoritative)
3. **Honesty gate (S)** — threshold tuned on val; `call`/`no-call` in API + UI badge.
4. **Form badges + H2H (S)** — pure frontend from replayed history (risk-free, first).
5. **Scorelines (M)** — Dixon-Coles from FTHG/FTAG; ship only under XGB-consistency rule.
6. **Scoreboard (M)** — `score_live.py` (acc/LL/Brier overall + per-league + per-bucket);
   aggregate B365 gap surfaced; backfilled to season start via point-in-time replay,
   backfill LABELED, live calls take over at ship date.
7. **Simulator v1 (M)** — title/top-4 only, banded ranges, no false precision.
8. **Share cards (S)** — OG route on ember/cream/lime system.

## Explicitly out
Value finder, paper ROI, manager tenure, squad value, travel, referee-as-feature,
lineups, in-play. Bookmaker comparison lives ONLY as the aggregate honesty number.
Brand stays "not betting advice."

Total: ~6–8 build sessions. Parked items need a source + green light, not revisiting.
