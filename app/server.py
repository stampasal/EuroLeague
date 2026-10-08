# ============================================================
# app/server.py
# ------------------------------------------------------------
# EuroLeague app server (port 5000).
#
# Σερβίρει το app + optimizer API. ΔΕΝ έχει script runner.
#
# Endpoints:
#   GET  /                     → app/html/EuroLeague.html
#   GET  /<path>               → static files (app/)
#   GET  /api/players          → λίστα παικτών
#   GET  /api/coaches          → λίστα coaches
#   GET  /api/optimize/test    → dummy team + 3 λύσεις
#   POST /api/optimize         → optimize από current team
#
# Εκκίνηση:  py app/server.py
# ============================================================

from __future__ import annotations

import random
import sys
import traceback
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, send_from_directory

# --- core imports ---
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.paths import APP, APP_HTML
from core.config import SERVER_HOST, SERVER_PORT_APP
from core.logger import get_logger

from core.optimize import (
    Player, Coach, CurrentTeam, OptimizerInput,
    TOTAL_G, TOTAL_F, TOTAL_C,
    DEFAULT_MAX_TRANSFERS,
    build_players, build_coaches,
)
from core.optimize import solve_scenario, SolveResult


log = get_logger("app_server", category="server")


app = Flask(
    __name__,
    static_folder=str(APP),
    static_url_path="",
)


@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


# ============================================================
# SERVE
# ============================================================

@app.route("/")
def index():
    return send_from_directory(str(APP_HTML), "EuroLeague.html")


@app.route("/<path:filename>")
def serve_static(filename: str):
    return send_from_directory(str(APP), filename)


# ============================================================
# SERIALIZERS
# ============================================================

def _player_to_dict(p: Player) -> dict:
    return {
        "id": p.id, "name": p.name, "pos": p.pos, "team": p.team,
        "credits": p.credits, "xpdk": p.xpdk,
        "confidence": p.confidence, "is_fallback": p.is_fallback,
        "injury_status": p.injury_status,
        "injury_round": p.injury_round,
        "is_available": p.is_available,
    }


def _coach_to_dict(c: Coach) -> dict:
    return {
        "id": c.id, "name": c.name, "team": c.team,
        "credits": c.credits, "avg_xp": c.avg_xp,
        "adj_avg_xp": c.effective_xp,
        "next_opp": c.next_opp,
        "next_is_home": c.next_is_home,
    }


def _result_to_dict(rank: int, r: SolveResult) -> dict:
    return {
        "rank": rank,
        "scenario": r.scenario,
        "formation": r.formation,
        "score": r.score,
        "cost": r.cost,
        "net_cost": r.net_cost,
        "coach_changed": r.coach_changed,
        "n_player_transfers": r.n_player_transfers,
        "total_transfers": r.total_transfers,
        "captain": _player_to_dict(r.captain),
        "starters": [_player_to_dict(p) for p in r.starters],
        "sixth": _player_to_dict(r.sixth),
        "bench": [_player_to_dict(p) for p in r.bench],
        "coach": _coach_to_dict(r.coach),
        "coach_out": _coach_to_dict(r.coach_out) if r.coach_out else None,
        "coach_in": _coach_to_dict(r.coach_in) if r.coach_in else None,
        "transfers_in": [_player_to_dict(p) for p in r.transfers_in],
        "transfers_out": [_player_to_dict(p) for p in r.transfers_out],
    }


# ============================================================
# DUMMY TEAM
# ============================================================

def _build_dummy_team(seed: int = 42) -> CurrentTeam:
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
        squad_value=0.0, cash=10.0,
    )


# ============================================================
# OPTIMIZE
# ============================================================

def _find_player(pid_or_name: str, all_players: dict[str, Player]) -> Optional[Player]:
    p = all_players.get(pid_or_name)
    if p is not None:
        return p
    for player in all_players.values():
        if player.name == pid_or_name:
            return player
    return None


def _run_optimizer(current: CurrentTeam,
                   max_transfers: int = DEFAULT_MAX_TRANSFERS) -> list[dict]:
    input_ = OptimizerInput(
        current_team=current,
        max_transfers=max_transfers,
        scenarios=["A", "B"],
    )
    all_results: list[SolveResult] = []
    for sc in input_.scenarios:
        all_results.extend(solve_scenario(input_, sc))

    all_results.sort(key=lambda r: r.score, reverse=True)

    final: list[SolveResult] = []
    seen: list[frozenset] = []
    for r in all_results:
        sig = frozenset(p.id for p in r.players)
        if any(sig == prev for prev in seen):
            continue
        final.append(r)
        seen.append(sig)
        if len(final) >= 3:
            break

    return [_result_to_dict(i + 1, r) for i, r in enumerate(final)]


# ============================================================
# ENDPOINTS
# ============================================================

@app.route("/api/players", methods=["GET"])
def api_players():
    try:
        players = build_players()
        lst = [_player_to_dict(p) for p in players.values()]
        lst.sort(key=lambda x: x["name"])
        return jsonify({"ok": True, "count": len(lst), "players": lst})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/coaches", methods=["GET"])
def api_coaches():
    try:
        coaches = build_coaches()
        lst = [_coach_to_dict(c) for c in coaches.values()]
        lst.sort(key=lambda x: x["name"])
        return jsonify({"ok": True, "count": len(lst), "coaches": lst})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/optimize/test", methods=["GET"])
def optimize_test():
    try:
        current = _build_dummy_team()
        results = _run_optimizer(current, max_transfers=DEFAULT_MAX_TRANSFERS)
        return jsonify({
            "ok": True,
            "current_team": {
                "players": [_player_to_dict(p) for p in current.players],
                "coach": _coach_to_dict(current.coach),
                "cash": current.cash,
            },
            "results": results,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/optimize", methods=["POST", "OPTIONS"])
def optimize():
    if request.method == "OPTIONS":
        return ("", 204)
    try:
        data = request.get_json(force=True) or {}
        player_ids = data.get("player_ids") or []
        coach_id = data.get("coach_id")
        cash = float(data.get("cash", 0.0))
        max_tr = int(data.get("max_transfers", DEFAULT_MAX_TRANSFERS))

        if len(player_ids) != 10:
            return jsonify({"ok": False, "error": f"Χρειάζονται 10 player_ids, βρέθηκαν {len(player_ids)}."}), 400
        if len(set(player_ids)) != len(player_ids):
            return jsonify({"ok": False, "error": "Έχεις βάλει τον ίδιο παίκτη 2 φορές."}), 400
        if not coach_id:
            return jsonify({"ok": False, "error": "Λείπει coach_id."}), 400

        all_players = build_players()
        all_coaches = build_coaches()

        players: list[Player] = []
        missing: list[str] = []
        for pid in player_ids:
            p = _find_player(str(pid), all_players)
            if p is None:
                missing.append(str(pid))
            else:
                players.append(p)

        if missing:
            return jsonify({"ok": False, "error": f"Άγνωστοι παίκτες: {', '.join(missing)}"}), 400

        coach = all_coaches.get(str(coach_id))
        if coach is None:
            return jsonify({"ok": False, "error": f"Άγνωστος coach_id: {coach_id!r}"}), 400

        current = CurrentTeam(
            players=players, coach=coach,
            formation=None, captain_id=None,
            squad_value=0.0, cash=cash,
        )
        results = _run_optimizer(current, max_transfers=max_tr)
        return jsonify({
            "ok": True,
            "current_team": {
                "players": [_player_to_dict(p) for p in current.players],
                "coach": _coach_to_dict(current.coach),
                "cash": current.cash,
            },
            "results": results,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    log.info("=" * 60)
    log.info("EuroLeague App Server")
    log.info("=" * 60)
    log.info(f"APP:  {APP}")
    log.info(f"URL:  http://{SERVER_HOST}:{SERVER_PORT_APP}/")
    log.info("=" * 60)
    app.run(host=SERVER_HOST, port=SERVER_PORT_APP, debug=False, threaded=True)