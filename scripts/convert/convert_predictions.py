#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_predictions.py
----------------------
Διαβάζει player_predictions.json (data/processed/)
Γράφει player_predictions.js (app/js/data/)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import DATA_PROC, APP_JS_DATA

IN_FILE  = DATA_PROC / "player_predictions.json"
OUT_FILE = APP_JS_DATA / "player_predictions.js"


def main():
    print("=" * 60)
    print("CONVERT player_predictions.json → player_predictions.js")
    print("=" * 60)

    with open(IN_FILE, encoding="utf-8") as f:
        preds = json.load(f)
    print(f"Loaded {len(preds)} predictions from {IN_FILE}")

    out = []
    for p in preds:
        rec = {
            "player_code":        p["player_code"],
            "player":             p["player"],
            "team":               p["team"],
            "position_norm":      p["position_norm"],
            "gp":                 p["gp"],
            "pdk":                p["pdk"],
            "xpdk":               p["xpdk_v4_2"],
            "p_ridge":            p["p_ridge"],
            "p_gb":               p["p_gb"],
            "p_ma":               p["p_ma"],
            "floor_pdk":          p["floor_pdk"],
            "ceiling_pdk":        p["ceiling_pdk"],
            "cv":                 p["cv"],
            "ewma5_pdk":          p["ewma5_pdk"],
            "min_trend_label":    p["min_trend_label"],
            "confidence":         p["confidence"],
            "next_opp":           p.get("next_opp"),
            "next_is_home":       p.get("next_is_home"),
            "opp_adj_def":        p.get("opp_adj_def"),
            "opp_adj_z":          p.get("opp_adj_z"),
            "opp_pooled_def":     p.get("opp_pooled_def"),
            "opp_quality":        p.get("opp_quality"),
            "dvp_opp_vs_pos":     p.get("dvp_opp_vs_pos"),
            "dvp_opp_vs_pos_l20": p.get("dvp_opp_vs_pos_l20"),
        }
        out.append(rec)

    lines = []
    lines.append("// ============================================================")
    lines.append("// PLAYER PREDICTIONS — auto-generated (v4.2)")
    lines.append(f"// Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"// Players: {len(out)}")
    lines.append("// ============================================================")
    lines.append("")
    lines.append("const PLAYER_PREDICTIONS = ")
    lines.append(json.dumps(out, ensure_ascii=False, indent=1))
    lines.append(";")
    lines.append("")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"→ {OUT_FILE}  ({len(out)} players)")

    sample = out[0]
    print(f"\nSanity (first player):")
    for k in ("player", "team", "xpdk", "next_opp", "next_is_home",
              "opp_adj_def", "dvp_opp_vs_pos"):
        print(f"  {k}: {sample.get(k)}")

    n_next = sum(1 for p in out if p["next_opp"] is not None)
    print(f"\nΜε next_opp: {n_next}/{len(out)} "
          f"({100*n_next/len(out):.1f}%)")

    print("=" * 60)


if __name__ == "__main__":
    main()
