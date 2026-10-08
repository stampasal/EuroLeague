#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
validate_all.py — Data validation για το EuroLeague Fantasy project.

Τρέχει από: Fantasy/python/
    py validate_all.py

Ελέγχει 4 πράγματα:
  1. Data integrity     (seasons, game logs ανά παίκτη, missing values)
  2. Prediction sanity  (top παίκτες, 0-value, outliers)
  3. Model quality      (MAE per position, baseline/improvement)
  4. Consistency        (ίδιος αριθμός παικτών σε όλα τα αρχεία)
"""

import json
import sys
import statistics
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.paths import DATA_RAW, DATA_PROC
from collections import Counter

# ---------------------------------------------------------------- paths
FILES = {
    "fantasy":     DATA_RAW / "fantasy_data.json",
    "metrics":     DATA_PROC / "model_metrics.json",
    "predictions": DATA_PROC / "player_predictions.json",
}

# Filter που εφαρμόζει το training — κρατάμε μόνο παίκτες με αρκετά δεδομένα
MIN_GAMES    = 10
MIN_AVG_MIN  = 5.0

# ---------------------------------------------------------------- reporting
TALLY = Counter()

def ok(m):   TALLY["OK"]   += 1; print(f"  [OK]   {m}")
def warn(m): TALLY["WARN"] += 1; print(f"  [WARN] {m}")
def fail(m): TALLY["FAIL"] += 1; print(f"  [FAIL] {m}")
def head(t): print(f"\n{'='*62}\n  {t}\n{'='*62}")
def sub(t):  print(f"\n-- {t}")

# ---------------------------------------------------------------- helpers
NAME_KEYS = ("player", "player_name", "name", "PLAYER", "Player")
XP_KEYS   = ("xpdk_v4_2", "xpdk", "xp", "prediction", "predicted_xp")
GAME_KEYS = ("games", "game_logs", "gamelogs", "rounds", "logs", "stats", "matches")
SEASON_KEYS = ("season", "Season", "year", "Year")


def load_json(path):
    if not path.exists():
        return None, f"δεν βρέθηκε ({path.name})"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, f"σφάλμα ανάγνωσης: {e}"


def load_all():
    head("Φόρτωση αρχείων")
    data = {}
    for key, path in FILES.items():
        obj, err = load_json(path)
        if err:
            fail(f"{path.name} — {err}")
            data[key] = None
        else:
            kb = path.stat().st_size / 1024
            ok(f"{path.name} ({kb:.1f} KB)")
            data[key] = obj
    return data


def is_player(d):
    return isinstance(d, dict) and any(k in d for k in NAME_KEYS)


def player_lists(obj, path=""):
    """Επιστρέφει [(path, [player_dict, ...]), ...] για κάθε λίστα/ομάδα παικτών."""
    if is_player(obj):
        return []                       # μεμονωμένος παίκτης, όχι λίστα
    out = []
    if isinstance(obj, list):
        if obj and is_player(obj[0]):
            out.append((path or "/", obj))
        else:
            for i, v in enumerate(obj):
                out += player_lists(v, f"{path}[{i}]")
    elif isinstance(obj, dict):
        pvals = [v for v in obj.values() if isinstance(v, dict)]
        if pvals and sum(1 for v in pvals if is_player(v)) >= 0.8 * len(pvals):
            out.append((path or "/", pvals))
        else:
            for k, v in obj.items():
                out += player_lists(v, f"{path}/{k}")
    return out


def player_name(p):
    for k in NAME_KEYS:
        if p.get(k):
            return str(p[k])
    return "?"


def xp_key_of(rec):
    return next((k for k in XP_KEYS if k in rec), None)


# ---------------------------------------------------------------- 1. integrity
def check_integrity(fantasy):
    sub("1. Data integrity")
    if fantasy is None:
        fail("fantasy_data.json δεν φορτώθηκε — παράλειψη")
        return

    if isinstance(fantasy, dict):
        print(f"  Top-level keys: {list(fantasy.keys())[:12]}")

    lists = player_lists(fantasy)
    if not lists:
        warn("Δεν βρέθηκε λίστα παικτών — έλεγξε το schema του fantasy_data.json")
        return

    seasons_seen = set()
    all_records  = []
    total        = 0

    for p, lst in lists:
        total += len(lst)
        all_records.extend(lst)

        s_in_list = {str(r[k]) for r in lst for k in SEASON_KEYS if k in r}
        if s_in_list:
            seasons_seen |= s_in_list
            label = ",".join(sorted(s_in_list))
        else:
            label = p.strip("/").split("/")[-1] or "?"

        game_key = next((k for k in GAME_KEYS if k in lst[0]), None)
        if game_key:
            counts = [len(r.get(game_key) or []) for r in lst]
            zero   = sum(1 for c in counts if c == 0)
            avg    = statistics.mean(counts) if counts else 0
            print(f"  • {label:<18} {len(lst):>4} παίκτες | avg games={avg:5.1f} | χωρίς logs={zero}")
            if zero > 0:
                warn(f"{zero} παίκτες χωρίς game logs στο {label}")
        else:
            print(f"  • {label:<18} {len(lst):>4} παίκτες (χωρίς game-log key)")

    print(f"\n  Σύνολο εγγραφών : {total}")
    print(f"  Seasons         : {sorted(seasons_seen) or '—'}")

    if len(seasons_seen) >= 3:
        ok(f"{len(seasons_seen)} seasons βρέθηκαν")
    elif seasons_seen:
        warn(f"Αναμένονταν ≥3 seasons, βρέθηκαν {len(seasons_seen)}")
    else:
        warn("Δεν εντοπίστηκαν πεδία season στα records")

    # missing values σε όλες τις εγγραφές
    missing = Counter()
    for r in all_records:
        for k, v in r.items():
            if v is None or v == "":
                missing[k] += 1
    if missing:
        warn(f"Missing values ανά key (top5): {missing.most_common(5)}")
    else:
        ok("Καθόλου missing values σε όλες τις εγγραφές")


# ---------------------------------------------------------------- 2. predictions
def check_predictions(preds):
    sub("2. Prediction sanity")
    if preds is None:
        fail("player_predictions_v3.json δεν φορτώθηκε — παράλειψη")
        return

    if isinstance(preds, list):
        lst = preds
    else:
        pls = player_lists(preds)
        lst = pls[0][1] if pls else []

    if not lst:
        fail("Κενή λίστα προβλέψεων")
        return
    print(f"  Πλήθος παικτών: {len(lst)}")

    key = xp_key_of(lst[0])
    if not key:
        fail(f"Δεν βρέθηκε key πρόβλεψης (δοκίμασε: {XP_KEYS})")
        return
    print(f"  Key πρόβλεψης : {key}")

    vals = [(player_name(p), p.get(key)) for p in lst]
    vals = [(n, float(v)) for n, v in vals if isinstance(v, (int, float))]

    xs = [v for _, v in vals]
    mean = statistics.mean(xs)
    sd   = statistics.pstdev(xs)

    print(f"  Mean={mean:.2f} | SD={sd:.2f} | min={min(xs):.2f} | max={max(xs):.2f}")

    zero_players = [(n, p.get("confidence"), p.get("cv")) for (n, _), p in zip(vals, lst) if _ == 0]
    negs  = sum(1 for v in xs if v < 0)
    if not zero_players:
        ok("Κανένας παίκτης με τιμή 0")
    else:
        warn(f"{len(zero_players)} παίκτες με xpdk=0 (χωρίς game logs → πιθανώς πρέπει να φιλτραριστούν):")
        for n, c, cv in zero_players:
            print(f"      {n:<28} conf={c}  cv={cv}")
    ok("Καμία αρνητική τιμή") if not negs else fail(f"{negs} αρνητικές τιμές")

    hi, lo = mean + 3 * sd, mean - 3 * sd
    out = [(n, v) for n, v in vals if v > hi or v < lo]
    if out:
        warn(f"{len(out)} outliers (|3σ|): {out[:5]}")
    else:
        ok("Καθόλου outliers (3σ)")

    print("\n  Top-10 προβλέψεις:")
    for name, v in sorted(vals, key=lambda x: -x[1])[:10]:
        print(f"    {v:6.2f}  {name}")

    print()
    for k in ("floor", "ceiling", "cv", "trend", "confidence"):
        present = sum(1 for p in lst if k in p)
        pct = 100 * present / len(lst)
        if pct == 100:
            ok(f"'{k}' σε όλους τους παίκτες")
        elif present:
            warn(f"'{k}' σε {present}/{len(lst)} ({pct:.0f}%)")


# ---------------------------------------------------------------- 3. metrics
def check_metrics(metrics):
    sub("3. Model quality")
    if metrics is None:
        fail("model_metrics_v3.json δεν φορτώθηκε — παράλειψη")
        return

    if isinstance(metrics, dict):
        print(f"  Keys: {list(metrics.keys())}")

    mae = {}

    def find_mae(obj, pos=None, in_mae=False):
        if not isinstance(obj, dict):
            return
        for k, v in obj.items():
            kl = str(k).upper()
            nxt = k if kl in ("G", "F", "C", "GUARD", "FORWARD", "CENTER") else pos
            now_mae = in_mae or ("MAE" in kl)
            if isinstance(v, (int, float)) and now_mae and nxt:
                mae[nxt] = float(v)
            elif isinstance(v, dict):
                find_mae(v, nxt, now_mae)

    find_mae(metrics)

    if not mae:
        warn("Δεν βρέθηκαν τιμές MAE — έλεγξε το schema")
    else:
        for pos, v in mae.items():
            (ok if v < 6.5 else warn)(f"MAE {pos}: {v:.2f}")

    # baseline / improvement flag
    blob = json.dumps(metrics).lower()
    if "baseline" in blob or "improvement" in blob or "prev" in blob:
        ok("Υπάρχει αναφορά σε baseline/improvement")
    else:
        warn("Δεν βρέθηκε baseline/improvement — δεν επιβεβαιώνεται η βελτίωση")


# ---------------------------------------------------------------- 4. consistency
def check_consistency(fantasy, preds):
    sub("4. Consistency")

    # --- fantasy raw names ---
    f_names = set()
    if fantasy is not None:
        for _, lst in player_lists(fantasy):
            for r in lst:
                f_names.add(player_name(r))

    # --- pred names ---
    p_names = set()
    p_list  = []
    if preds is not None:
        if isinstance(preds, list):
            p_list = preds
        else:
            pls = player_lists(preds)
            p_list = pls[0][1] if pls else []
        p_names = {player_name(p) for p in p_list}

    print(f"  fantasy raw         : {len(f_names)} unique παίκτες")
    print(f"  player_predictions  : {len(p_names)} unique παίκτες")

    # --- 1. Subset check (το πραγματικό consistency) ---
    not_in_fantasy = sorted(p_names - f_names)
    if not not_in_fantasy:
        ok("Subset OK — όλοι οι παίκτες των predictions υπάρχουν στο fantasy_data")
    else:
        fail(f"{len(not_in_fantasy)} παίκτες στα predictions ΔΕΝ υπάρχουν στο fantasy_data")
        print(f"    Πρώτοι 10: {not_in_fantasy[:10]}")

    # --- 2. Coverage ---
    if f_names:
        cov = 100 * len(p_names) / len(f_names)
        dropped = len(f_names - p_names)
        msg = f"Coverage: {len(p_names)}/{len(f_names)} = {cov:.1f}%  (κόπηκαν {dropped})"
        # v4.2: φιλτράρουμε historical players → coverage ~20-30% αναμενόμενο
        if 15 <= cov <= 50:
            ok(msg)
        elif 10 <= cov < 15 or 50 < cov <= 60:
            warn(msg)
        else:
            fail(msg)
    else:
        warn("Δεν μπορεί να υπολογιστεί coverage")

# ---------------------------------------------------------------- main
def main():
    print("EuroLeague Fantasy — Data Validation")
    print(f"Data RAW: {DATA_RAW}")
    print(f"Data PROC: {DATA_PROC}")

    data = load_all()
    check_integrity(data["fantasy"])
    check_predictions(data["predictions"])
    check_metrics(data["metrics"])
    check_consistency(data["fantasy"], data["predictions"])

    head("ΣΥΝΟΨΗ")
    print(f"  OK   : {TALLY['OK']}")
    print(f"  WARN : {TALLY['WARN']}")
    print(f"  FAIL : {TALLY['FAIL']}")

    if TALLY["FAIL"]:
        print("\n  >> Υπάρχουν FAIL — μην προχωρήσεις σε app integration πριν τα λύσεις.")
        return 1
    if TALLY["WARN"]:
        print("\n  >> Μόνο warnings — μπορείς να προχωρήσεις, αλλά έλεγξέ τα.")
        return 0
    print("\n  >> Όλα OK — έτοιμο για Βήμα 2 (app integration).")
    return 0


if __name__ == "__main__":
    sys.exit(main())