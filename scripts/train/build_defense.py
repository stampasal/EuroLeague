#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_defense_v2.py  (v4 - Βήμα 4.1.2b)
----------------------------------------
Defensive profiles με Strength-of-Schedule (SOS) adjustment + shrinkage
+ pooled 2024-2025 fallback για seasons με μικρό sample.

Λογική:
  1. OS(team, season) = μέσο PIR που ΠΑΡΑΓΕΙ η επίθεση της ομάδας ανά 100'.
  2. raw_PIR_allowed(opp, season) = μέσο PIR που ΔΕΧΕΤΑΙ η άμυνα.
  3. SOS_X = μέσος OS των αντιπάλων της X (στα games της).
  4. SOS_adjustment_X = SOS_X - league_mean_OS(season).
  5. adj_PIR_per_100 = raw_PIR_per_100 - SOS_adjustment_X.
  6. Shrinkage: w = min(games/15, 1.0); adj_final = w*adj + (1-w)*mean(season).
  7. z-score πάνω στο adj_final.
  8. Για seasons με very_low/low sample: pooled_2024_2025 fallback.

Output: defensive_profiles_v2.json
"""
import json
import math
from collections import defaultdict
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import DATA_RAW, DATA_PROC

FANTASY_JSON = DATA_RAW / "fantasy_data.json"
MAPPING_JSON = DATA_RAW / "team_mapping.json"
OUT          = DATA_PROC / "defensive_profiles.json"

MIN_MINUTES   = 5.0
MIN_VALUATION = -10.0
MAX_VALUATION = 60.0
SHRINK_GAMES  = 15.0
POOLED_SEASONS = ("2024", "2025")


def load_mapping():
    with open(MAPPING_JSON, encoding="utf-8") as f:
        m = json.load(f)
    canon = {sc: sc for sc in m["short_to_full"]}
    for alias, full in m["aliases"].items():
        cs = m["full_to_short"].get(full)
        if cs:
            canon[alias] = cs
    historical = set(m["historical"].keys())
    return canon, historical


def quality_label(ng):
    if ng >= 15:
        return "high"
    if ng >= 8:
        return "medium"
    if ng >= 5:
        return "low"
    return "very_low"


def main():
    print("=" * 70)
    print("ΒΗΜΑ 4.1.2b — DEFENSIVE PROFILES v2 (SOS-adjusted + pooled)")
    print("=" * 70)

    canon, historical = load_mapping()

    with open(FANTASY_JSON, encoding="utf-8") as f:
        d = json.load(f)

    # ── Accumulators ───────────────────────────────────────
    os_acc  = defaultdict(lambda: {"pir": 0.0, "min": 0.0, "games": set()})
    def_acc = defaultdict(lambda: {"pir": 0.0, "min": 0.0, "games": set()})
    per_game = defaultdict(lambda: {"pir": 0.0, "min": 0.0})
    game_opp = {}   # (team, season, gc) -> opp

    skipped = 0
    for p in d["players"]:
        for g in p.get("game_logs", []):
            if float(g.get("min", 0)) < MIN_MINUTES:
                skipped += 1
                continue
            val = float(g.get("pdk", 0))
            if not (MIN_VALUATION <= val <= MAX_VALUATION):
                skipped += 1
                continue
            team = canon.get(g.get("team_code"), g.get("team_code"))
            opp  = canon.get(g.get("opp_code"),  g.get("opp_code"))
            if not team or not opp:
                continue
            season = int(g["season"])
            gc     = g["gamecode"]

            os_acc[(team, season)]["pir"] += val
            os_acc[(team, season)]["min"] += float(g["min"])
            os_acc[(team, season)]["games"].add(gc)

            def_acc[(opp, season)]["pir"] += val
            def_acc[(opp, season)]["min"] += float(g["min"])
            def_acc[(opp, season)]["games"].add(gc)

            per_game[(team, season, gc)]["pir"] += val
            per_game[(team, season, gc)]["min"] += float(g["min"])
            game_opp[(team, season, gc)] = opp

    print(f"Skipped rows: {skipped}")
    print(f"OS profiles:  {len(os_acc)}")
    print(f"DEF profiles: {len(def_acc)}\n")

    # ── OS per (team, season) ανά 100' ──────────────────────
    OS = {}
    for (team, season), v in os_acc.items():
        if v["min"] > 0:
            OS[(team, season)] = (v["pir"] / v["min"]) * 100.0

    league_os = defaultdict(list)
    for (team, season), val in OS.items():
        league_os[season].append(val)
    league_mean_os = {s: sum(v) / len(v) for s, v in league_os.items()}
    print("League mean OS per season:")
    for s in sorted(league_mean_os):
        print(f"  {s}: {league_mean_os[s]:.2f}")

    # ── SOS ────────────────────────────────────────────────
    sos_acc = defaultdict(lambda: defaultdict(list))
    for (team, season, gc), opp in game_opp.items():
        os_val = OS.get((opp, season))
        if os_val is not None:
            sos_acc[(team, season)][gc].append(os_val)

    SOS = {}
    for (team, season), games in sos_acc.items():
        vals = [v[0] for v in games.values() if v]
        if vals:
            SOS[(team, season)] = sum(vals) / len(vals)

    print(f"\nSOS profiles: {len(SOS)}")

    # ── Raw def per 100' ───────────────────────────────────
    raw = {}
    for (opp, season), v in def_acc.items():
        ng = len(v["games"])
        if ng == 0 or v["min"] == 0:
            continue
        raw[(opp, season)] = {
            "PIR_allowed_total":    round(v["pir"], 2),
            "min_allowed_total":    round(v["min"], 2),
            "games_count":          ng,
            "PIR_allowed_per_game": round(v["pir"] / ng, 3),
            "PIR_allowed_per_100min": round((v["pir"] / v["min"]) * 100.0, 3),
        }

    # ── SOS-adjusted + shrinkage + z-score, ανά season ─────
    out = defaultdict(dict)
    seasons = sorted(set(s for (_, s) in raw))
    for season in seasons:
        teams = [k[0] for k in raw if k[1] == season]
        raw_vals = [raw[(t, season)]["PIR_allowed_per_100min"] for t in teams]
        if not raw_vals:
            continue
        season_mean = sum(raw_vals) / len(raw_vals)

        for t in teams:
            r = raw[(t, season)]
            sos = SOS.get((t, season))
            lmean_os = league_mean_os.get(season)
            sos_adj = (sos - lmean_os) if (sos is not None and lmean_os is not None) else 0.0

            adj = r["PIR_allowed_per_100min"] - sos_adj
            w = min(r["games_count"] / SHRINK_GAMES, 1.0)
            adj_final = w * adj + (1 - w) * season_mean

            ng = r["games_count"]
            quality = quality_label(ng)

            out[str(season)][t] = {
                "raw": r,
                "sos": {
                    "SOS_raw":         round(sos, 3) if sos is not None else None,
                    "league_mean_OS":  round(lmean_os, 3) if lmean_os is not None else None,
                    "SOS_adjustment":  round(sos_adj, 3),
                },
                "adjusted": {
                    "adj_PIR_per_100min": round(adj, 3),
                    "weight":             round(w, 4),
                    "adj_final":          round(adj_final, 3),
                },
                "sample": {
                    "games_count":          ng,
                    "low_sample":           ng < 8,
                    "sample_quality":       quality,
                    "use_pooled_fallback":  quality in ("very_low", "low"),
                },
                "historical": t in historical,
            }

        # z-score πάνω στο adj_final
        finals = [v["adjusted"]["adj_final"] for v in out[str(season)].values()]
        m = sum(finals) / len(finals)
        var = sum((x - m) ** 2 for x in finals) / len(finals)
        std = math.sqrt(var) if var > 0 else 1.0
        for v in out[str(season)].values():
            v["adjusted"]["zscore_adj_final"] = round(
                (v["adjusted"]["adj_final"] - m) / std, 4
            )
        print(f"  Season {season}: mean_adj={m:.2f}  std={std:.2f}")

    # ── Pooled 2024-2025 fallback ──────────────────────────
    print(f"\nBuilding pooled fallback ({POOLED_SEASONS}) …")
    pooled_teams = set()
    for s in POOLED_SEASONS:
        if s in out:
            pooled_teams |= set(out[s].keys())

    pooled = {}
    for t in pooled_teams:
        vals_raw, vals_adj, ng_total = [], [], 0
        for s in POOLED_SEASONS:
            if s in out and t in out[s]:
                vals_raw.append(out[s][t]["raw"]["PIR_allowed_per_100min"])
                vals_adj.append(out[s][t]["adjusted"]["adj_final"])
                ng_total += out[s][t]["raw"]["games_count"]
        if vals_raw:
            pooled[t] = {
                "PIR_allowed_per_100min": round(sum(vals_raw) / len(vals_raw), 3),
                "adj_final":              round(sum(vals_adj) / len(vals_adj), 3),
                "games_count":            ng_total,
                "seasons":                list(POOLED_SEASONS),
            }

    # z-score του pooled
    if pooled:
        pv = [v["adj_final"] for v in pooled.values()]
        pm = sum(pv) / len(pv)
        pvar = sum((x - pm) ** 2 for x in pv) / len(pv)
        pstd = math.sqrt(pvar) if pvar > 0 else 1.0
        for v in pooled.values():
            v["zscore_pooled"] = round((v["adj_final"] - pm) / pstd, 4)

    print(f"  Pooled teams: {len(pooled)}")

    # Ενσωμάτωση pooled σε κάθε season entry
    for season in seasons:
        for t in out[str(season)]:
            if t in pooled:
                out[str(season)][t]["pooled_2024_2025"] = pooled[t]

    # ── Write ──────────────────────────────────────────────
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n→ Wrote {OUT}")
    print("=" * 70)

    # ── Preview 2026 ───────────────────────────────────────
    if "2026" in out:
        print("\nPREVIEW 2026 (sorted by adj_final, πιο χαλαρή πρώτη):")
        rows = sorted(out["2026"].items(),
                      key=lambda x: -x[1]["adjusted"]["adj_final"])
        print(f"  {'CODE':<6} {'G':>3} {'RAW':>7} {'SOSadj':>8} "
              f"{'W':>5} {'ADJ':>7} {'Z':>7}  {'QUAL':<9} {'POOL':>7}")
        for code, t in rows:
            r = t["raw"]; s = t["sos"]; a = t["adjusted"]; q = t["sample"]
            pl = t.get("pooled_2024_2025", {})
            pool_str = f"{pl.get('adj_final', 0):>7.2f}" if pl else "      -"
            print(f"  {code:<6} {r['games_count']:>3} "
                  f"{r['PIR_allowed_per_100min']:>7.2f} "
                  f"{s['SOS_adjustment']:>+8.2f} "
                  f"{a['weight']:>5.2f} "
                  f"{a['adj_final']:>7.2f} "
                  f"{a['zscore_adj_final']:>+7.3f}  "
                  f"{q['sample_quality']:<9} {pool_str}")
    print("=" * 70)


if __name__ == "__main__":
    main()