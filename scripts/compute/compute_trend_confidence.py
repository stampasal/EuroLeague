#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compute_trend_confidence.py
---------------------------
Υπολογίζει Trend (↑/→/↓) και Confidence (🟢/🟡/🔴) για κάθε predicted παίκτη.

Input:
  ../json/player_predictions_v4_2.json   (xp, pdk, gp, opp_quality)
  ../json/fantasy_data.json              (game_logs για slope, cv, avg)
  ../json/model_metrics_v4_2.json        (residual_std ανά position)

Output:
  ../../js/data/player-trend-confidence.js
"""
import json
import math
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import DATA_RAW, DATA_PROC, APP_JS_DATA

PRED_FILE    = DATA_PROC / "player_predictions.json"
FANTASY_FILE = DATA_RAW / "fantasy_data.json"
METRICS_FILE = DATA_PROC / "model_metrics.json"
OUT_FILE     = APP_JS_DATA / "player-trend-confidence.js"

CURRENT_SEASON = 2026


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def std_pop(values):
    if not values:
        return 0.0
    m = sum(values) / len(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / len(values))


def safe_slope(values):
    """Normalized slope (ίδιο με train_model_v4_2)."""
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


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else 0.0


# ─────────────────────────────────────────────────────────────
# Trend (composite: A + C + D)
# ─────────────────────────────────────────────────────────────

def compute_trend(xp, pdks):
    """
    xp    = πρόβλεψη επόμενου αγώνα
    pdks  = λίστα πραγματικών PIR (χρονολογικά, ascending)
    """
    if not pdks or xp is None:
        return {"label": "Stable", "score": 0.0, "icon": "→"}

    last3 = pdks[-3:] if len(pdks) >= 3 else pdks
    last5 = pdks[-5:] if len(pdks) >= 5 else pdks
    avg3 = mean(last3)
    season_avg = mean(pdks)

    # A: xP vs avg3 (relative)
    denom_a = max(abs(avg3), 3.0)
    A = (xp - avg3) / denom_a

    # C: slope last 5 (normalized)
    C = safe_slope(last5)

    # D: xP vs season_avg (relative)
    denom_d = max(abs(season_avg), 3.0)
    D = (xp - season_avg) / denom_d

    score = 0.5 * A + 0.3 * C + 0.2 * D

    if score >= 0.12:
        label = "Rising";  icon = "↑"
    elif score <= -0.12:
        label = "Falling"; icon = "↓"
    else:
        label = "Stable";  icon = "→"

    return {"label": label, "score": round(score, 3), "icon": icon}


# ─────────────────────────────────────────────────────────────
# Confidence (composite: consistency + sample + opp_quality)
# ─────────────────────────────────────────────────────────────

def compute_confidence(pdks, games_2026, opp_quality):
    """
    pdks        = λίστα πραγματικών PIR
    games_2026  = πόσα games έχει παίξει φέτος
    opp_quality = 0-3 από v4.2 (ποιότητα δεδομένων αντιπάλου)
    """
    # A: consistency (cv)
    m = mean(pdks)
    sd = std_pop(pdks)
    cv = (sd / m) if m > 0 else 2.0
    if cv < 0.4:
        A = 3
    elif cv < 0.7:
        A = 2
    elif cv < 1.0:
        A = 1
    else:
        A = 0

    # B: sample size
    if games_2026 >= 20:
        B = 3
    elif games_2026 >= 10:
        B = 2
    elif games_2026 >= 5:
        B = 1
    else:
        B = 0

    # ΣΗΜΕΙΩΣΗ: Το opp_quality είναι πάντα 0 (limitation των defensive_profiles_v2)
    # → δεν το χρησιμοποιούμε. Μόνο A (cv) + B (sample size).

    score = (A + B) / 2.0

    if score >= 1.5:
        label = "high";   emoji = "🟢"
    elif score >= 0.8:
        label = "medium"; emoji = "🟡"
    else:
        label = "low";    emoji = "🔴"

    return {
        "label": label,
        "emoji": emoji,
        "score": round(score, 2),
        "components": {"cv": round(cv, 2), "A": A, "B": B},
    }


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("COMPUTE TREND + CONFIDENCE")
    print("=" * 60)

    with open(PRED_FILE, encoding="utf-8") as f:
        preds = json.load(f)
    print(f"Predictions: {len(preds)}")

    with open(FANTASY_FILE, encoding="utf-8") as f:
        fantasy = json.load(f)
    fantasy_by_code = {str(p["player_code"]): p for p in fantasy["players"]}
    print(f"Fantasy players: {len(fantasy_by_code)}")

    with open(METRICS_FILE, encoding="utf-8") as f:
        metrics = json.load(f)
    residual_std = {
        pos: m.get("residual_std", 5.0)
        for pos, m in metrics.get("per_position", {}).items()
    }
    print(f"Residual std per position: {residual_std}")

    out = {}
    n_rising = 0
    n_falling = 0
    n_stable = 0
    n_conf = {"high": 0, "medium": 0, "low": 0}

    for pred in preds:
        code = str(pred["player_code"])
        name = pred["player"].strip().upper()
        pos = pred.get("position_norm", "G")
        xp = pred.get("xpdk_v4_2")
        opp_quality = pred.get("opp_quality", 0)

        fp = fantasy_by_code.get(code)
        if not fp:
            continue

        # Πάρε τα PIR από τα game logs 2026 (ή όλα αν δεν έχει 2026)
        logs = fp.get("game_logs", [])
        logs_2026 = [
            g for g in logs
            if int(g.get("season", 0)) >= CURRENT_SEASON
            and float(g.get("min", 0)) > 0
        ]
        # Για trend/cv θέλουμε τα 2026 (ή fallback σε όλα)
        use_logs = logs_2026 if len(logs_2026) >= 3 else [
            g for g in logs if float(g.get("min", 0)) > 0
        ]

        if not use_logs:
            continue

        pdks = [float(g.get("pdk", 0)) for g in use_logs]
        games_2026 = len(logs_2026)

        trend = compute_trend(xp, pdks)
        conf  = compute_confidence(pdks, games_2026, opp_quality)

        # residual_std για το position
        rstd = residual_std.get(pos, 5.0)

        out[name] = {
            "trend":       trend["label"],
            "trend_icon":  trend["icon"],
            "trend_score": trend["score"],
            "conf":        conf["label"],
            "conf_emoji":  conf["emoji"],
            "conf_score":  conf["score"],
            "residual_std": rstd,
        }

        if trend["label"] == "Rising":   n_rising += 1
        elif trend["label"] == "Falling": n_falling += 1
        else:                             n_stable += 1
        n_conf[conf["label"]] += 1

    js = "// Auto-generated by compute_trend_confidence.py\n"
    js += "window.PLAYER_TREND_CONFIDENCE = "
    js += json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    js += ";\n"

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(js, encoding="utf-8")

    print(f"\nTrend:       ↑ {n_rising}  → {n_stable}  ↓ {n_falling}")
    print(f"Confidence:  🟢 {n_conf['high']}  🟡 {n_conf['medium']}  🔴 {n_conf['low']}")
    print(f"→ {OUT_FILE}  ({OUT_FILE.stat().st_size/1024:.1f} KB)")
    print("=" * 60)


if __name__ == "__main__":
    main()
