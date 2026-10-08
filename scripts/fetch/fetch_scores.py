#!/usr/bin/env python3
"""
EuroLeague Tracker — Auto Score Updater
Κατεβάζει τα τελευταία scores από το EuroLeague API
και ενημερώνει το js/data.js

Τρέξε με: py -3.14 "Update EuroLeague Scores.py"
"""

import subprocess
import sys
import os
import re
import shutil
from datetime import datetime

# ============================================================
# 1. AUTO-INSTALL
# ============================================================
REQUIRED_PACKAGES = ["euroleague-api"]

def ensure_packages():
    print("🔧 Έλεγχος απαιτούμενων packages...")
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"   ✓ {pkg} (εγκατεστημένο)")
        except ImportError:
            print(f"   ⚙️  Εγκατάσταση {pkg}...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "--quiet", pkg],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                print(f"   ✓ {pkg} (εγκαταστάθηκε)")
            except subprocess.CalledProcessError as e:
                print(f"   ✗ Σφάλμα: {e}")
                sys.exit(1)

ensure_packages()

from euroleague_api.schedule import Schedule
from euroleague_api.game_stats import GameStats

# ============================================================
# 2. ΡΥΘΜΙΣΕΙΣ
# ============================================================
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR   = os.path.dirname(_SCRIPT_DIR)

DATA_JS_PATH = os.path.join(_ROOT_DIR, "js", "config", "data.js")
BACKUP_DIR   = os.path.join(_ROOT_DIR, "backups")
HTML_PATH    = os.path.join(_ROOT_DIR, "EuroLeague.html")
SEASON       = 2026
COMPETITION  = "E"
FORCE_UPDATE = True   # True = αντικαθιστά ΟΛΑ τα σκορ με αυτά του API
                      # False = ενημερώνει μόνο όσα είναι null

# ============================================================
# 3. TEAM NAME NORMALIZATION
# ============================================================
TEAM_ALIASES = {
    # EuroLeague API → data.js
    "CRVENA ZVEZDA MERIDIANBET BELGRADE": "CRVENA ZVEZDA BELGRADE",
    "CRVENA ZVEZDA": "CRVENA ZVEZDA BELGRADE",
    "EA7 EMPORIO ARMANI MILAN": "ARMANI OLIMPIA MILAN",
    "OLIMPIA MILANO": "ARMANI OLIMPIA MILAN",
    "ARMANI OLIMPIA MILAN": "ARMANI OLIMPIA MILAN",
    "PANATHINAIKOS AKTOR ATHENS": "PANATHINAIKOS AKTOR ATHENS",
    "PANATHINAIKOS": "PANATHINAIKOS AKTOR ATHENS",
    "FENERBAHCE BEKO ISTANBUL": "FENERBAHCE ISTANBUL",
    "FENERBAHCE TARFIN ISTANBUL": "FENERBAHCE ISTANBUL",
    "FENERBAHCE": "FENERBAHCE ISTANBUL",
    "HAPOEL TEL AVIV": "HAPOEL IBI TEL AVIV",
    "HAPOEL": "HAPOEL IBI TEL AVIV",
    "MACCABI RAPYD TEL AVIV": "MACCABI RAPYD TEL AVIV",
    "MACCABI TEL AVIV": "MACCABI RAPYD TEL AVIV",
    "REAL MADRID": "REAL MADRID",
    "FC BARCELONA": "FC BARCELONA",
    "FC BAYERN MUNICH": "FC BAYERN MUNICH",
    "PARIS BASKETBALL": "PARIS BASKETBALL",
    "PARTIZAN MOZZART BET BELGRADE": "PARTIZAN MOZZART BELGRADE",
    "PARTIZAN MOZZART BELGRADE": "PARTIZAN MOZZART BELGRADE",
    "PARTIZAN": "PARTIZAN MOZZART BELGRADE",
    "OLYMPIACOS PIRAEUS": "OLYMPIACOS PIRAEUS",
    "OLYMPIACOS": "OLYMPIACOS PIRAEUS",
    "VALENCIA BASKET": "VALENCIA BASKET",
    "VIRTUS BOLOGNA": "VIRTUS BOLOGNA",
    "VIRTUS SEGAFREDO BOLOGNA": "VIRTUS BOLOGNA",
    "ZALGIRIS KAUNAS": "ZALGIRIS KAUNAS",
    "ZALGIRIS": "ZALGIRIS KAUNAS",
    "LDLC ASVEL VILLEURBANNE": "LDLC ASVEL VILLEURBANNE",
    "ASVEL": "LDLC ASVEL VILLEURBANNE",
    "ANADOLU EFES ISTANBUL": "ANADOLU EFES ISTANBUL",
    "ANADOLU EFES": "ANADOLU EFES ISTANBUL",
    "KOSNER BASKONIA VITORIA-GASTEIZ": "BASKONIA VITORIA-GASTEIZ",
    "BASKONIA VITORIA-GASTEIZ": "BASKONIA VITORIA-GASTEIZ",
    "BASKONIA": "BASKONIA VITORIA-GASTEIZ",
    "BESIKTAS ISTANBUL": "BESIKTAS ISTANBUL",
    "BESIKTAS": "BESIKTAS ISTANBUL",
    "DUBAI BASKETBALL": "DUBAI BASKETBALL",
}

def normalize_team(api_name):
    if not api_name:
        return None
    name = str(api_name).strip().upper()

    if name in TEAM_ALIASES:
        return TEAM_ALIASES[name]

    cleanup_patterns = [
        " TARFIN", " MERIDIANBET", " MOZZART BET", " KOSNER",
        " EMPORIO", " EA7", " SEGAFREDO", " BEKO",
    ]
    for pattern in cleanup_patterns:
        name = name.replace(pattern, "")
    name = name.strip()

    if name in TEAM_ALIASES:
        return TEAM_ALIASES[name]

    return name

# ============================================================
# 4. ΒΟΗΘΗΤΙΚΕΣ
# ============================================================
def log(msg, icon="•"):
    print(f"{icon} {msg}")

def backup_data_js():
    if not os.path.exists(DATA_JS_PATH):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"data_{ts}.js")
    shutil.copy2(DATA_JS_PATH, backup_path)
    log(f"Backup → {backup_path}", "💾")
    return backup_path

def cleanup_old_backups(keep=30):
    if not os.path.exists(BACKUP_DIR):
        return
    files = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.startswith("data_") and f.endswith(".js")],
        reverse=True
    )
    for old in files[keep:]:
        os.remove(os.path.join(BACKUP_DIR, old))
        log(f"Διαγράφηκε παλιό backup: {old}", "🗑️")

def open_html():
    """Ανοίγει το EuroLeague.html στον default browser."""
    import webbrowser
    if os.path.exists(HTML_PATH):
        webbrowser.open(f"file:///{HTML_PATH.replace(os.sep, '/')}")
        log("Άνοιγμα EuroLeague.html στον browser...", "🌐")

def parse_games_from_data_js(content):
    match = re.search(r"const GAMES_RAW\s*=\s*\[(.*?)\];", content, re.DOTALL)
    if not match:
        raise ValueError("Δεν βρέθηκε το GAMES_RAW στο data.js")
    raw = match.group(1).strip()
    games = []
    for line in raw.split("\n"):
        line = line.strip().rstrip(",")
        if not line.startswith("["):
            continue
        m = re.match(
            r'\[\s*(\d+)\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,'
            r'\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,'
            r'\s*(null|\d+)\s*,\s*(null|\d+)\s*\]',
            line
        )
        if m:
            hs = None if m.group(8) == "null" else int(m.group(8))
            aw = None if m.group(9) == "null" else int(m.group(9))
            games.append([
                int(m.group(1)), m.group(2), m.group(3), m.group(4), m.group(5),
                m.group(6), m.group(7), hs, aw
            ])
    return games

def write_games_to_data_js(content, games):
    lines = []
    for g in games:
        hs = "null" if g[7] is None else str(g[7])
        aw = "null" if g[8] is None else str(g[8])
        lines.append(
            f'[{g[0]},"{g[1]}","{g[2]}","{g[3]}","{g[4]}","{g[5]}","{g[6]}",{hs},{aw}]'
        )
    new_block = "const GAMES_RAW = [\n" + ",\n".join(lines) + "\n];"
    return re.sub(r"const GAMES_RAW\s*=\s*\[.*?\];", new_block, content, flags=re.DOTALL)

def write_boxscores_js(boxscores):
    """Γράφει το js/data/game-boxscores.js"""
    if not boxscores:
        return False

    BOX_JS_PATH = os.path.join(_ROOT_DIR, "js", "data", "game-boxscores.js")

    # Backup
    if os.path.exists(BOX_JS_PATH):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"game-boxscores_{ts}.js")
        shutil.copy2(BOX_JS_PATH, backup_path)

    def _s(v):
        """String escape για JS"""
        if v is None:
            return '""'
        s = str(v).replace("\\", "\\\\").replace('"', '\\"')
        return f'"{s}"'

    def _n(v):
        """Number ή null"""
        return "null" if v is None else str(v)

    def _b(v):
        return "true" if v else "false"

    lines = []
    lines.append("// ============================================================")
    lines.append("// GAME BOX SCORES — auto-generated from EuroLeague API")
    lines.append(f"// Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"// Games: {len(boxscores)}")
    lines.append("// ============================================================")
    lines.append("")
    lines.append("window.GAME_BOXSCORES = {")

    keys = sorted(boxscores.keys())
    for i, key in enumerate(keys):
        bs = boxscores[key]
        comma = "," if i < len(keys) - 1 else ""
        lines.append(f'  "{key}": {{')
        lines.append(f'    season: {bs["season"]},')
        lines.append(f'    gamecode: {bs["gamecode"]},')
        lines.append(f'    round: {bs["round"]},')
        lines.append(f'    date: {_s(bs["date"])},')
        lines.append(f'    home: {_s(bs["home"])},')
        lines.append(f'    away: {_s(bs["away"])},')
        lines.append(f'    hs: {bs["hs"]},')
        lines.append(f'    aw: {bs["aw"]},')
        lines.append(f'    players: [')
        for p in bs["players"]:
            p_line = (
                '{'
                f'name:{_s(p["name"])}, code:{_s(p["code"])}, alias:{_s(p["alias"])}, '
                f'jerseyName:{_s(p["jerseyName"])}, team:{_s(p["team"])}, '
                f'teamCode:{_s(p["teamCode"])}, pos:{_s(p["pos"])}, posNum:{_n(p["posNum"])}, '
                f'jersey:{_n(p["jersey"])}, '
                f'country:{_s(p["country"])}, countryFull:{_s(p["countryFull"])}, '
                f'birthDate:{_s(p["birthDate"])}, birthCountry:{_s(p["birthCountry"])}, '
                f'height:{_n(p["height"])}, weight:{_n(p["weight"])}, photo:{_s(p["photo"])}, '
                f'startFive:{_b(p["startFive"])}, played:{_b(p["played"])}, '
                f'sec:{_n(p["sec"])}, min:{_n(p["min"])}, pir:{_n(p["pir"])}, pts:{_n(p["pts"])}, '
                f'reb:{_n(p["reb"])}, rebD:{_n(p["rebD"])}, rebO:{_n(p["rebO"])}, '
                f'ast:{_n(p["ast"])}, stl:{_n(p["stl"])}, blk:{_n(p["blk"])}, '
                f'blkAgainst:{_n(p["blkAgainst"])}, to:{_n(p["to"])}, pf:{_n(p["pf"])}, fr:{_n(p["fr"])}, '
                f'fgm2:{_n(p["fgm2"])}, fga2:{_n(p["fga2"])}, '
                f'fgm3:{_n(p["fgm3"])}, fga3:{_n(p["fga3"])}, '
                f'fgm:{_n(p["fgm"])}, fga:{_n(p["fga"])}, '
                f'ftm:{_n(p["ftm"])}, fta:{_n(p["fta"])}, '
                f'plusMinus:{_n(p["plusMinus"])}'
                '}'
            )
            lines.append(f'      {p_line},')
        lines.append(f'    ]')
        lines.append(f'  }}{comma}')

    lines.append("};")
    lines.append("")

    with open(BOX_JS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    log(f"Εγγράφηκε: {BOX_JS_PATH}", "💾")
    return True

# ============================================================
# 5. ΚΥΡΙΑ ΛΟΓΙΚΗ
# ============================================================
def fetch_all_scores():
    log(f"Φόρτωση schedule season {SEASON}...", "📡")
    sched = Schedule(COMPETITION)
    df = sched.get_schedule(season=SEASON)
    log(f"Βρέθηκαν {len(df)} παιχνίδια στο schedule", "📋")

    played_mask = df["played"].astype(str).str.lower() == "true"
    played = df[played_mask]

    log(f"Από αυτά, {len(played)} έχουν παιχτεί", "🏀")

    if len(played) == 0:
        return {}

    gs = GameStats(COMPETITION)
    scores = {}
    total = len(played)
    errors = 0
    success = 0

    for i, (_, row) in enumerate(played.iterrows(), 1):
        gamecode = row.get("gamecode")
        api_home = row.get("hometeam")
        api_away = row.get("awayteam")

        gc_match = re.search(r"_(\d+)$", str(gamecode))
        gc_num = int(gc_match.group(1)) if gc_match else None

        if gc_num is None:
            continue

        print(f"   [{i}/{total}] {str(api_home)[:30]:30s} vs {str(api_away)[:30]:30s}...", end=" ")
        try:
            report = gs.get_game_report(SEASON, gc_num)
            if hasattr(report, "iloc") and len(report) > 0:
                r = report.iloc[0]
                hs = int(r["local.score"]) if "local.score" in r and r["local.score"] is not None else None
                aw = int(r["road.score"]) if "road.score" in r and r["road.score"] is not None else None
                home_api = r["local.club.name"] if "local.club.name" in r else api_home
                away_api = r["road.club.name"] if "road.club.name" in r else api_away

                if hs is not None and aw is not None:
                    home = normalize_team(home_api)
                    away = normalize_team(away_api)
                    scores[(home, away)] = (hs, aw)
                    success += 1
                    print(f"✓ {hs}-{aw}")
                else:
                    print("✗ no scores")
            else:
                print("✗ no data")
        except Exception as e:
            errors += 1
            print(f"✗ {str(e)[:60]}")
            continue

    log(f"Επιτυχίες: {success} / {total}, Σφάλματα: {errors}", "📊")
    return scores

def fetch_box_scores():
    """
    Κατεβάζει box scores για όλους τους played αγώνες.
    Επιστρέφει dict: { "2026-1": {...}, "2026-2": {...}, ... }
    """
    log("Φόρτωση box scores...", "📦")
    sched = Schedule(COMPETITION)
    df = sched.get_schedule(season=SEASON)

    played = df[df["played"].astype(str).str.lower() == "true"]

    gs = GameStats(COMPETITION)
    boxscores = {}
    total = len(played)

    for i, (_, row) in enumerate(played.iterrows(), 1):
        # Extract gamecode number
        gc_match = re.search(r"_(\d+)$", str(row.get("gamecode")))
        gc_num = int(gc_match.group(1)) if gc_match else None
        if gc_num is None:
            continue

        try:
            df_stats = gs.get_game_stats(SEASON, gc_num)
            if not hasattr(df_stats, "iloc") or len(df_stats) == 0:
                continue
            r = df_stats.iloc[0]

            # Teams από Schedule
            home = normalize_team(row.get("hometeam"))
            away = normalize_team(row.get("awayteam"))

            # Date: "Sep 24, 2026" → "2026-09-24"
            date_raw = str(row.get("date", "")).strip()
            try:
                date_str = datetime.strptime(date_raw, "%b %d, %Y").strftime("%Y-%m-%d")
            except Exception:
                date_str = date_raw[:10]

            # Round: "RS1" → 1
            round_raw = str(row.get("round") or "0")
            round_match = re.search(r"(\d+)", round_raw)
            round_num = int(round_match.group(1)) if round_match else 0

            # Scores: άθροισμα πόντων παικτών
            hs = sum(int(p.get("stats", {}).get("points", 0) or 0)
                     for p in (r.get("local.players") or []))
            aw = sum(int(p.get("stats", {}).get("points", 0) or 0)
                     for p in (r.get("road.players") or []))

            # Parse players
            players = []
            for side, team_norm in [("local", home), ("road", away)]:
                raw_players = r.get(f"{side}.players") or []
                for p in raw_players:
                    player  = p.get("player", {})
                    person  = player.get("person", {})
                    stats   = p.get("stats", {})
                    club    = player.get("club", {})
                    images  = player.get("images", {}) or {}
                    country = person.get("country", {}) or {}
                    birth_c = person.get("birthCountry", {}) or {}

                    players.append({
                        # ---- Identity ----
                        "name":       person.get("name"),
                        "code":       person.get("code"),
                        "alias":      person.get("alias"),
                        "jerseyName": person.get("jerseyName"),
                        "team":       team_norm,
                        "teamCode":   club.get("code"),
                        "pos":        player.get("positionName"),
                        "posNum":     player.get("position"),
                        "jersey":     player.get("dorsal"),
                        # ---- Bio ----
                        "country":    country.get("code"),
                        "countryFull":country.get("name"),
                        "birthDate":  (person.get("birthDate") or "")[:10],
                        "birthCountry": birth_c.get("code"),
                        "height":     person.get("height"),
                        "weight":     person.get("weight"),
                        "photo":      images.get("headshot"),
                        # ---- Playing status ----
                        "startFive":  bool(stats.get("startFive")),
                        "played":     (stats.get("timePlayed") or 0) > 0,
                        # ---- Core stats ----
                        "sec":        stats.get("timePlayed"),
                        "min":        round((stats.get("timePlayed") or 0) / 60, 1),
                        "pir":        stats.get("valuation"),
                        "pts":        stats.get("points"),
                        "reb":        stats.get("totalRebounds"),
                        "rebD":       stats.get("defensiveRebounds"),
                        "rebO":       stats.get("offensiveRebounds"),
                        "ast":        stats.get("assistances"),
                        "stl":        stats.get("steals"),
                        "blk":        stats.get("blocksFavour"),
                        "blkAgainst": stats.get("blocksAgainst"),
                        "to":         stats.get("turnovers"),
                        "pf":         stats.get("foulsCommited"),
                        "fr":         stats.get("foulsReceived"),
                        # ---- Shooting ----
                        "fgm2":       stats.get("fieldGoalsMade2"),
                        "fga2":       stats.get("fieldGoalsAttempted2"),
                        "fgm3":       stats.get("fieldGoalsMade3"),
                        "fga3":       stats.get("fieldGoalsAttempted3"),
                        "fgm":        stats.get("fieldGoalsMadeTotal"),
                        "fga":        stats.get("fieldGoalsAttemptedTotal"),
                        "ftm":        stats.get("freeThrowsMade"),
                        "fta":        stats.get("freeThrowsAttempted"),
                        # ---- Misc ----
                        "plusMinus":  stats.get("plusMinus"),
                    })

            key = f"{SEASON}-{gc_num}"
            boxscores[key] = {
                "season":   SEASON,
                "gamecode": gc_num,
                "round":    round_num,
                "date":     date_str,
                "home":     home,
                "away":     away,
                "hs":       hs,
                "aw":       aw,
                "players":  players,
            }
            print(f"   [{i}/{total}] {home} {hs}-{aw} {away} → {len(players)} players")
        except Exception as e:
            print(f"   [{i}/{total}] ✗ {str(e)[:60]}")
            continue

    log(f"Κατεβάστηκαν box scores για {len(boxscores)} αγώνες", "📦")
    return boxscores

def fetch_playoff_games():
    """
    Κατεβάζει τα playoff games από το API.
    Επιστρέφει λίστα από arrays [round, day, date, utc, local, home, away, hs, aw]
    """
    log("Έλεγχος για playoff games...", "🏆")
    try:
        sched = Schedule(COMPETITION)
        df = sched.get_schedule(season=SEASON)
    except Exception as e:
        log(f"Σφάλμα API: {e}", "✗")
        return []

    # Φιλτράρουμε ΜΟΝΟ τα playoff games (όχι RS)
    # Το API βάζει phaseType.alias = "PO" ή "PI" για playoffs/play-in
    playoff_df = df[~df["round"].astype(str).str.startswith("RS")]
    
    # Ή πιο απλά: ψάξε για το "phaseType.alias"
    if "phaseType.alias" in df.columns:
        playoff_df = df[df["phaseType.alias"].isin(["PO", "PI", "QF", "SF", "F"])]
    else:
        playoff_df = df[df["round"].astype(str).str.contains("Playoff|Final|Quarter|Semi", case=False, na=False)]

    if len(playoff_df) == 0:
        log("Δεν βρέθηκαν playoff games (season ακόμα σε RS)", "ℹ️")
        return []

    log(f"Βρέθηκαν {len(playoff_df)} playoff games", "🏆")

    gs = GameStats(COMPETITION)
    playoff_games = []
    errors = 0

    for i, (_, row) in enumerate(playoff_df.iterrows(), 1):
        gamecode = row.get("gamecode")
        round_num = row.get("round")

        # Extract number from gamecode
        gc_match = re.search(r"_(\d+)$", str(gamecode))
        gc_num = int(gc_match.group(1)) if gc_match else None

        if gc_num is None:
            continue

        # Υπολόγισε "round" για playoff (1-2 = play-in, 3 = QF, 4 = SF, 5 = Final)
        phase = str(row.get("phaseType.alias", "")).upper()
        if phase == "PI": p_round = 1
        elif phase == "QF": p_round = 3
        elif phase == "SF": p_round = 4
        elif phase == "F": p_round = 5
        else: p_round = 3  # default

        try:
            report = gs.get_game_report(SEASON, gc_num)
            if hasattr(report, "iloc") and len(report) > 0:
                r = report.iloc[0]
                hs = int(r["local.score"]) if "local.score" in r and r["local.score"] is not None else None
                aw = int(r["road.score"]) if "road.score" in r and r["road.score"] is not None else None
                home_api = r["local.club.name"] if "local.club.name" in r else row.get("hometeam")
                away_api = r["road.club.name"] if "road.club.name" in r else row.get("awayteam")

                home = normalize_team(home_api)
                away = normalize_team(away_api)

                # Parse date/time
                date_str = str(row.get("date", ""))[:10]
                time_utc = str(row.get("startime", "20:00"))
                time_local = time_utc  # πρόχειρο
                day = str(row.get("date", ""))[:3]

                playoff_games.append([
                    p_round, day, date_str, time_utc, time_local,
                    home, away, hs, aw
                ])
                print(f"   [{i}/{len(playoff_df)}] {home} vs {away} → {hs}-{aw if hs else '—'}")
        except Exception as e:
            errors += 1
            continue

    log(f"Κατεβάστηκαν {len(playoff_games)} playoff games", "🏆")
    return playoff_games


def write_playoff_games(content, playoff_games):
    """Γράφει το PLAYOFF_GAMES block στο data.js"""
    if not playoff_games:
        new_block = "const PLAYOFF_GAMES = [\n];"
    else:
        lines = []
        for g in playoff_games:
            hs = "null" if g[7] is None else str(g[7])
            aw = "null" if g[8] is None else str(g[8])
            lines.append(
                f'[{g[0]},"{g[1]}","{g[2]}","{g[3]}","{g[4]}","{g[5]}","{g[6]}",{hs},{aw}]'
            )
        new_block = "const PLAYOFF_GAMES = [\n" + ",\n".join(lines) + "\n];"

    # Αν δεν υπάρχει το block, πρόσθεσέ το στο τέλος
    if "const PLAYOFF_GAMES" in content:
        return re.sub(
            r"const PLAYOFF_GAMES\s*=\s*\[.*?\];",
            new_block,
            content,
            flags=re.DOTALL
        )
    else:
        return content + "\n\n" + new_block + "\n"

def update_scores():
    log("=" * 50, "")
    log("EuroLeague Tracker — Score Updater", "🏀")
    log("=" * 50, "")

    backup_data_js()
    cleanup_old_backups(keep=30)

    if not os.path.exists(DATA_JS_PATH):
        log(f"Δεν βρέθηκε το {DATA_JS_PATH}", "✗")
        sys.exit(1)

    with open(DATA_JS_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    games = parse_games_from_data_js(content)
    log(f"Βρέθηκαν {len(games)} παιχνίδια στο data.js", "📋")

    missing = sum(1 for g in games if g[7] is None or g[8] is None)
    log(f"Παιχνίδια χωρίς σκορ: {missing}", "📊")

    api_scores = fetch_all_scores()
    log(f"Κατεβάστηκαν {len(api_scores)} σκορ από το API", "📡")

    if not api_scores:
        log("Δεν βρέθηκαν σκορ. Το data.js έμεινε ίδιο.", "ℹ️")
        return

    updated = 0
    matched_keys = set()
    for g in games:
        key = (g[5].upper(), g[6].upper())
        if key in api_scores:
            matched_keys.add(key)
            hs, aw = api_scores[key]
            if FORCE_UPDATE:
                if g[7] != hs or g[8] != aw:
                    g[7], g[8] = hs, aw
                    updated += 1
            else:
                if g[7] is None or g[8] is None:
                    g[7], g[8] = hs, aw
                    updated += 1

    unmatched = set(api_scores.keys()) - matched_keys
    if unmatched:
        log(f"⚠️  {len(unmatched)} σκορ δεν ταίριαξαν με το data.js:", "⚠️")
        for u in list(unmatched)[:15]:
            log(f"    API: {u[0]} vs {u[1]}", "  ")

    if updated > 0:
        new_content = write_games_to_data_js(content, games)
        with open(DATA_JS_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        log(f"✅ Ενημερώθηκαν {updated} παιχνίδια", "✓")
    else:
        log("Δεν χρειάζεται update", "ℹ️")

    log("=" * 50, "")

    # ---- BOX SCORES ----
    log("=" * 50, "")
    boxscores = fetch_box_scores()
    if boxscores:
        write_boxscores_js(boxscores)
    else:
        log("⚠️  Δεν κατεβάστηκαν box scores", "⚠️")

    # ---- PLAYOFF GAMES ----
    playoff_games = fetch_playoff_games()
    if playoff_games:
        with open(DATA_JS_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        content = write_playoff_games(content, playoff_games)
        with open(DATA_JS_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        log(f"✅ Ενημερώθηκαν {len(playoff_games)} playoff games", "🏆")

    # ---- ADVANCED TEAM STATS ----
    log("=" * 50, "")
    team_stats = fetch_team_advanced()
    if team_stats:
        write_team_advanced_js(team_stats)
    else:
        log("⚠️  Δεν κατεβάστηκαν advanced stats (θα χρησιμοποιηθούν τα προηγούμενα)", "⚠️")

    log("Ολοκληρώθηκε! Άνοιξε το EuroLeague.html", "🎉")
    #open_html()

# ============================================================
# 5.5 DEBUG MODE v6 — Traditional retry
# ============================================================
def debug_api_structure():
    import time
    
    print("=" * 70)
    print("🔍 DEBUG v6 — Traditional retry")
    print("=" * 70)
    
    from euroleague_api.team_stats import TeamStats
    ts = TeamStats(COMPETITION)
    
    # ---- Δοκίμασε traditional ΠΟΛΛΕΣ φορές ----
    print("\n📊 Traditional — 5 προσπάθειες με 2s delay")
    print("-" * 70)
    
    df_trad = None
    for attempt in range(1, 6):
        try:
            df = ts.get_team_stats_single_season(
                endpoint="traditional",
                season=SEASON,
                phase_type_code="RS",
                statistic_mode="PerGame",
            )
            rows = len(df)
            cols = len(df.columns)
            print(f"   [{attempt}/5] Rows: {rows}, Cols: {cols}")
            
            if rows > 0 and cols > 0:
                df_trad = df
                print(f"   ✅ ΕΠΙΤΥΧΙΑ στην προσπάθεια {attempt}!")
                break
            else:
                print(f"   ⚠️  Κενό — περιμένω 2s...")
                time.sleep(2)
        except Exception as e:
            print(f"   [{attempt}/5] ✗ ERROR: {str(e)[:80]}")
            time.sleep(2)
    
    # ---- Δοκίμασε και τα δύο endpoints μαζί ----
    print("\n📊 Δοκιμή: advanced πρώτα, μετά traditional")
    print("-" * 70)
    try:
        df_adv = ts.get_team_stats_single_season(
            endpoint="advanced",
            season=SEASON,
            phase_type_code="RS",
            statistic_mode="PerGame",
        )
        print(f"   ✓ advanced → {len(df_adv)} rows")
        time.sleep(1.5)
        
        df_trad2 = ts.get_team_stats_single_season(
            endpoint="traditional",
            season=SEASON,
            phase_type_code="RS",
            statistic_mode="PerGame",
        )
        print(f"   ✓ traditional → {len(df_trad2)} rows")
        
        if len(df_trad2) > 0:
            df_trad = df_trad2
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
    
    # ---- Αν πήραμε traditional, δες το ----
    if df_trad is not None and len(df_trad) > 0:
        print(f"\n\n{'=' * 70}")
        print(f"📊 TRADITIONAL — ΠΛΗΡΕΣ ({len(df_trad)} rows)")
        print("=" * 70)
        print(f"\n✓ Columns ({len(df_trad.columns)}):")
        for i, col in enumerate(df_trad.columns, 1):
            print(f"   [{i:2d}] {col}")
        
        print(f"\n📋 FIRST ROW — ΟΛΑ τα values:")
        for col in df_trad.columns:
            print(f"   {col:40s} = {df_trad.iloc[0][col]}")
        
        print(f"\n📋 ΟΛΑ τα team names:")
        for i, name in enumerate(df_trad["team.name"], 1):
            print(f"   [{i:2d}] {name}")
        
        # ---- Normalize test ----
        print(f"\n\n{'=' * 70}")
        print("🔧 NORMALIZE TEST")
        print("=" * 70)
        app_teams = [
            "ANADOLU EFES ISTANBUL","ARMANI OLIMPIA MILAN","BASKONIA VITORIA-GASTEIZ",
            "BESIKTAS ISTANBUL","CRVENA ZVEZDA BELGRADE","DUBAI BASKETBALL",
            "FC BARCELONA","FC BAYERN MUNICH","FENERBAHCE ISTANBUL","HAPOEL IBI TEL AVIV",
            "LDLC ASVEL VILLEURBANNE","MACCABI RAPYD TEL AVIV","OLYMPIACOS PIRAEUS",
            "PANATHINAIKOS AKTOR ATHENS","PARIS BASKETBALL","PARTIZAN MOZZART BELGRADE",
            "REAL MADRID","VALENCIA BASKET","VIRTUS BOLOGNA","ZALGIRIS KAUNAS"
        ]
        
        api_normalized = set()
        print("\n📋 API name → normalized:")
        for name in df_trad["team.name"]:
            norm = normalize_team(name)
            api_normalized.add(norm)
            status = "✓" if norm in app_teams else "⚠️"
            print(f"   {status} '{name}' → '{norm}'")
        
        print("\n✅ Matched:")
        for t in app_teams:
            if t in api_normalized:
                print(f"   ✓ {t}")
        
        print("\n❌ Unmatched από API:")
        for n in api_normalized:
            if n not in app_teams:
                print(f"   ✗ {n}")
        
        print("\n❌ Unmatched από App:")
        for t in app_teams:
            if t not in api_normalized:
                print(f"   ✗ {t}")
    else:
        print("\n⚠️ ΔΕΝ πήραμε traditional ούτε μετά από 5 προσπάθειες + 1.5s delay")
        print("   Πιθανότατα το endpoint traditional έχει αυστηρό rate limit.")
    
    print("\n" + "=" * 70)
    print("✅ DEBUG v6 ΟΛΟΚΛΗΡΩΘΗΚΕ")
    print("=" * 70)

# ============================================================
# 5.6 FETCH TEAM ADVANCED STATS
# ============================================================
def _safe_num(val):
    """Μετατρέπει '52.6%' → 52.6, '1.1' → 1.1, None → None."""
    if val is None:
        return None
    s = str(val).strip().replace("%", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _fetch_with_retry(func, max_attempts=5, delay=2.0):
    """Δοκιμάζει μέχρι max_attempts φορές."""
    import time
    for attempt in range(1, max_attempts + 1):
        try:
            result = func()
            if result is not None and len(result) > 0:
                return result
        except Exception as e:
            print(f"      [{attempt}/{max_attempts}] ✗ {str(e)[:60]}")
        if attempt < max_attempts:
            time.sleep(delay)
    return None

def fetch_team_advanced():
    """
    Κατεβάζει traditional + advanced stats.
    - traditional: PIR, REB, AST, STL, BLK, TOV, 2P%, 3P%, FT%
    - advanced:    TS%, eFG%, AST/TO
    """
    import time
    log("Φόρτωση advanced team stats...", "📊")

    from euroleague_api.team_stats import TeamStats
    ts = TeamStats(COMPETITION)

    # ---- 1. Traditional PerGame ----
    print("   [1/2] Traditional PerGame...", end=" ", flush=True)
    df_trad = _fetch_with_retry(
        lambda: ts.get_team_stats_single_season(
            endpoint="traditional",
            season=SEASON,
            phase_type_code="RS",
            statistic_mode="PerGame",
        ),
        max_attempts=15,
        delay=4.0
    )
    if df_trad is None:
        log("Αποτυχία", "✗")
        return {}
    print(f"✓ {len(df_trad)} rows")

    # ---- 2. Advanced PerGame ----
    # Delay πριν τη 2η κλήση για να μην μας block-άρει
    time.sleep(5)

    print("   [2/2] Advanced PerGame...", end=" ", flush=True)
    df_adv = _fetch_with_retry(
        lambda: ts.get_team_stats_single_season(
            endpoint="advanced",
            season=SEASON,
            phase_type_code="RS",
            statistic_mode="PerGame",
        ),
        max_attempts=15,
        delay=4.0
    )
    if df_adv is None:
        print("✗ (θα μείνουν '—')")
        df_adv = None
    else:
        print(f"✓ {len(df_adv)} rows")

    # ---- Merge: Traditional ----
    result = {}
    for _, row in df_trad.iterrows():
        team = normalize_team(row["team.name"])
        result[team] = {
            "perGame": {
                "PIR":  _safe_num(row.get("pir")),
                "REB":  _safe_num(row.get("totalRebounds")),
                "AST":  _safe_num(row.get("assists")),
                "STL":  _safe_num(row.get("steals")),
                "BLK":  _safe_num(row.get("blocks")),
                "TOV":  _safe_num(row.get("turnovers")),
                "2P%":  _safe_num(row.get("twoPointersPercentage")),
                "3P%":  _safe_num(row.get("threePointersPercentage")),
                "FT%":  _safe_num(row.get("freeThrowsPercentage")),
                # Advanced — default null, θα γεμίσουν παρακάτω
                "TS":     None,
                "eFG":    None,
                "AST/TO": None,
            },
            "totals": {
                "PIR": None, "REB": None, "AST": None,
                "STL": None, "BLK": None, "TOV": None,
                "2P%": _safe_num(row.get("twoPointersPercentage")),
                "3P%": _safe_num(row.get("threePointersPercentage")),
                "FT%": _safe_num(row.get("freeThrowsPercentage")),
                # Advanced — ίδια με perGame (δεν αλλάζουν)
                "TS":     None,
                "eFG":    None,
                "AST/TO": None,
            }
        }

    # ---- Merge: Advanced → TS, eFG, AST/TO ----
    if df_adv is not None:
        for _, row in df_adv.iterrows():
            team = normalize_team(row["team.name"])
            if team not in result:
                continue
            ts_val     = _safe_num(row.get("trueShootingPercentage"))
            efg_val    = _safe_num(row.get("effectiveFieldGoalPercentage"))
            astto_val  = _safe_num(row.get("assistsToTurnoversRatio"))

            result[team]["perGame"]["TS"]     = ts_val
            result[team]["perGame"]["eFG"]    = efg_val
            result[team]["perGame"]["AST/TO"] = astto_val

            # Τα ποσοστά είναι ΙΔΙΑ και στα totals
            result[team]["totals"]["TS"]     = ts_val
            result[team]["totals"]["eFG"]    = efg_val
            result[team]["totals"]["AST/TO"] = astto_val

        log(f"Κατεβάστηκαν advanced stats για {len(result)} ομάδες", "✓")
    else:
        log(f"Κατεβάστηκαν traditional stats για {len(result)} ομάδες (χωρίς advanced)", "⚠️")

    return result

# ============================================================
# 5.7 WRITE team-advanced.js
# ============================================================
def write_team_advanced_js(team_stats):
    """Γράφει το js/team-advanced.js με δομή { perGame, totals }"""
    if not team_stats:
        return False

    ADVANCED_JS_PATH = os.path.join(_ROOT_DIR, "js", "data", "team-advanced.js")

    # ---- Backup ----
    if os.path.exists(ADVANCED_JS_PATH):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"team-advanced_{ts}.js")
        shutil.copy2(ADVANCED_JS_PATH, backup_path)

    # ---- Build JS ----
    ALL_KEYS = ["PIR", "TS", "eFG", "AST/TO", "REB", "AST", "STL", "BLK", "TOV", "3P%", "2P%", "FT%"]

    def _js_obj(stats_dict):
        parts = []
        for key in ALL_KEYS:
            val = stats_dict.get(key)
            if val is None:
                parts.append(f'"{key}": null')
            else:
                parts.append(f'"{key}": {val}')
        return "{ " + ", ".join(parts) + " }"

    lines = []
    lines.append("// ============================================================")
    lines.append("// TEAM ADVANCED STATS — auto-generated from EuroLeague API")
    lines.append(f"// Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("// Structure: { perGame: {...}, totals: {...} }")
    lines.append("// ============================================================")
    lines.append("")
    lines.append("const TEAM_ADVANCED = {")

    teams_sorted = sorted(team_stats.keys())
    for i, team in enumerate(teams_sorted):
        stats = team_stats[team]
        pg  = _js_obj(stats.get("perGame", {}))
        tot = _js_obj(stats.get("totals", {}))
        comma = "," if i < len(teams_sorted) - 1 else ""
        lines.append(f'  "{team}": {{')
        lines.append(f'    "perGame": {pg},')
        lines.append(f'    "totals":  {tot}')
        lines.append(f'  }}{comma}')

    lines.append("};")
    lines.append("")

    with open(ADVANCED_JS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    log(f"Εγγράφηκε: {ADVANCED_JS_PATH}", "💾")
    return True

# ============================================================
# 6. ENTRY POINT
# ============================================================
if __name__ == "__main__":
    try:
        update_scores()
    except KeyboardInterrupt:
        print("\n\nΑκυρώθηκε.")
    except Exception as e:
        print(f"\n✗ Σφάλμα: {e}")
        import traceback
        traceback.print_exc()
    if os.name == "nt" and sys.stdin.isatty():
        input("\nΠάτα Enter για κλείσιμο...")
