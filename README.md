# Football Match Outcome Predictor

Predicts Home Win / Draw / Away Win for the top 5 European leagues (England, Spain, Italy, Germany, France) using only pre-match information — no betting odds as inputs.

**Live demo:** [matchday.pxxl.click](https://matchday.pxxl.click) — pick a fixture, run the manual predictor, or check the title-odds simulator.

This repo covers the data pipeline and model. The live site consumes model output through a FastAPI service (`api.py`) containerized with the root `Dockerfile` and hosted on Pxxl, with the Next.js frontend on Vercel; see `src/predict_live.py` for the inference entry point and `src/inference.py` for the shared train==serve logic.

## Results

Test set: 146 matches, held out chronologically (trained on seasons 2015/16–2024/25, validated on 2025/26, tested on the 2026/27 partial window 2026-08-15 to 2026-09-07 — see [Methodology](#methodology)). Primary metric is log loss, benchmarked against bookmaker-implied probabilities as the practical ceiling.

| Model                        | Log Loss ↓ | Notes                                                              |
|------------------------------|-----------|---------------------------------------------------------------------|
| Naive (training prior)       | 1.0781    | Always predicts the training class distribution                     |
| Logistic Regression          | 1.0196    | Linear baseline (accuracy 48.6%)                                    |
| XGBoost (tuned, fair-play)   | **0.9885**| Production model (`no_odds_xgb_tuned`, accuracy 50.7%) — no odds features |
| Bookmaker (Bet365, benchmark)| n/a on this window | No B365 odds coverage for the 2026/27-partial test set (0/146), so no bookmaker log loss can be computed here — disclosed on purpose rather than substituted |

Because the current test window has no odds coverage, the locked full-season benchmark is the honest bookmaker comparison — archived in `models/evaluation_2425_locked.json` (2024/25 test, 1,752 matches, full B365 coverage):

| Model (2024/25 locked, n=1,752)      | Log Loss ↓ |
|--------------------------------------|-----------|
| Naive (training prior)               | 1.0766    |
| Logistic Regression (no odds)        | 0.9863    |
| XGBoost-tuned, fair-play (PROD)      | **0.9853**|
| Bookmaker (Bet365, normalized)       | 0.9647    |

Secondary metrics tracked in `evaluate.py`: Brier score (tuned XGB 0.5868 vs. naive 0.6533 on the current window), accuracy, per-league breakdown, and a calibration curve (predicted probability vs. observed frequency) — see `notebooks/calibration_plot.png`.

**Read on the numbers:** the model beats a naive baseline by a meaningful margin (~0.09 log-loss points) and does so without ever seeing an odds-derived feature. It does not yet beat the bookmaker — on the full-season locked test the gap is ~0.02 log-loss points. That gap is expected (bookmakers price in information this model doesn't have, like team news and market sentiment) and is reported here deliberately rather than hidden.

## Approach

- **Data source:** [football-data.co.uk](https://www.football-data.co.uk) — historical CSVs, seasons 2015/16 through 2024/25 — plus [openfootball/football.json](https://github.com/openfootball/football.json) for 2025/26–2026/27 via `src/pull_openfootball.py`
- **Model:** XGBoost multiclass classifier (H/D/A), tuned (`max_depth=3`, `learning_rate=0.1`, `n_estimators=750`, subsample/colsample 0.5 — see `models/xgb_best_params.json`)
- **Baseline:** Logistic regression + "always predict training prior" naive
- **Features (23 total):** Elo ratings (+ margin-adjusted Elo), rolling form (5/10-match windows), head-to-head streak, rest days, league context, recent goals/shots/shots-on-target/corners
- **Evaluation:** Log loss vs. bookmaker-implied probabilities (where odds exist), with Brier score, accuracy, and calibration as secondary checks

## Methodology

The single most important engineering constraint on this project: **no feature is allowed to use information that wouldn't be available before kickoff.**

Concretely:
- The train/val/test split (`split.py`) is chronological, not random — train on seasons ≤2024/25 (n=18,011), validate on 2025/26 (n=1,751), test on 2026/27-partial (n=146). Pinned windows fail loudly on unmapped seasons rather than silently redefining the test set. The model is always evaluated on matches that happened *after* everything it was trained on, which mirrors how it would actually be used.
- Rolling form, Elo, and head-to-head features are computed as of the match date, not recalculated with hindsight.
- No betting-market features are included, by design — the goal was to see how far pure match signal (form, strength, rest, history) can get without leaning on the market's own pricing. A with-odds variant exists in `train.py` only as a diagnostic control.

This is the difference between a backtest that looks good and a model that would survive being deployed on next week's fixtures.

## Findings & next steps

- **Elo dominates.** Per the tuned model's feature importances, margin-adjusted Elo difference (`EloDiffMargin`, 0.26) alone carries ~6× the weight of any single form or goals feature, with raw `EloDiff` second (0.13). Strength ratings do almost all the work; everything else is refinement.
- **The surprise was what *didn't* matter.** Rest days (`HomeRest`/`AwayRest`, ~0.024 each) sit in the bottom half of importances, head-to-head streak is dead last (0.019), and gated walk-forward experiments (`experiments/results_batch.json`) explicitly REJECTED rest-differential, fixture congestion, game-number, derby, and points-per-game variants — none beat baseline across all folds. Shots-on-target averages outrank raw goals averages, i.e. chance quality beats scorelines.
- **What I'd try next:** player-level availability (injuries/suspensions/lineups) is the biggest known blind spot vs. the bookmaker; then expanding beyond the top 5 leagues for more training volume, and ensembling the tuned XGB with the logistic regression (which wins on calibration stability even when it loses on log loss).

## Project Structure

```
football-prediction/
├── api.py              # FastAPI service (health, fixtures, predict, evaluate, season-record, simulation)
├── Dockerfile          # Container build (Pxxl / Cloud Run / HF Spaces / Render)
├── data/
│   ├── raw/            # Raw CSVs from football-data.co.uk
│   └── processed/      # Cleaned + featurized data, pinned splits
├── src/
│   ├── config.py         # Single source of truth (features, leagues, gate threshold)
│   ├── inference.py      # Shared train==serve inference
│   ├── data_pull.py      # Download historical CSVs
│   ├── pull_openfootball.py # 2025/26+ results (explicit team map)
│   ├── clean.py          # Clean, normalize, add points
│   ├── features.py       # Feature engineering (Elo, form, H2H, rest; leakage-checked)
│   ├── split.py          # Pinned chronological train/val/test split
│   ├── train.py          # Baseline training (LR + XGBoost, with/without odds)
│   ├── train_tuned_prod.py # Production tuned retrain (writes model registry)
│   ├── evaluate.py       # Metrics, calibration, per-league comparison
│   ├── predict_live.py   # Predict upcoming fixtures (CLI)
│   ├── score_live.py     # Season scoreboard: backfill + live-call scoring
│   ├── simulate.py       # Monte Carlo title/top-4 simulator
│   └── shap_analysis.py  # SHAP importance plots (notebooks/shap_*.png)
├── web/                # Next.js 14 + TypeScript frontend
├── models/             # Registry + metrics JSONs (joblibs rebuilt via make)
├── notebooks/          # calibration_plot.png, SHAP plots
├── tests/              # pytest suite (parity, gates, API contracts)
├── Makefile
└── README.md
```

## Usage

Fresh clone — build everything end to end:

```bash
pip install -r requirements.txt
make bootstrap   # pull → clean → features → split → train → evaluate → score → simulate
```

Weekly refresh (frozen weights) and retrain:

```bash
make refresh                 # pull → clean → features → split (then restart the API)
make train evaluate score simulate
```

Live predictions, API and tests:

```bash
python -m src.predict_live       # CLI live predictor
python -m pytest tests/ -v       # test suite: parity, gates, API contracts
uvicorn api:app --reload         # FastAPI on :8000
```

Frontend (`web/`, Next.js 14 + TypeScript):

```bash
cd web && npm install && npm run dev   # :3000, proxies to API_URL
```

Deploy notes: set `API_URL` (web → API base) and `ALLOWED_ORIGINS` (API CORS allowlist, comma-separated) in the hosting env. After any refresh/retrain, either restart the API or `POST /reload` with `Authorization: Bearer $RELOAD_TOKEN`.

## Metrics

- **Primary:** Log loss (cross-entropy)
- **Secondary:** Brier score, accuracy, calibration curve
- **Baseline:** Training-prior naive ("always predict the class distribution")
- **Benchmark:** Bookmaker-implied log loss (Bet365 odds, normalized; where odds exist — 0/146 coverage on the current partial window, full coverage on the 2024/25 locked test)

## License

MIT

---

*Research demo, not betting advice. Built by [Ogundele Oluwadamilare / Kynigma](https://kynigma.vercel.app) — part of the [Matchday Fate](https://matchday.pxxl.click) case study.*
