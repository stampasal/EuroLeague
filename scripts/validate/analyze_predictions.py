#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_predictions.py
----------------------
Συγκρίνει logged predictions με πραγματικά αποτελέσματα.

Auto-detect: βρίσκει το round από το filename (R04 → 4).
Για κάθε prediction, ψάχνει το αντίστοιχο actual game_log στο fantasy_data.json
του ιδίου round.

Output:
  ../json/predictions_log/2026-R04_<timestamp>_report.json

Χρήση:
  py analyze_predictions.py                # τελευταίο log
  py analyze_predictions.py --all          # όλα τα logs
  py analyze_predictions.py --file X.json  # συγκεκριμένο
"""

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import DATA_RAW, OUTPUT_PRED_LOG
from statistics import mean


FANTASY_FILE = DATA_RAW / "fantasy_data.json"
LOG_DIR      = OUTPUT_PRED_LOG

STD_BY_POS = {"G": 7.56, "F": 6.58, "C": 7.33}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def extract_round_from_filename(filename):
    m = re.search(r"R(\d+)", filename)
    if m:
        return int(m.group(1))
    return None


def build_actuals_by_round(fantasy_data, target_round):
    """
    code -> pdk για game_logs με round == target_round
    (οπουδήποτε στο historical)
    """
    out = {}
    for p in fantasy_data["players"]:
        code = p.get("player_code")
        if not code:
            continue
        for g in p.get("game_logs", []):
            if g.get("round") == target_round and g.get("min", 0) > 0:
                out[code] = {
                    "pdk":       g.get("pdk"),
                    "min":       g.get("min"),
                    "opp_code":  g.get("opp_code"),
                    "is_home":   g.get("is_home"),
                    "team_code": g.get("team_code"),
                }
                break
    return out


def pearson(xs, ys):
    n = len(xs)
    if n < 5:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return round(num / (dx * dy), 4) if dx > 0 and dy > 0 else 0.0


def analyze_log(log_data, fantasy_data, verbose=True):
    preds = log_data.get("predictions", [])
    logged_at = log_data.get("logged_at", "?")
    round_num = log_data.get("round", None)

    if round_num is None:
        if verbose:
            print(f"  ⚠️  Λείπει round από το log")
        return None

    if verbose:
        print(f"\n▶ Log: {logged_at}")
        print(f"  Round: R{round_num}")
        print(f"  Total predictions: {len(preds)}")

    actuals = build_actuals_by_round(fantasy_data, round_num)
    if verbose:
        print(f"  Actuals found:  {len(actuals)}")

    matches = []
    for p in preds:
        code = p.get("player_code")
        predicted = p.get("xpdk_v4_2")
        if predicted is None or code is None:
            continue
        act = actuals.get(code)
        if act is None:
            continue

        actual = act.get("pdk")
        if actual is None:
            continue

        matches.append({
            "player_code": code,
            "player":      p.get("player"),
            "position":    p.get("position_norm"),
            "predicted":   predicted,
            "actual":      actual,
            "error":       actual - predicted,
            "abs_error":   abs(actual - predicted),
            "next_opp":    p.get("next_opp"),
        })

    if not matches:
        if verbose:
            print("  ❌ Δεν βρέθηκαν matches (πιθανόν δεν έχουν παιχτεί τα ματς)")
        return None

    errors = [m["abs_error"] for m in matches]
    signed = [m["error"] for m in matches]
    sq = [m["error"] ** 2 for m in matches]

    mae = mean(errors)
    rmse = math.sqrt(mean(sq))
    bias = mean(signed)

    within_1std = 0
    within_2std = 0
    total_cal = 0
    for m in matches:
        pos = m.get("position")
        std = STD_BY_POS.get(pos)
        if std is None:
            continue
        total_cal += 1
        if abs(m["error"]) <= std:
            within_1std += 1
        if abs(m["error"]) <= 2 * std:
            within_2std += 1

    per_pos = {}
    for pos in ("G", "F", "C"):
        sub = [m for m in matches if m.get("position") == pos]
        if sub:
            per_pos[pos] = {
                "n":    len(sub),
                "mae":  round(mean(abs(m["error"]) for m in sub), 3),
                "bias": round(mean(m["error"] for m in sub), 3),
            }

    worst = sorted(matches, key=lambda m: -m["abs_error"])[:10]
    best = sorted(matches, key=lambda m: m["abs_error"])[:5]

    corr = pearson([m["predicted"] for m in matches],
                   [m["actual"] for m in matches])

    report = {
        "round":       round_num,
        "logged_at":   logged_at,
        "analyzed_at": datetime.now().isoformat(),
        "n_matches":   len(matches),
        "mae":         round(mae, 3),
        "rmse":        round(rmse, 3),
        "bias":        round(bias, 3),
        "correlation": corr,
        "calibration": {
            "within_1std":   round(within_1std / total_cal, 3) if total_cal else None,
            "within_2std":   round(within_2std / total_cal, 3) if total_cal else None,
            "n":             total_cal,
            "expected_1std": 0.68,
            "expected_2std": 0.95,
        },
        "per_position": per_pos,
        "top_worst":    worst,
        "top_best":     best,
    }

    if verbose:
        print(f"\n  n_matches:     {len(matches)}")
        print(f"  MAE:           {report['mae']}")
        print(f"  RMSE:          {report['rmse']}")
        print(f"  Bias:          {report['bias']}")
        print(f"  Correlation:   {corr}")
        cal = report["calibration"]
        print(f"\n  Calibration:")
        print(f"    Within 1std: {cal['within_1std']}  (expected 0.68)")
        print(f"    Within 2std: {cal['within_2std']}  (expected 0.95)")
        print(f"\n  Per position:")
        for pos, v in per_pos.items():
            print(f"    {pos}: n={v['n']:4d}, MAE={v['mae']}, bias={v['bias']}")
        print(f"\n  Top 5 worst:")
        for m in worst[:5]:
            print(f"    {m['player'][:28]:28s} "
                  f"pred={m['predicted']:6.2f} "
                  f"actual={m['actual']:6.2f} "
                  f"err={m['error']:+.2f}")

    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="Συγκεκριμένο log file")
    ap.add_argument("--all", action="store_true", help="Όλα τα logs")
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args()

    print("=" * 60)
    print("ANALYZE PREDICTIONS")
    print("=" * 60)

    if not FANTASY_FILE.exists():
        print(f"❌ {FANTASY_FILE} δεν βρέθηκε")
        return 1

    fantasy = load_json(FANTASY_FILE)

    if args.file:
        log_files = [Path(args.file)]
    elif args.all:
        log_files = sorted(LOG_DIR.glob("*_predictions.json"))
    else:
        log_files = sorted(LOG_DIR.glob("*_predictions.json"))[-1:]

    if not log_files:
        print(f"❌ Δεν βρέθηκαν log files στο {LOG_DIR}")
        print("   Τρέξε πρώτα: py log_predictions.py")
        return 1

    print(f"Found {len(log_files)} log file(s)")

    all_reports = []
    for log_file in log_files:
        log_data = load_json(log_file)
        report = analyze_log(log_data, fantasy, verbose=True)
        if report is not None:
            all_reports.append(report)

            if not args.no_save:
                out_name = log_file.stem.replace("_predictions", "_report") + ".json"
                out = log_file.with_name(out_name)
                with open(out, "w", encoding="utf-8") as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                print(f"\n  → {out.name}")

    if len(all_reports) > 1:
        print("\n" + "=" * 60)
        print("AGGREGATE")
        print("=" * 60)
        avg_mae = mean(r["mae"] for r in all_reports)
        avg_bias = mean(r["bias"] for r in all_reports)
        print(f"  Rounds analyzed: {len(all_reports)}")
        print(f"  Avg MAE:         {avg_mae:.3f}")
        print(f"  Avg Bias:        {avg_bias:.3f}")

    return 0


if __name__ == "__main__":
    exit(main())