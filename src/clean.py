import pandas as pd
import numpy as np
import re
from pathlib import Path

RAW_FILE = Path("data/raw/matches_raw.csv")
OUTPUT = Path("data/processed/matches_clean.csv")

TEAM_NAME_MAP = {
    "Man United": "Manchester United",
    "Man City": "Manchester City",
    "Newcastle": "Newcastle United",
    "Tottenham": "Tottenham Hotspur",
    "Nott'm Forest": "Nottingham Forest",
    "West Ham": "West Ham United",
    "Ath Bilbao": "Athletic Bilbao",
    "Ath Madrid": "Atletico Madrid",
    "Ein Frankfurt": "Eintracht Frankfurt",
    "FC Koln": "FC Cologne",
    "M'gladbach": "Borussia Monchengladbach",
    "Sociedad": "Real Sociedad",
    "Sp Gijon": "Sporting Gijon",
    "Vallecano": "Rayo Vallecano",
    "St Pauli": "FC St Pauli",
    "Paris SG": "Paris Saint-Germain",
    "St Etienne": "Saint Etienne",
    "Mainz": "Mainz 05",
    "Ajaccio GFCO": "GFC Ajaccio",
    "Ajaccio": "AC Ajaccio",
    "Caen": "SM Caen",
    "Nancy": "AS Nancy",
}

CORE_COLS = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]
ODDS_COLS = ["B365H", "B365D", "B365A"]

def parse_mixed_date(d):
    if pd.isna(d):
        return pd.NaT
    d = str(d).strip()
    if re.match(r"\d{2}/\d{2}/\d{4}$", d):
        return pd.to_datetime(d, format="%d/%m/%Y", errors="coerce")
    if re.match(r"\d{2}/\d{2}/\d{2}$", d):
        return pd.to_datetime(d, format="%d/%m/%y", errors="coerce")
    return pd.to_datetime(d, dayfirst=True, errors="coerce")

def main():
    df = pd.read_csv(RAW_FILE, low_memory=False).copy()

    df.columns = df.columns.str.replace("\ufeff", "", regex=False)

    print(f"Loaded {len(df)} rows")

    before = len(df)
    df = df.dropna(subset=CORE_COLS, how="any")
    print(f"Dropped {before - len(df)} rows with missing core columns")

    df["HomeTeam"] = df["HomeTeam"].replace(TEAM_NAME_MAP)
    df["AwayTeam"] = df["AwayTeam"].replace(TEAM_NAME_MAP)

    appearances = pd.concat([df["HomeTeam"], df["AwayTeam"]]).value_counts()
    rare = set(appearances[appearances < 3].index)
    if rare:
        print(f"Flagging {len(rare)} rare teams as 'Other': {sorted(rare)}")
        df["HomeTeam"] = df["HomeTeam"].apply(lambda x: "Other" if x in rare else x)
        df["AwayTeam"] = df["AwayTeam"].apply(lambda x: "Other" if x in rare else x)

    df["Date"] = df["Date"].apply(parse_mixed_date)
    pre = len(df)
    df = df.dropna(subset=["Date"])
    print(f"Dropped {pre - len(df)} rows with unparseable dates")

    df = df.sort_values(["Date", "League", "HomeTeam"]).reset_index(drop=True)

    df["HomePoints"] = np.where(df["FTR"] == "H", 3, np.where(df["FTR"] == "D", 1, 0))
    df["AwayPoints"] = np.where(df["FTR"] == "A", 3, np.where(df["FTR"] == "D", 1, 0))

    keep_cols = CORE_COLS + ["Season", "League", "HomePoints", "AwayPoints"]
    for c in ODDS_COLS:
        if c in df.columns:
            keep_cols.append(c)
    df = df[keep_cols]

    df.to_csv(OUTPUT, index=False)
    print(f"Saved {len(df)} rows to {OUTPUT}")
    print(f"Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")

if __name__ == "__main__":
    main()
