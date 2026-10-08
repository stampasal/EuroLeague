#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_optimizer.py
---------------------
Επιβεβαιώνει ότι το MILP (best_team.py) δίνει ΒΕΛΤΙΣΤΗ λύση.

Μέθοδος:
  1. Παίρνει 6G + 6F + 6C τυχαίους παίκτες (seed=42)
  2. Κλειδώνει formation = 2-2-1
  3. Brute-force: δοκιμάζει όλα τα ρόστερ (4G/4F/2C) + starters + 6th + captain
  4. Λύνει με MILP (ίδιο subset)
  5. Συγκρίνει scores

Αν |brute - milp| < 0.01 → OK

Εκτέλεση:  py validate_optimizer.py
"""

from __future__ import annotations

import itertools
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.optimize.constraints import (
    Player, Coach, CurrentTeam, OptimizerInput,
    FORMATIONS, TOTAL_G, TOTAL_F, TOTAL_C, TOTAL_PLAYERS,
    N_STARTERS, N_SIXTH, N_BENCH,
    STARTER_MULT, SIXTH_MULT, BENCH_MULT, CAPTAIN_MULT,
    COACH_MULT,
    build_players, build_coaches,
)
from core.optimize.best_team import _solve_once, SolveResult


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

SEED          = 42
N_G, N_F, N_C = 6, 6, 6       # subset μεγέθη
FORMATION     = "2-2-1"       # κλειδωμένο
CASH          = 100.0         # αρκετό για να μην κόβει λύσεις
MAX_TRANSFERS = 10            # αρκετό για να μην κόβει
TOLERANCE     = 0.01


# ------------------------------------------------------------
# BUILD SUBSET
# ------------------------------------------------------------

def build_subset(players: dict[str, Player]) -> dict[str, Player]:
    """Επιστρέφει 6G + 6F + 6C τυχαίους (seed=42)."""
    rng = random.Random(SEED)
    by_pos: dict[str, list[Player]] = {"G": [], "F": [], "C": []}
    for p in players.values():
        by_pos[p.pos].append(p)

    for k in by_pos:
        by_pos[k].sort(key=lambda x: x.id)   # deterministic
        rng.shuffle(by_pos[k])

    chosen: dict[str, Player] = {}
    for pos, n in (("G", N_G), ("F", N_F), ("C", N_C)):
        for p in by_pos[pos][:n]:
            chosen[p.id] = p
    return chosen


# ------------------------------------------------------------
# BRUTE-FORCE SCORE
# ------------------------------------------------------------

def brute_force_best(players: dict[str, Player],
                     coach: Coach,
                     formation: str) -> tuple[float, tuple]:
    """
    Επιστρέφει (max_score, (roster_ids, starter_ids, sixth_id, captain_id)).
    """
    f_slots = FORMATIONS[formation]
    by_pos: dict[str, list[Player]] = {"G": [], "F": [], "C": []}
    for p in players.values():
        by_pos[p.pos].append(p)

    g_list, f_list, c_list = by_pos["G"], by_pos["F"], by_pos["C"]

    best_score = -1e9
    best_combo = None

    coach_xp = coach.effective_xp * COACH_MULT

    # 1) Ρόστερ: 4G / 4F / 2C
    for roster_g in itertools.combinations(g_list, TOTAL_G):
        for roster_f in itertools.combinations(f_list, TOTAL_F):
            for roster_c in itertools.combinations(c_list, TOTAL_C):
                roster = list(roster_g) + list(roster_f) + list(roster_c)
                roster_ids = {p.id for p in roster}

                # 2) Starters βάσει formation
                for start_g in itertools.combinations(roster_g, f_slots["G"]):
                    for start_f in itertools.combinations(roster_f, f_slots["F"]):
                        for start_c in itertools.combinations(roster_c, f_slots["C"]):
                            starters = list(start_g) + list(start_f) + list(start_c)
                            starter_ids = {p.id for p in starters}

                            # 3) 6th από τους υπόλοιπους 5
                            remaining = [p for p in roster if p.id not in starter_ids]
                            for sixth in remaining:
                                bench = [p for p in remaining if p.id != sixth.id]

                                # 4) Captain από τους starters
                                for captain in starters:
                                    score = 0.0
                                    for p in starters:
                                        m = CAPTAIN_MULT if p.id == captain.id else STARTER_MULT
                                        score += p.xpdk * m
                                    score += sixth.xpdk * SIXTH_MULT
                                    for p in bench:
                                        score += p.xpdk * BENCH_MULT
                                    score += coach_xp

                                    if score > best_score:
                                        best_score = score
                                        best_combo = (
                                            tuple(sorted(roster_ids)),
                                            tuple(sorted(starter_ids)),
                                            sixth.id,
                                            captain.id,
                                        )
    return best_score, best_combo


# ------------------------------------------------------------
# MILP CALL
# ------------------------------------------------------------

def run_milp(players_subset: dict[str, Player],
             coaches: dict[str, Coach],
             coach: Coach,
             formation: str) -> SolveResult | None:
    """
    Καλεί το _solve_once του best_team.py με το subset.
    Φτιάχνει CurrentTeam με ΟΛΟΥΣ τους subset παίκτες ως "current"
    (για να μην επηρεάζει το cash constraint — θέλουμε ελεύθερη βελτιστοποίηση).
    """
    # Φτιάχνουμε dummy current team με 10 παίκτες (τυχαίους) + cash μεγάλο
    # Για να μην περιορίζει transfers, δίνουμε cash=1000
    dummy_players = list(players_subset.values())[:TOTAL_PLAYERS]
    # Βεβαιώσου ότι έχει σωστές θέσεις
    by_pos: dict[str, list[Player]] = {"G": [], "F": [], "C": []}
    for p in players_subset.values():
        by_pos[p.pos].append(p)
    dummy_players = (
        by_pos["G"][:TOTAL_G] + by_pos["F"][:TOTAL_F] + by_pos["C"][:TOTAL_C]
    )

    current = CurrentTeam(
        players=dummy_players,
        coach=coach,
        formation=None,
        captain_id=None,
        squad_value=0.0,
        cash=1000.0,   # αρκετά μεγάλο
    )

    result = _solve_once(
        all_players=players_subset,
        all_coaches={coach.id: coach},   # μόνο ένας coach
        current_team=current,
        formation=formation,
        scenario="B",
        max_transfers=MAX_TRANSFERS,
        cash=1000.0,
        exclude_rosters=None,
    )
    return result


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():
    print("=" * 70)
    print("VALIDATE OPTIMIZER — MILP vs BRUTE-FORCE")
    print("=" * 70)
    print(f"Seed:         {SEED}")
    print(f"Subset:       {N_G}G + {N_F}F + {N_C}C = {N_G+N_F+N_C} παίκτες")
    print(f"Formation:    {FORMATION}")
    print(f"Tolerance:    {TOLERANCE}")
    print()

    all_players = build_players()
    all_coaches = build_coaches()

    subset = build_subset(all_players)
    print(f"Subset φορτώθηκε: {len(subset)} παίκτες")

    by_pos = {"G": 0, "F": 0, "C": 0}
    for p in subset.values():
        by_pos[p.pos] += 1
    print(f"  G={by_pos['G']}  F={by_pos['F']}  C={by_pos['C']}")

    # Διάλεξε έναν coach (π.χ. PAM με καλό adj)
    coach = all_coaches.get("PAM") or next(iter(all_coaches.values()))
    print(f"Coach:        {coach.name} ({coach.id})  "
          f"avg={coach.avg_xp:.2f}  adj={coach.effective_xp:.2f}")
    print()

    # ---- BRUTE FORCE ----
    print("→ Brute-force...")
    t0 = time.time()
    brute_score, brute_combo = brute_force_best(subset, coach, FORMATION)
    t_brute = time.time() - t0
    print(f"  Τέλος σε {t_brute:.2f}s")
    print(f"  Best score:  {brute_score:.4f}")
    print()

    # ---- MILP ----
    print("→ MILP...")
    t0 = time.time()
    milp_res = run_milp(subset, all_coaches, coach, FORMATION)
    t_milp = time.time() - t0
    print(f"  Τέλος σε {t_milp:.2f}s")

    if milp_res is None:
        print("  ❌ MILP: infeasible!")
        return

    print(f"  Best score:  {milp_res.score:.4f}")
    print()

    # ---- ΣΥΓΚΡΙΣΗ ----
    print("=" * 70)
    print("ΑΠΟΤΕΛΕΣΜΑ")
    print("=" * 70)
    diff = abs(brute_score - milp_res.score)

    if diff < TOLERANCE:
        print(f"✅ PASS — diff = {diff:.6f} (< {TOLERANCE})")
    else:
        print(f"❌ FAIL — diff = {diff:.6f} (>= {TOLERANCE})")

    print()
    print(f"Brute:  {brute_score:.4f}")
    print(f"MILP:   {milp_res.score:.4f}")
    print()

    # Λεπτομέρειες brute
    if brute_combo:
        roster_ids, starter_ids, sixth_id, captain_id = brute_combo
        print("Brute-force roster:")
        print(f"  Roster:    {sorted(roster_ids)}")
        print(f"  Starters:  {sorted(starter_ids)}")
        print(f"  6th:       {sixth_id}")
        print(f"  Captain:   {captain_id}")

    print()
    print("MILP roster:")
    print(f"  Roster:    {sorted(p.id for p in milp_res.players)}")
    print(f"  Starters:  {sorted(p.id for p in milp_res.starters)}")
    print(f"  6th:       {milp_res.sixth.id}")
    print(f"  Captain:   {milp_res.captain.id}")


if __name__ == "__main__":
    main()