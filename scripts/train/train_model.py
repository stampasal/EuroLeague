#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
train_model_v4_2.py  (v4.2 — 17 features, dual DvP + filter historical)
-----------------------------------------------------------------------
v4.1 +:
  - dvp_opp_vs_pos     → short EWMA span=5 (expanding, reactive)
  - dvp_opp_vs_pos_l20 → long rolling 20 (expanding, baseline)
  - predict_player: ΜΟΝΟ ενεργοί παίκτες (last game στο 2026)

Features (17):
  base10 + dvp_short + dvp_long + opp_adj_def + opp_adj_z
        + opp_pooled_def + opp_quality + is_home
"""

import json
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import DATA_RAW, DATA_PROC, APP_JS_CONFIG

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit


# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
DATA_FILE          = DATA_RAW / "fantasy_data.json"
METRICS_FILE       = DATA_PROC / "model_metrics.json"
PRED_FILE          = DATA_PROC / "player_predictions.json"
DEF_PROFILES_FILE  = DATA_PROC / "defensive_profiles.json"
GAMES_RAW_FILE     = APP_JS_CONFIG / "data.js"

RIDGE_ALPHA     = 1.0
MIN_GAMES_FIT   = 5
MIN_GAMES_PRED  = 3
EWMA_SPAN       = 5
TRAIN_RATIO     = 0.70
N_SPLITS        = 5
WEIGHT_STEP     = 0.05
DVP_SHORT_SPAN  = 5
DVP_LONG_WINDOW = 20
DVP_MIN_GAMES   = 3

MIN_MINUTES     = 5.0
MIN_VALUATION   = -10.0
MAX_VALUATION   = 60.0

# v4.2: μόνο last game στο 2026+ → predict
MIN_PREDICT_SEASON = 2026

SEASON_WEIGHTS = {2022: 0.3, 2023: 0.6, 2024: 1.0, 2025: 1.0, 2026: 0.0}

FEATURE_NAMES = [
    "ewma5_pdk", "roll3_pdk", "roll5_pdk", "season_avg",
    "ewma5_min", "ewma5_fouls", "pdk_std5", "min_trend", "pdk_trend",
    "games_count",
    "dvp_opp_vs_pos",      # short EWMA (expanding)
    "dvp_opp_vs_pos_l20",  # long rolling 20 (expanding)
    "opp_adj_def",         # raw adj_final
    "opp_adj_z",           # z-score
    "opp_pooled_def",
    "opp_quality",
    "is_home",
]

GB_PARAM_GRID = [
    {"n_estimators": 200, "max_depth": 3, "learning_rate": 0.05},
    {"n_estimators": 200, "max_depth": 3, "learning_rate": 0.10},
    {"n_estimators": 300, "max_depth": 4, "learning_rate": 0.05},
]

QUALITY_ENCODE = {"very_low": 0, "low": 1, "medium": 2, "high": 3}

TEAM_FULL_TO_SHORT = {
    "ANADOLU EFES ISTANBUL":      "ULK",
    "ARMANI OLIMPIA MILAN":       "MIL",
    "BASKONIA VITORIA-GASTEIZ":   "BAS",
    "BESIKTAS ISTANBUL":          "BES",
    "CRVENA ZVEZDA BELGRADE":     "RED",
    "DUBAI BASKETBALL":           "DUB",
    "FC BARCELONA":               "BAR",
    "FC BAYERN MUNICH":           "MUN",
    "FENERBAHCE ISTANBUL":        "IST",
    "HAPOEL IBI TEL AVIV":        "HTA",
    "LDLC ASVEL VILLEURBANNE":    "ASV",
    "MACCABI RAPYD TEL AVIV":     "TEL",
    "OLYMPIACOS PIRAEUS":         "OLY",
    "PANATHINAIKOS AKTOR ATHENS": "PAN",
    "PARIS BASKETBALL":           "PRS",
    "PARTIZAN MOZZART BELGRADE":  "PAR",
    "REAL MADRID":                "MAD",
    "VALENCIA BASKET":            "PAM",
    "VIRTUS BOLOGNA":             "VIR",
    "ZALGIRIS KAUNAS":            "ZAL",
}


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def ewma_last(values, span):
    if not values:
        return 0.0
    alpha = 2.0 / (span + 1)
    r = float(values[0])
    for v in values[1:]:
        r = alpha * float(v) + (1.0 - alpha) * r
    return r


def safe_slope(values):
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    xm = sum(xs) / n
    ym = sum(values) / n
    num = sum((xi - xm) * (yi - ym) for xi, yi in zip(xs, values))
    den = sum((xi - xm) ** 2 for xi in xs)
    if den == 0:
        return 0.0
    slope = num / den
    norm = slope / abs(ym) if ym != 0 else slope
    return max(-2.0, min(2.0, norm))


def std_pop(values):
    if not values:
        return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / len(values))


def build_features(prior_played, opp_ctx=None):
    """17 features. opp_ctx: 7 κλειδιά."""
    if len(prior_played) < MIN_GAMES_FIT:
        return None

    pdks  = [float(g.get("pdk", 0)) for g in prior_played]
    mins  = [float(g.get("min", 0)) for g in prior_played]
    fouls = [float(g.get("pf", 0)) for g in prior_played]

    last3 = pdks[-3:] if len(pdks) >= 3 else pdks
    last5 = pdks[-5:] if len(pdks) >= 5 else pdks

    base = {
        "ewma5_pdk":   ewma_last(pdks, EWMA_SPAN),
        "roll3_pdk":   sum(last3) / len(last3),
        "roll5_pdk":   sum(last5) / len(last5),
        "season_avg":  sum(pdks) / len(pdks),
        "ewma5_min":   ewma_last(mins, EWMA_SPAN),
        "ewma5_fouls": ewma_last(fouls, EWMA_SPAN),
        "pdk_std5":    std_pop(last5),
        "min_trend":   safe_slope(mins[-5:] if len(mins) >= 2 else mins),
        "pdk_trend":   safe_slope(pdks[-5:] if len(pdks) >= 2 else pdks),
        "games_count": min(len(prior_played), 30) / 30.0,
    }

    if opp_ctx is None:
        base["dvp_opp_vs_pos"]     = 0.0
        base["dvp_opp_vs_pos_l20"] = 0.0
        base["opp_adj_def"]        = 0.0
        base["opp_adj_z"]          = 0.0
        base["opp_pooled_def"]     = 0.0
        base["opp_quality"]        = 0
        base["is_home"]            = 0.0
    else:
        base["dvp_opp_vs_pos"]     = float(opp_ctx.get("dvp_opp_vs_pos", 0.0))
        base["dvp_opp_vs_pos_l20"] = float(opp_ctx.get("dvp_opp_vs_pos_l20", 0.0))
        base["opp_adj_def"]        = float(opp_ctx.get("opp_adj_def", 0.0))
        base["opp_adj_z"]          = float(opp_ctx.get("opp_adj_z", 0.0))
        base["opp_pooled_def"]     = float(opp_ctx.get("opp_pooled_def", 0.0))
        base["opp_quality"]        = int(opp_ctx.get("opp_quality", 0))
        base["is_home"]            = 1.0 if opp_ctx.get("is_home") else 0.0

    return base


# ─────────────────────────────────────────────────────────────
# LOADERS
# ─────────────────────────────────────────────────────────────

def load_data(path=DATA_FILE):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return d["players"], d.get("metadata", {})


def load_defensive_profiles(path=DEF_PROFILES_FILE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compute_league_mean_pooled(profiles):
    vals = []
    for season, teams in profiles.items():
        if not isinstance(teams, dict):
            continue
        for code, entry in teams.items():
            pooled = entry.get("pooled_2024_2025") or {}
            af = pooled.get("adj_final")
            if af is not None:
                vals.append(float(af))
    return float(np.mean(vals)) if vals else 0.0


def lookup_opp_def(profiles, season, opp_code, league_mean_pooled=0.0):
    """(opp_adj_raw, opp_adj_z, opp_pooled, opp_quality)."""
    entry = profiles.get(str(season), {}).get(opp_code)
    if entry is None:
        return 0.0, 0.0, float(league_mean_pooled), 0

    adj    = entry.get("adjusted", {}) or {}
    sample = entry.get("sample", {}) or {}
    pooled = entry.get("pooled_2024_2025", {}) or {}

    use_fallback = bool(sample.get("use_pooled_fallback", False))

    if use_fallback:
        opp_raw = float(pooled.get("adj_final", league_mean_pooled))
        opp_z   = float(pooled.get("zscore_pooled", 0.0))
    else:
        opp_raw = float(adj.get("adj_final", league_mean_pooled))
        opp_z   = float(adj.get("zscore_adj_final", 0.0))

    opp_pooled = float(pooled.get("adj_final", league_mean_pooled))
    q_label = sample.get("sample_quality", "very_low")
    opp_q = int(QUALITY_ENCODE.get(q_label, 0))
    return opp_raw, opp_z, opp_pooled, opp_q


def load_games_raw(path=GAMES_RAW_FILE):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"GAMES_RAW file not found: {path}")
    text = p.read_text(encoding="utf-8")
    m = re.search(r"GAMES_RAW\s*=\s*(\[.*?\])\s*;", text, re.DOTALL)
    if not m:
        raise ValueError("GAMES_RAW pattern δεν βρέθηκε")
    raw = re.sub(r",\s*\]", "]", m.group(1))
    return json.loads(raw)


def build_games_index(games_raw):
    idx = {}
    skipped = 0
    for row in games_raw:
        if len(row) < 7:
            skipped += 1
            continue
        rnd = int(row[0])
        season = int(row[2][:4])
        home_short = TEAM_FULL_TO_SHORT.get(row[5])
        away_short = TEAM_FULL_TO_SHORT.get(row[6])
        if home_short is None or away_short is None:
            skipped += 1
            continue
        idx[(home_short, season, rnd)] = {"opp": away_short, "is_home": True}
        idx[(away_short, season, rnd)] = {"opp": home_short, "is_home": False}
    return idx, skipped


# ─────────────────────────────────────────────────────────────
# DvP TABLE — dual window
# ─────────────────────────────────────────────────────────────

def build_dvp_table(players):
    rows = []
    all_vals = []
    for p in players:
        pos = p["position_norm"]
        if pos not in ("G", "F", "C"):
            continue
        for g in p["game_logs"]:
            if float(g.get("min", 0)) < MIN_MINUTES:
                continue
            if g.get("opp_code") is None:
                continue
            val = float(g.get("pdk", 0))
            if not (MIN_VALUATION <= val <= MAX_VALUATION):
                continue
            rows.append({
                "season":   g["season"],
                "gamecode": g["gamecode"],
                "opp_code": g["opp_code"],
                "pos":      pos,
                "val":      val,
            })
            all_vals.append(val)

    league_avg = float(np.mean(all_vals)) if all_vals else 8.0
    rows.sort(key=lambda r: (r["season"], r["gamecode"]))

    history = defaultdict(list)
    dvp_map_short = {}
    dvp_map_long = {}

    for r in rows:
        key = (r["opp_code"], r["pos"])
        h = history[key]
        if len(h) >= DVP_MIN_GAMES:
            short_val = ewma_last(h[-DVP_SHORT_SPAN:], DVP_SHORT_SPAN)
            window = h[-DVP_LONG_WINDOW:]
            long_val = sum(window) / len(window)
        else:
            short_val = league_avg
            long_val = league_avg
        dvp_map_short[(r["season"], r["gamecode"], r["opp_code"], r["pos"])] = short_val
        dvp_map_long[(r["season"], r["gamecode"], r["opp_code"], r["pos"])] = long_val
        history[key].append(r["val"])

    dvp_hist_short = {k: list(v) for k, v in history.items()}
    dvp_hist_long = {k: list(v) for k, v in history.items()}
    print(f"  DvP table: {len(dvp_map_short)} entries  |  league_avg={league_avg:.2f}")
    return dvp_map_short, dvp_map_long, dvp_hist_short, dvp_hist_long, league_avg


def get_dvp_short(dvp_hist_short, opp_code, pos, league_avg):
    h = dvp_hist_short.get((opp_code, pos), [])
    if len(h) < DVP_MIN_GAMES:
        return league_avg
    return ewma_last(h[-DVP_SHORT_SPAN:], DVP_SHORT_SPAN)


def get_dvp_long(dvp_hist_long, opp_code, pos, league_avg):
    h = dvp_hist_long.get((opp_code, pos), [])
    if len(h) < DVP_MIN_GAMES:
        return league_avg
    window = h[-DVP_LONG_WINDOW:]
    return sum(window) / len(window)


# ─────────────────────────────────────────────────────────────
# TRAINING ROWS
# ─────────────────────────────────────────────────────────────

def build_training_rows(players, profiles, dvp_map_short, dvp_map_long,
                        league_mean_pooled, league_avg_dvp):
    X_rows, y_vals, pos_list, meta, sw_list = [], [], [], [], []
    skipped_by_weight = 0
    lookup_hit = 0
    lookup_miss = 0

    for p in players:
        pos = p["position_norm"]
        if pos not in ("G", "F", "C"):
            continue
        logs = sorted(p.get("game_logs", []),
                      key=lambda g: (g["season"], g["gamecode"]))
        prior = []
        for game in logs:
            if float(game.get("min", 0)) > 0:
                if len(prior) >= MIN_GAMES_FIT:
                    season = int(game["season"])
                    w = SEASON_WEIGHTS.get(season, 0.0)
                    opp_code = game.get("opp_code")

                    dvp_key = (game["season"], game["gamecode"], opp_code, pos)
                    dvp_s = dvp_map_short.get(dvp_key, league_avg_dvp)
                    dvp_l = dvp_map_long.get(dvp_key, league_avg_dvp)

                    adj_raw, adj_z, pooled, q = lookup_opp_def(
                        profiles, season, opp_code, league_mean_pooled
                    )

                    if opp_code and str(season) in profiles \
                            and opp_code in profiles.get(str(season), {}):
                        lookup_hit += 1
                    else:
                        lookup_miss += 1

                    opp_ctx = {
                        "dvp_opp_vs_pos":     dvp_s,
                        "dvp_opp_vs_pos_l20": dvp_l,
                        "opp_adj_def":        adj_raw,
                        "opp_adj_z":          adj_z,
                        "opp_pooled_def":     pooled,
                        "opp_quality":        q,
                        "is_home":            bool(game.get("is_home")),
                    }

                    feats = build_features(prior, opp_ctx)
                    if feats is not None:
                        target = float(game.get("pdk", 0))
                        if MIN_VALUATION <= target <= MAX_VALUATION:
                            row = [feats[f] for f in FEATURE_NAMES]
                            if all(math.isfinite(v) for v in row):
                                if w > 0:
                                    X_rows.append(row)
                                    y_vals.append(target)
                                    pos_list.append(pos)
                                    sw_list.append(w)
                                    meta.append({
                                        "season": season,
                                        "gamecode": game["gamecode"],
                                        "player_code": p["player_code"],
                                    })
                                else:
                                    skipped_by_weight += 1
                prior.append(game)

    X = np.array(X_rows, dtype=float) if X_rows \
        else np.zeros((0, len(FEATURE_NAMES)))
    y = np.array(y_vals, dtype=float)
    pos_arr = np.array(pos_list)
    sw = np.array(sw_list, dtype=float)

    print(f"  Training rows: {len(X)}  (skipped by weight=0: {skipped_by_weight})")
    print(f"  Opp lookup: hit={lookup_hit}  miss={lookup_miss}")
    return X, y, pos_arr, meta, sw


# ─────────────────────────────────────────────────────────────
# RIDGE / SCALING / OOF / GRID
# ─────────────────────────────────────────────────────────────

def ridge_fit(X, y, alpha=RIDGE_ALPHA, sample_weight=None):
    Xb = np.hstack([np.ones((X.shape[0], 1)), X])
    if sample_weight is None:
        sw = np.ones((X.shape[0], 1), dtype=float)
    else:
        sw = np.asarray(sample_weight, dtype=float).reshape(-1, 1)
    k = Xb.shape[1]
    reg = alpha * np.eye(k)
    reg[0, 0] = 0.0
    with np.errstate(all="ignore"):
        A = (Xb * sw).T @ Xb + reg
        b = (Xb * sw).T @ y
    try:
        return np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(A, b, rcond=None)[0]


def ridge_predict(X, w):
    Xb = np.hstack([np.ones((X.shape[0], 1)), X])
    with np.errstate(all="ignore"):
        return Xb @ w


def z_scale(X_train, X_other=None):
    mu = X_train.mean(axis=0)
    sig = X_train.std(axis=0)
    sig[sig == 0] = 1.0
    Xtr = np.clip((X_train - mu) / sig, -5.0, 5.0)
    if X_other is None:
        return Xtr, mu, sig
    return Xtr, np.clip((X_other - mu) / sig, -5.0, 5.0), mu, sig


def oof_predictions(X, y, gb_params, sample_weight=None, n_splits=N_SPLITS):
    tscv = TimeSeriesSplit(n_splits=n_splits)
    oof_ridge = np.full(len(X), np.nan)
    oof_gb    = np.full(len(X), np.nan)
    oof_ma    = np.full(len(X), np.nan)
    ma_idx = FEATURE_NAMES.index("roll5_pdk")
    for train_idx, val_idx in tscv.split(X):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr = y[train_idx]
        sw_tr = sample_weight[train_idx] if sample_weight is not None else None
        Xtr_s, Xval_s, _, _ = z_scale(X_tr, X_val)
        w = ridge_fit(Xtr_s, y_tr, sample_weight=sw_tr)
        oof_ridge[val_idx] = ridge_predict(Xval_s, w)
        gb = GradientBoostingRegressor(**gb_params, random_state=42)
        gb.fit(X_tr, y_tr, sample_weight=sw_tr)
        oof_gb[val_idx] = gb.predict(X_val)
        oof_ma[val_idx] = X_val[:, ma_idx]
    mask = ~np.isnan(oof_ridge)
    return {"ridge": oof_ridge, "gb": oof_gb, "ma": oof_ma}, mask


def grid_search_gb(X, y, sample_weight=None):
    tscv = TimeSeriesSplit(n_splits=3)
    best, best_mae = None, float("inf")
    for params in GB_PARAM_GRID:
        preds = np.full(len(X), np.nan)
        for train_idx, val_idx in tscv.split(X):
            sw_tr = sample_weight[train_idx] if sample_weight is not None else None
            gb = GradientBoostingRegressor(**params, random_state=42)
            gb.fit(X[train_idx], y[train_idx], sample_weight=sw_tr)
            preds[val_idx] = gb.predict(X[val_idx])
        mask = ~np.isnan(preds)
        mae = float(np.mean(np.abs(y[mask] - preds[mask])))
        print(f"    GB {params} → OOF MAE = {mae:.3f}")
        if mae < best_mae:
            best_mae, best = mae, params
    print(f"    → best GB: {best}  (MAE={best_mae:.3f})")
    return best


def grid_search_weights(oof, mask, y):
    y_m = y[mask]
    a = oof["ridge"][mask]
    b = oof["gb"][mask]
    c = oof["ma"][mask]
    best_mae = float("inf")
    best_w = (1/3, 1/3, 1/3)
    steps = np.arange(0.0, 1.0 + 1e-9, WEIGHT_STEP)
    for wA in steps:
        for wB in steps:
            wC = 1.0 - wA - wB
            if wC < -1e-9:
                continue
            pred = wA * a + wB * b + wC * c
            mae = float(np.mean(np.abs(y_m - pred)))
            if mae < best_mae:
                best_mae = mae
                best_w = (round(wA, 2), round(wB, 2), round(wC, 2))
    return best_w, best_mae


# ─────────────────────────────────────────────────────────────
# TRAIN ONE POSITION
# ─────────────────────────────────────────────────────────────

def train_position(X, y, sample_weight, pos_name):
    n = len(X)
    if n < 100:
        print(f"  [{pos_name}] too few samples ({n}) — skipping")
        return None
    split = int(n * TRAIN_RATIO)
    X_tr, X_te = X[:split], X[split:]
    y_tr, y_te = y[:split], y[split:]
    sw_tr = sample_weight[:split]
    print(f"  [{pos_name}] n={n}  train={len(X_tr)}  test={len(X_te)}")

    print(f"  [{pos_name}] grid search GB …")
    best_gb_params = grid_search_gb(X_tr, y_tr, sample_weight=sw_tr)

    print(f"  [{pos_name}] OOF predictions …")
    oof, mask = oof_predictions(X_tr, y_tr, best_gb_params, sample_weight=sw_tr)
    print(f"  [{pos_name}] OOF coverage: {mask.sum()}/{len(X_tr)}")

    print(f"  [{pos_name}] weight grid search …")
    best_w, oof_mae = grid_search_weights(oof, mask, y_tr)
    print(f"  [{pos_name}] best weights: Ridge={best_w[0]}  GB={best_w[1]}  "
          f"MA={best_w[2]}  (OOF MAE={oof_mae:.3f})")

    Xtr_s, mu, sig = z_scale(X_tr)
    w_ridge = ridge_fit(Xtr_s, y_tr, sample_weight=sw_tr)

    gb = GradientBoostingRegressor(**best_gb_params, random_state=42)
    gb.fit(X_tr, y_tr, sample_weight=sw_tr)

    Xte_s = np.clip((X_te - mu) / sig, -5.0, 5.0)
    pred_ridge = ridge_predict(Xte_s, w_ridge)
    pred_gb = gb.predict(X_te)
    pred_ma = X_te[:, FEATURE_NAMES.index("roll5_pdk")]

    wA, wB, wC = best_w
    pred = wA * pred_ridge + wB * pred_gb + wC * pred_ma
    pred = np.maximum(pred, 0.0)

    mae = float(np.mean(np.abs(y_te - pred)))
    rmse = float(np.sqrt(np.mean((y_te - pred) ** 2)))
    baseline_mae = float(np.mean(np.abs(y_te - y_tr.mean())))
    print(f"  [{pos_name}] TEST: MAE={mae:.3f}  RMSE={rmse:.3f}  "
          f"baseline={baseline_mae:.3f}  improve={100*(1-mae/baseline_mae):.1f}%")

    return {
        "ridge_w":       w_ridge.tolist(),
        "ridge_mu":      mu.tolist(),
        "ridge_sig":     sig.tolist(),
        "gb_params":     best_gb_params,
        "gb_model":      gb,
        "weights":       {"ridge": wA, "gb": wB, "ma": wC},
        "n_train":       int(len(X_tr)),
        "n_test":        int(len(X_te)),
        "mae":           round(mae, 3),
        "rmse":          round(rmse, 3),
        "baseline_mae":  round(baseline_mae, 3),
        "residual_std":  round(rmse, 3),   # std των residuals ≈ RMSE (για test set)
        "improvement_pct": round(100 * (1 - mae / baseline_mae), 1),
        "oof_mae":       round(oof_mae, 3),
    }


# ─────────────────────────────────────────────────────────────
# NEXT OPPONENT + PREDICT
# ─────────────────────────────────────────────────────────────

def find_next_opponent(player, games_index):
    logs = sorted(player.get("game_logs", []),
                  key=lambda g: (g["season"], g["gamecode"]))
    played = [g for g in logs if float(g.get("min", 0)) > 0]
    if not played:
        return None
    last = played[-1]
    team = last.get("team_code")
    season = int(last["season"])
    rnd = last.get("round")
    if team is None or rnd is None:
        return None
    for r in (rnd + 1, rnd + 2, rnd + 3):
        hit = games_index.get((team, season, r))
        if hit is not None:
            return hit
    return None


def predict_player(p, model, profiles, games_index, dvp_hist_short,
                   dvp_hist_long, league_mean_pooled, league_avg_dvp):
    logs = sorted(p.get("game_logs", []),
                  key=lambda g: (g["season"], g["gamecode"]))
    played = [g for g in logs if float(g.get("min", 0)) > 0]
    if len(played) < MIN_GAMES_PRED:
        return None

    # v4.2: ΜΟΝΟ ενεργοί παίκτες (last game στο 2026+)
    last_season = max(g["season"] for g in played)
    if last_season < MIN_PREDICT_SEASON:
        return None

    next_info = find_next_opponent(p, games_index)
    pos = p["position_norm"]

    if next_info is not None:
        last = played[-1]
        season = int(last["season"])
        opp_code = next_info["opp"]
        adj_raw, adj_z, pooled, q = lookup_opp_def(
            profiles, season, opp_code, league_mean_pooled
        )
        dvp_s = get_dvp_short(dvp_hist_short, opp_code, pos, league_avg_dvp)
        dvp_l = get_dvp_long(dvp_hist_long, opp_code, pos, league_avg_dvp)
        opp_ctx = {
            "dvp_opp_vs_pos":     dvp_s,
            "dvp_opp_vs_pos_l20": dvp_l,
            "opp_adj_def":        adj_raw,
            "opp_adj_z":          adj_z,
            "opp_pooled_def":     pooled,
            "opp_quality":        q,
            "is_home":            bool(next_info["is_home"]),
        }
        next_opp_label = opp_code
        next_is_home = bool(next_info["is_home"])
    else:
        # Fallback: neutral defaults (league averages, όχι 0)
        opp_ctx = {
            "dvp_opp_vs_pos":     league_avg_dvp,
            "dvp_opp_vs_pos_l20": league_avg_dvp,
            "opp_adj_def":        league_mean_pooled,
            "opp_adj_z":          0.0,
            "opp_pooled_def":     league_mean_pooled,
            "opp_quality":        0,
            "is_home":            False,
        }
        next_opp_label = None
        next_is_home = None

    feats = build_features(played, opp_ctx)
    if feats is None:
        return None

    fvec = np.array([[feats[f] for f in FEATURE_NAMES]])
    mu = np.array(model["ridge_mu"])
    sig = np.array(model["ridge_sig"])
    fvec_s = np.clip((fvec - mu) / sig, -5.0, 5.0)
    p_ridge = float(ridge_predict(fvec_s, np.array(model["ridge_w"]))[0])
    p_gb = float(model["gb_model"].predict(fvec)[0])
    p_ma = float(feats["roll5_pdk"])

    w = model["weights"]
    xpdk = w["ridge"] * p_ridge + w["gb"] * p_gb + w["ma"] * p_ma
    xpdk = max(0.0, xpdk)

    pdks = [float(g.get("pdk", 0)) for g in played]
    sorted_pdks = sorted(pdks)
    n = len(sorted_pdks)
    floor_pdk = sorted_pdks[max(0, int(n * 0.20))]
    ceiling_pdk = sorted_pdks[min(n - 1, int(n * 0.80))]
    mean_pdk = sum(pdks) / len(pdks)
    cv = (std_pop(pdks) / mean_pdk * 100) if mean_pdk > 0 else 0.0

    mt = feats["min_trend"]
    if mt > 0.05:
        trend = "Rising"
    elif mt < -0.05:
        trend = "Falling"
    else:
        trend = "Stable"

    conf = "high" if n >= 15 else "medium" if n >= 7 else "low"

    return {
        "xpdk_v4_2":          round(xpdk, 2),
        "p_ridge":            round(p_ridge, 2),
        "p_gb":               round(p_gb, 2),
        "p_ma":               round(p_ma, 2),
        "floor_pdk":          round(floor_pdk, 1),
        "ceiling_pdk":        round(ceiling_pdk, 1),
        "cv":                 round(cv, 1),
        "ewma5_pdk":          round(feats["ewma5_pdk"], 2),
        "min_trend_label":    trend,
        "confidence":         conf,
        "next_opp":           next_opp_label,
        "next_is_home":       next_is_home,
        "opp_adj_def":        round(feats["opp_adj_def"], 3),
        "opp_adj_z":          round(feats["opp_adj_z"], 3),
        "opp_pooled_def":     round(feats["opp_pooled_def"], 2),
        "opp_quality":        int(feats["opp_quality"]),
        "dvp_opp_vs_pos":     round(feats["dvp_opp_vs_pos"], 3),
        "dvp_opp_vs_pos_l20": round(feats["dvp_opp_vs_pos_l20"], 3),
    }


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("EUROLEAGUE FANTASY — TRAIN MODEL v4.2")
    print(f"  ({len(FEATURE_NAMES)} features, dual DvP, filter>=2026)")
    print("=" * 60)
    print(f"SEASON_WEIGHTS = {SEASON_WEIGHTS}")
    print(f"MIN_PREDICT_SEASON = {MIN_PREDICT_SEASON}\n")

    players, metadata = load_data()
    print(f"Loaded {len(players)} players")

    print("\n[1/7] Loading defensive_profiles_v2 …")
    profiles = load_defensive_profiles()
    league_mean_pooled = compute_league_mean_pooled(profiles)
    print(f"  league_mean_pooled = {league_mean_pooled:.3f}")

    print("\n[2/7] Loading GAMES_RAW …")
    games_raw = load_games_raw()
    games_index, skipped = build_games_index(games_raw)
    print(f"  games_index: {len(games_index)} entries (skipped {skipped})")

    print("\n[3/7] Building DvP tables (dual window) …")
    dvp_map_short, dvp_map_long, dvp_hist_short, dvp_hist_long, league_avg_dvp = \
        build_dvp_table(players)

    print("\n[4/7] Building training rows …")
    X, y, positions, meta, sample_weight = build_training_rows(
        players, profiles, dvp_map_short, dvp_map_long,
        league_mean_pooled, league_avg_dvp
    )

    print("\n[5/7] Training per position …")
    models = {}
    all_metrics = {}
    for pos in ("G", "F", "C"):
        mask = positions == pos
        X_pos, y_pos, sw_pos = X[mask], y[mask], sample_weight[mask]
        print(f"\n  === {pos} ===")
        result = train_position(X_pos, y_pos, sw_pos, pos)
        if result is not None:
            models[pos] = result
            all_metrics[pos] = {
                k: v for k, v in result.items()
                if k not in ("gb_model", "ridge_w", "ridge_mu", "ridge_sig")
            }

    print("\n[6/7] Predicting for all players …")
    n_pred = 0
    n_no_opp = 0
    n_filtered_historical = 0
    for p in players:
        pos = p["position_norm"]
        if pos not in models:
            continue

        # Count filtered
        logs = sorted(p.get("game_logs", []),
                      key=lambda g: (g["season"], g["gamecode"]))
        played = [g for g in logs if float(g.get("min", 0)) > 0]
        if len(played) >= MIN_GAMES_PRED:
            last_season = max(g["season"] for g in played)
            if last_season < MIN_PREDICT_SEASON:
                n_filtered_historical += 1
                continue

        pred = predict_player(p, models[pos], profiles, games_index,
                              dvp_hist_short, dvp_hist_long,
                              league_mean_pooled, league_avg_dvp)
        if pred is not None:
            p.update(pred)
            n_pred += 1
            if pred["next_opp"] is None:
                n_no_opp += 1

    print(f"  Predictions for {n_pred} players")
    print(f"  Φιλτραρίστηκαν (historical, <{MIN_PREDICT_SEASON}): "
          f"{n_filtered_historical}")
    if n_pred:
        print(f"  Χωρίς next opp lookup: {n_no_opp}  "
              f"({100*n_no_opp/n_pred:.1f}%)")

    print("\n[7/7] Writing outputs …")
    metrics_out = {
        "generated_at":       datetime.now().isoformat(),
        "model_version":      "v4.2",
        "feature_names":      FEATURE_NAMES,
        "season_weights":     SEASON_WEIGHTS,
        "min_predict_season": MIN_PREDICT_SEASON,
        "league_mean_pooled": round(league_mean_pooled, 3),
        "league_avg_dvp":     round(league_avg_dvp, 3),
        "per_position":       all_metrics,
    }
    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics_out, f, ensure_ascii=False, indent=2)
    print(f"  → {METRICS_FILE}")

    preds_out = []
    for p in players:
        if "xpdk_v4_2" not in p:
            continue
        preds_out.append({
            "player_code":        p["player_code"],
            "player":             p["player"],
            "team":               p["team"],
            "position_norm":      p["position_norm"],
            "gp":                 p["gp"],
            "pdk":                p["pdk"],
            "xpdk_v4_2":          p["xpdk_v4_2"],
            "p_ridge":            p["p_ridge"],
            "p_gb":               p["p_gb"],
            "p_ma":               p["p_ma"],
            "floor_pdk":          p["floor_pdk"],
            "ceiling_pdk":        p["ceiling_pdk"],
            "cv":                 p["cv"],
            "ewma5_pdk":          p["ewma5_pdk"],
            "min_trend_label":    p["min_trend_label"],
            "confidence":         p["confidence"],
            "next_opp":           p["next_opp"],
            "next_is_home":       p["next_is_home"],
            "opp_adj_def":        p["opp_adj_def"],
            "opp_adj_z":          p["opp_adj_z"],
            "opp_pooled_def":     p["opp_pooled_def"],
            "opp_quality":        p["opp_quality"],
            "dvp_opp_vs_pos":     p["dvp_opp_vs_pos"],
            "dvp_opp_vs_pos_l20": p["dvp_opp_vs_pos_l20"],
        })
    with open(PRED_FILE, "w", encoding="utf-8") as f:
        json.dump(preds_out, f, ensure_ascii=False, indent=2)
    print(f"  → {PRED_FILE}  ({len(preds_out)} players)")

    print("\n" + "=" * 60)
    print("SUMMARY v4.2")
    print("=" * 60)
    for pos, m in all_metrics.items():
        print(f"  {pos}:  MAE={m['mae']:.2f}  RMSE={m['rmse']:.2f}  "
              f"baseline={m['baseline_mae']:.2f}  improve={m['improvement_pct']}%")
    print("=" * 60)


if __name__ == "__main__":
    main()