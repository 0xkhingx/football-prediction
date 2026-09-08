"""Single source of truth for football-prediction (fair-play, no-odds).

Everything (train, inference, API, web types) must import from here.
Do NOT hardcode feature lists elsewhere.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
RAW_FILE = DATA_DIR / "raw" / "matches_raw.csv"
CLEAN_FILE = DATA_DIR / "processed" / "matches_clean.csv"
FEATURIZED_FILE = DATA_DIR / "processed" / "matches_featurized.csv"
SPLITS_FILE = DATA_DIR / "processed" / "splits.npz"
META_FILE = DATA_DIR / "processed" / "split_meta.json"
PREDICTIONS_LOG = DATA_DIR / "predictions_log.csv"

MODEL_DIR = ROOT / "models"
REGISTRY_FILE = MODEL_DIR / "model_registry.json"
TUNED_PARAMS_FILE = MODEL_DIR / "xgb_best_params.json"

# Prod model = tuned XGB, fair-play (no odds). See plan.
PROD_MODEL_NAME = "no_odds_xgb_tuned"
PROD_IMPUTER_NAME = "no_odds_imputer"

# 23 fair-play features — must match split_meta.json feature_cols_no_odds.
FEATURE_COLS_NO_ODDS: list[str] = [
    "EloHome",
    "EloAway",
    "EloDiff",
    "EloHomeMargin",
    "EloAwayMargin",
    "EloDiffMargin",
    "HomeForm5",
    "HomeForm10",
    "AwayForm5",
    "AwayForm10",
    "H2HStreak",
    "HomeRest",
    "AwayRest",
    "HomeGoalsAvg5",
    "AwayGoalsAvg5",
    "HomeGoalsConcededAvg5",
    "AwayGoalsConcededAvg5",
    "HomeShotsAvg5",
    "AwayShotsAvg5",
    "HomeShotsOnTargetAvg5",
    "AwayShotsOnTargetAvg5",
    "HomeCornersAvg5",
    "AwayCornersAvg5",
]

# Banned from fair-play serving — assertion guard in inference.
BANNED_ODDS_COLS: list[str] = ["ProbB365H", "ProbB365D", "ProbB365A", "B365H", "B365D", "B365A"]

TARGET_MAP: dict[str, int] = {"H": 0, "D": 1, "A": 2}
INV_TARGET_MAP: dict[int, str] = {v: k for k, v in TARGET_MAP.items()}

LEAGUE_MAP: dict[str, str] = {
    "E0": "England",
    "SP1": "Spain",
    "I1": "Italy",
    "D1": "Germany",
    "F1": "France",
}

LEAGUE_NAMES: dict[str, str] = {
    "E0": "Premier League",
    "SP1": "La Liga",
    "I1": "Serie A",
    "D1": "Bundesliga",
    "F1": "Ligue 1",
}

TOP_LEAGUE_CODES: list[str] = ["E0", "SP1", "I1", "D1", "F1"]

ELO_K = 20
ELO_INIT = 1500

# Honesty gate (Step 3): only stamp a call at/above this confidence.
# Tuned on val (2526, n=1751): t=0.45 -> coverage 0.67, acc-on-called 0.577
# vs base acc 0.516. Below it: "too close to call" (bars still shown).
MIN_CONFIDENCE = 0.45

# Curated rivalry pairs (our clean team names). Static, no leakage.
# Used by the Step-2 derby-flag experiment; merged to prod only if gated.
DERBY_PAIRS: set[frozenset] = frozenset({
    # England
    frozenset({"Arsenal", "Tottenham Hotspur"}),
    frozenset({"Manchester City", "Manchester United"}),
    frozenset({"Liverpool", "Everton"}),
    frozenset({"Newcastle United", "Sunderland"}),
    frozenset({"Chelsea", "Fulham"}),
    frozenset({"West Ham United", "Tottenham Hotspur"}),
    frozenset({"Aston Villa", "Wolves"}),
    # Spain
    frozenset({"Real Madrid", "Barcelona"}),
    frozenset({"Real Madrid", "Atletico Madrid"}),
    frozenset({"Sevilla", "Betis"}),
    frozenset({"Athletic Bilbao", "Real Sociedad"}),
    frozenset({"Valencia", "Levante"}),
    frozenset({"Valencia", "Villarreal"}),
    # Italy
    frozenset({"Inter", "Milan"}),
    frozenset({"Roma", "Lazio"}),
    frozenset({"Juventus", "Torino"}),
    frozenset({"Genoa", "Sampdoria"}),
    frozenset({"Napoli", "Roma"}),
    frozenset({"Verona", "Venezia"}),
    # Germany
    frozenset({"Dortmund", "Schalke 04"}),
    frozenset({"Bayern Munich", "Dortmund"}),
    frozenset({"Hamburg", "Werder Bremen"}),
    frozenset({"Borussia Monchengladbach", "FC Cologne"}),
    frozenset({"Union Berlin", "Hertha"}),
    frozenset({"Hamburg", "FC St Pauli"}),
    # France
    frozenset({"Paris Saint-Germain", "Marseille"}),
    frozenset({"Lille", "Lens"}),
    frozenset({"Nice", "Monaco"}),
    frozenset({"Lyon", "Saint Etienne"}),
    frozenset({"Nantes", "Rennes"}),
    frozenset({"Brest", "Rennes"}),
})

# Step-2 experiment candidates: name -> added columns (appended AFTER the 23
# prod cols; prod order untouched so parity tests keep passing).
EXPERIMENT_SETS: dict[str, list[str]] = {
    "restdiff": ["RestDiff"],
    "congestion": ["HomeCongestion14", "AwayCongestion14"],
    "gameno": ["HomeGameNo", "AwayGameNo"],
    "derby": ["Derby"],
    "ppg": ["PPGDiff"],
}
