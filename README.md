# Football Match Outcome Predictor

Predicts Home Win / Draw / Away Win for the top 5 European leagues (England, Spain, Italy, Germany, France) using only pre-match information.

## Approach

- **Data sources**: [football-data.co.uk](https://www.football-data.co.uk) (2015/16–2024/25; currently host-blocked) + [openfootball/football.json](https://github.com/openfootball/football.json) (2025/26–2026/27 via `src/pull_openfootball.py`)
- **Model**: tuned XGBoost multiclass classifier (H/D/A), 23 fair-play features (no odds)
- **Baseline**: Logistic Regression + training-prior naive
- **Features**: Elo (+ margin Elo), rolling form (5/10), head-to-head, rest days, goals/shots/corners averages
- **Evaluation**: Log loss vs bookmaker implied probabilities (where odds exist)

## Project Structure

```
football-prediction/
├── api.py                # FastAPI: health, fixtures, predict, evaluate, season-record, simulation
├── src/
│   ├── config.py         # Single source of truth (features, leagues, gate threshold)
│   ├── inference.py      # Shared train==serve inference (fails loud, never silent fallback)
│   ├── data_pull.py      # football-data.co.uk historical CSVs (best-effort)
│   ├── pull_openfootball.py  # openfootball 2025/26+ results (explicit team map)
│   ├── clean.py          # Clean, normalize, add points
│   ├── features.py       # Feature engineering (leakage-checked)
│   ├── split.py          # PINNED train/val/test windows (fails on unmapped seasons)
│   ├── train.py          # Baseline training (LR + XGB, with/without odds)
│   ├── train_tuned_prod.py   # Prod tuned retrain (refits imputer, writes registry)
│   ├── evaluate.py       # Metrics, calibration, per-league
│   ├── predict_live.py   # CLI live predictor (network → local fixtures → season fallback)
│   ├── goals.py          # Dixon-Coles scorelines (conditional-on-XGB stamping)
│   ├── score_live.py     # Season scoreboard: backfill (labeled) + live-call scoring
│   ├── simulate.py       # Monte Carlo title/top-4 simulator (rounded bands)
│   ├── experiment_batch.py   # Gated walk-forward feature experiments
│   └── shap_analysis.py  # SHAP importance plots
├── web/                  # Next.js 14 + TS frontend (fixtures, predict, model, simulator)
├── tests/                # pytest suite (parity, gates, API contracts, no hardcoded snapshots)
├── models/               # Registry + metrics JSONs (joblibs gitignored, rebuilt by make)
├── experiments/          # Batch experiment verdicts
├── Makefile              # bootstrap / refresh / train / evaluate / score / simulate / test
└── PLAN_V2.md            # Locked v2 build plan + as-built amendments
```

## Usage

Fresh clone — build everything end to end:

```bash
pip install -r requirements.txt
make bootstrap   # pull → clean → features → split → train → evaluate → score → simulate
```

Weekly state refresh (frozen weights) and monthly retrain:

```bash
make refresh     # pull → clean → features → split (then restart the API)
make train evaluate score simulate
```

Live predictions, API and tests:

```bash
python -m src.predict_live       # CLI (deduped log, honesty-gate stamped)
python -m pytest tests/ -v       # 51 tests: parity, gates, API contracts
uvicorn api:app --reload         # FastAPI on :8000
```

Frontend (`web/`, Next.js 14 + TypeScript monorepo):

```bash
cd web && npm install && npm run dev   # :3000, proxies to API_URL
```

Micro-interactions in `web/src/components/interior/` are vendored from
[interior.dev](https://www.interior.dev) by Ozzy (MIT licensed; see headers) —
motion logic unchanged, surfaces restyled to this app's token system.
Digit transitions (`ReelNumber`, pop-in, error shake) adapt recipes from
[transitions.dev](https://transitions.dev) by Jakub Antalik (free copy-paste
set) — retuned durations, same reduced-motion guarantees.

Deploy notes: set `API_URL` (web → API base) and `ALLOWED_ORIGINS` (API CORS allowlist,
comma-separated) in the hosting env. The API holds state in memory — after any
`make refresh` / retrain, either restart it or `POST /reload` with
`Authorization: Bearer $RELOAD_TOKEN` (set `RELOAD_TOKEN` server-side; unset =
reload disabled). Heavy traffic is throttled per-IP on `/predict` and
`/fixtures` (429 + Retry-After).

## Metrics

Locked benchmark (2024/25 test, 1752 matches, archived in `models/evaluation_2425_locked.json`):

| Model | Log-loss |
|---|---|
| Naive (training prior) | 1.077 |
| XGB-tuned, fair-play (PROD) | **0.985** |
| Bookmaker B365 (benchmark) | 0.965 |

Current model (trained ..2024/25, val 2025/26 n=1751, live test 2026/27-partial n=146):

| Split | XGB-tuned log-loss | Acc |
|---|---|---|
| Val 2025/26 | 0.996 | — |
| Test 2026/27-partial | 0.988 | 0.507 |

Fair-play: no odds features — Elo, form, H2H, rest, goals, shots, corners only.
Research demo, not betting advice.

Metric definitions: primary log loss (cross-entropy); secondary Brier score,
accuracy, calibration curve; baseline training-prior naive; benchmark bookmaker
implied log loss (B365 odds, where available).
