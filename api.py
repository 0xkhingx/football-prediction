"""FastAPI service — fair-play XGB-tuned, no odds.

Endpoints: GET /health, GET /fixtures, POST /predict, GET /evaluate.
Run: uvicorn api:app --reload  (from repo root)
"""
from __future__ import annotations

import os
from datetime import date as _date
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.config import LEAGUE_NAMES, MODEL_DIR, TOP_LEAGUE_CODES
from src.inference import build_state_from_historical, load_artifacts, predict_one
from src.predict_live import fetch_fixtures

app = FastAPI(title="Football Predictor (fair-play XGB)", version="1.0.0")

ALLOWED_ORIGINS = [o for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictRequest(BaseModel):
    home: str = Field(min_length=2)
    away: str = Field(min_length=2)
    date: str = Field(default_factory=lambda: _date.today().isoformat(),
                      description="ISO date; predictions use history strictly before it")


class PredictResponse(BaseModel):
    home: str
    away: str
    prediction: str
    confidence: float
    pH: float
    pD: float
    pA: float
    model: str
    call: bool
    call_label: str
    form_home: list[str]
    form_away: list[str]
    h2h: dict | None
    scoreline: dict | None


@lru_cache(maxsize=1)
def _state():
    elo, melo, hist = build_state_from_historical()
    imp, model, name = load_artifacts()
    return elo, melo, hist, imp, model, name


@app.get("/health")
def health():
    _, _, _, _, _, name = _state()
    reg_path = MODEL_DIR / "model_registry.json"
    registry = {}
    if reg_path.exists():
        import json

        registry = json.loads(reg_path.read_text())
    return {
        "status": "ok",
        "model": name,
        "features": registry.get("n_features", len(registry.get("features", [])) or None),
        "fair_play": True,
        "metrics": registry.get("metrics", {}),
    }


@app.get("/fixtures")
def fixtures():
    df = fetch_fixtures()
    source = df.attrs.get("source", "none")
    network_ok = df.attrs.get("network_ok", False)
    if df.empty:
        if not network_ok and source == "none":
            # Genuinely unknown: upstream unreachable AND no local cache.
            raise HTTPException(status_code=502, detail="fixtures source unreachable and no local cache")
        return {"fixtures": [], "source": source,
                "note": "offseason — use POST /predict with manual teams"}
    out = []
    for _, r in df.iterrows():
        code = r.get("Div", "?")
        out.append(
            {
                "date": str(r.get("Date", "")),
                "league": code,
                "league_name": LEAGUE_NAMES.get(code, code),
                "home": r.get("HomeTeam", ""),
                "away": r.get("AwayTeam", ""),
            }
        )
    return {"fixtures": out, "source": source}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if req.home.strip().lower() == req.away.strip().lower():
        raise HTTPException(status_code=422, detail="home and away must differ")
    elo, melo, hist, imp, model, name = _state()
    if req.home not in hist or req.away not in hist:
        raise HTTPException(status_code=404, detail="unknown team — check spelling (e.g. 'Arsenal')")
    try:
        r = predict_one(req.home, req.away, req.date, elo, melo, hist, imp, model)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    p = r["probabilities"]
    g = r["gate"]
    return PredictResponse(
        home=r["home"],
        away=r["away"],
        prediction=r["prediction"],
        confidence=r["confidence"],
        pH=p["H"],
        pD=p["D"],
        pA=p["A"],
        model=name,
        call=g["call"],
        call_label=g["label"],
        form_home=r["form"][r["home"]],
        form_away=r["form"][r["away"]],
        h2h=r["h2h"],
        scoreline=r["scoreline"],
    )


@app.get("/season-record")
def season_record():
    import pandas as pd

    from src.score_live import RECORD_FILE, metrics

    if not RECORD_FILE.exists():
        raise HTTPException(status_code=404, detail="run python -m src.score_live first")
    df = pd.read_csv(RECORD_FILE)
    m = metrics(df)
    recent = df.tail(10)[["Date", "League", "Home", "Away", "Prediction", "Confidence",
                          "Actual", "Correct", "Source"]].to_dict(orient="records")
    return {
        "tally": {k: m[k] for k in ("n", "acc", "log_loss", "brier")},
        "per_league": m["per_league"],
        "buckets": m["buckets"],
        "recent": recent,
        "disclaimer": "Backfill = point-in-time replay, labeled; live calls take over from ship date.",
    }


@app.get("/simulation")
def simulation(league: str = "E0"):
    import json

    from src.simulate import OUTPUT_FILE as SIM_FILE

    if league not in ("E0", "SP1", "I1", "D1", "F1"):
        raise HTTPException(status_code=422, detail="unknown league")
    if not SIM_FILE.exists():
        raise HTTPException(status_code=404, detail="run python -m src.simulate first")
    data = json.loads(SIM_FILE.read_text())
    return data["leagues"][league]


@app.get("/evaluate")
def evaluate():
    import json

    eval_path = MODEL_DIR / "evaluation.json"
    if not eval_path.exists():
        raise HTTPException(status_code=404, detail="run python -m src.evaluate first")
    data = json.loads(eval_path.read_text())
    return {
        "test_set_size": data.get("test_set_size"),
        "naive": data.get("naive"),
        "prod_tuned": data.get("prod_tuned"),
        "bookmaker": data.get("bookmaker"),
        "disclaimer": "Research demo, not betting advice.",
    }
