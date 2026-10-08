# scrape_basketstories_player_stats.py
# Scrape player.php για κάθε BS ID → per-game averages + totals (FR, BLA, FTM, FTA, FGM, FGA)
# Output: ../json/basketstories_player_stats.json
#
# Table 0 headers: Round|Game|MP|PTS|2FG|3FG|FT|OR|DR|TR|AS|STL|TO|BL|BLA|F|FR|RKG

# --- Auto-install dependencies (μόνο αν λείπουν) ---
import subprocess, sys, importlib

for pkg, mod in [("beautifulsoup4", "bs4"),
                 ("requests", "requests"),
                 ("lxml", "lxml")]:
    try:
        importlib.import_module(mod)
    except ImportError:
        print(f"[setup] Installing {pkg} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
# --- End auto-install ---

import os
import re
import json
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import DATA_RAW
import requests
from bs4 import BeautifulSoup

BASE       = "https://www.basketstories.net"
IN_PATH    = DATA_RAW / "basketstories_credits.json"
OUT_PATH   = DATA_RAW / "basketstories_player_stats.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36"
}

# Στήλες του Table 0 (index → key). Οι 4,5,6 (2FG/3FG/FT) γίνονται ειδική μεταχείριση.
COL = {
    2:  "min",
    3:  "pts",
    7:  "or",
    8:  "dr",
    9:  "reb",   # TR
    10: "ast",
    11: "stl",
    12: "to",
    13: "blk",   # BL
    14: "bla",   # BLA (blocks against)
    15: "pf",    # F (fouls committed)
    16: "fr",    # FR (fouls received / drawn)
    17: "pir",   # RKG
}
EXTRA = ["fgm", "fga", "ftm", "fta"]


def parse_mp(s):
    """'29:11' -> 29.183"""
    if not s:
        return 0.0
    m = re.match(r"(\d+):(\d+)", str(s))
    if not m:
        return 0.0
    return int(m.group(1)) + int(m.group(2)) / 60.0


def parse_num(s):
    """'' -> 0, '5' -> 5.0, '0.7' -> 0.7"""
    if s is None:
        return 0.0
    s = str(s).strip()
    if not s or s in ("-", "—"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_fg(s):
    """'4/5' -> (4, 5); '0/4' -> (0, 4); '' -> (0, 0)"""
    if not s or "/" not in str(s):
        return (0.0, 0.0)
    parts = str(s).split("/")
    try:
        made = float(parts[0]) if parts[0].strip() else 0.0
        att  = float(parts[1]) if len(parts) > 1 and parts[1].strip() else 0.0
        return (made, att)
    except ValueError:
        return (0.0, 0.0)


def find_game_log_table(soup):
    """Βρες table με headers Round + MP + FR."""
    for t in soup.find_all("table"):
        first = t.find("tr")
        if not first:
            continue
        cells = [c.get_text(strip=True) for c in first.find_all(["th", "td"])]
        if "Round" in cells and "MP" in cells and "FR" in cells:
            return t
    return None


def parse_player_page(html):
    soup = BeautifulSoup(html, "html.parser")
    t = find_game_log_table(soup)
    if not t:
        return None

    rows = t.find_all("tr")
    sums = {k: 0.0 for k in COL.values()}
    for k in EXTRA:
        sums[k] = 0.0
    games = 0

    for tr in rows:
        cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 18:
            continue
        if not cells[0].isdigit():
            continue
        # Απόκλεισε TOTALS / AVERAGE rows
        game_col = cells[1].strip().lower()
        if "total" in game_col or "average" in game_col:
            continue
        if not (game_col.startswith("vs ") or game_col.startswith("at ")):
            continue

        # Βασικές στήλες
        for idx, key in COL.items():
            raw = cells[idx]
            val = parse_mp(raw) if key == "min" else parse_num(raw)
            sums[key] += val

        # 2FG (4), 3FG (5), FT (6)
        fg2_m, fg2_a = parse_fg(cells[4])
        fg3_m, fg3_a = parse_fg(cells[5])
        ft_m,  ft_a  = parse_fg(cells[6])
        sums["fgm"] += fg2_m + fg3_m
        sums["fga"] += fg2_a + fg3_a
        sums["ftm"] += ft_m
        sums["fta"] += ft_a

        games += 1

    if games == 0:
        return None

    avg    = {k: round(v / games, 2) for k, v in sums.items()}
    totals = {k: round(v, 2) for k, v in sums.items()}
    return {"games": games, "avg": avg, "totals": totals}


def main():
    print("=" * 60)
    print("SCRAPE BASKETSTORIES PLAYER STATS v2 (FR/BLA/FTM/FTA/FGM/FGA)")
    print("=" * 60)

    with open(IN_PATH, encoding="utf-8") as f:
        bs = json.load(f)

    players = bs["players"]
    print(f"[i] {len(players)} players να scraπαριστούν\n")

    session = requests.Session()
    session.headers.update(HEADERS)

    out = {}
    ok = 0
    fail = []

    for i, p in enumerate(players):
        bs_id = p.get("bs_id")
        if not bs_id:
            continue

        url = f"{BASE}/datacenter/player.php?competition=euroleague&player={bs_id}&season=2027"
        try:
            r = session.get(url, timeout=20)
            if r.status_code != 200:
                fail.append({"bs_id": bs_id, "err": f"HTTP {r.status_code}"})
                time.sleep(0.3)
                continue

            stats = parse_player_page(r.text)
            if not stats:
                fail.append({"bs_id": bs_id, "err": "parse_fail"})
                time.sleep(0.3)
                continue

            out[bs_id] = {
                "name_bs":   p.get("name_bs"),
                "name_norm": p.get("name_norm"),
                "team":      p.get("team"),
                "credits":   p.get("credits"),
                **stats,
            }
            ok += 1

            if (i + 1) % 25 == 0:
                print(f"  [{i+1:>3}/{len(players)}]  ok={ok:<3}  fail={len(fail)}")

            time.sleep(0.3)

        except Exception as e:
            fail.append({"bs_id": bs_id, "err": str(e)[:80]})
            time.sleep(0.3)

    output = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "count":      ok,
        "failed":     fail,
        "players":    out,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n[✓] {ok} OK, {len(fail)} failed → {OUT_PATH}")

    # Sample
    print("\n--- Sample (FR/BLA/FTA check) ---")
    for k, v in list(out.items())[:5]:
        a = v["avg"]
        t = v["totals"]
        sfp_full = a["reb"] + a["ast"] + a["stl"] + a["blk"] + a["fr"] - a["to"] - a["pf"] - a["bla"]
        print(f"  {v['name_bs']:<22} G={v['games']}  "
              f"FGA_tot={t['fga']} FTA_tot={t['fta']} TO_tot={t['to']} MP_tot={t['min']:.0f}  "
              f"SFP_full={round(sfp_full, 2)}")
    print("=" * 60)


if __name__ == "__main__":
    main()