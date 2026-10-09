#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_injuries.py
-----------------
Scrape BasketNews EuroLeague injury report.
Γράφει: ../json/injuries.json

Εκτέλεση: py fetch_injuries.py
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import DATA_RAW
# Auto-install
import subprocess, importlib
for pkg, mod in [("beautifulsoup4", "bs4"), ("requests", "requests"), ("lxml", "lxml")]:
    try:
        importlib.import_module(mod)
    except ImportError:
        print(f"[setup] Installing {pkg} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

import requests
from bs4 import BeautifulSoup


OUT_JSON = DATA_RAW / "injuries.json"

URL = "https://basketnews.com/leagues/25-euroleague/injured.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36"
}


# Team mapping: BasketNews (uppercase) → short code
TEAM_MAP = {
    "ANADOLU EFES ISTANBUL":           "ULK",
    "ARMANI OLIMPIA MILAN":            "MIL",
    "BASKONIA VITORIA-GASTEIZ":        "BAS",
    "KOSNER BASKONIA VITORIA-GASTEIZ": "BAS",
    "BESIKTAS ISTANBUL":               "BES",
    "CRVENA ZVEZDA MERIDIANBET BELGRADE": "RED",
    "CRVENA ZVEZDA BELGRADE":          "RED",
    "DUBAI BASKETBALL":                "DUB",
    "FC BARCELONA":                    "BAR",
    "FC BAYERN MUNICH":                "MUN",
    "FENERBAHCE BEKO ISTANBUL":        "IST",
    "FENERBAHCE ISTANBUL":             "IST",
    "HAPOEL IBI TEL AVIV":             "HTA",
    "LDLC ASVEL VILLEURBANNE":         "ASV",
    "MACCABI RAPYD TEL AVIV":          "TEL",
    "OLYMPIACOS PIRAEUS":              "OLY",
    "PANATHINAIKOS AKTOR ATHENS":      "PAN",
    "PARIS BASKETBALL":                "PRS",
    "PARTIZAN MOZZART BET BELGRADE":   "PAR",
    "REAL MADRID":                     "MAD",
    "VALENCIA BASKET":                 "PAM",
    "VIRTUS BOLOGNA":                  "VIR",
    "ZALGIRIS KAUNAS":                 "ZAL",
}

POS_MAP = {
    "PG": "G", "SG": "G",
    "SF": "F", "PF": "F",
    "C":  "C",
}

STATUS_MAP = {
    "OUT":            "out",
    "INDEFINITELY":   "out",
    "OUT FOR SEASON": "out",
    "OUT OF TEAM":    "out",
    "LONG-TERM":      "out",
    "GAME-TIME":      "game_time",
    "UNCERTAIN":      "uncertain",
    "DOUBTFUL":       "doubtful",
    "EXPECTED":       "expected",
    "READY":          "ready",
}


def normalize_team(name: str) -> str | None:
    key = re.sub(r"\s+", " ", name.strip().upper())
    if key in TEAM_MAP:
        return TEAM_MAP[key]
    # partial match
    for k, v in TEAM_MAP.items():
        if k in key or key in k:
            return v
    return None


def normalize_status(raw: str) -> str:
    key = raw.strip().upper()
    if key in STATUS_MAP:
        return STATUS_MAP[key]
    for k, v in STATUS_MAP.items():
        if k in key:
            return v
    return "unknown"


def fetch() -> str:
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def parse(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if len(tables) < 2:
        raise RuntimeError("Δεν βρέθηκε ο πίνακας τραυματισμών")

    t = tables[1]
    rows = t.find_all("tr")

    players = []
    current_team = None
    current_team_raw = None
    skipped = 0

    for tr in rows:
        cells = tr.find_all(["td", "th"])
        texts = [c.get_text(strip=True) for c in cells]

        # Skip header row
        if texts and texts[0] == "P":
            continue

        # Team header: 1 cell
        if len(texts) == 1 and texts[0]:
            raw = texts[0]
            short = normalize_team(raw)
            if short:
                current_team = short
                current_team_raw = raw
            else:
                # π.χ. "payabl." ή duplicate
                pass
            continue

        # Player row: 5 cells
        if len(texts) >= 5 and current_team:
            pos_raw = texts[0]
            player_name = texts[1]
            status_raw = texts[2]
            round_raw = texts[3]
            comment = texts[4]

            if not player_name:
                skipped += 1
                continue

            players.append({
                "team": current_team,
                "team_raw": current_team_raw,
                "position": POS_MAP.get(pos_raw, pos_raw),
                "position_raw": pos_raw,
                "player_name": player_name,
                "status": normalize_status(status_raw),
                "status_raw": status_raw,
                "round": round_raw,
                "comment": comment,
            })
        else:
            skipped += 1

    return players


def main():
    print("=" * 60)
    print("FETCH INJURIES — BasketNews")
    print("=" * 60)

    print(f"\n→ GET {URL}")
    html = fetch()
    print(f"  HTML: {len(html)} bytes")

    players = parse(html)
    print(f"\n  Players: {len(players)}")

    # Group by team
    by_team = {}
    for p in players:
        by_team.setdefault(p["team"], []).append(p)

    # Counts by status
    by_status = {}
    for p in players:
        by_status[p["status"]] = by_status.get(p["status"], 0) + 1

    print(f"  Teams:   {len(by_team)}")
    print(f"  Status:  {by_status}")

    # Output
    out = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "source_url": URL,
        "total": len(players),
        "by_team": {t: len(v) for t, v in by_team.items()},
        "by_status": by_status,
        "players": players,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n→ {OUT_JSON}")

    # Preview
    print("\nΔείγμα (πρώτοι 10):")
    for p in players[:10]:
        print(f"  {p['team']:<4} {p['position']:<2} "
              f"{p['player_name']:<30} {p['status']:<10} {p['round']}")


if __name__ == "__main__":
    main()