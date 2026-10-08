#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
log_predictions.py
------------------
Αποθηκεύει snapshot προβλέψεων με round detection.

Auto-detect: round_next = max(round με scores στο data.js) + 1
Αν δεν βρει, χρησιμοποιεί 0.

Output:
  ../json/predictions_log/2026-R04_<timestamp>.json
"""

import json
import re
from datetime import datetime
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import ROOT, DATA_PROC, APP_JS_CONFIG, OUTPUT_PRED_LOG

PREDICTIONS_FILE = DATA_PROC / "player_predictions.json"
DATA_JS          = APP_JS_CONFIG / "data.js"
LOG_DIR          = OUTPUT_PRED_LOG


def detect_next_round():
    """max(round με scores) + 1"""
    if not DATA_JS.exists():
        return 0
    text = DATA_JS.read_text(encoding="utf-8")
    match = re.search(r"const GAMES_RAW\s*=\s*\[(.*?)\];", text, re.DOTALL)
    if not match:
        return 0

    rounds_played = set()
    for line in match.group(1).split("\n"):
        line = line.strip().rstrip(",")
        if not line.startswith("["):
            continue
        m = re.match(
            r'\[\s*(\d+)\s*,\s*"[^"]*"\s*,\s*"[^"]*"\s*,\s*"[^"]*"\s*,'
            r'\s*"[^"]*"\s*,\s*"[^"]*"\s*,\s*"[^"]*"\s*,'
            r'\s*(null|\d+)\s*,\s*(null|\d+)\s*\]',
            line
        )
        if m:
            r = int(m.group(1))
            hs = m.group(2)
            aw = m.group(3)
            if hs != "null" and aw != "null":
                rounds_played.add(r)

    if not rounds_played:
        return 0
    return max(rounds_played) + 1


def main():
    print("=" * 60)
    print("LOG PREDICTIONS")
    print("=" * 60)

    if not PREDICTIONS_FILE.exists():
        print(f"❌ {PREDICTIONS_FILE} δεν βρέθηκε")
        print("   Τρέξε πρώτα: py train_model_v4_2.py")
        return 1

    with open(PREDICTIONS_FILE, encoding="utf-8") as f:
        predictions = json.load(f)

    if not predictions:
        print("❌ predictions είναι άδειο")
        return 1

    next_round = detect_next_round()
    if next_round == 0:
        print("⚠️  Δεν ανιχνεύτηκε round (χωρίς scores στο data.js)")
        print("   Θα χρησιμοποιήσω round=0")
    else:
        print(f"📅 Επόμενο round: R{next_round}")

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"2026-R{next_round:02d}_{timestamp}_predictions.json"
    out_path = LOG_DIR / filename

    payload = {
        "round":         next_round,
        "logged_at":     now.isoformat(),
        "total_players": len(predictions),
        "predictions":   predictions,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    n_with_xp = sum(1 for p in predictions if p.get("xpdk_v4_2", 0) > 0)
    n_high_conf = sum(1 for p in predictions if p.get("confidence") == "high")

    print(f"✅ {len(predictions)} predictions logged")
    print(f"   → {filename}")
    print(f"   με xp > 0:       {n_with_xp}")
    print(f"   confidence=high: {n_high_conf}")
    print(f"   location:        {out_path}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())