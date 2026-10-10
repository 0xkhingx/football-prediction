from pathlib import Path

import numpy as np
import pandas as pd

from .config import DERBY_PAIRS

CLEAN_FILE = Path("data/processed/matches_clean.csv")
OUTPUT = Path("data/processed/matches_featurized.csv")

ELO_K = 20
ELO_INIT = 1500

# Online strength ratings (opp-adjusted candidates): exponential update rate
# + hard clip so a 5-0 vs a promoted side can't detonate the rating.
_STR_ALPHA = 0.10
_STR_LO, _STR_HI = 0.40, 2.00
# League-average priors until enough past games accumulate (goals/match).
_LG_HOME_PRIOR, _LG_AWAY_PRIOR = 1.45, 1.15
_LG_PRIOR_N = 20


def verify_no_leakage(df):
    # MUST replay in the exact order the featurizer used. sort_values defaults
    # to quicksort (unstable on same-day ties); the 3-key sort is fully
    # deterministic, so use it here too — anything else manufactures phantom
    # "leaks" out of same-day ordering noise.
    df_check = df.sort_values(["Date", "League", "HomeTeam"]).reset_index(drop=True)
    team_last_elo = {}
    team_last_margin_elo = {}
    team_history = {}
    season_apps_v = {}
    season_pts_v = {}
    result_map = {"H": 1, "D": 0, "A": -1}
    att_v: dict = {}
    dfn_v: dict = {}
    lg_h_sum_v: dict = {}
    lg_h_n_v: dict = {}
    lg_a_sum_v: dict = {}
    lg_a_n_v: dict = {}
    errors = 0

    def _cong(hist, date):
        n = 0
        for r in reversed(hist):
            if (date - r["date"]).days > 14:
                break
            n += 1
        return float(n)

    def _close_or_nan(actual, expected, tag, i, date):
        if pd.isna(expected) and pd.isna(actual):
            return 0
        if pd.isna(expected) != pd.isna(actual) or not np.isclose(actual, expected, atol=1e-6):
            print(f"CANDIDATE-LEAK {tag}: row {i} date {date} has {actual} expected {expected}")
            return 1
        return 0
    for i, row in df_check.iterrows():
        home, away = row["HomeTeam"], row["AwayTeam"]
        date = row["Date"]
        ftr = row["FTR"]
        fthg = row["FTHG"]
        ftag = row["FTAG"]

        expected_home_elo = team_last_elo.get(home, ELO_INIT)
        expected_away_elo = team_last_elo.get(away, ELO_INIT)
        expected_home_margin = team_last_margin_elo.get(home, ELO_INIT)
        expected_away_margin = team_last_margin_elo.get(away, ELO_INIT)

        if not np.isclose(row["EloHome"], expected_home_elo, atol=1e-6):
            print(f"ELO-LEAK home {home}: row {i} date {date} has {row['EloHome']} expected {expected_home_elo}")
            errors += 1
        if not np.isclose(row["EloAway"], expected_away_elo, atol=1e-6):
            print(f"ELO-LEAK away {away}: row {i} date {date} has {row['EloAway']} expected {expected_away_elo}")
            errors += 1
        if not np.isclose(row["EloHomeMargin"], expected_home_margin, atol=1e-6):
            print(f"MARGIN-ELO-LEAK home {home}: row {i} date {date} has {row['EloHomeMargin']} expected {expected_home_margin}")
            errors += 1
        if not np.isclose(row["EloAwayMargin"], expected_away_margin, atol=1e-6):
            print(f"MARGIN-ELO-LEAK away {away}: row {i} date {date} has {row['EloAwayMargin']} expected {expected_away_margin}")
            errors += 1

        home_hist = team_history.get(home, [])
        away_hist = team_history.get(away, [])

        def form(hist, n):
            if len(hist) == 0:
                return np.nan
            recent = hist[-n:] if n < len(hist) else hist
            return np.mean([r["result"] for r in recent])

        def goals_avg(hist, n):
            if len(hist) == 0:
                return np.nan
            recent = hist[-n:] if n < len(hist) else hist
            return np.mean([r["gf"] for r in recent])

        def goals_conceded_avg(hist, n):
            if len(hist) == 0:
                return np.nan
            recent = hist[-n:] if n < len(hist) else hist
            return np.mean([r["ga"] for r in recent])

        def rolling_stat_verify(hist, n, key):
            if len(hist) == 0:
                return np.nan
            recent = hist[-n:] if n < len(hist) else hist
            return np.mean([r[key] for r in recent])

        checks = [
            ("HomeForm5", form(home_hist, 5)),
            ("HomeForm10", form(home_hist, 10)),
            ("AwayForm5", form(away_hist, 5)),
            ("AwayForm10", form(away_hist, 10)),
            ("HomeGoalsAvg5", goals_avg(home_hist, 5)),
            ("AwayGoalsAvg5", goals_avg(away_hist, 5)),
            ("HomeGoalsConcededAvg5", goals_conceded_avg(home_hist, 5)),
            ("AwayGoalsConcededAvg5", goals_conceded_avg(away_hist, 5)),
            ("HomeShotsAvg5", rolling_stat_verify(home_hist, 5, "hs")),
            ("AwayShotsAvg5", rolling_stat_verify(away_hist, 5, "as")),
            ("HomeShotsOnTargetAvg5", rolling_stat_verify(home_hist, 5, "hst")),
            ("AwayShotsOnTargetAvg5", rolling_stat_verify(away_hist, 5, "ast")),
            ("HomeCornersAvg5", rolling_stat_verify(home_hist, 5, "hc")),
            ("AwayCornersAvg5", rolling_stat_verify(away_hist, 5, "ac")),
        ]
        for feat_name, expected_val in checks:
            actual = row[feat_name]
            if np.isnan(expected_val) and not np.isnan(actual):
                print(f"FORM-LEAK {feat_name}: row {i} expected NaN, got {actual}")
                errors += 1
            elif not np.isnan(expected_val) and not np.isclose(actual, expected_val, atol=1e-6):
                print(f"FORM-LEAK {feat_name}: row {i} date {date} has {actual} expected {expected_val}")
                errors += 1

        last_h2h = next((r for r in reversed(home_hist) if r["opponent"] == away), None)
        expected_h2h = last_h2h["result"] if last_h2h is not None else 0
        if row["H2HStreak"] != expected_h2h:
            print(f"H2H-LEAK: row {i} date {date} has {row['H2HStreak']} expected {expected_h2h}")
            errors += 1

        expected_home_rest = (date - home_hist[-1]["date"]).days if home_hist else np.nan
        expected_away_rest = (date - away_hist[-1]["date"]).days if away_hist else np.nan
        if not (np.isnan(expected_home_rest) and np.isnan(row["HomeRest"])) and \
           not np.isclose(row["HomeRest"], expected_home_rest, atol=1e-6):
            print(f"REST-LEAK home: row {i} has {row['HomeRest']} expected {expected_home_rest}")
            errors += 1
        if not (np.isnan(expected_away_rest) and np.isnan(row["AwayRest"])) and \
           not np.isclose(row["AwayRest"], expected_away_rest, atol=1e-6):
            print(f"REST-LEAK away: row {i} has {row['AwayRest']} expected {expected_away_rest}")
            errors += 1

        new_home_elo, new_away_elo = elo_update(expected_home_elo, expected_away_elo, ftr)
        team_last_elo[home] = new_home_elo
        team_last_elo[away] = new_away_elo

        margin_h, margin_a = margin_actual_score(fthg, ftag)
        exp_h = expected_score(expected_home_margin, expected_away_margin)
        new_home_margin = expected_home_margin + ELO_K * (margin_h - exp_h)
        new_away_margin = expected_away_margin + ELO_K * (margin_a - (1 - exp_h))
        team_last_margin_elo[home] = new_home_margin
        team_last_margin_elo[away] = new_away_margin

        match_result = result_map[ftr]

        # Step-2 candidate verification (past data only, mirrors main loop).
        # NOTE: runs BEFORE the history appends — home_hist/away_hist are live
        # references and congestion counts pre-match history only.
        season = row["Season"]
        errors += _close_or_nan(row["HomeCongestion14"], _cong(home_hist, date), "HomeCongestion14", i, date)
        errors += _close_or_nan(row["AwayCongestion14"], _cong(away_hist, date), "AwayCongestion14", i, date)
        errors += _close_or_nan(row["HomeGameNo"], season_apps_v.get((home, season), 0) + 1, "HomeGameNo", i, date)
        errors += _close_or_nan(row["AwayGameNo"], season_apps_v.get((away, season), 0) + 1, "AwayGameNo", i, date)
        errors += _close_or_nan(row["Derby"], 1 if frozenset({home, away}) in DERBY_PAIRS else 0, "Derby", i, date)
        hsum, hn = season_pts_v.get((home, season), (0.0, 0))
        asum, an = season_pts_v.get((away, season), (0.0, 0))
        exp_ppg = (hsum / hn if hn else np.nan) - (asum / an if an else np.nan)
        errors += _close_or_nan(row["PPGDiff"], exp_ppg, "PPGDiff", i, date)
        exp_rd = row["HomeRest"] - row["AwayRest"]
        errors += _close_or_nan(row["RestDiff"], exp_rd, "RestDiff", i, date)
        # Phase-1 verification (past only, mirrors main loop).
        def _exp_ratio(hist, num_key, den_key, n=5):
            if not hist:
                return np.nan
            vals = []
            for r in hist[-n:]:
                num, den = r.get(num_key, np.nan), r.get(den_key, np.nan)
                if pd.isna(num) or pd.isna(den) or not den:
                    continue
                vals.append(num / den)
            return float(np.mean(vals)) if vals else np.nan

        errors += _close_or_nan(row["HomeShotAcc5"], _exp_ratio(home_hist, "hst", "hs"), "HomeShotAcc5", i, date)
        errors += _close_or_nan(row["AwayShotAcc5"], _exp_ratio(away_hist, "ast", "as"), "AwayShotAcc5", i, date)
        errors += _close_or_nan(row["HomeConvRate5"], _exp_ratio(home_hist, "gf", "hst"), "HomeConvRate5", i, date)
        errors += _close_or_nan(row["AwayConvRate5"], _exp_ratio(away_hist, "gf", "ast"), "AwayConvRate5", i, date)
        errors += _close_or_nan(row["HomeNewTeam"], 1.0 if len(home_hist) < 8 else 0.0, "HomeNewTeam", i, date)
        errors += _close_or_nan(row["AwayNewTeam"], 1.0 if len(away_hist) < 8 else 0.0, "AwayNewTeam", i, date)
        errors += _close_or_nan(row["AvailMissing"], 1.0, "AvailMissing", i, date)
        # Opp-adjusted verification (snapshot before update, mirrors main loop).
        _lg = row["League"]
        _hn = lg_h_n_v.get(_lg, 0)
        _an = lg_a_n_v.get(_lg, 0)
        _lgh = lg_h_sum_v.get(_lg, 0.0) / _hn if _hn >= _LG_PRIOR_N else _LG_HOME_PRIOR
        _lga = lg_a_sum_v.get(_lg, 0.0) / _an if _an >= _LG_PRIOR_N else _LG_AWAY_PRIOR
        errors += _close_or_nan(row["HomeAttStr"], att_v.get(home, 1.0), "HomeAttStr", i, date)
        errors += _close_or_nan(row["AwayAttStr"], att_v.get(away, 1.0), "AwayAttStr", i, date)
        errors += _close_or_nan(row["HomeDefStr"], dfn_v.get(home, 1.0), "HomeDefStr", i, date)
        errors += _close_or_nan(row["AwayDefStr"], dfn_v.get(away, 1.0), "AwayDefStr", i, date)
        season_apps_v[(home, season)] = season_apps_v.get((home, season), 0) + 1
        season_apps_v[(away, season)] = season_apps_v.get((away, season), 0) + 1
        vhp = 3.0 if ftr == "H" else (1.0 if ftr == "D" else 0.0)
        vap = 3.0 if ftr == "A" else (1.0 if ftr == "D" else 0.0)
        s, n = season_pts_v.get((home, season), (0.0, 0))
        season_pts_v[(home, season)] = (s + vhp, n + 1)
        s, n = season_pts_v.get((away, season), (0.0, 0))
        season_pts_v[(away, season)] = (s + vap, n + 1)

        # Opp-adjusted state update (mirrors main loop, past-only denominators).
        def _vclip(x):
            return min(_STR_HI, max(_STR_LO, x))

        _ah, _aa = att_v.get(home, 1.0), att_v.get(away, 1.0)
        _dh, _da = dfn_v.get(home, 1.0), dfn_v.get(away, 1.0)
        _den_h = _lgh * _da if _lgh * _da > 1e-6 else np.nan
        _den_a = _lga * _dh if _lga * _dh > 1e-6 else np.nan
        _obs_h = (fthg / _den_h) if not pd.isna(_den_h) else np.nan
        _obs_a = (ftag / _den_a) if not pd.isna(_den_a) else np.nan
        if not pd.isna(_obs_h):
            att_v[home] = _vclip((1 - _STR_ALPHA) * _ah + _STR_ALPHA * _obs_h)
            dfn_v[away] = _vclip((1 - _STR_ALPHA) * _da + _STR_ALPHA * _obs_h)
        if not pd.isna(_obs_a):
            att_v[away] = _vclip((1 - _STR_ALPHA) * _aa + _STR_ALPHA * _obs_a)
            dfn_v[home] = _vclip((1 - _STR_ALPHA) * _dh + _STR_ALPHA * _obs_a)
        lg_h_sum_v[_lg] = lg_h_sum_v.get(_lg, 0.0) + float(fthg)
        lg_h_n_v[_lg] = lg_h_n_v.get(_lg, 0) + 1
        lg_a_sum_v[_lg] = lg_a_sum_v.get(_lg, 0.0) + float(ftag)
        lg_a_n_v[_lg] = lg_a_n_v.get(_lg, 0) + 1

        team_history.setdefault(home, []).append(
            {"date": date, "result": match_result, "opponent": away,
             "gf": fthg, "ga": ftag,
             "hs": row.get("HS", np.nan), "as": row.get("AS", np.nan),
             "hst": row.get("HST", np.nan), "ast": row.get("AST", np.nan),
             "hc": row.get("HC", np.nan), "ac": row.get("AC", np.nan)}
        )
        team_history.setdefault(away, []).append(
            {"date": date, "result": -match_result, "opponent": home,
             "gf": ftag, "ga": fthg,
             "hs": row.get("AS", np.nan), "as": row.get("HS", np.nan),
             "hst": row.get("AST", np.nan), "ast": row.get("HST", np.nan),
             "hc": row.get("AC", np.nan), "ac": row.get("HC", np.nan)}
        )

    assert errors == 0, f"{errors} leakage violations detected"
    print("Leakage check PASSED: all features (Elo, margin-Elo, form, goals, H2H, rest) computed from past data only")

def expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def elo_update(home_elo, away_elo, ftr):
    exp_h = expected_score(home_elo, away_elo)
    exp_a = 1 - exp_h
    if ftr == "H":
        score_h, score_a = 1, 0
    elif ftr == "A":
        score_h, score_a = 0, 1
    else:
        score_h, score_a = 0.5, 0.5
    new_home = home_elo + ELO_K * (score_h - exp_h)
    new_away = away_elo + ELO_K * (score_a - exp_a)
    return new_home, new_away

def margin_actual_score(fthg, ftag):
    """Goal-margin-aware score for Elo updates.
    Uses clamped goal difference capped at 3:
      draw  -> 0.5
      1-0   -> 0.6667
      2-0   -> 0.8333
      3-0+  -> 1.0
    (and symmetrically for away wins).
    """
    gd = fthg - ftag
    if gd == 0:
        return 0.5, 0.5
    mf = min(abs(gd), 3) / 3
    if gd > 0:
        return 0.5 + 0.5 * mf, 0.5 - 0.5 * mf
    else:
        return 0.5 - 0.5 * mf, 0.5 + 0.5 * mf

def main():
    df = pd.read_csv(CLEAN_FILE, low_memory=False)
    df["Date"] = pd.to_datetime(df["Date"])

    df = df.sort_values(["Date", "League", "HomeTeam"]).reset_index(drop=True)

    elo_dict = {}
    margin_elo_dict = {}
    team_history = {}
    season_apps: dict = {}
    season_pts: dict = {}
    result_map = {"H": 1, "D": 0, "A": -1}
    # Online strength state (past-only): attack/defense multipliers per team
    # + running league goal averages for the expectation denominator.
    att: dict = {}
    dfn: dict = {}
    lg_h_sum: dict = {}
    lg_h_n: dict = {}
    lg_a_sum: dict = {}
    lg_a_n: dict = {}

    def congestion(hist, date):
        # matches in the 14 days strictly before this one (past only)
        n = 0
        for r in reversed(hist):
            if (date - r["date"]).days > 14:
                break
            n += 1
        return float(n)

    home_elo_vals = np.empty(len(df), dtype=np.float64)
    away_elo_vals = np.empty(len(df), dtype=np.float64)
    home_elo_margin_vals = np.empty(len(df), dtype=np.float64)
    away_elo_margin_vals = np.empty(len(df), dtype=np.float64)
    home_form5 = np.empty(len(df), dtype=np.float64)
    home_form10 = np.empty(len(df), dtype=np.float64)
    away_form5 = np.empty(len(df), dtype=np.float64)
    away_form10 = np.empty(len(df), dtype=np.float64)
    h2h_streak = np.empty(len(df), dtype=np.int64)
    home_rest = np.empty(len(df), dtype=np.float64)
    away_rest = np.empty(len(df), dtype=np.float64)
    home_goals_avg5 = np.empty(len(df), dtype=np.float64)
    away_goals_avg5 = np.empty(len(df), dtype=np.float64)
    home_goals_conceded_avg5 = np.empty(len(df), dtype=np.float64)
    away_goals_conceded_avg5 = np.empty(len(df), dtype=np.float64)
    home_shots_avg5 = np.empty(len(df), dtype=np.float64)
    away_shots_avg5 = np.empty(len(df), dtype=np.float64)
    home_sot_avg5 = np.empty(len(df), dtype=np.float64)
    away_sot_avg5 = np.empty(len(df), dtype=np.float64)
    home_corners_avg5 = np.empty(len(df), dtype=np.float64)
    away_corners_avg5 = np.empty(len(df), dtype=np.float64)
    # Step-2 experiment candidates (appended after prod cols; prod order untouched)
    home_congestion14 = np.empty(len(df), dtype=np.float64)
    away_congestion14 = np.empty(len(df), dtype=np.float64)
    home_gameno = np.empty(len(df), dtype=np.float64)
    away_gameno = np.empty(len(df), dtype=np.float64)
    derby_flag = np.empty(len(df), dtype=np.int64)
    ppg_diff = np.empty(len(df), dtype=np.float64)
    # Phase-1 candidates (free, past-only): chance-quality proxies + new-team flags.
    # Availability cols stay all-NaN until a free pre-match feed lands (schema reserved).
    home_shotacc5 = np.empty(len(df), dtype=np.float64)
    away_shotacc5 = np.empty(len(df), dtype=np.float64)
    home_conv5 = np.empty(len(df), dtype=np.float64)
    away_conv5 = np.empty(len(df), dtype=np.float64)
    home_newteam = np.empty(len(df), dtype=np.float64)
    away_newteam = np.empty(len(df), dtype=np.float64)
    home_out = np.empty(len(df), dtype=np.float64)
    away_out = np.empty(len(df), dtype=np.float64)
    avail_missing = np.empty(len(df), dtype=np.float64)
    # Opp-adjusted strengths (online, past-only): exponential attack/defense
    # ratings vs running league averages. See _STR_ALPHA / _STR_CLIP below.
    home_att_str = np.empty(len(df), dtype=np.float64)
    away_att_str = np.empty(len(df), dtype=np.float64)
    home_def_str = np.empty(len(df), dtype=np.float64)
    away_def_str = np.empty(len(df), dtype=np.float64)

    for i, row in df.iterrows():
        home = row["HomeTeam"]
        away = row["AwayTeam"]
        date = row["Date"]
        ftr = row["FTR"]
        fthg = row["FTHG"]
        ftag = row["FTAG"]

        home_elo = elo_dict.get(home, ELO_INIT)
        away_elo = elo_dict.get(away, ELO_INIT)
        home_elo_vals[i] = home_elo
        away_elo_vals[i] = away_elo

        home_elo_margin = margin_elo_dict.get(home, ELO_INIT)
        away_elo_margin = margin_elo_dict.get(away, ELO_INIT)
        home_elo_margin_vals[i] = home_elo_margin
        away_elo_margin_vals[i] = away_elo_margin

        home_hist = team_history.get(home, [])
        away_hist = team_history.get(away, [])

        def form(hist, n):
            if len(hist) == 0:
                return np.nan
            recent = hist[-n:] if n < len(hist) else hist
            return np.mean([r["result"] for r in recent])

        home_form5[i] = form(home_hist, 5)
        home_form10[i] = form(home_hist, 10)
        away_form5[i] = form(away_hist, 5)
        away_form10[i] = form(away_hist, 10)

        def goals_avg(hist, n):
            if len(hist) == 0:
                return np.nan
            recent = hist[-n:] if n < len(hist) else hist
            return np.mean([r["gf"] for r in recent])

        def goals_conceded_avg(hist, n):
            if len(hist) == 0:
                return np.nan
            recent = hist[-n:] if n < len(hist) else hist
            return np.mean([r["ga"] for r in recent])

        home_goals_avg5[i] = goals_avg(home_hist, 5)
        away_goals_avg5[i] = goals_avg(away_hist, 5)
        home_goals_conceded_avg5[i] = goals_conceded_avg(home_hist, 5)
        away_goals_conceded_avg5[i] = goals_conceded_avg(away_hist, 5)

        def rolling_stat(hist, n, key):
            if len(hist) == 0:
                return np.nan
            recent = hist[-n:] if n < len(hist) else hist
            return np.mean([r[key] for r in recent])

        home_shots_avg5[i] = rolling_stat(home_hist, 5, "hs")
        away_shots_avg5[i] = rolling_stat(away_hist, 5, "as")
        home_sot_avg5[i] = rolling_stat(home_hist, 5, "hst")
        away_sot_avg5[i] = rolling_stat(away_hist, 5, "ast")
        home_corners_avg5[i] = rolling_stat(home_hist, 5, "hc")
        away_corners_avg5[i] = rolling_stat(away_hist, 5, "ac")

        # --- Step-2 candidates (past data only) ---
        season = row["Season"]
        home_congestion14[i] = congestion(home_hist, date)
        away_congestion14[i] = congestion(away_hist, date)
        home_gameno[i] = season_apps.get((home, season), 0) + 1
        away_gameno[i] = season_apps.get((away, season), 0) + 1
        derby_flag[i] = 1 if frozenset({home, away}) in DERBY_PAIRS else 0
        hsum, hn = season_pts.get((home, season), (0.0, 0))
        asum, an = season_pts.get((away, season), (0.0, 0))
        hppg = hsum / hn if hn else np.nan
        appg = asum / an if an else np.nan
        ppg_diff[i] = hppg - appg

        # --- Phase-1 candidates (past data only, NaN-safe) ---
        def _ratio_mean(hist, num_key, den_key, n=5):
            if not hist:
                return np.nan
            vals = []
            for r in hist[-n:]:
                num, den = r.get(num_key, np.nan), r.get(den_key, np.nan)
                if pd.isna(num) or pd.isna(den) or not den:
                    continue
                vals.append(num / den)
            return float(np.mean(vals)) if vals else np.nan

        # Chance quality: shot accuracy (SOT/shots) + conversion (goals/SOT).
        # Home perspective uses hs/hst/gf; away uses as/ast/gf (swapped at log time).
        home_shotacc5[i] = _ratio_mean(home_hist, "hst", "hs")
        away_shotacc5[i] = _ratio_mean(away_hist, "ast", "as")
        home_conv5[i] = _ratio_mean(home_hist, "gf", "hst")
        away_conv5[i] = _ratio_mean(away_hist, "gf", "ast")
        # New-team flag: <8 prior appearances -> promoted-like prior signal.
        # Replaces the need to read the 'Other' ghost entity downstream.
        home_newteam[i] = 1.0 if len(home_hist) < 8 else 0.0
        away_newteam[i] = 1.0 if len(away_hist) < 8 else 0.0
        # Availability: reserved schema, all-NaN until free feed lands.
        home_out[i] = np.nan
        away_out[i] = np.nan
        avail_missing[i] = 1.0

        # --- Opp-adjusted strengths (past only): snapshot before update ---
        league = row["League"]
        hn_lg = lg_h_n.get(league, 0)
        an_lg = lg_a_n.get(league, 0)
        lg_h = lg_h_sum.get(league, 0.0) / hn_lg if hn_lg >= _LG_PRIOR_N else _LG_HOME_PRIOR
        lg_a = lg_a_sum.get(league, 0.0) / an_lg if an_lg >= _LG_PRIOR_N else _LG_AWAY_PRIOR
        home_att_str[i] = att.get(home, 1.0)
        away_att_str[i] = att.get(away, 1.0)
        home_def_str[i] = dfn.get(home, 1.0)
        away_def_str[i] = dfn.get(away, 1.0)

        last_h2h = next(
            (
                r
                for r in reversed(home_hist)
                if r["opponent"] == away
            ),
            None,
        )
        if last_h2h is not None:
            h2h_streak[i] = last_h2h["result"]
        else:
            h2h_streak[i] = 0

        if home_hist:
            home_rest[i] = (date - home_hist[-1]["date"]).days
        else:
            home_rest[i] = np.nan

        if away_hist:
            away_rest[i] = (date - away_hist[-1]["date"]).days
        else:
            away_rest[i] = np.nan

        new_home_elo, new_away_elo = elo_update(home_elo, away_elo, ftr)
        elo_dict[home] = new_home_elo
        elo_dict[away] = new_away_elo

        margin_h, margin_a = margin_actual_score(fthg, ftag)
        exp_h = expected_score(home_elo_margin, away_elo_margin)
        new_home_margin = home_elo_margin + ELO_K * (margin_h - exp_h)
        new_away_margin = away_elo_margin + ELO_K * (margin_a - (1 - exp_h))
        margin_elo_dict[home] = new_home_margin
        margin_elo_dict[away] = new_away_margin

        match_result = result_map[ftr]
        team_history.setdefault(home, []).append(
            {
                "date": date,
                "result": match_result,
                "opponent": away,
                "gf": fthg, "ga": ftag,
                "hs": row.get("HS", np.nan),
                "as": row.get("AS", np.nan),
                "hst": row.get("HST", np.nan),
                "ast": row.get("AST", np.nan),
                "hc": row.get("HC", np.nan),
                "ac": row.get("AC", np.nan),
            }
        )
        team_history.setdefault(away, []).append(
            {
                "date": date,
                "result": -match_result,
                "opponent": home,
                "gf": ftag, "ga": fthg,
                "hs": row.get("AS", np.nan),
                "as": row.get("HS", np.nan),
                "hst": row.get("AST", np.nan),
                "ast": row.get("HST", np.nan),
                "hc": row.get("AC", np.nan),
                "ac": row.get("HC", np.nan),
            }
        )

        season_apps[(home, season)] = season_apps.get((home, season), 0) + 1
        season_apps[(away, season)] = season_apps.get((away, season), 0) + 1
        # Points derived from the result itself — works for every source.
        hp = 3.0 if ftr == "H" else (1.0 if ftr == "D" else 0.0)
        ap = 3.0 if ftr == "A" else (1.0 if ftr == "D" else 0.0)
        s, n = season_pts.get((home, season), (0.0, 0))
        season_pts[(home, season)] = (s + hp, n + 1)
        s, n = season_pts.get((away, season), (0.0, 0))
        season_pts[(away, season)] = (s + ap, n + 1)

        # Online strength update (uses pre-match snapshot denominators only).
        def _clip(x):
            return min(_STR_HI, max(_STR_LO, x))

        ah_old, aa_old = att.get(home, 1.0), att.get(away, 1.0)
        dh_old, da_old = dfn.get(home, 1.0), dfn.get(away, 1.0)
        denom_h = lg_h * da_old if lg_h * da_old > 1e-6 else np.nan
        denom_a = lg_a * dh_old if lg_a * dh_old > 1e-6 else np.nan
        obs_h = (fthg / denom_h) if not pd.isna(denom_h) else np.nan
        obs_a = (ftag / denom_a) if not pd.isna(denom_a) else np.nan
        if not pd.isna(obs_h):
            att[home] = _clip((1 - _STR_ALPHA) * ah_old + _STR_ALPHA * obs_h)
            dfn[away] = _clip((1 - _STR_ALPHA) * da_old + _STR_ALPHA * obs_h)
        if not pd.isna(obs_a):
            att[away] = _clip((1 - _STR_ALPHA) * aa_old + _STR_ALPHA * obs_a)
            dfn[home] = _clip((1 - _STR_ALPHA) * dh_old + _STR_ALPHA * obs_a)
        lg_h_sum[league] = lg_h_sum.get(league, 0.0) + float(fthg)
        lg_h_n[league] = lg_h_n.get(league, 0) + 1
        lg_a_sum[league] = lg_a_sum.get(league, 0.0) + float(ftag)
        lg_a_n[league] = lg_a_n.get(league, 0) + 1

    df["EloHome"] = home_elo_vals
    df["EloAway"] = away_elo_vals
    df["EloDiff"] = df["EloHome"] - df["EloAway"]
    df["EloHomeMargin"] = home_elo_margin_vals
    df["EloAwayMargin"] = away_elo_margin_vals
    df["EloDiffMargin"] = df["EloHomeMargin"] - df["EloAwayMargin"]
    df["HomeForm5"] = home_form5
    df["HomeForm10"] = home_form10
    df["AwayForm5"] = away_form5
    df["AwayForm10"] = away_form10
    df["H2HStreak"] = h2h_streak
    df["HomeRest"] = home_rest
    df["AwayRest"] = away_rest
    df["HomeGoalsAvg5"] = home_goals_avg5
    df["AwayGoalsAvg5"] = away_goals_avg5
    df["HomeGoalsConcededAvg5"] = home_goals_conceded_avg5
    df["AwayGoalsConcededAvg5"] = away_goals_conceded_avg5
    df["HomeShotsAvg5"] = home_shots_avg5
    df["AwayShotsAvg5"] = away_shots_avg5
    df["HomeShotsOnTargetAvg5"] = home_sot_avg5
    df["AwayShotsOnTargetAvg5"] = away_sot_avg5
    df["HomeCornersAvg5"] = home_corners_avg5
    df["AwayCornersAvg5"] = away_corners_avg5
    # Step-2 candidates (appended after prod cols; prod order untouched)
    df["RestDiff"] = df["HomeRest"] - df["AwayRest"]
    df["HomeCongestion14"] = home_congestion14
    df["AwayCongestion14"] = away_congestion14
    df["HomeGameNo"] = home_gameno
    df["AwayGameNo"] = away_gameno
    df["Derby"] = derby_flag
    df["PPGDiff"] = ppg_diff
    # Phase-1 candidates (appended after Step-2; prod 23 order still untouched)
    df["HomeShotAcc5"] = home_shotacc5
    df["AwayShotAcc5"] = away_shotacc5
    df["HomeConvRate5"] = home_conv5
    df["AwayConvRate5"] = away_conv5
    df["HomeNewTeam"] = home_newteam
    df["AwayNewTeam"] = away_newteam
    df["HomeOut"] = home_out
    df["AwayOut"] = away_out
    df["AvailMissing"] = avail_missing
    df["HomeAttStr"] = home_att_str
    df["AwayAttStr"] = away_att_str
    df["HomeDefStr"] = home_def_str
    df["AwayDefStr"] = away_def_str

    # Normalized B365 implied probabilities
    odds_cols = ["B365H", "B365D", "B365A"]
    if all(c in df.columns for c in odds_cols):
        raw = np.column_stack([df[c].values for c in odds_cols]).astype(np.float64)
        inv = 1.0 / raw
        total = inv.sum(axis=1, keepdims=True)
        normed = inv / total
        df["ProbB365H"] = normed[:, 0]
        df["ProbB365D"] = normed[:, 1]
        df["ProbB365A"] = normed[:, 2]
        n_missing = np.isnan(raw).any(axis=1).sum()
        if n_missing:
            print(f"Warning: {n_missing} rows have missing B365 odds (ProbB365 will be NaN)")

    verify_no_leakage(df)

    df.to_csv(OUTPUT, index=False)
    print(f"Saved {len(df)} rows to {OUTPUT}")
    print(f"Feature columns: {[c for c in df.columns if c not in ['Date','HomeTeam','AwayTeam','FTHG','FTAG','FTR','Season','League','HomePoints','AwayPoints','B365H','B365D','B365A']]}")

if __name__ == "__main__":
    main()
