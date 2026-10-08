#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_stats.py
----------------
2026 stats ανά παίκτη: PIR, SFP (full), Credits/Value, Usage% (BasketStories FTA).
Output: app/js/data/player-stats-2026.js
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import DATA_RAW, APP_JS_CONFIG, APP_JS_DATA
from core.team_mapping import FULL_TO_SHORT as TEAM_FULL_TO_SHORT

FANTASY_JSON       = DATA_RAW / "fantasy_data.json"
DATA_JS            = APP_JS_CONFIG / "data.js"
OUT_FILE           = APP_JS_DATA / "player-stats-2026.js"
BASKETSTORIES_JSON = DATA_RAW / "basketstories_credits.json"
BS_PLAYER_STATS    = DATA_RAW / "basketstories_player_stats.json"

CURRENT_SEASON = 2026

# Manual positions για παίκτες που ΔΕΝ υπάρχουν στο EuroLeague people API
MANUAL_POSITIONS = {
    "LEAF, TJ":                  "F",
    "MILTON, SHAKE":             "G",
    "HOLMES, RICHAUN":           "F",
    "TOLIOPOULOS, VASSILIS":     "G",
    "ALSTON JR. , DERRICK":      "F",
    "JALLOW, KARIM":             "F",
    "NIANG, SALIOU":             "F",
    "TAYLOR, BRANDON":           "G",
    "OKEKE, CHUMA":              "F",
    "DOKOSSI, ALLAN":            "C",
    "FAYE, MOUHAMED":            "C",
    "MORGAN, JEREMY":            "G",
    "RUBSTAVICIUS, MANTAS":      "G",
    "SLEVA, DUSTIN":             "F",
    "MASSA, BODIAN":             "C",
    "ALMANSA, IZAN":             "F",
    "KOUZELOGLOU, IOANNIS":      "F",
    "HEURTEL, THOMAS":           "G",
}

# Overrides — διορθώσεις θέσεων που το EuroLeague API έχει ΛΑΘΟΣ
POSITION_OVERRIDES = {
    "FOURNIER, EVAN":            "G",
}


def load_games_raw():
    txt = DATA_JS.read_text(encoding="utf-8")
    m = re.search(r"GAMES_RAW\s*=\s*(\[.*?\])\s*;", txt, re.DOTALL)
    if not m:
        return []
    raw = re.sub(r",\s*\]", "]", m.group(1))
    return json.loads(raw)


def build_games_index(games_raw):
    idx = {}
    for row in games_raw:
        if len(row) < 7:
            continue
        rnd = int(row[0]); season = int(row[2][:4])
        home = TEAM_FULL_TO_SHORT.get(row[5]); away = TEAM_FULL_TO_SHORT.get(row[6])
        if not home or not away:
            continue
        idx[(home, season, rnd)] = {"opp": away, "is_home": True}
        idx[(away, season, rnd)] = {"opp": home, "is_home": False}
    return idx


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def r(x, n=2):
    return round(x, n) if x is not None else None


def norm_name(s):
    if not s:
        return ""
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return " ".join(sorted(t for t in s.split() if t))


def load_basketstories_credits():
    if not BASKETSTORIES_JSON.exists():
        return {}
    with open(BASKETSTORIES_JSON, encoding="utf-8") as f:
        return json.load(f).get("by_norm_name", {})


def load_bs_player_stats():
    if not BS_PLAYER_STATS.exists():
        return {}
    with open(BS_PLAYER_STATS, encoding="utf-8") as f:
        return json.load(f).get("players", {})


def build_team_totals(players_data):
    """Aggregate 2026 logs ανά team_code: MP, FGA, FTA, TO, games."""
    totals = {}
    for p in players_data:
        logs = [g for g in (p.get("game_logs") or [])
                if int(g.get("season", 0)) >= CURRENT_SEASON
                and float(g.get("min", 0)) > 0]
        if not logs:
            continue
        team = logs[0].get("team_code")
        if not team:
            continue
        if team not in totals:
            totals[team] = {"mp": 0.0, "fga": 0.0, "fta": 0.0,
                            "to": 0.0, "games": set()}
        for g in logs:
            totals[team]["mp"]  += float(g.get("min", 0) or 0)
            totals[team]["fga"] += float(g.get("fga", 0) or 0)
            totals[team]["fta"] += float(g.get("fta", 0) or 0)
            totals[team]["to"]  += float(g.get("to", 0) or 0)
            totals[team]["games"].add((g.get("season"), g.get("round")))
    for t in totals.values():
        t["games"] = len(t["games"])
    return totals


BS_TO_EL_TEAM = {
    "BAY": "MUN", "BKN": "BAS", "CZT": "RED", "EFS": "ULK",
    "FCB": "BAR", "FNB": "IST", "MAC": "TEL", "PAO": "PAN",
    "RMB": "MAD", "VAL": "PAM",
}


def build_team_fta_from_bs(bs_stats):
    """Aggregate FTA per team από BasketStories players."""
    by_team = {}
    for entry in bs_stats.values():
        team = entry.get("team")
        if not team:
            continue
        team_el = BS_TO_EL_TEAM.get(team, team)
        totals = entry.get("totals") or {}
        fta = float(totals.get("fta", 0) or 0)
        by_team[team_el] = by_team.get(team_el, 0.0) + fta
    return by_team


def calc_usage(player_totals, team_totals):
    """
    USG% = 100 × ((FGA + 0.44×FTA + TOV) × (TmMP/5))
              / (MP × (TmFGA + 0.44×TmFTA + TmTOV))
    """
    if not player_totals or not team_totals:
        return None
    try:
        mp   = float(player_totals.get("min", 0) or 0)
        fga  = float(player_totals.get("fga", 0) or 0)
        fta  = float(player_totals.get("fta", 0) or 0)
        tov  = float(player_totals.get("to", 0) or 0)

        tm_fga = float(team_totals.get("fga", 0) or 0)
        tm_fta = float(team_totals.get("fta", 0) or 0)
        tm_tov = float(team_totals.get("to", 0) or 0)
        tm_games = int(team_totals.get("games", 0) or 0)
        tm_mp  = tm_games * 200.0

        if mp <= 0 or tm_mp <= 0:
            return None
        denom = mp * (tm_fga + 0.44 * tm_fta + tm_tov)
        if denom <= 0:
            return None
        return 100.0 * ((fga + 0.44 * fta + tov) * (tm_mp / 5.0)) / denom
    except Exception:
        return None


def main():
    print("=" * 60)
    print("BUILD STATS 2026 (credits + value + full SFP + usage)")
    print("=" * 60)

    with open(FANTASY_JSON, encoding="utf-8") as f:
        d = json.load(f)

    games_index = build_games_index(load_games_raw())
    print(f"GAMES_RAW index: {len(games_index)} entries")

    bs_lookup = load_basketstories_credits()
    bs_stats  = load_bs_player_stats()
    print(f"BasketStories credits: {len(bs_lookup)}")
    print(f"BasketStories full stats (FR/BLA/FT): {len(bs_stats)}")

    team_totals = build_team_totals(d["players"])
    print(f"Team totals (2026): {len(team_totals)} teams")

    bs_team_fta = build_team_fta_from_bs(bs_stats)
    merged_fta = 0
    for team, tt in team_totals.items():
        if team in bs_team_fta and bs_team_fta[team] > 0:
            tt["fta"] = bs_team_fta[team]
            merged_fta += 1
    print(f"Team FTA από BasketStories: {merged_fta}/{len(team_totals)} teams")

    n_matched   = 0
    n_missing   = 0
    n_full_sfp  = 0
    n_usage     = 0
    n_manual_pos = 0
    missing_sample = []

    out = {}
    n_2026 = 0

    for p in d["players"]:
        name = str(p.get("player", "")).strip().upper()
        if not name:
            continue

        bs_hit = bs_lookup.get(norm_name(name))
        credits = None
        bs_id   = None
        if bs_hit:
            credits = bs_hit.get("credits")
            bs_id   = bs_hit.get("bs_id")
            n_matched += 1
        else:
            n_missing += 1
            if len(missing_sample) < 10:
                missing_sample.append(name)

        fr  = None; bla = None
        player_totals = None
        if bs_id and bs_id in bs_stats:
            entry = bs_stats[bs_id]
            avg = entry.get("avg", {})
            fr  = avg.get("fr")
            bla = avg.get("bla")
            player_totals = entry.get("totals")

        logs = [g for g in (p.get("game_logs") or [])
                if int(g.get("season", 0)) >= CURRENT_SEASON
                and float(g.get("min", 0)) > 0]

        if not logs:
            out[name] = {"games_2026": 0, "credits": credits,
                         "value": None, "bs_id": bs_id}
            continue

        n_2026 += 1

        pir   = mean([g.get("pdk") for g in logs])
        mins  = mean([g.get("min") for g in logs])
        pts   = mean([g.get("pts") for g in logs])
        reb   = mean([g.get("reb") for g in logs])
        ast   = mean([g.get("ast") for g in logs])
        stl   = mean([g.get("stl") for g in logs])
        blk   = mean([g.get("blk") for g in logs])
        to    = mean([g.get("to") for g in logs])
        pf    = mean([g.get("pf") for g in logs])

        fgm_sum = sum(float(g.get("fgm", 0) or 0) for g in logs)
        fga_sum = sum(float(g.get("fga", 0) or 0) for g in logs)
        fg_pct = (fgm_sum / fga_sum * 100) if fga_sum > 0 else None

        sfp = None; sfp_full = False
        if all(x is not None for x in (reb, ast, stl, blk, to, pf)):
            if fr is not None and bla is not None:
                sfp = reb + ast + stl + blk + fr - to - pf - bla
                sfp_full = True
                n_full_sfp += 1
            else:
                sfp = reb + ast + stl + blk - to - pf

        team = logs[0].get("team_code")
        tt = team_totals.get(team)
        usage = calc_usage(player_totals, tt) if (player_totals and tt) else None
        if usage is not None and (usage < 0 or usage > 60):
            usage = None
        if usage is not None:
            n_usage += 1

        last = max(logs, key=lambda g: (g["season"], g["round"]))
        position = POSITION_OVERRIDES.get(name)
        if position is None:
            position = p.get("position_norm", "—")
            if position in (None, "", "?"):
                manual = MANUAL_POSITIONS.get(name)
                if manual:
                    position = manual
                    n_manual_pos += 1
                else:
                    position = "?"
        season = int(last["season"]); rnd = int(last["round"])
        next3 = []
        for delta in range(1, 15):
            hit = games_index.get((team, season, rnd + delta))
            if hit:
                next3.append({"opp": hit["opp"], "home": hit["is_home"]})
            if len(next3) == 3:
                break

        out[name] = {
            "games_2026": len(logs),
            "team":        team,
            "position":    position,
            "pir":         r(pir),
            "avg_min":     r(mins, 1),
            "pts":         r(pts, 1),
            "reb":         r(reb, 1),
            "ast":         r(ast, 1),
            "stl":         r(stl, 1),
            "blk":         r(blk, 1),
            "to":          r(to, 1),
            "pf":          r(pf, 1),
            "fg_pct":      r(fg_pct, 1),
            "sfp":         r(sfp, 1),
            "sfp_full":    sfp_full,
            "usage":       r(usage, 1),
            "next3":       next3,
            "credits":     credits,
            "value":       r(pir / credits, 3) if (pir and credits and credits > 0) else None,
            "bs_id":       bs_id,
        }

    js = "// Auto-generated by convert_stats.py\n"
    js += "window.PLAYER_STATS_2026 = "
    js += json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    js += ";\n"

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(js, encoding="utf-8")

    print(f"Players με 2026 games: {n_2026}")
    print(f"Full SFP (FR+BLA): {n_full_sfp}/{n_2026}")
    print(f"Usage υπολογισμένο: {n_usage}/{n_2026}")
    print(f"Manual positions: {n_manual_pos}")
    print(f"→ {OUT_FILE}  ({OUT_FILE.stat().st_size/1024:.1f} KB)")
    print(f"BasketStories matched: {n_matched}/{n_matched + n_missing} "
          f"({100*n_matched/max(n_matched+n_missing,1):.1f}%)")
    if missing_sample:
        print("Missing (δείγμα):")
        for m in missing_sample:
            print(f"  {m}")
    print("=" * 60)


if __name__ == "__main__":
    main()
