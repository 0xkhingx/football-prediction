"""Monte Carlo simulator: internal consistency + API + bands."""
import pandas as pd

from src.simulate import band, rare_teams


def test_bands_never_false_precision():
    assert band(0.0) == "<5%"
    assert band(0.37) == "35-40%"
    assert band(0.5) == "50-55%"
    assert band(1.0) == ">95%"


def test_simulation_sums():
    import json

    d = json.load(open("data/simulation_2627.json"))
    for lg, L in d["leagues"].items():
        assert abs(sum(r["title_raw"] for r in L["table"]) - 1.0) < 1e-9
        assert abs(sum(r["top4_raw"] for r in L["table"]) - 4.0) < 1e-9


def test_rare_and_unknown_resolve_to_other():
    import pandas as pd

    clean = pd.read_csv("data/processed/matches_clean.csv", low_memory=False)
    rare = rare_teams(clean)
    known = set(clean["HomeTeam"]) | set(clean["AwayTeam"])
    resolve = lambda t: t if (t in known and t not in rare) else "Other"
    assert resolve("Arsenal") == "Arsenal"  # known, common
    assert resolve("Coventry") == "Other"  # never appears (mapped at clean time)
    assert resolve("Nope FC") == "Other"  # unknown entirely


def test_api_simulation():
    from fastapi.testclient import TestClient

    from api import app
    from src.simulate import N_SIMS

    c = TestClient(app)
    body = c.get("/simulation", params={"league": "E0"}).json()
    assert body["league"] == "E0"
    assert body["sims"] == N_SIMS
    assert len(body["table"]) >= 18
    assert c.get("/simulation", params={"league": "XX"}).status_code == 422
