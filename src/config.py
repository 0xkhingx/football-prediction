"""Single source of truth for football-prediction (fair-play, no-odds).

Everything (train, inference, API, web types) must import from here.
Do NOT hardcode feature lists elsewhere.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
RAW_FILE = DATA_DIR / "raw" / "matches_raw.csv"
PROCESSED_DIR = DATA_DIR / "processed"
CLEAN_FILE = PROCESSED_DIR / "matches_clean.csv"
FEATURIZED_FILE = PROCESSED_DIR / "matches_featurized.csv"
SPLITS_FILE = PROCESSED_DIR / "splits.npz"
META_FILE = PROCESSED_DIR / "split_meta.json"
PREDICTIONS_LOG = DATA_DIR / "predictions_log.csv"
FIXTURES_FILE = DATA_DIR / "fixtures_2627.csv"
RECORD_FILE = DATA_DIR / "season_record.csv"
SIMULATION_FILE = DATA_DIR / "simulation_2627.json"

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

# Team-name forgiveness (serving only — training data untouched).
# Normalized keys (lowercase, collapsed spaces, no trailing club suffix).
# Deliberately EXCLUDES ambiguous stubs: united, city, real, athletic alone
# (each matches 2+ clubs — guessing is worse than asking).
TEAM_ALIASES: dict[str, str] = {
    # England
    "man utd": "Manchester United", "man united": "Manchester United",
    "man city": "Manchester City", "spurs": "Tottenham Hotspur",
    "hammers": "West Ham United", "west ham": "West Ham United",
    "toon": "Newcastle United", "newcastle": "Newcastle United",
    "magpies": "Newcastle United", "wolverhampton": "Wolves",
    "wolverhampton wanderers": "Wolves", "gunners": "Arsenal",
    "toffees": "Everton", "seagulls": "Brighton",
    "bees": "Brentford", "cherries": "Bournemouth",
    "eagles": "Crystal Palace", "palace": "Crystal Palace",
    "forest": "Nottingham Forest", "nottingham": "Nottingham Forest",
    "villa": "Aston Villa", "saints": "Southampton",
    "black cats": "Sunderland", "coventry city": "Coventry",
    "hull city": "Hull",
    # Spain
    "atleti": "Atletico Madrid", "barca": "Barcelona",
    "athletic": "Athletic Bilbao", "sociedad": "Real Sociedad",
    "la real": "Real Sociedad", "rayo": "Rayo Vallecano",
    "racing": "Racing",
    # Italy
    "juve": "Juventus",
    # Germany
    "bayern": "Bayern Munich", "gladbach": "Borussia Monchengladbach",
    "monchengladbach": "Borussia Monchengladbach", "schalke": "Schalke 04",
    "mainz": "Mainz 05", "koln": "FC Cologne", "cologne": "FC Cologne",
    "st pauli": "FC St Pauli", "sankt pauli": "FC St Pauli",
    "freiburg": "Freiburg", "bvb": "Dortmund",
    # France
    "psg": "Paris Saint-Germain", "om": "Marseille",
    "asm": "Monaco",
}

# Trailing tokens stripped before matching (e.g. "Arsenal FC" -> arsenal).
# Applied only when the stripped form is UNAMBIGUOUS (see resolve_team).
CLUB_SUFFIXES: tuple[str, ...] = ("fc", "afc", "cf", "ud", "sc")

FUZZY_CUTOFF = 0.85
FUZZY_MARGIN = 0.05

# Single tokens that match 2+ clubs (or invite guessing): never resolve,
# even fuzzily. "city" almost means Man City — almost isn't good enough.
AMBIGUOUS_STUBS: tuple[str, ...] = ("united", "city", "real")

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
