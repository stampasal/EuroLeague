#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
coach_stats.py
--------------
Υπολογίζει xp + credits για κάθε προπονητή από τα αποτελέσματα αγώνων.
ΕΠΙΣΗΣ: adj_avg_xp για τον ΕΠΟΜΕΝΟ αγώνα:
  avg_xp × home_factor × opp_factor × streak_factor

Streak factor:
  4+ νίκες:  ×1.10  (+0.05 αν 3+ εκτός)
  3 νίκες:   ×1.05  (+0.03 αν 2+ εκτός)
  2 νίκες:   ×1.00
  2 ήττες:   ×1.00
  3 ήττες:   ×0.95  (-0.03 αν 2+ εκτός)
  4+ ήττες:  ×0.90  (-0.05 αν 3+ εκτός)
"""

import json
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import DATA_RAW, DATA_PROC, APP_JS_CONFIG
COACHES_JSON = DATA_RAW / "coaches.json"
DATA_JS      = APP_JS_CONFIG / "data.js"
OUT_JSON     = DATA_PROC / "coach_stats.json"

SCORING_RULES = {
    "win_20_plus":    25,
    "win_11_20":      20,
    "win_1_10_or_ot": 10,
    "loss_1_10_or_ot": -5,
    "loss_11_20":     -10,
    "loss_20_plus":   -20,
}

HOME_FACTOR    = 1.10
AWAY_FACTOR    = 0.90
OPP_TOP_FACTOR = 0.80
OPP_MID_FACTOR = 1.00
OPP_BOT_FACTOR = 1.20


def load_games_raw():
    txt = DATA_JS.read_text(encoding="utf-8")
    m = re.search(r"const GAMES_RAW\s*=\s*\[(.*?)\];", txt, re.DOTALL)
    if not m:
        raise ValueError("GAMES_RAW δεν βρέθηκε")
    body = m.group(1)

    pattern = re.compile(
        r'\[(\d+),"([^"]*)","([^"]*)","[^"]*","[^"]*","([^"]+)","([^"]+)",'
        r'(null|\d+),(null|\d+)\]'
    )
    games = []
    for mm in pattern.finditer(body):
        rnd, day, date, home, away, hs, aw = mm.groups()
        games.append({
            "round": int(rnd),
            "day":   day,
            "date":  date,
            "home":  home,
            "away":  away,
            "hs":    None if hs == "null" else int(hs),
            "aw":    None if aw == "null" else int(aw),
        })
    return games


def compute_coach_xp(margin, won):
    if won:
        if margin >= 20:
            return SCORING_RULES["win_20_plus"]
        if margin >= 11:
            return SCORING_RULES["win_11_20"]
        return SCORING_RULES["win_1_10_or_ot"]
    else:
        if margin >= 20:
            return SCORING_RULES["loss_20_plus"]
        if margin >= 11:
            return SCORING_RULES["loss_11_20"]
        return SCORING_RULES["loss_1_10_or_ot"]


# ---------------------------------------------------------------
# Standings / next round / opponent
# ---------------------------------------------------------------

def build_standings(games, team_full_to_short):
    stats = {}
    for g in games:
        if g["hs"] is None or g["aw"] is None:
            continue
        home = team_full_to_short.get(g["home"])
        away = team_full_to_short.get(g["away"])
        if not home or not away:
            continue
        if home not in stats:
            stats[home] = {"wins": 0, "losses": 0}
        if away not in stats:
            stats[away] = {"wins": 0, "losses": 0}

        if g["hs"] > g["aw"]:
            stats[home]["wins"]   += 1
            stats[away]["losses"] += 1
        else:
            stats[home]["losses"] += 1
            stats[away]["wins"]   += 1

    ranked = sorted(
        stats.items(),
        key=lambda kv: (-kv[1]["wins"], kv[1]["losses"])
    )
    for i, (team, s) in enumerate(ranked, start=1):
        s["rank"] = i
    return stats


def find_next_round(games):
    played_rounds = [
        g["round"] for g in games
        if g["hs"] is not None and g["aw"] is not None
    ]
    if not played_rounds:
        return None
    return max(played_rounds) + 1


def get_next_opponent(games, team_short, next_round, team_full_to_short):
    for g in games:
        if g["round"] != next_round:
            continue
        home = team_full_to_short.get(g["home"])
        away = team_full_to_short.get(g["away"])
        if home == team_short:
            return {"opp": away, "is_home": True}
        if away == team_short:
            return {"opp": home, "is_home": False}
    return None


def opp_factor_from_rank(rank):
    if rank is None:
        return 1.0
    if rank <= 6:
        return OPP_TOP_FACTOR
    if rank <= 13:
        return OPP_MID_FACTOR
    return OPP_BOT_FACTOR


# ---------------------------------------------------------------
# ΝΕΟ: Streak factor
# ---------------------------------------------------------------

def compute_streak_factor(history):
    """
    Κοιτάει το history (τελευταία πρώτα ή τελευταία τελευταία?) —
    έχουμε append με χρονολογική σειρά (round ascending).
    Οπότε διαβάζουμε ΑΝΑΠΟΔΑ (από το τέλος προς την αρχή)
    για να βρούμε το τρέχον σερί.

    Επιστρέφει (factor, streak_len, streak_type, away_count).
    """
    if not history:
        return 1.0, 0, None, 0

    # Τελευταίο αποτέλεσμα
    last_won = history[-1]["won"]

    streak_len = 0
    away_count = 0
    for h in reversed(history):
        if h["won"] != last_won:
            break
        streak_len += 1
        if not h.get("is_home", True):
            away_count += 1

    # Base factor
    if last_won:
        if streak_len >= 4:
            base = 1.10
            bonus = 0.05 if away_count >= 3 else 0.0
        elif streak_len == 3:
            base = 1.05
            bonus = 0.03 if away_count >= 2 else 0.0
        else:
            base = 1.00
            bonus = 0.0
    else:
        if streak_len >= 4:
            base = 0.90
            bonus = -0.05 if away_count >= 3 else 0.0
        elif streak_len == 3:
            base = 0.95
            bonus = -0.03 if away_count >= 2 else 0.0
        else:
            base = 1.00
            bonus = 0.0

    factor = round(base + bonus, 3)
    streak_type = "W" if last_won else "L"
    return factor, streak_len, streak_type, away_count


# ---------------------------------------------------------------

def main():
    print("=" * 78)
    print("COACH STATS")
    print("=" * 78)

    with open(COACHES_JSON, encoding="utf-8") as f:
        coaches_data = json.load(f)

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

    games = load_games_raw()
    print(f"Games loaded: {len(games)}")

    played = [g for g in games if g["hs"] is not None and g["aw"] is not None]
    print(f"Played games: {len(played)}")

    stats = {c["team"]: {
        "coach_name": c["name"],
        "team_full":  c["team_full"],
        "wins":    0,
        "losses":  0,
        "xp_list": [],
        "history": [],
    } for c in coaches_data["coaches"]}

    for g in played:
        home_short = TEAM_FULL_TO_SHORT.get(g["home"])
        away_short = TEAM_FULL_TO_SHORT.get(g["away"])
        if not home_short or not away_short:
            continue

        hs, aw = g["hs"], g["aw"]
        margin = abs(hs - aw)
        home_won = hs > aw

        if home_short in stats:
            xp = compute_coach_xp(margin, home_won)
            stats[home_short]["xp_list"].append(xp)
            stats[home_short]["history"].append({
                "round": g["round"], "opp": away_short,
                "hs": hs, "aw": aw, "margin": margin,
                "won": home_won, "is_home": True, "xp": xp,
            })
            if home_won:
                stats[home_short]["wins"] += 1
            else:
                stats[home_short]["losses"] += 1

        if away_short in stats:
            xp = compute_coach_xp(margin, not home_won)
            stats[away_short]["xp_list"].append(xp)
            stats[away_short]["history"].append({
                "round": g["round"], "opp": home_short,
                "hs": hs, "aw": aw, "margin": margin,
                "won": not home_won, "is_home": False, "xp": xp,
            })
            if not home_won:
                stats[away_short]["wins"] += 1
            else:
                stats[away_short]["losses"] += 1

    standings = build_standings(games, TEAM_FULL_TO_SHORT)
    next_round = find_next_round(games)
    print(f"Next round: {next_round}")

    out = {}
    for team, s in stats.items():
        xp_list = s["xp_list"]
        total_xp = sum(xp_list)
        games_count = len(xp_list)
        avg_xp = total_xp / games_count if games_count else 0.0

        last5 = xp_list[-5:] if len(xp_list) >= 5 else xp_list
        form = sum(last5) / len(last5) if last5 else 0.0

        next_info = get_next_opponent(
            games, team, next_round, TEAM_FULL_TO_SHORT
        ) if next_round else None

        if next_info:
            opp_short = next_info["opp"]
            is_home   = next_info["is_home"]
            opp_rank  = standings.get(opp_short, {}).get("rank")
        else:
            opp_short = None
            is_home   = None
            opp_rank  = None

        # Factors
        hf = HOME_FACTOR if is_home else (AWAY_FACTOR if is_home is False else 1.0)
        of = opp_factor_from_rank(opp_rank)
        sf, streak_len, streak_type, away_in_streak = compute_streak_factor(s["history"])

        adj_xp = round(avg_xp * hf * of * sf, 2) if games_count else 0.0

        out[team] = {
            "coach_name":   s["coach_name"],
            "team_full":    s["team_full"],
            "games":        games_count,
            "wins":         s["wins"],
            "losses":       s["losses"],
            "win_pct":      round(100 * s["wins"] / games_count, 1) if games_count else 0.0,
            "total_xp":     total_xp,
            "avg_xp":       round(avg_xp, 2),
            "form_last5":   round(form, 2),
            "next_round":   next_round,
            "next_opp":     opp_short,
            "next_is_home": is_home,
            "opp_rank":     opp_rank,
            "streak_len":   streak_len,
            "streak_type":  streak_type,
            "streak_away":  away_in_streak,
            "streak_factor": sf,
            "adj_avg_xp":   adj_xp,
            "history":      s["history"],
        }

    output = {
        "season":         coaches_data["season"],
        "updated_at":     "auto",
        "games_analyzed": len(played),
        "next_round":     next_round,
        "coaches":        out,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n→ {OUT_JSON}")
    print(f"Coaches analyzed: {len(out)}")

    print("\n" + "=" * 92)
    print(f"{'TEAM':<5} {'COACH':<22} {'W-L':>6} {'AVG':>7} {'OPP':>5} "
          f"{'H/A':>4} {'STREAK':>8} {'SF':>6} {'ADJ':>7}")
    print("=" * 92)
    sorted_coaches = sorted(out.items(), key=lambda x: -x[1]["adj_avg_xp"])
    for team, c in sorted_coaches:
        wl = f"{c['wins']}-{c['losses']}"
        opp = c["next_opp"] or "-"
        ha = "H" if c["next_is_home"] else ("A" if c["next_is_home"] is False else "-")
        st = f"{c['streak_len']}{c['streak_type']}" if c['streak_type'] else "-"
        print(f"{team:<5} {c['coach_name']:<22} {wl:>6} "
              f"{c['avg_xp']:>7.2f} {opp:>5} {ha:>4} {st:>8} "
              f"{c['streak_factor']:>6.2f} {c['adj_avg_xp']:>7.2f}")
    print("=" * 92)


if __name__ == "__main__":
    main()