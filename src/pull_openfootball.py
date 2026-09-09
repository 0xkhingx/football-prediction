"""Pull 2025/26 + 2026/27 results from openfootball/football.json (GitHub).

football-data.co.uk is unreachable from here (host-level 503); openfootball
carries full fixtures+results for all 5 leagues. Played matches are appended to
data/raw/matches_raw.csv (core cols only; shots/odds stay NaN — the no-odds
pipeline already handles that). Unplayed 2627 fixtures go to data/fixtures_2627.csv.

Team names are mapped EXPLICITLY to our football-data names. Unknown names
fail loud — never silently merge into the wrong entity.
"""
from __future__ import annotations

import json
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests

RAW_FILE = Path("data/raw/matches_raw.csv")
FIXTURES_FILE = Path("data/fixtures_2627.csv")
BASE = "https://raw.githubusercontent.com/openfootball/football.json/master"
UA = {"User-Agent": "football-prediction/1.0 (research project)"}

# (season_label, openfootball_file, our season, our league)
SOURCES: list[tuple[str, str, int, str]] = [
    ("2025-26", "en.1", 2526, "E0"),
    ("2025-26", "es.1", 2526, "SP1"),
    ("2025-26", "it.1", 2526, "I1"),
    ("2025-26", "de.1", 2526, "D1"),
    ("2025-26", "fr.1", 2526, "F1"),
    ("2026-27", "en.1", 2627, "E0"),
    ("2026-27", "es.1", 2627, "SP1"),
    ("2026-27", "it.1", 2627, "I1"),
    ("2026-27", "de.1", 2627, "D1"),
    ("2026-27", "fr.1", 2627, "F1"),
]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


# openfootball (normalized) -> our football-data clean names
TEAM_MAP: dict[str, str] = {
    # England
    "afc bournemouth": "Bournemouth", "arsenal fc": "Arsenal",
    "aston villa fc": "Aston Villa", "brentford fc": "Brentford",
    "brighton & hove albion fc": "Brighton", "burnley fc": "Burnley",
    "chelsea fc": "Chelsea", "coventry city fc": "Coventry",
    "crystal palace fc": "Crystal Palace", "everton fc": "Everton",
    "fulham fc": "Fulham", "hull city afc": "Hull",
    "ipswich town fc": "Ipswich", "leeds united fc": "Leeds",
    "liverpool fc": "Liverpool", "manchester city fc": "Manchester City",
    "manchester united fc": "Manchester United",
    "newcastle united fc": "Newcastle United",
    "nottingham forest fc": "Nottingham Forest", "sunderland afc": "Sunderland",
    "tottenham hotspur fc": "Tottenham Hotspur",
    "west ham united fc": "West Ham United",
    "wolverhampton wanderers fc": "Wolves",
    # Spain
    "athletic club": "Athletic Bilbao", "ca osasuna": "Osasuna",
    "club atletico de madrid": "Atletico Madrid", "deportivo alaves": "Alaves",
    "elche cf": "Elche", "fc barcelona": "Barcelona", "getafe cf": "Getafe",
    "girona fc": "Girona", "levante ud": "Levante",
    "rc celta de vigo": "Celta", "rcd espanyol de barcelona": "Espanol",
    "rcd mallorca": "Mallorca", "rayo vallecano de madrid": "Rayo Vallecano",
    "real betis balompie": "Betis", "real madrid cf": "Real Madrid",
    "real oviedo": "Oviedo", "real sociedad de futbol": "Real Sociedad",
    "sevilla fc": "Sevilla", "valencia cf": "Valencia",
    "villarreal cf": "Villarreal", "malaga cf": "Malaga",
    "rc deportivo la coruna": "La Coruna",
    "real racing club de santander": "Racing",
    # Italy
    "ac milan": "Milan", "ac pisa 1909": "Pisa", "acf fiorentina": "Fiorentina",
    "as roma": "Roma", "atalanta bc": "Atalanta", "bologna fc 1909": "Bologna",
    "cagliari calcio": "Cagliari", "como 1907": "Como",
    "fc internazionale milano": "Inter", "genoa cfc": "Genoa",
    "hellas verona fc": "Verona", "juventus fc": "Juventus",
    "parma calcio 1913": "Parma", "ss lazio": "Lazio", "ssc napoli": "Napoli",
    "torino fc": "Torino", "us cremonese": "Cremonese", "us lecce": "Lecce",
    "us sassuolo calcio": "Sassuolo", "udinese calcio": "Udinese",
    "ac monza": "Monza", "frosinone calcio": "Frosinone",
    "venezia fc": "Venezia",
    # Germany
    "1. fc heidenheim 1846": "Heidenheim", "1. fc koln": "FC Cologne",
    "1. fc union berlin": "Union Berlin", "1. fsv mainz 05": "Mainz 05",
    "bayer 04 leverkusen": "Leverkusen", "borussia dortmund": "Dortmund",
    "borussia monchengladbach": "Borussia Monchengladbach",
    "eintracht frankfurt": "Eintracht Frankfurt", "fc augsburg": "Augsburg",
    "fc bayern munchen": "Bayern Munich", "fc st. pauli 1910": "FC St Pauli",
    "hamburger sv": "Hamburg", "rb leipzig": "RB Leipzig",
    "sc freiburg": "Freiburg", "sv werder bremen": "Werder Bremen",
    "tsg 1899 hoffenheim": "Hoffenheim", "vfb stuttgart": "Stuttgart",
    "vfl wolfsburg": "Wolfsburg", "fc schalke 04": "Schalke 04",
    "sc paderborn 07": "Paderborn", "sv 07 elversberg": "Elversberg",
    # France
    "aj auxerre": "Auxerre", "as monaco fc": "Monaco", "angers sco": "Angers",
    "fc lorient": "Lorient", "fc metz": "Metz", "fc nantes": "Nantes",
    "le havre ac": "Le Havre", "lille osc": "Lille", "ogc nice": "Nice",
    "olympique lyonnais": "Lyon", "olympique de marseille": "Marseille",
    "paris fc": "Paris FC", "paris saint-germain fc": "Paris Saint-Germain",
    "rc strasbourg alsace": "Strasbourg", "racing club de lens": "Lens",
    "stade brestois 29": "Brest", "stade rennais fc 1901": "Rennes",
    "toulouse fc": "Toulouse", "es troyes ac": "Troyes",
    "le mans fc": "Le Mans",
}


def fetch(season_label: str, code: str) -> dict:
    url = f"{BASE}/{season_label}/{code}.json"
    last = None
    for attempt, wait in ((1, 5), (2, 20), (3, 60)):
        try:
            r = requests.get(url, timeout=60, headers=UA)
            r.raise_for_status()
            return json.loads(r.content.decode("utf-8"))
        except Exception as e:
            last = e
            print(f"  retry {attempt}/3 {season_label}/{code} after {wait}s ({e})")
            time.sleep(wait)
    raise last


def main() -> None:
    raw = pd.read_csv(RAW_FILE, low_memory=False)
    existing = set(
        zip(raw["Season"].astype(str), raw["League"], raw["Date"].astype(str),
            raw["HomeTeam"], raw["AwayTeam"])
    )
    # Season-blind keys: openfootball season files demonstrably contain
    # fixtures from other seasons (2024/25 tail in 2025-26 files, early
    # 2026/27 in 2025-26 files). Never double-count a real match.
    any_season = set(
        zip(raw["League"], raw["Date"].astype(str), raw["HomeTeam"], raw["AwayTeam"])
    )
    dropped_window = dropped_dupe = 0
    new_rows: list[dict] = []
    fixtures: list[dict] = []

    for season_label, code, season, league in SOURCES:
        data = fetch(season_label, code)
        time.sleep(2)  # stay polite to raw.githubusercontent
        played = skipped = 0
        for m in data["matches"]:
            home_raw, away_raw = m["team1"], m["team2"]
            for t in (home_raw, away_raw):
                if norm(t) not in TEAM_MAP:
                    raise ValueError(f"UNMAPPED team {t!r} ({season_label}/{code}) — add to TEAM_MAP")
            home, away = TEAM_MAP[norm(home_raw)], TEAM_MAP[norm(away_raw)]
            score = m.get("score")
            ft = score.get("ft") if isinstance(score, dict) else score
            if not ft or len(ft) != 2 or ft[0] is None or ft[1] is None:
                if season == 2627 and m.get("status") != "canceled":
                    fixtures.append({"Date": m["date"], "League": league,
                                     "Home": home, "Away": away,
                                     "Round": str(m.get("round", "") or "")})
                skipped += 1
                continue
            fthg, ftag = int(ft[0]), int(ft[1])
            key = (str(season), league, m["date"], home, away)
            if key in existing:
                continue
            if season == 2526 and not ("2025-08-01" <= m["date"] <= "2026-05-31"):
                dropped_window += 1
                continue
            if (league, m["date"], home, away) in any_season:
                dropped_dupe += 1
                continue
            new_rows.append({"Date": m["date"], "HomeTeam": home, "AwayTeam": away,
                             "FTHG": fthg, "FTAG": ftag,
                             "FTR": "H" if fthg > ftag else ("A" if ftag > fthg else "D"),
                             "Season": season, "League": league})
            existing.add(key)
            played += 1
        print(f"OK  {season} / {league}  ({played} new played, {skipped} unplayed)")

    if new_rows:
        raw = pd.concat([raw, pd.DataFrame(new_rows)], ignore_index=True)
        raw.to_csv(RAW_FILE, index=False)
    print(f"Appended {len(new_rows)} rows -> {RAW_FILE} ({len(raw)} total)")
    print(f"Dropped: {dropped_window} out-of-window 2526, {dropped_dupe} cross-season dupes")

    if fixtures:
        pd.DataFrame(fixtures).to_csv(FIXTURES_FILE, index=False)
        print(f"Wrote {len(fixtures)} unplayed 2627 fixtures -> {FIXTURES_FILE}")


if __name__ == "__main__":
    main()
