# ============================================================
# scripts/optimize/best_team.py
# ------------------------------------------------------------
# Best Fantasy Team Optimizer — MILP με PuLP.
#
# Σενάριο A: έως N αλλαγές παικτών, ΙΔΙΟΣ coach
# Σενάριο B: έως N αλλαγές παικτών + προαιρετικά αλλαγή coach
#
# Self-test:  py best_team.py
# ============================================================

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

import pulp

from core.optimize.constraints import (
    Player, Coach, CurrentTeam, OptimizerInput,
    FORMATIONS,
    TOTAL_G, TOTAL_F, TOTAL_C, TOTAL_PLAYERS,
    N_STARTERS, N_SIXTH, N_BENCH,
    STARTER_MULT, SIXTH_MULT, BENCH_MULT, COACH_MULT, CAPTAIN_MULT,
    DEFAULT_MAX_TRANSFERS,
    build_players, build_coaches,
    compute_cost,
)


# ------------------------------------------------------------
# 1. ΑΠΟΤΕΛΕΣΜΑ
# ------------------------------------------------------------

@dataclass
class SolveResult:
    scenario: str
    formation: str
    players: list[Player]
    coach: Coach
    starters: list[Player]
    sixth: Player
    bench: list[Player]
    captain: Player
    score: float
    cost: float
    transfers_out: list[Player]
    transfers_in: list[Player]
    coach_changed: bool
    coach_out: Optional[Coach] = None
    coach_in: Optional[Coach] = None
    formation_changed: bool = False

    @property
    def n_player_transfers(self) -> int:
        return len(self.transfers_in)

    @property
    def total_transfers(self) -> int:
        return self.n_player_transfers + (1 if self.coach_changed else 0)

    @property
    def net_cost(self) -> float:
        """Καθαρό κόστος (in - out) — συμπεριλαμβάνει coach αν άλλαξε."""
        player_net = (
            sum(p.credits for p in self.transfers_in)
            - sum(p.credits for p in self.transfers_out)
        )
        coach_net = 0.0
        if self.coach_changed and self.coach_in and self.coach_out:
            coach_net = self.coach_in.credits - self.coach_out.credits
        return round(player_net + coach_net, 2)


# ------------------------------------------------------------
# 2. SOLVER — ΕΝΑ MILP
# ------------------------------------------------------------

def _solve_once(
    all_players: dict[str, Player],
    all_coaches: dict[str, Coach],
    current_team: CurrentTeam,
    formation: str,
    scenario: str,
    max_transfers: int,
    cash: float,
    exclude_rosters: Optional[list[set[str]]] = None,
) -> Optional[SolveResult]:
    if formation not in FORMATIONS:
        raise ValueError(f"Άγνωστο formation: {formation!r}")
    f_slots = FORMATIONS[formation]

    players = {pid: p for pid, p in all_players.items() if p.is_available}
    player_ids = list(players.keys())

    coaches = dict(all_coaches)
    coach_ids = list(coaches.keys())

    current_ids = current_team.player_ids
    current_coach_id = current_team.coach.id

    prob = pulp.LpProblem(f"fantasy_{scenario}_{formation}", pulp.LpMaximize)

    x   = {pid: pulp.LpVariable(f"x_{pid}",   cat="Binary") for pid in player_ids}
    s   = {pid: pulp.LpVariable(f"s_{pid}",   cat="Binary") for pid in player_ids}
    six = {pid: pulp.LpVariable(f"six_{pid}", cat="Binary") for pid in player_ids}
    b   = {pid: pulp.LpVariable(f"b_{pid}",   cat="Binary") for pid in player_ids}
    cap = {pid: pulp.LpVariable(f"cap_{pid}", cat="Binary") for pid in player_ids}
    c   = {kid: pulp.LpVariable(f"c_{kid}",   cat="Binary") for kid in coach_ids}

    # Objective — effective_xp
    obj = pulp.lpSum(
        players[pid].xpdk * (s[pid] + six[pid] + BENCH_MULT * b[pid] + cap[pid])
        for pid in player_ids
    ) + pulp.lpSum(
        coaches[kid].effective_xp * c[kid] for kid in coach_ids
    )
    prob += obj

    # Slot constraints
    for pid in player_ids:
        prob += x[pid] == s[pid] + six[pid] + b[pid], f"slot_{pid}"

    prob += pulp.lpSum(x.values()) == TOTAL_PLAYERS, "total_players"
    prob += pulp.lpSum(s.values()) == N_STARTERS, "total_starters"
    prob += pulp.lpSum(six.values()) == N_SIXTH, "total_sixth"
    prob += pulp.lpSum(b.values()) == N_BENCH, "total_bench"

    prob += pulp.lpSum(cap.values()) == 1, "total_captain"
    for pid in player_ids:
        prob += cap[pid] <= s[pid], f"cap_starter_{pid}"

    # Θέσεις
    for pos, total in (("G", TOTAL_G), ("F", TOTAL_F), ("C", TOTAL_C)):
        prob += pulp.lpSum(
            x[pid] for pid in player_ids if players[pid].pos == pos
        ) == total, f"pos_total_{pos}"

    for pos, count in f_slots.items():
        prob += pulp.lpSum(
            s[pid] for pid in player_ids if players[pid].pos == pos
        ) == count, f"pos_starters_{pos}"

    # Coach
    prob += pulp.lpSum(c.values()) == 1, "total_coach"

    # Transfers budget
    out_sum = pulp.lpSum(
        (1 - x[pid]) * players[pid].credits
        for pid in player_ids if pid in current_ids
    )
    in_sum = pulp.lpSum(
        x[pid] * players[pid].credits
        for pid in player_ids if pid not in current_ids
    )

    if current_coach_id in coaches:
        coach_out_sum = (1 - c[current_coach_id]) * coaches[current_coach_id].credits
    else:
        coach_out_sum = 0
    coach_in_sum = pulp.lpSum(
        c[kid] * coaches[kid].credits
        for kid in coach_ids if kid != current_coach_id
    )

    prob += (in_sum + coach_in_sum) - (out_sum + coach_out_sum) <= cash, "cash_constraint"

    # Max transfers
    non_current_ids = [pid for pid in player_ids if pid not in current_ids]
    prob += (
        pulp.lpSum(x[pid] for pid in non_current_ids) <= max_transfers
    ), "max_transfers"

    # Scenario A: ίδιος coach
    if scenario == "A":
        if current_coach_id not in coaches:
            return None
        prob += c[current_coach_id] == 1, "fixed_coach"

    # Diversification
    if exclude_rosters:
        for i, prev_roster in enumerate(exclude_rosters):
            valid_pids = [pid for pid in prev_roster if pid in player_ids]
            if valid_pids:
                prob += (
                    pulp.lpSum(x[pid] for pid in valid_pids) <= TOTAL_PLAYERS - 1
                ), f"diversify_roster_{i}"

    # Solve
    solver = pulp.PULP_CBC_CMD(msg=False)
    status = prob.solve(solver)

    if pulp.LpStatus[status] != "Optimal":
        return None

    # Extract
    chosen_players = [players[pid] for pid in player_ids if x[pid].value() > 0.5]
    chosen_coach_id = next(
        (kid for kid in coach_ids if c[kid].value() > 0.5), None
    )
    if chosen_coach_id is None:
        return None
    chosen_coach = coaches[chosen_coach_id]

    starters = [players[pid] for pid in player_ids if s[pid].value() > 0.5]
    sixth = next(players[pid] for pid in player_ids if six[pid].value() > 0.5)
    bench = [players[pid] for pid in player_ids if b[pid].value() > 0.5]
    captain = next(players[pid] for pid in player_ids if cap[pid].value() > 0.5)

    new_ids = {p.id for p in chosen_players}
    transfers_out = [p for p in current_team.players if p.id not in new_ids]
    transfers_in = [p for p in chosen_players if p.id not in current_ids]

    coach_changed = chosen_coach.id != current_team.coach.id
    coach_out = current_team.coach if coach_changed else None
    coach_in = chosen_coach if coach_changed else None

    cost = compute_cost(chosen_players, chosen_coach)

    return SolveResult(
        scenario=scenario,
        formation=formation,
        players=chosen_players,
        coach=chosen_coach,
        starters=starters,
        sixth=sixth,
        bench=bench,
        captain=captain,
        score=round(pulp.value(prob.objective), 3),
        cost=cost,
        transfers_out=transfers_out,
        transfers_in=transfers_in,
        coach_changed=coach_changed,
        coach_out=coach_out,
        coach_in=coach_in,
        formation_changed=(current_team.formation is not None
                           and current_team.formation != formation),
    )


# ------------------------------------------------------------
# 3. TOP-K
# ------------------------------------------------------------

def solve_top_k(
    all_players: dict[str, Player],
    all_coaches: dict[str, Coach],
    current_team: CurrentTeam,
    formation: str,
    scenario: str,
    max_transfers: int,
    cash: float,
    k: int = 3,
) -> list[SolveResult]:
    results: list[SolveResult] = []
    exclude_rosters: list[set[str]] = []

    for _ in range(k):
        res = _solve_once(
            all_players, all_coaches, current_team,
            formation, scenario, max_transfers, cash,
            exclude_rosters=exclude_rosters or None,
        )
        if res is None:
            break
        results.append(res)
        exclude_rosters.append({p.id for p in res.players})

    return results


# ------------------------------------------------------------
# 4. SOLVE
# ------------------------------------------------------------

def solve_scenario(
    input_: OptimizerInput,
    scenario: str,
    formations: Optional[list[str]] = None,
) -> list[SolveResult]:
    if formations is None:
        formations = list(FORMATIONS.keys())

    all_players = build_players()
    all_coaches = build_coaches()

    current = input_.current_team
    cash = current.cash

    if scenario == "A":
        max_tr = input_.max_transfers
    elif scenario == "B":
        max_tr = min(3, input_.max_transfers)
    else:
        max_tr = input_.max_transfers

    all_results: list[SolveResult] = []
    for form in formations:
        res_list = solve_top_k(
            all_players, all_coaches, current,
            form, scenario, max_tr, cash, k=3,
        )
        all_results.extend(res_list)

    all_results.sort(key=lambda r: r.score, reverse=True)

    final: list[SolveResult] = []
    seen_signatures: list[frozenset] = []
    for r in all_results:
        sig = frozenset(p.id for p in r.players)
        if any(sig == prev for prev in seen_signatures):
            continue
        final.append(r)
        seen_signatures.append(sig)
        if len(final) >= 3:
            break

    return final


def solve_all(input_: OptimizerInput) -> dict[str, list[SolveResult]]:
    out: dict[str, list[SolveResult]] = {}
    for sc in input_.scenarios:
        out[sc] = solve_scenario(input_, sc)
    return out


def pick_best_per_scenario(input_: OptimizerInput) -> dict[str, Optional[SolveResult]]:
    out: dict[str, Optional[SolveResult]] = {}
    for sc in input_.scenarios:
        results = solve_scenario(input_, sc)
        out[sc] = results[0] if results else None
    return out


# ------------------------------------------------------------
# 5. SELF-TEST
# ------------------------------------------------------------

def _build_dummy_team(
    all_players: dict[str, Player],
    all_coaches: dict[str, Coach],
    seed: int = 42,
) -> CurrentTeam:
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
        players=chosen,
        coach=coach,
        formation=None,
        captain_id=None,
        squad_value=0.0,
        cash=10.0,
    )


if __name__ == "__main__":
    print("=" * 60)
    print("best_team.py — self test")
    print("=" * 60)

    all_players = build_players()
    all_coaches = build_coaches()

    current = _build_dummy_team(all_players, all_coaches)

    print(f"\nCurrent team ({len(current.players)} players + 1 coach):")
    for p in sorted(current.players, key=lambda x: (x.pos, x.name)):
        print(f"  {p.pos}  {p.name:35s} {p.team:4s}  "
              f"credits={p.credits:5.1f}  xpdk={p.xpdk:5.2f}")
    print(f"  COACH  {current.coach.name:35s} {current.coach.team:4s}  "
          f"credits={current.coach.credits:5.1f}  "
          f"avg_xp={current.coach.avg_xp:5.2f}  "
          f"adj_xp={current.coach.effective_xp:5.2f}")
    print(f"  Cash: {current.cash}")

    input_ = OptimizerInput(
        current_team=current,
        max_transfers=4,
        scenarios=["A", "B"],
    )

    print("\nSolving...")
    results = solve_all(input_)

    for sc in ("A", "B"):
        lst = results.get(sc, [])
        print(f"\n{'=' * 60}")
        print(f"SCENARIO {sc}  ({len(lst)} λύσεις)")
        print(f"{'=' * 60}")
        if not lst:
            print("  (καμία λύση)")
            continue
        for i, r in enumerate(lst, 1):
            print(f"\n  #{i}  formation={r.formation}  score={r.score:.2f}  "
                  f"cost={r.cost:.1f}  net={r.net_cost:+.2f}  "
                  f"transfers={r.n_player_transfers}"
                  + ("+coach" if r.coach_changed else ""))
            print(f"      Captain: {r.captain.name}")
            print(f"      Coach:   {r.coach.name}  "
                  f"(avg={r.coach.avg_xp:.2f}  adj={r.coach.effective_xp:.2f})")
            if r.transfers_in:
                print(f"      IN:  " + ", ".join(
                    f"{p.name}({p.credits})" for p in r.transfers_in))
                print(f"      OUT: " + ", ".join(
                    f"{p.name}({p.credits})" for p in r.transfers_out))
            else:
                print("      (καμία αλλαγή παικτών)")
            if r.coach_changed:
                print(f"      COACH IN:  {r.coach_in.name} ({r.coach_in.credits})")
                print(f"      COACH OUT: {r.coach_out.name} ({r.coach_out.credits})")

    print("\nSelf-test OK.")