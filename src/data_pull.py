import pandas as pd
import requests
import time
from pathlib import Path

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

SEASONS = [f"{y}{y+1}" for y in range(15, 25)]
LEAGUES = ["E0", "SP1", "I1", "D1", "F1"]
URL_TEMPLATE = "https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
OUTPUT = RAW_DIR / "matches_raw.csv"

all_dfs = []

for season in SEASONS:
    for code in LEAGUES:
        url = URL_TEMPLATE.format(season=season, code=code)
        for attempt in range(2):
            try:
                resp = requests.get(url, timeout=30)
                if resp.status_code == 200:
                    df = pd.read_csv(pd.io.common.StringIO(resp.text)).copy()
                    df["Season"] = season
                    df["League"] = code
                    all_dfs.append(df)
                    print(f"OK  {season} / {code}  ({len(df)} rows)")
                    break
                else:
                    print(f"HTTP {resp.status_code} {season} / {code}")
            except Exception as e:
                print(f"ERR {season} / {code} (attempt {attempt+1}): {e}")
                time.sleep(2)

if all_dfs:
    full = pd.concat(all_dfs, ignore_index=True)
    full.to_csv(OUTPUT, index=False)
    print(f"\nSaved {len(full)} rows to {OUTPUT}")
else:
    print("No data downloaded!")
