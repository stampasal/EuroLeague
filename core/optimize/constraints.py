# ============================================================
# scripts/optimize/constraints.py
# ------------------------------------------------------------
# Ορισμός δεδομένων + κανόνων για τον Best Fantasy Team Optimizer.
#
# Υποστηρίζει:
#   - Παίκτες με prediction (xpdk)
#   - Fallback παίκτες χωρίς prediction (xpdk = PIR × ratio)
#   - Coaches με adj_avg_xp (home/opp/streak adjusted)
#   - Injuries: out → is_available=False, uncertain/game_time → xpdk × 0.5
#   - Merge position/team από injuries.json για παίκτες χωρίς stats
#
# Self-test:  py constraints.py
# ============================================================

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ------------------------------------------------------------
# 1. ΣΤΑΘΕΡΕΣ
# ------------------------------------------------------------

FORMATIONS: dict[str, dict[str, int]] = {
    "1-2-2": {"G": 1, "F": 2, "C": 2},
    "1-3-1": {"G": 1, "F": 3, "C": 1},
    "2-1-2": {"G": 2, "F": 1, "C": 2},
    "2-2-1": {"G": 2, "F": 2, "C": 1},
    "3-1-1": {"G": 3, "F": 1, "C": 1},
}

TOTAL_G = 4
TOTAL_F = 4
TOTAL_C = 2
TOTAL_PLAYERS = TOTAL_G + TOTAL_F + TOTAL_C  # 10

N_STARTERS = 5
N_SIXTH = 1
N_BENCH = 4
N_COACH = 1

STARTER_MULT = 1.0
SIXTH_MULT = 1.0
BENCH_MULT = 0.5
COACH_MULT = 1.0
CAPTAIN_MULT = 2.0

DEFAULT_BUDGET = 100.0
DEFAULT_MAX_TRANSFERS = 4

VALID_POSITIONS = {"G", "F", "C"}

DEFAULT_XPDK_RATIO = 0.85

INJURY_REDUCED_STATUSES = {"uncertain", "game_time", "doubtful"}
INJURY_REDUCED_MULT = 0.5


# ------------------------------------------------------------
# 2. DATACLASSES
# ------------------------------------------------------------

@dataclass
class Player:
    """Παίκτης για τον optimizer."""
    player_code: str
    name: str
    pos: str
    team: str
    credits: float
    xpdk: float
    confidence: str = "high"
    is_available: bool = True
    is_fallback: bool = False
    injury_status: str = ""
    injury_round: str = ""

    @property
    def id(self) -> str:
        return self.player_code


@dataclass
class Coach:
    """Προπονητής με adjusted xp για τον επόμενο αγώνα."""
    coach_id: str
    name: str
    team: str
    credits: float
    avg_xp: float
    adj_avg_xp: float = 0.0
    next_opp: str = ""
    next_is_home: bool = False

    @property
    def id(self) -> str:
        return self.coach_id

    @property
    def effective_xp(self) -> float:
        return self.adj_avg_xp if self.adj_avg_xp != 0.0 else self.avg_xp


@dataclass
class CurrentTeam:
    players: list[Player]
    coach: Coach
    formation: Optional[str] = None
    captain_id: Optional[str] = None
    squad_value: float = DEFAULT_BUDGET
    cash: float = 0.0

    @property
    def available_budget(self) -> float:
        return self.squad_value + self.cash

    @property
    def player_ids(self) -> set[str]:
        return {p.id for p in self.players}


@dataclass
class OptimizerInput:
    current_team: CurrentTeam
    max_transfers: int = DEFAULT_MAX_TRANSFERS
    scenarios: list[str] = field(default_factory=lambda: ["A", "B"])


# ------------------------------------------------------------
# 3. PATHS + LOADERS
# ------------------------------------------------------------

# Paths από core.paths (single source of truth)
from core.paths import APP_JS_DATA as JS_DATA, DATA_RAW, DATA_PROC, ROOT, LOGS
from core.logger import get_logger

log = get_logger("constraints", category="server")


def _read_js_payload(path: Path, var_prefixes: tuple[str, ...]) -> str:
    text = path.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        lines.append(line)
    text = "\n".join(lines).strip()

    for prefix in var_prefixes:
        idx = text.find(prefix)
        if idx != -1:
            text = text[idx + len(prefix):].lstrip()
            break

    text = text.rstrip().rstrip(";").rstrip()
    return text


def load_predictions(path: Optional[Path] = None) -> list[dict]:
    if path is None:
        path = JS_DATA / "player_predictions.js"
    raw = _read_js_payload(
        path,
        var_prefixes=(
            "const PLAYER_PREDICTIONS =",
            "window.PLAYER_PREDICTIONS =",
            "PLAYER_PREDICTIONS =",
        ),
    )
    return json.loads(raw)


def load_stats_2026(path: Optional[Path] = None) -> dict:
    if path is None:
        path = JS_DATA / "player-stats-2026.js"
    raw = _read_js_payload(
        path,
        var_prefixes=(
            "window.PLAYER_STATS_2026 =",
            "const PLAYER_STATS_2026 =",
            "PLAYER_STATS_2026 =",
        ),
    )
    return json.loads(raw)


def load_coaches_js(path: Optional[Path] = None) -> dict:
    if path is None:
        path = JS_DATA / "coaches.js"
    raw = _read_js_payload(
        path,
        var_prefixes=(
            "window.COACHES =",
            "const COACHES =",
            "COACHES =",
        ),
    )
    return json.loads(raw)


def load_coach_stats_js(path: Optional[Path] = None) -> dict:
    if path is None:
        path = JS_DATA / "coach_stats.js"
    raw = _read_js_payload(
        path,
        var_prefixes=(
            "window.COACH_STATS =",
            "const COACH_STATS =",
            "COACH_STATS =",
        ),
    )
    return json.loads(raw)


def load_injuries_js(path: Optional[Path] = None) -> dict:
    """Φορτώνει player_injuries.js → dict {name_key: {status, round, ...}}."""
    if path is None:
        path = JS_DATA / "player_injuries.js"

    if not path.exists():
        return {}

    raw = _read_js_payload(
        path,
        var_prefixes=(
            "window.PLAYER_INJURIES =",
            "const PLAYER_INJURIES =",
            "PLAYER_INJURIES =",
        ),
    )
    try:
        return json.loads(raw)
    except Exception:
        return {}


def load_injuries_json(path: Optional[Path] = None) -> dict:
    """Φορτώνει injuries.json (raw από BasketNews)."""
    if path is None:
        path = DATA_RAW / "injuries.json"

    if not path.exists():
        return {"players": []}

    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"players": []}


# ------------------------------------------------------------
# 4. BUILDERS
# ------------------------------------------------------------

def _compute_fallback_ratio(predictions: list[dict], stats: dict) -> float:
    ratios = []
    for pred in predictions:
        name = pred.get("player")
        if not name:
            continue
        xpdk = pred.get("xpdk")
        if xpdk is None:
            continue
        s = stats.get(name)
        if not s:
            continue
        pir = s.get("pir")
        if pir is None or pir <= 0:
            continue
        ratio = float(xpdk) / float(pir)
        if 0.1 < ratio < 3.0:
            ratios.append(ratio)

    if not ratios:
        return DEFAULT_XPDK_RATIO

    return round(sum(ratios) / len(ratios), 4)


def _surname_from_key(name_key: str) -> str:
    """'NUNN, KENDRICK' → 'NUNN'."""
    return name_key.split(",")[0].strip().upper()


def _surname_from_full(full: str) -> str:
    """'Kendrick Nunn' → 'NUNN'."""
    parts = full.strip().split()
    return parts[-1].upper() if parts else ""


def _build_injuries_index(injuries_json: dict) -> dict:
    """
    Φτιάχνει index: επώνυμο → injury_row (για merge position/team).
    Αν υπάρχουν πολλοί με ίδιο επώνυμο, κρατάει τον πρώτο.
    """
    idx = {}
    rows = injuries_json.get("players", []) if isinstance(injuries_json, dict) else []
    for row in rows:
        sn = _surname_from_full(row.get("player_name", ""))
        if not sn:
            continue
        if sn not in idx:
            idx[sn] = row
    return idx


def build_players(
    predictions: Optional[list[dict]] = None,
    stats: Optional[dict] = None,
    injuries: Optional[dict] = None,
) -> dict[str, Player]:
    if predictions is None:
        predictions = load_predictions()
    if stats is None:
        stats = load_stats_2026()
    if injuries is None:
        injuries = load_injuries_js()

    injuries_json = load_injuries_json()
    injuries_by_surname = _build_injuries_index(injuries_json)

    ratio = _compute_fallback_ratio(predictions, stats)
    build_players.last_ratio = ratio

    pred_by_name: dict[str, dict] = {}
    for pred in predictions:
        name = pred.get("player")
        if name:
            pred_by_name[name] = pred

    players: dict[str, Player] = {}
    n_with_pred = 0
    n_fallback_pir = 0
    n_fallback_zero = 0
    n_skipped = 0
    n_out = 0
    n_reduced = 0
    n_merged = 0

    for name, s in stats.items():
        if not name:
            continue
        credits = s.get("credits")
        if credits is None:
            n_skipped += 1
            continue

        pos = (s.get("position") or "").upper()
        team = s.get("team") or ""

        _had_pos = pos in VALID_POSITIONS
        _had_team = bool(team)

        if (not _had_pos) or (not _had_team):
            sn = _surname_from_key(name)
            inj_row = injuries_by_surname.get(sn)
            if inj_row is not None:
                if not _had_pos:
                    pos = (inj_row.get("position") or "").upper()
                if not _had_team:
                    team = inj_row.get("team") or ""

        if pos not in VALID_POSITIONS:
            n_skipped += 1
            continue
        if not team:
            n_skipped += 1
            continue

        if (not _had_pos and pos in VALID_POSITIONS) or (not _had_team and team):
            n_merged += 1

        pred = pred_by_name.get(name)
        if pred and pred.get("player_code") is not None:
            pid = str(pred["player_code"])
            xpdk = float(pred.get("xpdk") or 0.0)
            confidence = str(pred.get("confidence") or "high").lower()
            is_fallback = False
            n_with_pred += 1
        else:
            pid = name
            pir = s.get("pir")
            if pir is not None and float(pir) > 0:
                xpdk = round(float(pir) * ratio, 2)
                n_fallback_pir += 1
            else:
                xpdk = 0.0
                n_fallback_zero += 1
            confidence = "low"
            is_fallback = True

        inj = injuries.get(name, {})
        inj_status = inj.get("status", "")
        inj_round = inj.get("round", "")

        is_available = True
        if inj_status == "out":
            is_available = False
            n_out += 1
        elif inj_status in INJURY_REDUCED_STATUSES:
            xpdk = round(xpdk * INJURY_REDUCED_MULT, 2)
            n_reduced += 1

        player = Player(
            player_code=pid,
            name=name,
            pos=pos,
            team=team,
            credits=float(credits),
            xpdk=xpdk,
            confidence=confidence,
            is_available=is_available,
            is_fallback=is_fallback,
            injury_status=inj_status,
            injury_round=inj_round,
        )
        players[player.id] = player

    build_players.last_n_with_pred = n_with_pred
    build_players.last_n_fallback_pir = n_fallback_pir
    build_players.last_n_fallback_zero = n_fallback_zero
    build_players.last_n_skipped = n_skipped
    build_players.last_total = len(players)
    build_players.last_n_out = n_out
    build_players.last_n_reduced = n_reduced
    build_players.last_n_merged = n_merged

    return players


def build_coaches() -> dict[str, Coach]:
    coaches_raw = load_coaches_js()
    stats_raw = load_coach_stats_js()

    coaches_list = coaches_raw if isinstance(coaches_raw, list) else []

    coaches: dict[str, Coach] = {}
    for c in coaches_list:
        cid = c.get("team") or c.get("name")
        if not cid:
            continue
        credits = c.get("credits")
        if credits is None:
            continue

        s = stats_raw.get(cid, {}) if isinstance(stats_raw, dict) else {}

        avg_xp = c.get("avg_xp")
        if avg_xp is None:
            avg_xp = s.get("avg_xp", 0.0)

        adj_avg_xp = s.get("adj_avg_xp", None)
        if adj_avg_xp is None:
            adj_avg_xp = float(avg_xp or 0.0)
        else:
            adj_avg_xp = float(adj_avg_xp)

        next_opp = s.get("next_opp", "") or ""
        next_is_home = bool(s.get("next_is_home", False))

        coach = Coach(
            coach_id=str(cid),
            name=str(c.get("name") or cid),
            team=str(c.get("team") or ""),
            credits=float(credits),
            avg_xp=float(avg_xp or 0.0),
            adj_avg_xp=adj_avg_xp,
            next_opp=str(next_opp),
            next_is_home=next_is_home,
        )
        coaches[coach.id] = coach

    return coaches


def load_all() -> tuple[dict[str, Player], dict[str, Coach]]:
    return build_players(), build_coaches()


# ------------------------------------------------------------
# 5. HELPERS / VALIDATORS
# ------------------------------------------------------------

def get_formation_slots(formation: str) -> dict[str, int]:
    if formation not in FORMATIONS:
        raise ValueError(f"Άγνωστο formation: {formation!r}")
    return dict(FORMATIONS[formation])


def compute_cost(players: list[Player], coach: Optional[Coach] = None) -> float:
    total = sum(p.credits for p in players)
    if coach is not None:
        total += coach.credits
    return round(total, 2)


def compute_score(
    players: list[Player],
    coach: Coach,
    formation: str,
    captain_id: str,
) -> float:
    if formation not in FORMATIONS:
        raise ValueError(f"Άγνωστο formation: {formation!r}")

    f = FORMATIONS[formation]

    by_pos: dict[str, list[Player]] = {"G": [], "F": [], "C": []}
    for p in players:
        if p.pos in by_pos:
            by_pos[p.pos].append(p)

    for k in by_pos:
        by_pos[k].sort(key=lambda x: x.xpdk, reverse=True)

    starters: list[Player] = []
    used: set[str] = set()
    for pos, count in f.items():
        for p in by_pos[pos][:count]:
            starters.append(p)
            used.add(p.id)

    remaining = [p for p in players if p.id not in used]
    remaining.sort(key=lambda x: x.xpdk, reverse=True)
    if not remaining:
        raise ValueError("Δεν υπάρχουν αρκετοί παίκτες για sixth slot")
    sixth = remaining.pop(0)
    used.add(sixth.id)

    bench = remaining[:N_BENCH]

    score = 0.0
    for p in starters:
        mult = CAPTAIN_MULT if p.id == captain_id else STARTER_MULT
        score += p.xpdk * mult
    score += sixth.xpdk * SIXTH_MULT
    for p in bench:
        score += p.xpdk * BENCH_MULT
    score += coach.effective_xp * COACH_MULT

    return round(score, 2)


def validate_roster(
    players: list[Player],
    coach: Optional[Coach],
    formation: Optional[str] = None,
    captain_id: Optional[str] = None,
) -> list[str]:
    errors: list[str] = []

    if len(players) != TOTAL_PLAYERS:
        errors.append(f"Χρειάζονται {TOTAL_PLAYERS} παίκτες, βρέθηκαν {len(players)}.")

    counts = {"G": 0, "F": 0, "C": 0}
    for p in players:
        if p.pos not in counts:
            errors.append(f"Άγνωστη θέση για παίκτη {p.name}: {p.pos!r}")
            continue
        counts[p.pos] += 1

    if counts["G"] != TOTAL_G:
        errors.append(f"Guards: {counts['G']} (απαιτούνται {TOTAL_G}).")
    if counts["F"] != TOTAL_F:
        errors.append(f"Forwards: {counts['F']} (απαιτούνται {TOTAL_F}).")
    if counts["C"] != TOTAL_C:
        errors.append(f"Centers: {counts['C']} (απαιτούνται {TOTAL_C}).")

    if coach is None:
        errors.append("Λείπει ο coach.")

    if formation is not None and formation not in FORMATIONS:
        errors.append(f"Άγνωστο formation: {formation!r}")

    if captain_id is not None:
        ids = {p.id for p in players}
        if captain_id not in ids:
            errors.append(f"Ο captain {captain_id!r} δεν είναι στο ρόστερ.")

    ids = [p.id for p in players]
    if len(ids) != len(set(ids)):
        errors.append("Υπάρχουν διπλότυποι παίκτες στο ρόστερ.")

    return errors


def players_diff(
    old_team: CurrentTeam,
    new_players: list[Player],
    new_coach: Optional[Coach] = None,
) -> tuple[set[str], set[str], set[str]]:
    old_ids = old_team.player_ids
    new_ids = {p.id for p in new_players}

    players_out = old_ids - new_ids
    players_in = new_ids - old_ids

    coaches_out: set[str] = set()
    if new_coach is not None and new_coach.id != old_team.coach.id:
        coaches_out.add(old_team.coach.id)

    return players_out, players_in, coaches_out


# ------------------------------------------------------------
# 6. SELF-TEST
# ------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("constraints.py — self test")
    print("=" * 70)

    players = build_players()
    coaches = build_coaches()

    print(f"\nFallback ratio (xpdk/PIR): {getattr(build_players, 'last_ratio', '?')}")
    print(f"\nPlayers loaded: {len(players)}")
    print(f"  with prediction:    {getattr(build_players, 'last_n_with_pred', '?')}")
    print(f"  fallback (PIR):     {getattr(build_players, 'last_n_fallback_pir', '?')}")
    print(f"  fallback (PIR=0):   {getattr(build_players, 'last_n_fallback_zero', '?')}")
    print(f"  skipped:            {getattr(build_players, 'last_n_skipped', '?')}")
    print(f"  merged (injuries):  {getattr(build_players, 'last_n_merged', '?')}")

    print(f"\n  Injuries:")
    print(f"    OUT (unavailable): {getattr(build_players, 'last_n_out', '?')}")
    print(f"    reduced xpdk:      {getattr(build_players, 'last_n_reduced', '?')}")

    pos_counts = {"G": 0, "F": 0, "C": 0}
    for p in players.values():
        if p.is_available:
            pos_counts[p.pos] += 1
    print(f"\n  Available by position: G={pos_counts['G']}  F={pos_counts['F']}  C={pos_counts['C']}")

    top = sorted(
        [p for p in players.values() if p.is_available and not p.is_fallback],
        key=lambda x: x.xpdk, reverse=True
    )[:5]
    print("\n  Top 5 available (με prediction):")
    for p in top:
        flag = f" [{p.injury_status}]" if p.injury_status else ""
        print(f"    {p.name:35s} {p.pos} {p.team:4s} "
              f"credits={p.credits:5.1f}  xpdk={p.xpdk:5.2f}{flag}")

    injured = [p for p in players.values() if not p.is_available]
    print(f"\n  Unavailable players: {len(injured)}")
    for p in injured[:10]:
        print(f"    {p.name:35s} {p.pos} {p.team:4s} "
              f"status={p.injury_status}  round={p.injury_round}")

    reduced = [p for p in players.values()
               if p.is_available and p.injury_status in INJURY_REDUCED_STATUSES]
    print(f"\n  Reduced-xpdk players: {len(reduced)}")
    for p in reduced[:10]:
        print(f"    {p.name:35s} {p.pos} {p.team:4s} "
              f"xpdk={p.xpdk:5.2f}  status={p.injury_status}")

    print(f"\nCoaches loaded: {len(coaches)}")

    print("\nSelf-test OK.")