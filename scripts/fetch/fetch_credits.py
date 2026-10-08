# scrape_basketstories_credits.py
# Scrape /datacenter/el_players.php → Credits + Fantasy Value + All-Games stats
# Output: ../json/basketstories_credits.json

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
import requests
from bs4 import BeautifulSoup

BASE = "https://www.basketstories.net"
URL = BASE + "/datacenter/el_players.php"
OUT_PATH = os.path.join("..", "json", "basketstories_credits.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36"
}


def norm_name(s):
    """'Vezenkov Sasha' -> 'sasha vezenkov' (lowercase, sorted tokens)."""
    if not s:
        return ""
    s = s.strip().lower()
    s = re.sub(r"[^a-zα-ωά-ώ0-9\s]", " ", s)
    tokens = [t for t in s.split() if t]
    return " ".join(sorted(tokens))


def parse_number(s):
    """'18.10' -> 18.10, '-' -> None, '' -> None."""
    if s is None:
        return None
    s = s.strip()
    if not s or s in ("-", "—", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def extract_bs_id(href):
    """https://...player.php?competition=euroleague&player=BS2235SV&season=2027#game-log -> BS2235SV"""
    if not href:
        return None
    m = re.search(r"player=([A-Z0-9]+)", href)
    return m.group(1) if m else None


def fetch():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="stats_table")
    if not table:
        raise RuntimeError("Δεν βρέθηκε table#stats_table")

    rows = table.find_all("tr")
    # Skip 3 header rows (title + section headers + th headers)
    # Data rows = όσα έχουν <td> με <a> στη θέση 0
    players = []
    skipped = 0
    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 11:
            skipped += 1
            continue

        a = tds[0].find("a")
        if not a:
            skipped += 1
            continue

        name_bs = a.get_text(strip=True)
        bs_id = extract_bs_id(a.get("href", ""))

        # Team: text από cell 1 (πριν το img), αφαιρούμε whitespace
        team_raw = tds[1].get_text(" ", strip=True)
        team = re.sub(r"\s+", " ", team_raw).strip()

        credits       = parse_number(tds[2].get_text(strip=True))
        fantasy_l3    = parse_number(tds[3].get_text(strip=True))
        fantasy_l4    = parse_number(tds[4].get_text(strip=True))
        fantasy_l5    = parse_number(tds[5].get_text(strip=True))
        fantasy_seas  = parse_number(tds[6].get_text(strip=True))
        allg_l3       = parse_number(tds[7].get_text(strip=True))
        allg_l4       = parse_number(tds[8].get_text(strip=True))
        allg_l5       = parse_number(tds[9].get_text(strip=True))
        allg_seas     = parse_number(tds[10].get_text(strip=True))

        players.append({
            "name_bs":   name_bs,
            "name_norm": norm_name(name_bs),
            "bs_id":     bs_id,
            "team":      team,
            "credits":   credits,
            "fantasy":   {"last3": fantasy_l3, "last4": fantasy_l4,
                          "last5": fantasy_l5, "season": fantasy_seas},
            "all_games": {"last3": allg_l3, "last4": allg_l4,
                          "last5": allg_l5, "season": allg_seas},
        })

    print(f"[i] Parsed {len(players)} players (skipped {skipped} header/empty rows)")
    return players


def build_lookup(players):
    """norm_name -> player (αν duplicate, κράτα τον πρώτο)."""
    out = {}
    dupes = 0
    for p in players:
        k = p["name_norm"]
        if not k:
            continue
        if k in out:
            dupes += 1
            continue
        out[k] = p
    if dupes:
        print(f"[!] {dupes} duplicate norm_names (κρατήθηκαν οι πρώτοι)")
    return out


def main():
    print(f"[i] Fetch: {URL}")
    html = fetch()
    print(f"[i] HTML: {len(html)} bytes")

    players = parse(html)
    by_norm = build_lookup(players)

    out = {
        "scraped_at":  datetime.now(timezone.utc).isoformat(),
        "source_url":  URL,
        "season":      "2027",
        "count":       len(players),
        "players":     players,
        "by_norm_name": by_norm,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[✓] Saved: {OUT_PATH}")

    # Sample
    print("\n--- Δείγμα (πρώτοι 5) ---")
    for p in players[:5]:
        print(f"  {p['name_bs']:<25} {p['team']:<5} credits={p['credits']}  bs_id={p['bs_id']}")


if __name__ == "__main__":
    main()