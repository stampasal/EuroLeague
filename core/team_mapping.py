#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
team_mapping.py  (v4 - Βήμα 4.1.1e)
------------------------------------
Hardcoded mapping short <-> full. Επιβεβαιωμένο από ονόματα παικτών.
Περιλαμβάνει ιστορικά codes (Monaco, Alba) για backward compatibility.

Output: team_mapping.json  (full_to_short, short_to_full, historical)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.paths import DATA_RAW

OUT = DATA_RAW / "team_mapping.json"

# ── Κύριες 20 ομάδες 2026 ──────────────────────────────────
FULL_TO_SHORT = {
    "PANATHINAIKOS AKTOR ATHENS":     "PAN",
    "OLYMPIACOS PIRAEUS":             "OLY",
    "ANADOLU EFES ISTANBUL":          "ULK",
    "FENERBAHCE ISTANBUL":            "IST",
    "ARMANI OLIMPIA MILAN":           "MIL",
    "FC BAYERN MUNICH":               "MUN",
    "FC BARCELONA":                   "BAR",
    "REAL MADRID":                    "MAD",
    "BASKONIA VITORIA-GASTEIZ":       "BAS",
    "CRVENA ZVEZDA BELGRADE":         "RED",
    "ZALGIRIS KAUNAS":                "ZAL",
    "MACCABI RAPYD TEL AVIV":         "TEL",
    "PARTIZAN MOZZART BELGRADE":      "PAR",
    "PARIS BASKETBALL":               "PRS",
    "VALENCIA BASKET":                "PAM",
    "VIRTUS BOLOGNA":                 "VIR",
    "LDLC ASVEL VILLEURBANNE":        "ASV",
    "BESIKTAS ISTANBUL":              "BES",
    "DUBAI BASKETBALL":               "DUB",
    "HAPOEL IBI TEL AVIV":            "HTA",
}

# ── Ιστορικά codes (ομάδες που έφυγαν) ─────────────────────
HISTORICAL = {
    "MCO": "AS MONACO",
    "BER": "ALBA BERLIN",
}

# ── Δευτερεύοντα codes (aliases για τις 20) ────────────────
# Αν το API επιστρέψει κάποιο από αυτά, να ξέρουμε σε ποια ομάδα πάει.
ALIASES = {
    "VBC": "VALENCIA BASKET",     # εναλλακτικό code Valencia
    "EFS": "ANADOLU EFES ISTANBUL",
    "PAO": "PANATHINAIKOS AKTOR ATHENS",
    "CZV": "CRVENA ZVEZDA BELGRADE",
    "MTA": "MACCABI RAPYD TEL AVIV",
    "BAY": "FC BAYERN MUNICH",
    "KBA": "BASKONIA VITORIA-GASTEIZ",
    "BJK": "BESIKTAS ISTANBUL",
    "RMB": "REAL MADRID",
    "FBT": "FENERBAHCE ISTANBUL",
    "PBB": "PARIS BASKETBALL",
}


def main():
    print("=" * 70)
    print("ΒΗΜΑ 4.1.1e — HARDCODED TEAM MAPPING")
    print("=" * 70)

    short_to_full = {v: k for k, v in FULL_TO_SHORT.items()}

    # Έλεγχος 1-1
    assert len(short_to_full) == len(FULL_TO_SHORT), "Διπλά shorts!"
    print(f"✅ Κύριες ομάδες: {len(FULL_TO_SHORT)} (1-1 OK)")

    # Έλεγχος: τα historical + aliases δεν συγκρούονται με τα κύρια
    conflicts = set(HISTORICAL) & set(short_to_full)
    assert not conflicts, f"Σύγκρουση historical: {conflicts}"
    conflicts = set(ALIASES) & set(short_to_full)
    assert not conflicts, f"Σύγκρουση aliases: {conflicts}"
    print(f"✅ Historical: {len(HISTORICAL)} (χωρίς σύγκρουση)")
    print(f"✅ Aliases:    {len(ALIASES)} (χωρίς σύγκρουση)")

    out = {
        "full_to_short": FULL_TO_SHORT,
        "short_to_full": short_to_full,
        "historical":    HISTORICAL,
        "aliases":       ALIASES,
        "version":       "v4.1.1e",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n→ Wrote {OUT}")
    print("=" * 70)

    # Preview
    print("\nPREVIEW:")
    for full, short in FULL_TO_SHORT.items():
        print(f"  {short:<5} ← {full}")


if __name__ == "__main__":
    main()