#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_sanity.py
------------------
Sanity checks στον optimizer με το πλήρες dataset (247 παίκτες).

Τρέχει το ίδιο dummy team με τον server (seed=42, Obradovic, cash=10)
και ελέγχει:
  1. Positions: 4G / 4F / 2C
  2. Duplicates: κανένας παίκτης 2 φορές
  3. Captain ∈ starters
  4. Cash: Σin - Σout ≤ cash
  5. 3 λύσεις διαφορετικές
  6. Score consistency
  7. Fallback ratio λογικό

Εκτέλεση:  py validate_sanity.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.optimize.constraints import (
    Player, Coach, CurrentTeam, OptimizerInput,
    TOTAL_G, TOTAL_F, TOTAL_C, TOTAL_PLAYERS,
    BENCH_MULT, STARTER_MULT, SIXTH_MULT, CAPTAIN_MULT, COACH_MULT,
    build_players, build_coaches,
)
from core.optimize.best_team import solve_scenario, SolveResult


SEED = 42
CASH = 10.0
MAX_TRANSFERS = 4


# ------------------------------------------------------------
# DUMMY TEAM (ίδιο με server)
# ------------------------------------------------------------

def _build_dummy_team(seed: int = SEED) -> CurrentTeam:
    all_players = build_players()
    all_coaches = build_coaches()

    rng = random.Random(seed)
    by_pos: dict[str, list[Player]] = {"G": [], "F": [], "C": []}
    for p in all_players.values():
        if p.is_available:
            by_pos[p.pos].append(p)
    for k in by_pos:
        rng.shuffle(by_pos[k])

    chosen = (
        by_pos["G"][:TOTAL_G]
        + by_pos["F"][:TOTAL_F]
        + by_pos["C"][:TOTAL_C]
    )
    coach = next(
        (c for c in all_coaches.values() if "obradovic" in c.name.lower()),
        next(iter(all_coaches.values())),
    )
    return CurrentTeam(
        players=chosen, coach=coach,
        formation=None, captain_id=None,
        squad_value=0.0, cash=CASH,
    )


# ------------------------------------------------------------
# CHECKS
# ------------------------------------------------------------

def check_positions(r: SolveResult) -> tuple[bool, str]:
    counts = {"G": 0, "F": 0, "C": 0}
    for p in r.players:
        counts[p.pos] += 1
    ok = (counts["G"] == TOTAL_G
          and counts["F"] == TOTAL_F
          and counts["C"] == TOTAL_C)
    msg = f"G={counts['G']} F={counts['F']} C={counts['C']}"
    return ok, msg


def check_duplicates(r: SolveResult) -> tuple[bool, str]:
    ids = [p.id for p in r.players]
    ok = len(ids) == len(set(ids))
    msg = f"{len(ids)} παίκτες, {len(set(ids))} μοναδικοί"
    return ok, msg


def check_captain(r: SolveResult) -> tuple[bool, str]:
    starter_ids = {p.id for p in r.starters}
    ok = r.captain.id in starter_ids
    msg = f"captain={r.captain.name}"
    return ok, msg


def check_cash(r: SolveResult, cash: float) -> tuple[bool, str]:
    net = r.net_cost
    ok = net <= cash + 0.001   # tolerance
    msg = f"net={net:+.2f}  cash={cash:.2f}"
    return ok, msg


def check_distinct(results: list[SolveResult]) -> tuple[bool, str]:
    sigs = [frozenset(p.id for p in r.players) for r in results]
    ok = len(sigs) == len(set(sigs))
    msg = f"{len(sigs)} λύσεις, {len(set(sigs))} διαφορετικές"
    return ok, msg


def check_score_consistency(r: SolveResult) -> tuple[bool, str]:
    """Επαναϋπολογίζει το score από τα xpdk και συγκρίνει."""
    manual = 0.0
    for p in r.starters:
        m = CAPTAIN_MULT if p.id == r.captain.id else STARTER_MULT
        manual += p.xpdk * m
    manual += r.sixth.xpdk * SIXTH_MULT
    for p in r.bench:
        manual += p.xpdk * BENCH_MULT
    manual += r.coach.effective_xp * COACH_MULT

    diff = abs(manual - r.score)
    ok = diff < 0.01
    msg = f"manual={manual:.4f}  optimizer={r.score:.4f}  diff={diff:.6f}"
    return ok, msg


def check_fallback_ratio() -> tuple[bool, str]:
    """Ελέγχει ότι το fallback ratio είναι λογικό (0.5-1.5)."""
    players = build_players()
    ratio = getattr(build_players, "last_ratio", None)
    if ratio is None:
        return False, "δεν υπολογίστηκε"
    ok = 0.5 < ratio < 1.5
    msg = f"ratio={ratio}"
    return ok, msg


# ------------------------------------------------------------
# RUN
# ------------------------------------------------------------

def run_checks(results: list[SolveResult], cash: float, label: str):
    print(f"\n{'=' * 70}")
    print(f"SCENARIO {label}  ({len(results)} λύσεις)")
    print(f"{'=' * 70}")

    if not results:
        print("  ❌ Καμία λύση!")
        return False

    all_ok = True

    for i, r in enumerate(results, 1):
        print(f"\n  Λύση #{i}  formation={r.formation}  score={r.score:.2f}")

        checks = [
            ("Positions",       check_positions(r)),
            ("Duplicates",      check_duplicates(r)),
            ("Captain",         check_captain(r)),
            ("Cash",            check_cash(r, cash)),
            ("Score consistency", check_score_consistency(r)),
        ]

        for name, (ok, msg) in checks:
            icon = "✅" if ok else "❌"
            print(f"    {icon} {name:<20} {msg}")
            if not ok:
                all_ok = False

    # Distinct check στο σύνολο των λύσεων
    ok, msg = check_distinct(results)
    icon = "✅" if ok else "❌"
    print(f"\n    {icon} {'Distinct rosters':<20} {msg}")
    if not ok:
        all_ok = False

    return all_ok


def main():
    print("=" * 70)
    print("VALIDATE SANITY — πλήρες dataset (247 παίκτες)")
    print("=" * 70)

    players = build_players()
    coaches = build_coaches()
    print(f"Players: {len(players)}")
    print(f"Coaches: {len(coaches)}")

    # Fallback ratio
    ok, msg = check_fallback_ratio()
    icon = "✅" if ok else "❌"
    print(f"\n{icon} Fallback ratio: {msg}")

    # Dummy team
    current = _build_dummy_team()
    print(f"\nDummy team (seed={SEED}, cash={CASH}):")
    for p in current.players:
        print(f"  {p.pos}  {p.name:<35} {p.team:<4}  cr={p.credits:5.1f}  xpdk={p.xpdk:5.2f}")
    print(f"  COACH  {current.coach.name}  (adj={current.coach.effective_xp:.2f})")

    input_ = OptimizerInput(
        current_team=current,
        max_transfers=MAX_TRANSFERS,
        scenarios=["A", "B"],
    )

    # Scenario A
    print("\n→ Solving Scenario A...")
    res_a = solve_scenario(input_, "A")
    ok_a = run_checks(res_a, CASH, "A")

    # Scenario B
    print("\n→ Solving Scenario B...")
    res_b = solve_scenario(input_, "B")
    ok_b = run_checks(res_b, CASH, "B")

    # Τελικό αποτέλεσμα
    print(f"\n{'=' * 70}")
    print("ΤΕΛΙΚΟ ΑΠΟΤΕΛΕΣΜΑ")
    print(f"{'=' * 70}")
    if ok_a and ok_b:
        print("✅ ΟΛΑ ΤΑ CHECKS ΠΕΡΑΣΑΝ")
    else:
        print("❌ ΚΑΠΟΙΑ CHECKS ΑΠΕΤΥΧΑΝ")
        sys.exit(1)


if __name__ == "__main__":
    main()