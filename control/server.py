# ============================================================
# control/server.py
# ------------------------------------------------------------
# Control Panel server (port 5001).
#
# Endpoints:
#   GET  /                     → control/html/control-center.html
#   GET  /<path>               → static files (control/html/)
#   GET  /api/scripts          → λίστα scripts + workflows
#   GET  /api/status           → last_run timestamps (auto-hints)
#   POST /api/run              → ξεκίνα script/workflow
#   GET  /api/run-status/<id>  → status + output
#
# Εκκίνηση:  py control/server.py
# ============================================================

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, send_from_directory

# --- core imports ---
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.paths import ROOT, SCRIPTS, CONTROL, CONTROL_HTML
from core.config import SERVER_HOST, SERVER_PORT_CONTROL
from core.logger import get_logger


log = get_logger("control_server", category="server")


app = Flask(
    __name__,
    static_folder=str(CONTROL_HTML),
    static_url_path="",
)


@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


# ============================================================
# SCRIPTS CATALOG
# ============================================================

SCRIPTS = [
    # ---- FETCH ----
    {"id": "fetch_euroleague",
     "category": "FETCH",
     "label": "Fetch EuroLeague data",
     "desc": "Game logs 2022-2026 (~15 λεπτά)",
     "file": "scripts/fetch/fetch_euroleague.py",
     "time": "~15λ"},

    {"id": "fetch_credits",
     "category": "FETCH",
     "label": "Scrape BasketStories credits",
     "desc": "Credits παικτών από BasketStories (~2 λεπτά)",
     "file": "scripts/fetch/fetch_credits.py",
     "time": "~2λ"},

    {"id": "fetch_player_stats",
     "category": "FETCH",
     "label": "Scrape BasketStories stats",
     "desc": "FR / BLA / FTA stats (~5 λεπτά)",
     "file": "scripts/fetch/fetch_player_stats.py",
     "time": "~5λ"},

    {"id": "fetch_injuries",
     "category": "FETCH",
     "label": "Fetch injuries (BasketNews)",
     "desc": "Injury report από BasketNews (~5 δευτ.)",
     "file": "scripts/fetch/fetch_injuries.py",
     "time": "~5δ"},

    {"id": "fetch_scores",
     "category": "FETCH",
     "label": "Update scores + boxscores",
     "desc": "Scores + boxscores + team advanced (~3 λεπτά)",
     "file": "scripts/fetch/fetch_scores.py",
     "time": "~3λ"},

    # ---- COMPUTE ----
    {"id": "compute_coach_stats",
     "category": "COMPUTE",
     "label": "Compute coach stats",
     "desc": "Coach xp (νίκες/ήττες + margin + adj)",
     "file": "scripts/compute/compute_coach_stats.py",
     "time": "~10δ"},

    {"id": "compute_trend_confidence",
     "category": "COMPUTE",
     "label": "Compute trend + confidence",
     "desc": "player-trend-confidence.js",
     "file": "scripts/compute/compute_trend_confidence.py",
     "time": "~10δ"},

    # ---- TRAIN ----
    {"id": "train_model",
     "category": "TRAIN",
     "label": "Train model v4.2",
     "desc": "Ensemble (Ridge + GB + MA) — 17 features (~10 λεπτά)",
     "file": "scripts/train/train_model.py",
     "time": "~10λ"},

    {"id": "build_defense",
     "category": "TRAIN",
     "label": "Build defensive profiles",
     "desc": "Defense v2 για όλες τις ομάδες (~1 λεπτό)",
     "file": "scripts/train/build_defense.py",
     "time": "~1λ"},

    # ---- CONVERT ----
    {"id": "convert_predictions",
     "category": "CONVERT",
     "label": "Convert predictions to JS",
     "desc": "player_predictions.js (xpdk)",
     "file": "scripts/convert/convert_predictions.py",
     "time": "~5δ"},

    {"id": "convert_gamelogs",
     "category": "CONVERT",
     "label": "Convert game logs to JS",
     "desc": "player-gamelogs.js",
     "file": "scripts/convert/convert_gamelogs.py",
     "time": "~5δ"},

    {"id": "convert_stats",
     "category": "CONVERT",
     "label": "Convert stats 2026 to JS",
     "desc": "player-stats-2026.js (credits, PIR, usage)",
     "file": "scripts/convert/convert_stats.py",
     "time": "~10δ"},

    {"id": "convert_coaches",
     "category": "CONVERT",
     "label": "Convert coaches to JS",
     "desc": "coaches.js + coach_stats.js",
     "file": "scripts/convert/convert_coaches.py",
     "time": "~5δ"},

    {"id": "apply_injuries",
     "category": "CONVERT",
     "label": "Apply injuries to JS",
     "desc": "Γράφει player_injuries.js",
     "file": "scripts/convert/apply_injuries.py",
     "time": "~5δ"},

    # ---- VALIDATE ----
    {"id": "validate_all",
     "category": "VALIDATE",
     "label": "Validate all v4",
     "desc": "Validation report (~30 δευτ.)",
     "file": "scripts/validate/validate_all.py",
     "time": "~30δ"},

    {"id": "validate_optimizer",
     "category": "VALIDATE",
     "label": "Validate optimizer (brute-force)",
     "desc": "MILP vs brute-force (~10 δευτ.)",
     "file": "scripts/validate/validate_optimizer.py",
     "time": "~10δ"},

    {"id": "validate_sanity",
     "category": "VALIDATE",
     "label": "Validate sanity (full dataset)",
     "desc": "Sanity checks σε 247 παίκτες",
     "file": "scripts/validate/validate_sanity.py",
     "time": "~5δ"},

    {"id": "analyze_predictions",
     "category": "VALIDATE",
     "label": "Analyze predictions",
     "desc": "Ανάλυση predictions",
     "file": "scripts/validate/analyze_predictions.py",
     "time": "~10δ"},

    {"id": "log_predictions",
     "category": "VALIDATE",
     "label": "Log current round predictions",
     "desc": "Αποθήκευση predictions σε log",
     "file": "scripts/validate/log_predictions.py",
     "time": "~5δ"},
]

WORKFLOWS = [
    {"id": "update_all",
     "label": "Update ALL",
     "desc": "Fetch + Train + Convert (~30 λεπτά)",
     "steps": [
         "fetch_euroleague",
         "fetch_credits",
         "fetch_player_stats",
         "fetch_scores",
         "train_model",
         "build_defense",
         "compute_coach_stats",
         "convert_predictions",
         "convert_gamelogs",
         "convert_stats",
         "compute_trend_confidence",
         "convert_coaches",
         "fetch_injuries",
         "apply_injuries",
     ],
     "time": "~30λ"},

    {"id": "fetch_convert",
     "label": "Fetch + Convert",
     "desc": "Fetch δεδομένα + JS generation (χωρίς train, ~20 λεπτά)",
     "steps": [
         "fetch_euroleague",
         "fetch_credits",
         "fetch_player_stats",
         "fetch_scores",
         "convert_predictions",
         "convert_gamelogs",
         "convert_stats",
         "compute_trend_confidence",
         "convert_coaches",
         "fetch_injuries",
         "apply_injuries",
     ],
     "time": "~20λ"},

    {"id": "convert_only",
     "label": "Only Convert",
     "desc": "Μόνο JS generation από υπάρχοντα data (~1 λεπτό)",
     "steps": [
         "convert_predictions",
         "convert_gamelogs",
         "convert_stats",
         "compute_trend_confidence",
         "convert_coaches",
         "fetch_injuries",
         "apply_injuries",
     ],
     "time": "~1λ"},

    {"id": "injuries_only",
     "label": "Only Injuries",
     "desc": "Fetch + apply injuries (~10 δευτ.)",
     "steps": [
         "fetch_injuries",
         "apply_injuries",
     ],
     "time": "~10δ"},

    {"id": "validate",
     "label": "Validate System",
     "desc": "Έλεγχος αν όλα δουλεύουν σωστά (~30 δευτ.)",
     "steps": [
         "validate_all",
         "validate_optimizer",
         "validate_sanity",
     ],
     "time": "~30δ"},
]


# ============================================================
# RUN STATE
# ============================================================

@dataclass
class RunState:
    run_id: str
    scripts: list[str]
    status: str = "queued"
    current_script: Optional[str] = None
    current_index: int = 0
    total: int = 0
    started_at: float = 0.0
    finished_at: float = 0.0
    output: list[str] = field(default_factory=list)
    error: Optional[str] = None


RUNS: dict[str, RunState] = {}
RUNS_LOCK = threading.Lock()


# ============================================================
# LAST RUNS PERSISTENCE (auto-hints)
# ============================================================

LAST_RUNS_FILE = ROOT / "output" / ".last_runs.json"


def _load_last_runs() -> dict:
    if not LAST_RUNS_FILE.exists():
        return {}
    try:
        with open(LAST_RUNS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_last_runs(data: dict) -> None:
    LAST_RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LAST_RUNS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


LAST_RUNS: dict = _load_last_runs()


# ============================================================
# SERVE
# ============================================================

@app.route("/")
def index():
    return send_from_directory(str(CONTROL_HTML), "control-center.html")


@app.route("/<path:filename>")
def serve_static(filename: str):
    return send_from_directory(str(CONTROL_HTML), filename)


# ============================================================
# API
# ============================================================

@app.route("/api/scripts", methods=["GET"])
def api_scripts():
    return jsonify({"ok": True, "scripts": SCRIPTS, "workflows": WORKFLOWS})


@app.route("/api/status", methods=["GET"])
def api_status():
    """Επιστρέφει last_run timestamps για auto-hints."""
    result = {}
    for wf in WORKFLOWS:
        wf_key = "workflow_" + "_".join(wf["steps"][:3])
        if wf_key in LAST_RUNS:
            result[wf["id"]] = LAST_RUNS[wf_key]
        elif all(step in LAST_RUNS for step in wf["steps"]):
            result[wf["id"]] = min(LAST_RUNS[step] for step in wf["steps"])
    return jsonify({"ok": True, "last_runs": result, "raw": LAST_RUNS})


@app.route("/api/run", methods=["POST", "OPTIONS"])
def api_run():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(force=True) or {}
    script_ids = data.get("scripts") or []
    workflow_id = data.get("workflow")

    if workflow_id:
        wf = next((w for w in WORKFLOWS if w["id"] == workflow_id), None)
        if not wf:
            return jsonify({"ok": False, "error": f"Άγνωστο workflow: {workflow_id}"}), 400
        script_ids = wf["steps"]

    if not script_ids:
        return jsonify({"ok": False, "error": "Δεν επιλέχθηκε script."}), 400

    run_id = str(uuid.uuid4())[:8]
    run = RunState(run_id=run_id, scripts=list(script_ids), total=len(script_ids))
    with RUNS_LOCK:
        RUNS[run_id] = run

    t = threading.Thread(target=_run_scripts_worker, args=(run_id, list(script_ids)), daemon=True)
    t.start()

    return jsonify({"ok": True, "run_id": run_id})


@app.route("/api/run-status/<run_id>", methods=["GET"])
def api_run_status(run_id: str):
    with RUNS_LOCK:
        run = RUNS.get(run_id)
        if not run:
            return jsonify({"ok": False, "error": "Άγνωστο run_id"}), 404

        elapsed = 0.0
        if run.started_at:
            end = run.finished_at if run.finished_at else time.time()
            elapsed = round(end - run.started_at, 1)

        return jsonify({
            "ok": True,
            "run_id": run.run_id,
            "status": run.status,
            "current_script": run.current_script,
            "current_index": run.current_index,
            "total": run.total,
            "elapsed": elapsed,
            "output": run.output[-200:],
            "error": run.error,
        })


# ============================================================
# WORKER
# ============================================================

def _run_scripts_worker(run_id: str, script_ids: list[str]):
    with RUNS_LOCK:
        run = RUNS.get(run_id)
        if not run:
            return
        run.status = "running"
        run.started_at = time.time()

    script_lookup = {s["id"]: s for s in SCRIPTS}

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    try:
        for idx, sid in enumerate(script_ids):
            script = script_lookup.get(sid)
            if not script:
                with RUNS_LOCK:
                    run.output.append(f"[ERROR] Unknown script: {sid}")
                continue

            with RUNS_LOCK:
                run.current_script = script["label"]
                run.current_index = idx + 1
                run.output.append("")
                run.output.append("=" * 60)
                run.output.append(f"[{idx+1}/{len(script_ids)}] {script['label']}")
                run.output.append(f"  File: {script['file']}")
                run.output.append(f"  Desc: {script['desc']}")
                run.output.append("=" * 60)

            script_path = (ROOT / script["file"]).resolve()

            if not script_path.exists():
                with RUNS_LOCK:
                    run.output.append(f"[ERROR] File not found: {script_path}")
                continue

            try:
                proc = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    cwd=str(ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    env=env,
                )

                for line in proc.stdout:
                    with RUNS_LOCK:
                        run.output.append(line.rstrip("\n"))
                    if len(run.output) > 5000:
                        with RUNS_LOCK:
                            run.output = run.output[-3000:]

                proc.wait()

                with RUNS_LOCK:
                    run.output.append(f"--- exit code: {proc.returncode} ---")
                    LAST_RUNS[sid] = time.time() * 1000
                    _save_last_runs(LAST_RUNS)

                if proc.returncode != 0:
                    with RUNS_LOCK:
                        run.output.append(f"[WARN] Το script επέστρεψε {proc.returncode}")

            except Exception as e:
                with RUNS_LOCK:
                    run.output.append(f"[ERROR] {e}")

        with RUNS_LOCK:
            run.status = "done"
            run.finished_at = time.time()
            run.current_script = None
            run.current_index = run.total

            # Save workflow-level hint
            if script_ids:
                key = script_ids[0] if len(script_ids) == 1 else "workflow_" + "_".join(script_ids[:3])
                LAST_RUNS[key] = time.time() * 1000
                _save_last_runs(LAST_RUNS)

    except Exception as e:
        with RUNS_LOCK:
            run.status = "error"
            run.error = str(e)
            run.finished_at = time.time()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    log.info("=" * 60)
    log.info("EuroLeague Control Panel")
    log.info("=" * 60)
    log.info(f"ROOT:     {ROOT}")
    log.info(f"CONTROL:  {CONTROL}")
    log.info(f"URL:      http://{SERVER_HOST}:{SERVER_PORT_CONTROL}/")
    log.info("=" * 60)
    app.run(host=SERVER_HOST, port=SERVER_PORT_CONTROL, debug=False, threaded=True)