# Football Match Outcome Predictor

Predicts Home Win / Draw / Away Win for the top 5 European leagues (England, Spain, Italy, Germany, France) using only pre-match information.

## Approach

- **Data source**: [football-data.co.uk](https://www.football-data.co.uk) — historical CSVs for seasons 2015/16 through 2024/25
- **Model**: XGBoost multiclass classifier (H/D/A)
- **Baseline**: Logistic Regression + "always predict home win"
- **Features**: Elo ratings, rolling form (5/10), head-to-head streak, rest days, league context
- **Evaluation**: Log loss vs bookmaker implied probabilities

## Project Structure

```
football-prediction/
├── data/
│   ├── raw/            # Raw CSVs from football-data.co.uk
│   └── processed/      # Cleaned + featurized data
├── src/
│   ├── data_pull.py    # Download historical CSVs
│   ├── clean.py        # Clean, normalize, add points
│   ├── features.py     # Feature engineering (Elo, form, H2H, rest)
│   ├── split.py        # Chronological train/val/test split
│   ├── train.py        # Model training (LR + XGBoost)
│   ├── evaluate.py     # Metrics, calibration, comparison
│   └── predict_live.py # Predict upcoming fixtures
├── models/             # Joblib artifacts
├── notebooks/          # Exploration notebooks
├── requirements.txt
└── README.md
```

## Usage

```bash
pip install -r requirements.txt
python src/data_pull.py
python src/clean.py
python src/features.py
python src/split.py
python src/train.py
python src/evaluate.py
```

## Metrics

- Primary: Log loss (cross-entropy)
- Secondary: Brier score, accuracy, calibration curve
- Baseline: "Always predict home win" (prior distribution)
- Benchmark: Bookmaker implied log loss (B365 odds)
