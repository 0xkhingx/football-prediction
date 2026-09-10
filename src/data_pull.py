import time
from pathlib import Path

import pandas as pd
import requests

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

SEASONS = [f"{y}{y+1}" for y in range(15, 26)]
LEAGUES = ["E0", "SP1", "I1", "D1", "F1"]
URL_TEMPLATE = "https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
OUTPUT = RAW_DIR / "matches_raw.csv"
UA = {"User-Agent": "football-prediction/1.0 (research project)"}


def main():
    all_dfs = []

    for season in SEASONS:
        for code in LEAGUES:
            url = URL_TEMPLATE.format(season=season, code=code)
            for attempt in range(2):
                try:
                    resp = requests.get(url, timeout=30, headers=UA)
                    if resp.status_code == 200:
                        df = pd.read_csv(pd.io.common.StringIO(resp.text)).copy()
                        df["Season"] = season
                        df["League"] = code
                        all_dfs.append(df)
                        print(f"OK  {season} / {code}  ({len(df)} rows)")
                        break
                    else:
                        print(f"HTTP {resp.status_code} {season} / {code}")
                except Exception as e:  # noqa: BLE001 — one bad download retries, never aborts the pull
                    print(f"ERR {season} / {code} (attempt {attempt+1}): {e}")
                    time.sleep(2)

    if not all_dfs:
        print("No data downloaded! Existing raw file untouched.")
        return

    fresh = pd.concat(all_dfs, ignore_index=True)
    if OUTPUT.exists():
        # Merge, don't overwrite: other seasons (e.g. openfootball 2627)
        # must survive, and re-runs must not duplicate.
        # Dates are normalized to ISO first: football-data uses DD/MM/YYYY
        # while stored rows may be ISO — raw strings never match across formats.
        def _norm_date(s):
            s = str(s).strip()
            for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
                try:
                    return pd.to_datetime(s, format=fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return s

        old = pd.read_csv(OUTPUT, low_memory=False)
        cols = ["Season", "League", "Date", "HomeTeam", "AwayTeam"]

        def _key(df):
            d = df.copy()
            d["Date"] = d["Date"].apply(_norm_date)
            return [tuple(r) for r in d[cols].astype(str).values.tolist()]

        old_key = set(_key(old))
        fresh = fresh[[t not in old_key for t in _key(fresh)]]
        full = pd.concat([old, fresh], ignore_index=True)
        print(f"Merged {len(fresh)} new rows ({len(full)} total)")
    else:
        full = fresh
    full.to_csv(OUTPUT, index=False)
    print(f"\nSaved {len(full)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
