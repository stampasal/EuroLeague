#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_data_euroleague.py  (v2)
------------------------------
Αντικαθιστά το παλιό fetch_data.py (Dunkest) χρησιμοποιώντας το
euroleague_api package (official Euroleague data).

Changelog v2:
  - is_home column στα game_logs (local → True, road → False)
  - Positions από το /people endpoint του euroleague API
    (person dict στο game stats δεν έχει position — bug του API)
  - Positions cached σε .cache/people_{year}.pkl

Output: fantasy_data.json — ίδια δομή με πριν + is_home + σωστά positions.
"""

import argparse
import json
import pickle
import sys
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import DATA_RAW

import pandas as pd
import requests
from euroleague_api.game_stats import GameStats


DEFAULT_SEASONS = [2022, 2023, 2024, 2025, 2026]
CACHE_DIR       = DATA_RAW / ".cache"
OUTPUT_FILE     = DATA_RAW / "fantasy_data.json"

POSITION_MAP = {"Guard": "G", "Forward": "F", "Center": "C"}
PEOPLE_API_BASE = "https://api-live.euroleague.net/v2/competitions/E/seasons"


# ─────────────────────────────────────────────────────────────
# FETCH
# ─────────────────────────────────────────────────────────────

def fetch_season(year, use_cache=True):
    CACHE_DIR.mkdir(exist_ok=True)
    cache = CACHE_DIR / f"season_{year}.pkl"
    if use_cache and cache.exists():
        print(f"  [{year}] loading games from cache")
        return pd.read_pickle(cache)

    print(f"  [{year}] fetching from euroleague_api (~2-3 min) …")
    gs = GameStats()
    df = gs.get_game_stats_single_season(year)
    if df is None or len(df) == 0:
        raise RuntimeError(f"Season {year}: empty DataFrame")
    df.to_pickle(cache)
    print(f"  [{year}] got {len(df)} games × {df.shape[1]} cols → cached")
    return df


def fetch_positions(year, use_cache=True):
    CACHE_DIR.mkdir(exist_ok=True)
    cache = CACHE_DIR / f"people_{year}.pkl"
    if use_cache and cache.exists():
        print(f"  [{year}] loading positions from cache")
        with open(cache, "rb") as f:
            return pickle.load(f)

    url = f"{PEOPLE_API_BASE}/E{year}/people"
    print(f"  [{year}] fetching positions …")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    people = r.json().get("data", [])

    out = {}
    for p in people:
        if p.get("typeName") != "Player":
            continue
        code = p["person"]["code"]
        pos_name = p.get("positionName")
        out[code] = {
            "position_id":   p.get("position"),
            "position_name": pos_name,
            "position_norm": POSITION_MAP.get(pos_name, "?"),
        }

    with open(cache, "wb") as f:
        pickle.dump(out, f)
    print(f"  [{year}] cached {len(out)} players")
    return out


# ─────────────────────────────────────────────────────────────
# FLATTEN
# ─────────────────────────────────────────────────────────────

def _safe_float(v):
    try:
        if v is None:
            return 0.0
        f = float(v)
        if f != f:
            return 0.0
        return f
    except (TypeError, ValueError):
        return 0.0


def _opponent_code(game_row, side):
    other = "road" if side == "local" else "local"
    other_players = game_row.get(f"{other}.players")
    if isinstance(other_players, list) and other_players:
        try:
            return other_players[0]["player"]["club"]["code"]
        except (KeyError, TypeError, IndexError):
            return None
    return None


def flatten_season(df, season_year):
    rows = []
    for _, game in df.iterrows():
        season = int(game.get("Season", season_year))
        phase  = str(game.get("Phase", ""))
        rnd    = int(game.get("Round", 0))
        gcode  = int(game.get("Gamecode", 0))

        for side in ("local", "road"):
            players = game.get(f"{side}.players")
            if not isinstance(players, list):
                continue
            opp_code = _opponent_code(game, side)
            is_home  = (side == "local")

            for entry in players:
                try:
                    p = entry["player"]
                    s = entry.get("stats", {})
                    person = p["person"]
                    club   = p["club"]

                    rows.append({
                        "season":            season,
                        "phase":             phase,
                        "round":             rnd,
                        "gamecode":          gcode,
                        "player_code":       person["code"],
                        "player_name":       person["name"],
                        "team_code":         club["code"],
                        "opp_code":          opp_code,
                        "is_home":           is_home,
                        "time_played_s":     _safe_float(s.get("timePlayed")),
                        "valuation":         _safe_float(s.get("valuation")),
                        "points":            _safe_float(s.get("points")),
                        "total_rebounds":    _safe_float(s.get("totalRebounds")),
                        "assistances":       _safe_float(s.get("assistances")),
                        "steals":            _safe_float(s.get("steals")),
                        "turnovers":         _safe_float(s.get("turnovers")),
                        "blocks_favour":     _safe_float(s.get("blocksFavour")),
                        "blocks_against":    _safe_float(s.get("blocksAgainst")),
                        "fouls_commited":    _safe_float(s.get("foulsCommited")),
                        "fouls_received":    _safe_float(s.get("foulsReceived")),
                        "fgm_total":         _safe_float(s.get("fieldGoalsMadeTotal")),
                        "fga_total":         _safe_float(s.get("fieldGoalsAttemptedTotal")),
                        "fgm2":              _safe_float(s.get("fieldGoalsMade2")),
                        "fga2":              _safe_float(s.get("fieldGoalsAttempted2")),
                        "fgm3":              _safe_float(s.get("fieldGoalsMade3")),
                        "fga3":              _safe_float(s.get("fieldGoalsAttempted3")),
                        "ftm":               _safe_float(s.get("freeThrowsMade")),
                        "fta":               _safe_float(s.get("freeThrowsAttempted")),
                        "plus_minus":        _safe_float(s.get("plusMinus")),
                        "start_five":        bool(s.get("startFive", False)),
                    })
                except (KeyError, TypeError) as e:
                    print(f"    [WARN] skipping malformed player entry: {e}",
                          file=sys.stderr)
                    continue

    out = pd.DataFrame(rows)
    out["minutes"] = out["time_played_s"] / 60.0
    return out


# ─────────────────────────────────────────────────────────────
# BUILD PLAYERS
# ─────────────────────────────────────────────────────────────

def build_players(long_df, positions_map):
    long_df = long_df.sort_values(
        ["season", "gamecode"], kind="stable"
    ).reset_index(drop=True)
    long_df["chrono_index"] = range(len(long_df))

    players = []
    skipped = 0

    for code, grp in long_df.groupby("player_code", sort=False):
        grp = grp.sort_values(["season", "gamecode"]).reset_index(drop=True)

        latest = grp.iloc[-1]
        name      = latest["player_name"]
        team_code = latest["team_code"]

        pos_info = positions_map.get(str(code), {})
        pos_name = pos_info.get("position_name", "")
        pos_norm = pos_info.get("position_norm", "?")

        played = grp[grp["minutes"] > 0]
        gp = int(len(played))
        if gp == 0:
            skipped += 1
            continue

        def _mean(col):
            return round(float(played[col].mean()), 2)

        game_logs = []
        for _, g in grp.iterrows():
            game_logs.append({
                "season":       int(g["season"]),
                "phase":        str(g["phase"]),
                "round":        int(g["round"]),
                "gamecode":     int(g["gamecode"]),
                "chrono_index": int(g["chrono_index"]),
                "team_code":    str(g["team_code"]),
                "opp_code":     (str(g["opp_code"])
                                 if pd.notna(g["opp_code"]) else None),
                "is_home":      bool(g["is_home"]),
                "pdk":          round(float(g["valuation"]), 2),
                "pts":          int(g["points"]),
                "reb":          int(g["total_rebounds"]),
                "ast":          int(g["assistances"]),
                "stl":          int(g["steals"]),
                "blk":          int(g["blocks_favour"]),
                "to":           int(g["turnovers"]),
                "min":          round(float(g["minutes"]), 2),
                "fgm":          int(g["fgm_total"]),
                "fga":          int(g["fga_total"]),
                "pf":           int(g["fouls_commited"]),
                "plus_minus":   int(g["plus_minus"]),
                "starter":      bool(g["start_five"]),
            })

        players.append({
            "player_code":   str(code),
            "player":        name,
            "team":          team_code,
            "position_norm": pos_norm,
            "position_name": pos_name,
            "cr":            None,
            "gp":            gp,
            "pdk":           _mean("valuation"),
            "total_pdk":     round(float(played["valuation"].sum()), 2),
            "pts":           _mean("points"),
            "reb":           _mean("total_rebounds"),
            "ast":           _mean("assistances"),
            "stl":           _mean("steals"),
            "blk":           _mean("blocks_favour"),
            "to":            _mean("turnovers"),
            "min":           _mean("minutes"),
            "pf":            _mean("fouls_commited"),
            "game_logs":     game_logs,
        })

    print(f"  Built {len(players)} players  (skipped {skipped} with 0 minutes)")
    return players


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", type=int, nargs="+", default=DEFAULT_SEASONS)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--output", default=OUTPUT_FILE)
    args = ap.parse_args()

    print("=" * 60)
    print("EUROLEAGUE FANTASY — FETCHER v2")
    print("=" * 60)
    print(f"Seasons: {args.seasons}\n")

    use_cache = not args.no_cache

    # 1. Positions
    print("Fetching positions …")
    all_pos = {}
    for y in sorted(args.seasons):
        pos = fetch_positions(y, use_cache=use_cache)
        all_pos.update(pos)
    print(f"  Total players in people API: {len(all_pos)}")

    # 2. Game stats
    print("\nFetching game stats …")
    all_flat = []
    for y in args.seasons:
        try:
            raw = fetch_season(y, use_cache=use_cache)
            flat = flatten_season(raw, y)
            print(f"  [{y}] flattened → {len(flat)} player-game rows")
            all_flat.append(flat)
        except Exception as e:
            print(f"  [{y}] FAILED: {e}", file=sys.stderr)

    if not all_flat:
        print("ERROR: no seasons fetched. Aborting.", file=sys.stderr)
        sys.exit(1)

    long_df = pd.concat(all_flat, ignore_index=True)
    print(f"\nTotal flattened rows: {len(long_df)}")
    print(f"Unique players:       {long_df['player_code'].nunique()}")
    print(f"Unique teams:         {long_df['team_code'].nunique()}")

    print("\nBuilding player summaries + game logs …")
    players = build_players(long_df, all_pos)

    # 3. Sanity
    import statistics
    pdks = [p["pdk"] for p in players if p["gp"] >= 5]
    if pdks:
        print(f"\nPDK sanity (gp>=5):  n={len(pdks)}  "
              f"mean={statistics.mean(pdks):.2f}  "
              f"median={statistics.median(pdks):.2f}  "
              f"range=[{min(pdks):.2f}, {max(pdks):.2f}]")

    pos_counts = {}
    for p in players:
        pos_counts[p["position_norm"]] = pos_counts.get(p["position_norm"], 0) + 1
    print(f"Position distribution: {pos_counts}")

    n_home  = sum(1 for p in players for g in p["game_logs"] if g["is_home"])
    n_total = sum(len(p["game_logs"]) for p in players)
    print(f"is_home: {n_home}/{n_total} ({100*n_home/n_total:.1f}% home)")

    metadata = {
        "source":        "euroleague_api",
        "target":        "valuation (PIR)",
        "seasons":       args.seasons,
        "fetched_at":    datetime.now().isoformat(),
        "total_players": len(players),
    }

    out = {"metadata": metadata, "players": players}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    size_mb = Path(args.output).stat().st_size / (1024 * 1024)
    print(f"\n✅ Wrote {len(players)} players to {args.output}  ({size_mb:.1f} MB)")
    print("=" * 60)


if __name__ == "__main__":
    main()