# ============================================================
# core/optimize/__init__.py
# ------------------------------------------------------------
# Exposes optimizer API για εύκολο import:
#
#     from core.optimize import Player, solve_scenario
# ============================================================

from core.optimize.constraints import (
    Player, Coach, CurrentTeam, OptimizerInput,
    FORMATIONS,
    TOTAL_G, TOTAL_F, TOTAL_C, TOTAL_PLAYERS,
    N_STARTERS, N_SIXTH, N_BENCH,
    STARTER_MULT, SIXTH_MULT, BENCH_MULT, COACH_MULT, CAPTAIN_MULT,
    DEFAULT_BUDGET, DEFAULT_MAX_TRANSFERS,
    INJURY_REDUCED_STATUSES, INJURY_REDUCED_MULT,
    build_players, build_coaches, load_all,
    get_formation_slots, compute_cost, compute_score,
    validate_roster, players_diff,
)

from core.optimize.best_team import (
    solve_scenario, SolveResult,
)

__all__ = [
    "Player", "Coach", "CurrentTeam", "OptimizerInput",
    "FORMATIONS",
    "TOTAL_G", "TOTAL_F", "TOTAL_C", "TOTAL_PLAYERS",
    "N_STARTERS", "N_SIXTH", "N_BENCH",
    "STARTER_MULT", "SIXTH_MULT", "BENCH_MULT", "COACH_MULT", "CAPTAIN_MULT",
    "DEFAULT_BUDGET", "DEFAULT_MAX_TRANSFERS",
    "INJURY_REDUCED_STATUSES", "INJURY_REDUCED_MULT",
    "build_players", "build_coaches", "load_all",
    "get_formation_slots", "compute_cost", "compute_score",
    "validate_roster", "players_diff",
    "solve_scenario", "SolveResult",
]
