# ============================================================
# core/paths.py
# ------------------------------------------------------------
# ΟΛΑ τα paths του project σε ΕΝΑ σημείο.
# Κανένα hardcoded path πουθενά αλλού.
#
# Χρήση:
#     from core.paths import ROOT, DATA_RAW, APP_DATA_JS
# ============================================================

from __future__ import annotations
from pathlib import Path


# ---- ROOT ----
# Το core/ είναι ένα επίπεδο κάτω από τη ρίζα
ROOT: Path = Path(__file__).resolve().parents[1]


# ============================================================
# APP (server + static)
# ============================================================
APP           = ROOT / "app"
APP_HTML      = APP / "html"
APP_CSS       = APP / "css"
APP_JS        = APP / "js"
APP_JS_CONFIG = APP_JS / "config"
APP_JS_CORE   = APP_JS / "core"
APP_JS_DATA   = APP_JS / "data"
APP_JS_UI     = APP_JS / "ui"
APP_JS_UTILS  = APP_JS / "utils"
APP_JS_VIEWS  = APP_JS / "views"
APP_LOGOS     = APP / "logos"
APP_SERVER    = APP / "server.py"
APP_INDEX     = APP_HTML / "EuroLeague.html"


# ============================================================
# CONTROL (control panel server + static)
# ============================================================
CONTROL          = ROOT / "control"
CONTROL_HTML     = CONTROL / "html"
CONTROL_STATIC   = CONTROL / "static"
CONTROL_SERVER   = CONTROL / "server.py"
CONTROL_INDEX    = CONTROL_HTML / "control-center.html"


# ============================================================
# SCRIPTS
# ============================================================
SCRIPTS         = ROOT / "scripts"
SCRIPTS_FETCH   = SCRIPTS / "fetch"
SCRIPTS_TRAIN   = SCRIPTS / "train"
SCRIPTS_COMPUTE = SCRIPTS / "compute"
SCRIPTS_CONVERT = SCRIPTS / "convert"
SCRIPTS_VALIDATE= SCRIPTS / "validate"


# ============================================================
# CORE (self)
# ============================================================
CORE          = ROOT / "core"
CORE_OPTIMIZE = CORE / "optimize"


# ============================================================
# DATA
# ============================================================
DATA          = ROOT / "data"
DATA_RAW      = DATA / "raw"
DATA_PROC     = DATA / "processed"
DATA_MODELS   = DATA / "models"


# ============================================================
# DATA FILES — RAW (κατεβασμένα)
# ============================================================
F_FANTASY_DATA       = DATA_RAW / "fantasy_data.json"
F_COACHES            = DATA_RAW / "coaches.json"
F_INJURIES           = DATA_RAW / "injuries.json"
F_BS_CREDITS         = DATA_RAW / "basketstories_credits.json"
F_BS_STATS           = DATA_RAW / "basketstories_player_stats.json"
F_PLAYER_BIOS        = DATA_RAW / "player_bios.json"
F_PLAYER_HEIGHTS     = DATA_RAW / "player_heights.json"
F_TEAM_MAPPING       = DATA_RAW / "team_mapping.json"
F_GAMELOGS           = DATA_RAW / "gamelogs"        # φάκελος
F_BOXSCORES          = DATA_RAW / "boxscores"        # φάκελος


# ============================================================
# DATA FILES — PROCESSED (μετά από επεξεργασία)
# ============================================================
F_PREDICTIONS        = DATA_PROC / "player_predictions.json"
F_PREDICTIONS_META   = DATA_PROC / "model_metrics.json"
F_COACH_STATS        = DATA_PROC / "coach_stats.json"
F_DEFENSE            = DATA_PROC / "defensive_profiles.json"
F_BACKTEST           = DATA_PROC / "backtest_results.json"
F_FEATURE_ANALYSIS   = DATA_PROC / "feature_analysis.json"
F_HEIGHT_ANALYSIS    = DATA_PROC / "height_analysis.json"


# ============================================================
# DATA FILES — MODELS (trained)
# ============================================================
F_MODEL              = DATA_MODELS / "model.pkl"
F_MODEL_GB           = DATA_MODELS / "model_gb.pkl"
F_MODEL_RIDGE        = DATA_MODELS / "model_ridge.pkl"


# ============================================================
# LOGS
# ============================================================
LOGS         = ROOT / "logs"
LOGS_FETCH   = LOGS / "fetch"
LOGS_TRAIN   = LOGS / "train"
LOGS_CONVERT = LOGS / "convert"
LOGS_SERVER  = LOGS / "server"


# ============================================================
# OUTPUT
# ============================================================
OUTPUT              = ROOT / "output"
OUTPUT_REPORTS      = OUTPUT / "reports"
OUTPUT_EXPORTS      = OUTPUT / "exports"
OUTPUT_PRED_LOG     = OUTPUT_REPORTS / "predictions_log"


# ============================================================
# ROOT FILES
# ============================================================
GITIGNORE      = ROOT / ".gitignore"
REQUIREMENTS   = ROOT / "requirements.txt"
README         = ROOT / "README.md"


# ============================================================
# HELPERS
# ============================================================
def ensure_dirs() -> None:
    """Δημιουργεί όλους τους φακέλους αν λείπουν."""
    for p in [
        APP, APP_HTML, APP_CSS, APP_JS, APP_JS_CONFIG, APP_JS_CORE,
        APP_JS_DATA, APP_JS_UI, APP_JS_UTILS, APP_JS_VIEWS, APP_LOGOS,
        CONTROL, CONTROL_HTML, CONTROL_STATIC,
        SCRIPTS, SCRIPTS_FETCH, SCRIPTS_TRAIN, SCRIPTS_COMPUTE,
        SCRIPTS_CONVERT, SCRIPTS_VALIDATE,
        CORE, CORE_OPTIMIZE,
        DATA, DATA_RAW, DATA_PROC, DATA_MODELS,
        LOGS, LOGS_FETCH, LOGS_TRAIN, LOGS_CONVERT, LOGS_SERVER,
        OUTPUT, OUTPUT_REPORTS, OUTPUT_EXPORTS, OUTPUT_PRED_LOG,
    ]:
        p.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    ensure_dirs()
    print("ROOT:", ROOT)
    for name in ["APP", "CONTROL", "SCRIPTS", "CORE",
                 "DATA", "DATA_RAW", "DATA_PROC",
                 "LOGS", "OUTPUT"]:
        print(f"  {name:14s} = {globals()[name]}")
